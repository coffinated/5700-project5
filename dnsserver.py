#! /usr/bin/env python3

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
        self.flag = 0
        self.qcount = 0
        self.acount = 0
        
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
        packet = DNSRecord.parse(data)
        if str(packet.q.qtype) == NS:
            response = construct_answer(ip, packet)
            socket.sendto(response, DEFAULT)
        else:
            pass


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
