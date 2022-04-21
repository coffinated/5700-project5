#! /usr/bin/env python3

import sys
import socketserver
import sys
import socket
import struct
import argparse
from dnslib import *


DEFAULT = '50.116.41.109'


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
            socket.sendto(response, self.client_address)
        else:
            pass


class DNS_Server(socketserver.UDPServer):
    def __init__(self, hostname, server_address, handler_class=DNS_Request_Handler):
        self.hostname = hostname
        socketserver.UDPServer.__init__(self, server_address, handler_class)


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
