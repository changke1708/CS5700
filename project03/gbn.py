import udt
import util
import config
import time
import collections
import threading
import _thread


# Go-Back-N reliable transport protocol.
class GoBackN:
  _N = 8
  # "msg_handler" is used to deliver messages to application layer
  # when it's ready.
  def __init__(self, local_ip, local_port,
               remote_ip, remote_port, msg_handler):
    self.network_layer = udt.NetworkLayer(local_ip, local_port,
                                          remote_ip, remote_port, self)
    self.msg_handler = msg_handler
    self.next_seq_number = 1
    self.base_seq_number = 1
    self.last_seq_number_to_be_sent = None
    self.base_seq_number_lock = threading.Lock()
    self.next_seq_number_lock = threading.Lock()
    self.last_ack_number = 0
    self.last_ack_number_lock = threading.Lock()
    self.timer = None
    self.timer_lock = threading.Lock()

  # "send" is called by application. Return true on success, false
  # otherwise.
  def send(self, msg):
    # TODO: impl protocol to send packet from application layer.
    # call self.network_layer.send() to send to network layer.
    msg_size = len(msg)
    bytes_sent = 0
    start = 0
    end = 0
    send_pkts = {}
    try:
        while True:
          with self.next_seq_number_lock:
            
            with self.base_seq_number_lock:
              base_seq_number = self.base_seq_number
            
            if self.next_seq_number < base_seq_number + self._N:
              if self.next_seq_number not in send_pkts:
                if bytes_sent < msg_size:
                  if msg_size - bytes_sent < config.MAX_MESSAGE_SIZE:
                    end = msg_size
                  else:
                    end += config.MAX_MESSAGE_SIZE

                  pkt = util.make_pkt(config.MSG_TYPE_DATA, self.next_seq_number, msg[start:end])
                  print("Saving pkt with seq_number: ", self.next_seq_number)
                  send_pkts[self.next_seq_number] = pkt
                  bytes_sent += (end - start)
                  start = end
                  if end == msg_size:
                    # we have reached end of message, track last seq number here
                    self.last_seq_number_to_be_sent = self.next_seq_number
                else:
                  if self.last_seq_number_to_be_sent is None:
                    # return once we have received the ack for the last seq number
                    return True

              if self.next_seq_number in send_pkts:
                self.network_layer.send(send_pkts[self.next_seq_number])
                
                with self.base_seq_number_lock:
                  base_seq_number = self.base_seq_number
                
                if self.next_seq_number == base_seq_number:
                  # start timer
                  with self.timer_lock:
                    if self.timer:
                      # if timer already exists, cancel and restart
                      self.timer.cancel()
                    self.timer = threading.Timer(config.TIMEOUT_MSEC/1000.0, self.reset_next_seq_num)
                    self.timer.start()
                    print("Started timer for pkt with seq_number: ", self.next_seq_number)

                self.next_seq_number += 1
    except:
      raise
      # return False
    return True

  def reset_next_seq_num(self):
    with self.base_seq_number_lock:
      base_seq_number = self.base_seq_number
    
    with self.next_seq_number_lock:
      self.next_seq_number = base_seq_number

  # "handler" to be called by network layer when packet is ready.
  def handle_arrival_msg(self):
    # TODO: impl protocol to handle arrived packet from network layer.
    # call self.msg_handler() to deliver to application layer.
    msg = self.network_layer.recv()
    
    if util.is_corrupt_pkt(msg):
      return

    seq_number = util.pkt_seq_number(msg)
    if util.is_ack_pkt(msg):
      with self.base_seq_number_lock:
        if seq_number >= self.base_seq_number and seq_number < self.base_seq_number + self._N:
          # slide the window by 1
          self.base_seq_number = seq_number + 1
          if seq_number == self.last_seq_number_to_be_sent:
            # if this is the last seq number of the stream, set it to None
            self.last_seq_number_to_be_sent = None
          
          # restart timer
          with self.timer_lock:
            if self.timer:
              self.timer.cancel()
              self.timer = threading.Timer(config.TIMEOUT_MSEC/1000.0, self.reset_next_seq_num)
              self.timer.start()
    else:
      received_msg = False
      with self.last_ack_number_lock:
        if seq_number == self.last_ack_number + 1:
          # if we receive a data pkt with next seq number, accept. otherwise, discard and send ack with last ack number
          received_msg = True
          self.last_ack_number = seq_number
        else:
          seq_number = self.last_ack_number
      
      if received_msg:
        self.msg_handler(util.pkt_data(msg))
      
      # send ack pkt for accepted/discarded pkts with last ack number
      ack_pkt = util.make_pkt(config.MSG_TYPE_ACK, seq_number)
      self.network_layer.send(ack_pkt)

  # Cleanup resources.
  def shutdown(self):
    # TODO: cleanup anything else you may have when implementing this
    # class.
    self.network_layer.shutdown()
