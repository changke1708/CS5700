import socket
import _thread
import time
import urllib.parse
# from ProxyServer.Assignment02.functions import *




# Get host name, IP address, port number
hostName = socket.gethostname()
hostIp = socket.gethostbyname(hostName)
hostPort = 8383

# Make a TCP socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind the socket to server
s.bind((hostIp, hostPort))
print("Server started at: " + hostIp + "\nThe port is: " + str(hostPort))

# Listen allow 5 pending connects
s.listen(5)


bufsize = 1024
# dict, key is tuple
cache = {}

# Current time on the server.
def now():
    return time.ctime(time.time())



# Get the first line of request data
def getRequestLine(data):
	# decode binary to string
	dataList = data.decode().split("\r\n")
	requestLine = dataList[0];
	return requestLine

# Given the first line of request and return the method, host, path, protocol as tuple
def getRequestInfo(header):
	header = header.split(" ")
	method = header[0]
	url = urllib.parse.urlparse(header[1])
	path = url.path
	if path == "":
		path = "/"
	host = url.netloc
	protocol = header[2]
	return (method, host, path, protocol)

# Given request data and first line of that data, return the request to real server
def buildForwardRequest(data, requestInfo):
	dataList = data.decode().split("\r\n")
	# requestInfo ("GET", "www.google.com", "/", "HTTP1.1")
	# new request header "GET / HTTP/1.1"
	firstLine = requestInfo[0] + " " + requestInfo[2] + " " + requestInfo[3]
	dataList[0] = firstLine

	isFound = False
	closeConnection = "Connection: close"
	print("Data list: ", dataList)
	# Connection: keep alive
	for index, line in enumerate(dataList):
		if "Connection" in line:
			isFound = True
			print("index ", index, "line ", line)
			dataList[index] = closeConnection
			break;
	if not isFound:
		dataList.insert(-2, closeConnection)


	# Insert line seperator into each pair in data
	forwardRequest = ("\r\n").join(dataList)
	return forwardRequest

def handler(conn):
	rawData = conn.recv(bufsize)
	# Examine the first line
	requestLine = getRequestLine(rawData)
	# ("GET", "www.google.com", "/", "HTTP/1.1")
	requestInfo = getRequestInfo(requestLine)
	method, host, path, protocol = requestInfo

	response = b""
	if method != "GET":
		conn.sendall(b"HTTP/1.1 400 Bad request\r\nContent-Type:text/html \r\n\r\n")
		conn.close()
		return

	if requestInfo in cache:
		# Get a tuple from dict
		response = cache[requestInfo]
		print("Get response from proxy cache: ", response)
	else:
		print("Get response from real server.")
		# Make TCP connection to the real server
		newSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# "www.google.com" 80
		newSocket.connect((host, 80))
		print("Request info: ", requestInfo)
		forwardRequest = buildForwardRequest(rawData, requestInfo)
		# Send over an HTTP request
		newSocket.send(forwardRequest.encode())
		while True:
			data = newSocket.recv(bufsize)
			if not data: break
			response += data
			print("data ", data)

		cache[requestInfo] = response
		# Close the TCP connection to the server
		newSocket.close()

	# Send the server's response back to client
	conn.sendall(response)
	#Close the connection socket to client
	conn.close()
	return	

while True:
	conn, addr = s.accept()
	print("Server connected by: ", addr, "at ", now())
	_thread.start_new(handler, (conn,))

