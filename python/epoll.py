from socket import socket as so, SOL_SOCKET, SO_REUSEADDR, SHUT_RDWR
from select import epoll, EPOLLIN, EPOLLHUP

sock = so()
sock.bind(('', 1337))
sock.listen(4)
sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
mainFid = sock.fileno()

polly = epoll()
polly.register(mainFid, EPOLLIN)

socks = {}

while 1:
        for fid, eid in polly.poll(1):
                print(eid)
                if fid == mainFid:
                        ns, na = sock.accept()
                        polly.register(ns.fileno(), EPOLLIN|EPOLLHUP)
                        print(na[0],'connected')
                        socks[ns.fileno()] = {'sock' : ns, 'addr' : na}
                elif fid in socks and eid == EPOLLIN:
                        data = socks[fid]['sock'].recv(8192)
                        if data == b'':
                                # We don't allow empty data, mostly because it
                                # is the only way we can detect a disconnect with epoll.
                                socks[fid]['sock'].shutdown(SHUT_RDWR)
                        else:
                                print(socks[fid]['addr'][0], ':]', data)
                elif fid in socks and eid == 17: #SHUT
                        # We closed the connection
                        print('We closed a connection')
                        polly.unregister(fid)
                        socks[fid]['sock'].close()
                        del(socks[fid])

for key, vals in socks.items():
        polly.unregister(key)
        vals['sock'].close()

polly.unregister(mainFid)
sock.close()
