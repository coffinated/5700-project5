#! /usr/bin/env python3

import threading
import traceback
import random
import sys
import socketserver
import sys
import socket
import struct
import argparse
import utility

##https://datatracker.ietf.org/doc/html/rfc1035


LOCATOR = utility.LocationHelper()

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
        self.flag = 0x8180
        packet = struct.pack('!HHHHHH',self.id,self.flag,self.qcount,self.acount,self.nscount,self.arcount)
        packet += self.query.assemble_question()
        return packet

    
    def unpack_dns_packet(self,data):
        [self.id,
        self.flag,
        self.qcount,
        self.account,
        self.nscount,
        self.arcount] = struct.unpack("!HHHHHH", data[:12])
        self.query = DnsQuery()
        self.query.unpack_dns_query(data[12:])
        self.answer = None
        
    def print_DNS_packet(self):
        print("DNS_Packet : ")
        print("id : ", self.id)
        print("flags : ", self.flag)
        print("qcount : ", self.qcount)
        print("account : ", self.account)
        print("nscount : ", self.nscount)
        print("arcount : ", self.arcount)
        print("query : ")
        self.query.print_DNS_query()
class DnsQuery:
    
    def __init__(self):
        self.qname = ''
        self.qtype = 1
        self.qclass = 0
        self.data = ''

    def unpack_dns_query(self, input_data):

        hostname = []
        size = 0
        index = 0
        
        
        self.data = input_data
        [self.qtype,
        self.qclass] = struct.unpack('>HH', input_data[-4:])
        qname = input_data[:-4]
 
        while True:
  
            size = qname[index]
                
            if size > 50:
                size = 9
                hostname.append(qname[index:index+size])
                index += size
                continue
            # print "length : ", length
            if size == 0:
                break


            index += 1
            hostname.append(qname[index:index+size])
            index += size
        self.qname = b'.'.join(hostname)
        
    def assemble_question(self):
        domainname = self.qname.split(b'.')
        qnamelist = []
        for name in domainname:

            qnamelist.append(chr(len(name)).encode()+name)
        qname = b''.join(qnamelist) +b'\x00'

        return qname+ struct.pack('>HH',self.qtype,self.qclass)
        
    def print_DNS_query(self):
        print("DNS_query : ")
        print("qtype : ", self.qtype)
        print("qclass : ", self.qclass)
        print("qname : ", self.qname)



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
        DNS_answer = struct.pack('>HHHLH4s', self.aname, self.atype, self.aclass,
                                  self.ttl, self.len, socket.inet_aton(self.data))
        print(type(DNS_answer))
        return DNS_answer
        
    def print_DNS_answer(self):
        print("DNS_answer : ")
        print("aname : ", self.aname)
        print("atype : ", self.atype)
        print("aclass : ", self.aclass)
        print("ttl : ", self.ttl)
        print("data : ", self.data)
        print("length : ", self.len)

    
client_mappings = {}





class DNS_Request_Handler(socketserver.BaseRequestHandler):
    def handle(self):

        global port
        data = self.request[0] ## or self.request[0].strip
        socket = self.request[1]
        dnspack = DnsPacket()
        dnspack.unpack_dns_packet(data)
        dnspack.print_DNS_packet()
        if LOCATOR.is_private(self.client_address[0]):
            
            if self.client_address[0] not in client_mappings:
                client_mappings[self.client_address[0]] = '50.116.41.109'
            data = dnspack.create_dns_answer(dnspack.query.qname,'50.116.41.109')
            print('------add answer')
            print(data)
            socket.sendto(data,self.client_address)
        else:
            if self.client_address[0] in client_mappings:
                data = dnspack.create_dns_answer(dnspack.query.qname, client_mappings[self.client_address[0]])
                socket.sendto(data,self.client_address)

            else:
                best_replica = LOCATOR.find_closest_server(self.client_address[0])
                client_mappings[self.client_address[0]] = best_replica
                data = dnspack.create_dns_answer(dnspack.query.qname,best_replica)
                socket.sendto(data,self.client_address)



                              
class DNS_Server(socketserver.UDPServer):
    def __init__(self, hostname, port,server_address, handler_class=DNS_Request_Handler):
        self.hostname = hostname
        self.port = port
        self.ip = self.get_ipaddr()
        socketserver.UDPServer.__init__(self, server_address, handler_class)
        ## i dont know if binding is needed here

    
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
    thread = threading.Thread(target = server.serve_forever)
    thread.daemon = True
    thread.start()
    
main()
