import config
import dummy
import gbn
import ss
import threading

MAX_INT16 = 1 << 16

def _get_transport_layer_by_name(name, local_ip, local_port, 
                                 remote_ip, remote_port, msg_handler):
  assert name == 'dummy' or name == 'ss' or name == 'gbn'
  if name == 'dummy':
    return dummy.DummyTransportLayer(local_ip, local_port,
                                     remote_ip, remote_port, msg_handler)
  if name == 'ss':
    return ss.StopAndWait(local_ip, local_port,
                          remote_ip, remote_port, msg_handler)
  if name == 'gbn':
    return gbn.GoBackN(local_ip, local_port,
                       remote_ip, remote_port, msg_handler)

# Factory method to construct transport layer.
def get_transport_layer(sender_or_receiver,
                        transport_layer_name,
                        msg_handler):
  assert sender_or_receiver == 'sender' or sender_or_receiver == 'receiver'
  if sender_or_receiver == 'sender':
    return _get_transport_layer_by_name(transport_layer_name,
                                        config.SENDER_IP_ADDRESS,
                                        config.SENDER_LISTEN_PORT,
                                        config.RECEIVER_IP_ADDRESS,
                                        config.RECEIVER_LISTEN_PORT,
                                        msg_handler)
  if sender_or_receiver == 'receiver':
    return _get_transport_layer_by_name(transport_layer_name,
                                        config.RECEIVER_IP_ADDRESS,
                                        config.RECEIVER_LISTEN_PORT,
                                        config.SENDER_IP_ADDRESS,
                                        config.SENDER_LISTEN_PORT,
                                        msg_handler)

def ones_complement_addition(n1, n2):
	result = int(n1) + int(n2)
	return result if result < MAX_INT16 else (int) ((result + 1) & 0xffff)

# def ones_complement_addition(n1, n2):
#       result = int(n1) + int(n2)
#       if result < MAX_INT16:
#           return result
#       else:
#           return (result & 0xffff) + (result & 0xff0000) >> 16

def compute_checksum(msg_type, seq_number, data = None, checksum = 0):
	checksum = ones_complement_addition(checksum, msg_type)
	checksum = ones_complement_addition(checksum, seq_number)
	if data is not None:
		length = len(data)
		data_bytearray = bytearray(data)
		# pad data with trailing 0s if needed
		if length % 2 != 0:
			data_bytearray.append(0)
			length += 1
		
		i = 0
		while i < length/2:
			x = data_bytearray[i] << 8 | data_bytearray[i + 1]
			checksum = ones_complement_addition(checksum, x & 0xffff)
			i += 2
	return ~checksum & 0xffff



def make_pkt(msg_type, seq_number, data = None):
    # create a rdt packet from udt payload
    pkt = bytearray()
    pkt.extend(msg_type.to_bytes(2, byteorder = 'big'))
    pkt.extend(seq_number.to_bytes(2, byteorder = 'big'))
    checksum = compute_checksum(msg_type, seq_number, data, 0)
    # checksum = ~checksum & 0xffff
    pkt.extend(checksum.to_bytes(2, byteorder = 'big'))
    if data is not None:
    	pkt.extend(data)
    return bytes(pkt)

def pkt_type(pkt):
	return int.from_bytes(pkt[0:2], byteorder = 'big')

def is_ack_pkt(pkt):
	return pkt_type(pkt) == config.MSG_TYPE_ACK

def pkt_seq_number(pkt):
	return int.from_bytes(pkt[2:4], byteorder = 'big')

def pkt_checksum(pkt):
	return int.from_bytes(pkt[4:6], byteorder = 'big')

def pkt_data(pkt):
	if len(pkt) > 6:
		return pkt[6:]
	else:
		return None

def is_corrupt_pkt(pkt):
	msg_type = pkt_type(pkt)
	seq_number = pkt_seq_number(pkt)
	checksum = pkt_checksum(pkt)
	data = pkt_data(pkt)
	chksum = compute_checksum(msg_type, seq_number, data, checksum)
	return chksum != 0

# Convenient class to run a function periodically in a separate
# thread.
class PeriodicClosure:
  def __init__(self, handler, interval_sec):
    self._handler = handler
    self._interval_sec = interval_sec
    self._lock = threading.Lock()
    self._timer = None

  def _timeout_handler(self):
    with self._lock:
      self._handler()
      self.start()

  def start(self):
    self._timer = threading.Timer(self._interval_sec, self._timeout_handler)
    self._timer.start()

  def stop(self):
    with self._lock:
      if self._timer:
        self._timer.cancel()	