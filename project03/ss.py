import udt
import util
import config
import time
import collections
import threading


# Stop-And-Wait reliable transport protocol.
class StopAndWait:
  # "msg_handler" is used to deliver messages to application layer
  # when it's ready.
  def __init__(self, local_ip, local_port, 
               remote_ip, remote_port, msg_handler):
    self.network_layer = udt.NetworkLayer(local_ip, local_port,
                                          remote_ip, remote_port, self)
    self.msg_handler = msg_handler
    self.msg_buffer = collections.deque(maxlen = 8)
    self.buffer_lock = threading.Lock()
    self.send_seq_number = 0
    self.recv_seq_number = 0
    self.send_seq_number_lock = threading.Lock()
    self.recv_seq_number_lock = threading.Lock()

  # "send" is called by application. Return true on success, false
  # otherwise.
  def send(self, msg):
    # TODO: impl protocol to send packet from application layer.
    # call self.network_layer.send() to send to network layer.
    msg_size = len(msg)
    bytes_sent = 0
    start = 0
    end = 0
    try:
      while bytes_sent < msg_size:
        if msg_size - bytes_sent < config.MAX_MESSAGE_SIZE:
          end = msg_size
        else:
          end += config.MAX_MESSAGE_SIZE
        
        with self.send_seq_number_lock:
          seq_number = self.send_seq_number
        pkt = util.make_pkt(config.MSG_TYPE_DATA, seq_number, msg[start:end])
        ack_pkt = None
        while ack_pkt is None:
          print("Sending pkt: ", pkt)
          self.network_layer.send(pkt)
          ack_pkt = self.start_timer_and_wait_for_ack(seq_number)
        
        bytes_sent += (end - start)
        start = end
        with self.send_seq_number_lock:
          self.send_seq_number ^= 1
    except:
      raise
      # return False
    return True

  # "handler" to be called by network layer when packet is ready.
  def handle_arrival_msg(self):
    msg = self.network_layer.recv()
    print("Received packet: ", msg)
    
    if util.is_corrupt_pkt(msg):
      print("Received corrupt packet: ", msg)
      return

    received_msg = False
    if util.is_ack_pkt(msg):
      while not received_msg:
        with self.buffer_lock:
          if len(self.msg_buffer) < self.msg_buffer.maxlen:
            self.msg_buffer.append(msg)
            received_msg = True
    else:
      seq_number = util.pkt_seq_number(msg)
      print("Received seq number: ", seq_number)
      with self.recv_seq_number_lock:
        print("Expected seq number: ", self.recv_seq_number)
        if seq_number == self.recv_seq_number:
          received_msg = True
          self.recv_seq_number ^= 1
      
      if received_msg:
        self.msg_handler(util.pkt_data(msg))
      
      ack_pkt = util.make_pkt(config.MSG_TYPE_ACK, seq_number)
      self.network_layer.send(ack_pkt)

    # TODO: impl protocol to handle arrived packet from network layer.
    # call self.msg_handler() to deliver to application layer.
    
  def start_timer_and_wait_for_ack(self, seq_number):
    timer_expiry = time.time() + config.TIMEOUT_MSEC/1000.0
    while time.time() < timer_expiry:
      time.sleep(0.001)
      with self.buffer_lock:
        if len(self.msg_buffer) > 0 and util.pkt_seq_number(self.msg_buffer[0]) == seq_number:
          return self.msg_buffer.popleft()
    return None


  # Cleanup resources.
  def shutdown(self):
    # TODO: cleanup anything else you may have when implementing this
    # class.
    self.network_layer.shutdown()
