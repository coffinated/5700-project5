
import sys
import socketserver
import sys
import socket
import struct
import argparse
import utility
import dnslib
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
        packet = self.construct_dns_query(name)
        packet += self.answer.create_answer(ip)
        return packet

    def create_query(self,name):
        self.account = 1
        self.flags = 0x8180
        packet = pack('!HHHHHH',self.id,self.flag,self.qcount,self.acount,self.nscount,self.ar)
        packet += self.query.data
        return packet

    
    def unpack_dns_packet(self,raw_packet):
        [self.id,
        self.flags,
        self.qcount,
        self.account,
        self.nscount,
        self.arcount] = unpack("!HHHHHH", raw_packet[:12])
        self.query = DNS_query()
        self.query.re_construct_dns_query(raw_packet[12:])
        self.answer = None

class DnsQuery:
    
    def __init__(self):
        self.qname = ''
        self.qtype = 1
        self.qclass = 0
        self.data = ''

    def re_construct_dns_query(self, raw_data):
        self.data = raw_data
        [self.qtype,
        self.qclass] = unpack('>HH', raw_data[-4:])
        self.qtype = 1
        qname = raw_data[:-4]
 
        length = 0
        index = 0
        name = []
        while True:
  
            length = ord(qname[index])
            if length > 50:
                length = 9
                name.append(qname[index:index+length])
                index += length
                continue
            if length == 0:
                break
            index += 1
            name.append(qname[index:index+length])
            index += length
        self.qname = '.'.join(name)


    def re_construct_dns_query_2(self, raw_data):
        
        length = -1
        index = 0
        name = []
        while length != 0:
            length = ord(raw_data[index])
            if length == 99:
                length = 9
                part = raw_data[index:index+length]
                name.append(part)
                index += length
                continue
            index += 1
            part = raw_data[index:index+length]
            name.append(part)
            index += length
        self.data = raw_data
        self.qtype = unpack("!H",raw_data[index:index+2])[0]
        self.qclass = unpack("!H", raw_data[index+2:index+4])[0]
        self.qname = '.'.join(name)

    def construct_dns_query(self, domain_name):

        dns_query = ''.join(chr(len(x)) + x for x in domain_name.split('.'))
        dns_query += '\x00'

        packet = dns_query + pack('!HH', self.qtype, self.qclass)
        print(packet)
        return packet

class DNS_answer():
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

def construct_answer(ip, packet):
    aname = 0xc00c
    atype = 0x0001
    aclass = 0x0001
    ttl = 50
    data = socket.inet_aton(ip)
    packet.add_answer(RR(rname=qname, rtype=atype,
                      rclass=aclass, ttl=50, rdata=data))
    return packet


class DNS_Request_Handler(socketserver.BaseRequestHandler):
    def handle(self):

        global port
        data = self.request[0].strip()
        socket = self.request[1]
        dnspack = DnsPacket()
        dnspack.unpack_dns_packet(data)
        
            
            

class DNS_Server(socketserver.UDPServer):
    def __init__(self, hostname, port,server_address, handler_class=DNS_Request_Handler):
        self.hostname = hostname
        self.port = port
        self.client_locations = {}
        self.ip = self.get_ipaddr()
        self.socket = -1
        socketserver.UDPServer.__init__(self, server_address, handler_class)

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.my_ip,self.port))
        except:
            sys.exit()
        socketserver.UDPServer.__init__(self, server_address, handler_class)
    
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

    server = DNS_Server(hostname, ('', port))

    server.serve_forever()


main()
