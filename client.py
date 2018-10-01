
import socket
import struct

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_ip = '35.196.0.161'
server_port = 8181
s.connect((server_ip, server_port))
print('Connected to server ', server_ip, ':', server_port)


def receiveMsg(strs):
	i = 2
	res = '';
	Len = strs[0:i]
	numOfLen = struct.unpack('!h', Len)[0];
	print('Number of answers is ', numOfLen);
	while(numOfLen > 0):
		size = struct.unpack('!h',strs[i : i + 2])[0];
		print('Length of answer is ', size)
		expression = strs[i + 2 : i + 2 + size];
		result = expression.decode('utf-8');
		print('Current result is ', result);
		numOfLen -= 1
		i += 2 + size

	

strs = [2,4, "5+17",6, "9+21/3"]
List = []
i = 0;
while(i < len(strs)):

	if(type(strs[i]) == str):
		str_byte = strs[i].encode('utf-8');
		List.append(str_byte);	
	else:
		# big endian
		int_byte = struct.pack('!h', strs[i]);		
		List.append(int_byte);
		
	i += 1

List.append(('\n').encode('utf-8'))
i = 0;


bufsize = 16
size = 0
i = 0;
data = b'';

while i < len(List):
	while size < 16:
		if i == len(List):
			break
		data += List[i]
		size += len(List[i])
		i += 1

	cur = data[0:16]
	s.sendall(cur)
	data = data[16:]
	size -= 16
	print('Client sent:', cur)
 
data = s.recv(bufsize)
print('Rreceive data: ', data);
receiveMsg(data)
s.close()
  
