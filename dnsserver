import threading
import traceback

import sys
import socketserver
import sys
import socket
import struct
import argparse
import utility
from dnslib import *
##https://datatracker.ietf.org/doc/html/rfc1035


class DnsPacket:
    def __init__(self):
        self.id = random.randint(0,65535)
        self.flag = 0
        self.qcount = 0
        self.acount = 0
        self.nscount = 0
        self.arcount =0
        self.query = DnsQuery()
        self.answer = DnsAnswer()
        
    def create_dns_answer(self, name,ip):
        self.answer = DnsAnswer()
        packet = self.create_query(name)
        packet += self.answer.create_answer(ip)
        return packet

    def create_query(self,name):
        self.account = 1
        self.flags = 0x8180
        packet = pack('!HHHHHH',self.id,self.flag,self.qcount,self.acount,self.nscount,self.ar)
        packet += self.query.data
        return packet

    
    def unpack_dns_packet(self,data):
        [self.id,
        self.flags,
        self.qcount,
        self.account,
        self.nscount,
        self.arcount] = unpack("!HHHHHH", data[:12])
        self.query = DNSquery()
        self.query.unpack_dns_query(data[12:])
        self.answer = None

class DnsQuery:
    
    def __init__(self):
        self.qname = ''
        self.qtype = 1
        self.qclass = 0
        self.data = ''

    def unpack_dns_query(self, raw_data):
        self.data = raw_data
        [self.qtype,
        self.qclass] = unpack('>HH', raw_data[-4:])
        qname = raw_data[:-4]
 
        length = 0
        index = 0
        name = []
        while True:
  
            size = ord(qname[index])
                
            if size == 0:
                break


            index += 1
            name.append(qname[index:index+length])
            index += length
        self.qname = '.'.join(name)






class DnsAnswer():
    def __init__(self):
        self.aname = 0
        self.atype = 0
        self.aclass = 0
        self.ttl = 0
        self.data = ''
        self.len = 0

    def create_answer(self, ip):
        self.aname = 0xc00c
        self.atype = 0x0001
        self.aclass = 0x0001
        self.ttl = 40
        self.data = ip
        self.len = 4
        DNS_answer = pack('>HHHLH4s', self.aname, self.atype, self.aclass,
                                  self.ttl, self.len, socket.inet_aton(self.data))

        return DNS_answer

    
client_mappings = {}



class DomainName(str):
    def __getattr__(self, item):
        return DomainName(item + '.' + self)

##dnslib usage https://gist.github.com/pklaus/b5a7876d4d2cf7271873
D = DomainName('example.com.')
IP = '127.0.0.1'
TTL = 60 * 5

soa_record = SOA(
    mname=D.ns1,  # primary name server
    rname=D.andrei,  # email of the domain administrator
    times=(
        201307231,  # serial number
        60 * 60 * 1,  # refresh
        60 * 60 * 3,  # retry
        60 * 60 * 24,  # expire
        60 * 60 * 1,  # minimum
    )
)
ns_records = [NS(D.ns1), NS(D.ns2)]
records = {
    D: [A(IP), AAAA((0,) * 16), MX(D.mail), soa_record] + ns_records,
    D.ns1: [A(IP)],  # MX and NS records must never point to a CNAME alias (RFC 2181 section 10.3)
    D.ns2: [A(IP)],
    D.mail: [A(IP)],
    D.andrei: [CNAME(D)],
}

## not sure if needed; dnslib implementation
def dns_response(data):
    request = DNSRecord.parse(data)

    print(request)

    reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=1), q=request.q)

    qname = request.q.qname
    qn = str(qname)
    qtype = request.q.qtype
    qt = QTYPE[qtype]

    if qn == D or qn.endswith('.' + D):

        for name, rrs in records.items():
            if name == qn:
                for rdata in rrs:
                    rqt = rdata.__class__.__name__
                    if qt in ['*', rqt]:
                        reply.add_answer(RR(rname=qname, rtype=getattr(QTYPE, rqt), rclass=1, ttl=TTL, rdata=rdata))

        for rdata in ns_records:
            reply.add_ar(RR(rname=D, rtype=QTYPE.NS, rclass=1, ttl=TTL, rdata=rdata))

        reply.add_auth(RR(rname=D, rtype=QTYPE.SOA, rclass=1, ttl=TTL, rdata=soa_record))

    print("---- Reply:\n", reply)

    return reply.pack()



class DNS_Request_Handler(socketserver.BaseRequestHandler):
    def handle(self):

        global port
        data = self.request[0] ## or self.request[0].strip
        socket = self.request[1]
        dnspack = DnsPacket()
        dnspack.unpack_dns_packet(data)
        
        if(dnspack.query.qtype ==1):
            if self.client_address[0] in client_mappings:
                data = dnspack.create_dns_answer(dnspack.query.qname, client_mappings[self.client_address[0]])
                socket.sendto(data,self.client_address)

            else:
                loc = utility.get_location(self.client_address[0])
                loc_float = [float(loc[0]), float(loc[1])]
                best_replica = find_cloest_server(loc_float)
                client_mapping[self.client_address[0]] = best_replica
                data = dnspack.create_dns_answer(dnspack.query.qname,best_replica)
                socket.sendto(data,self.client.address)



                              
class DNS_Server(socketserver.UDPServer):
    def __init__(self, hostname, port,server_address, handler_class=DNS_Request_Handler):
        self.hostname = hostname
        self.port = port
        self.ip = self.get_ipaddr()
        socketserver.UDPServer.__init__(self, server_address, handler_class)
        ## i dont know if binding is needed here
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.my_ip,self.port))
        except:
            sys.exit()
    
    def get_ipaddr(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('cs5700cdnproject.ccs.neu.edu', 80)) 
        ip = s.getsockname()[0]
        s.close()
        return ip


def main():
    parser = argparse.ArgumentParser(description='Start HTTP replica server using specified local'
                                     ' port and origin server')
    parser.add_argument('-p', '--port', type=int, required=True)
    parser.add_argument('-n', '--hostname', required=True, type=str)
    args = parser.parse_args()
    port = args.port
    hostname = args.hostname

    server = DNS_Server(hostname, port,('',port))
    
    server.serve_forever()
    thread = threading.Thread(target = server.server.forever)
    thread.daemon = True
    thread.start()
    
main()
