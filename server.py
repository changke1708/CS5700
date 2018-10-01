import socket
import time
import _thread
import struct

host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
host_port = 8181

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.bind((host_ip, host_port))

s.listen(10);

print('\nServer started. Waiting for connection...\n')

# Algo for calculation without parenthesis using stack
def calculate(s):  
    def update(op, num):
        if op == '+':
            stack.append(num)
        elif op == '-':
            stack.append(-num)
        elif op == '*':
            stack.append(stack.pop() * num)
        elif op == '/':
            stack.append(stack.pop() // num)
    
    stack = []
    num, op = 0, '+'
    for i in range(len(s)):
        if s[i].isdigit():
            num = num * 10 + int(s[i])
        elif s[i] in ['+', '-', '*', '/']:
            update(op, num)
            num, op = 0, s[i]
    update(op, num)
    return str(sum(stack))

#  Axillary function to call rec multiple times
def recvMsg(conn, bufsize):
    data = b''
    while True:
        part = conn.recv(bufsize)
        data += part
        if len(part) < bufsize:
            break
    return data

def getResult(data):
    result = b''
    numOfExpression = struct.unpack('>h', data[0: 2])[0]
    position = 2
    result += struct.pack('>h', numOfExpression)
    for i in range(0, numOfExpression):
        lenOfExpression = struct.unpack('>h', data[position: position + 2])[0]
        position += 2
        expression = data[position: position + lenOfExpression].decode('utf-8')
        position += lenOfExpression
        ans = calculate(expression)
        print(expression + '=' + ans)
        result += struct.pack('>h', len(ans))
        result += ans.encode('utf-8')
    return result

def sendResult(conn, result, bufsize):
    position = 0
    end = len(result)
    while end > position:
        if position + bufsize > end:
            conn.sendall(result[position: end])
        else: conn.sendall(result[position: position + 16])
        position += 16

def handler(conn):
    bufsize = 16
    data = recvMsg(conn, bufsize)
    result = getResult(data)
    sendResult(conn, result, bufsize)
    conn.close()    

# Current System Time
def now():
    return time.ctime(time.time())


while True:
    conn, addr = s.accept()
    print('Server connected by', addr,'at', now())
    _thread.start_new(handler, (conn,))