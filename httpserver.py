#! /usr/bin/env python3

'''
This file runs the HTTP service on the replica nodes for project 5.
'''

import argparse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.client import HTTPConnection, HTTPException
from sys import getsizeof
from csv import reader
from time import time
from urllib.parse import quote

ORIGIN: HTTPConnection
# TODO: get address dynamically since we'll want to upload same code to all replicas
ADDRESS = '50.116.41.109'
PORT = 40010
CACHE = {}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/grading/beacon':
            self.send_response(204)
            self.end_headers()
        else:
            if CACHE.get(self.path):
                status = 200
                content = CACHE[self.path]
                headers = [('Content-Type', 'text/html'), ('Content-Length', str(len(content)))]
            else:
                ORIGIN.request('GET', self.path)
                res = ORIGIN.getresponse()
                status = res.status
                content = res.read()
                headers = res.getheaders()
            
            self.send_response(status)
            for each in headers:
                self.send_header(each[0], each[1])
            self.end_headers()
            self.wfile.write(content)


def warm_cache():
    global CACHE

    print('Populating cache!')

    start = time()
    n = 0

    with open('pageviews.csv', newline='') as pop_dist:
        pop_reader = reader(pop_dist)
        for row in pop_reader:
            resource = quote('/' + row[0])
            try:
                ORIGIN.request('GET', resource)
            except HTTPException as he:
                print(f'Hit exception {he} trying to fetch resource {resource} from server, exiting')
            res = ORIGIN.getresponse()
            if res.status == 200:
                content = res.read()
            else:
                print(f'Received status {res.status} trying to fetch resource {resource} from server, exiting')
                exit(1)
            if getsizeof(CACHE) + len(content) <= 20000000:
                CACHE[resource] = content
                n += 1
            else:
                break

    print(f'Cache has been filled in {time()-start} seconds and contains {n} items!')


def main():
    global ORIGIN
    parser = argparse.ArgumentParser(description='Start HTTP replica server using specified local port and origin server')
    parser.add_argument('-p', '--port', type=int, required=True)
    parser.add_argument('-o', '--origin', required=True)
    args = parser.parse_args()
    try:
        ORIGIN = HTTPConnection(args.origin, 8080)
    except HTTPException as he:
        print(f'Could not connect to origin, exception: {he}\nExiting')
        exit(1)

    warm_cache()

    server = ThreadingHTTPServer((ADDRESS, args.port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        ORIGIN.close()
        print('Stopped server')


main()