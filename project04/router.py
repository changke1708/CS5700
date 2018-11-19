import os.path
import socket
import table
import threading
import util
import graph
import collections

_CONFIG_UPDATE_INTERVAL_SEC = 5

_MAX_UPDATE_MSG_SIZE = 1024
_BASE_ID = 8000

def _ToPort(router_id):
  return _BASE_ID + router_id

def _ToRouterId(port):
  return port - _BASE_ID


class Router:
  def __init__(self, config_filename):
    # ForwardingTable has 3 columns (DestinationId,NextHop,Cost). It's
    # threadsafe.
    self._forwarding_table = table.ForwardingTable()
    # Config file has router_id, neighbors, and link cost to reach
    # them.
    self._config_filename = config_filename
    self._router_id = None
    # Socket used to send/recv update messages (using UDP).
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self._msg_queue = collections.deque(maxlen = 32)
    self._recv_thread = threading.Thread(target = self.read_socket_msgs_from_neighbours)


  def start(self):
    # Start a periodic closure to update config.
    self._config_updater = util.PeriodicClosure(
        self.load_config, _CONFIG_UPDATE_INTERVAL_SEC)
    self._config_updater.start()
    # TODO: init and start other threads.
    self._running = True
    self._recv_thread.start()
    while True: pass


  def stop(self):
    if self._config_updater:
      self._config_updater.stop()
    # TODO: clean up other threads.
    self._running = False
    self._recv_thread.join(1)

  def read_socket_msgs_from_neighbours(self) :
    buf_size = 4096
    while self._running:
      (data, address) = self._socket.recvfrom(buf_size)
      (ip, port) = address
      count = int.from_bytes(data[0:2], byteorder = 'big')
      i = 0
      while i < count:
        offset = 4 * i + 2
        dest_router_id = int.from_bytes(data[offset: offset + 2], byteorder = 'big')
        offset += 2
        cost = int.from_bytes(data[offset: offset + 2], byteorder = 'big')
        self._msg_queue.append((_ToRouterId(port), dest_router_id, cost))
        i += 1    
  

  def send_out_update_message(self, entries):
    msg = bytearray()
    entry_count = len(entries)
    msg.extend(entry_count.to_bytes(2, byteorder = 'big'))
    for (dest, next_hop, cost) in entries:
      msg.extend(dest.to_bytes(2, byteorder = 'big'))
      msg.extend(cost.to_bytes(2, byteorder = 'big'))

    for (dest, next_hop, cost) in entries:
      print("Sending update msg to router id: ", dest)
      self._socket.sendto(msg, ('localhost', _ToPort(dest)))


  def load_config(self):
    assert os.path.isfile(self._config_filename)
    with open(self._config_filename, 'r') as f:
      router_id = int(f.readline().strip())
      # Only set router_id when first initialize.
      if not self._router_id:
        self._socket.bind(('localhost', _ToPort(router_id)))
        self._router_id = router_id
      # TODO: read and update neighbor link cost info.
  
      lines = f.readlines()
      router_graph = graph.Graph(len(lines) + 1)
      for line in lines:
        dest, cost = line.strip().split(",")
        router_graph.add_edge(self._router_id, dest, cost)

      while len(self._msg_queue) > 0:
        (src, dest, cost) = self._msg_queue.popleft()
        router_graph.add_edge(src, dest, cost)

      entries = router_graph.BellmanFord(self._router_id)
      # Update forwarding table
      self._forwarding_table.reset(entries)
      print("Table snapshot: ")
      print(self._forwarding_table.snapshot())
      self.send_out_update_message(entries)    