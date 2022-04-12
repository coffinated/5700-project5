'''
This file runs the HTTP service on the replica nodes for project 5.
'''

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.client import HTTPConnection
from sys import getsizeof

ORIGIN = HTTPConnection('cs5700cdnorigin.ccs.neu.edu', 8080)
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
            already_cached = False
            if CACHE.get(self.path):
                status = 200
                content = CACHE[self.path]
                headers = [('Content-Type', 'text/html'), ('Content-Length', str(len(content)))]
                already_cached = True
            else:
                ORIGIN.request('GET', self.path)
                res = ORIGIN.getresponse()
                status = res.status
                content = res.read()
                headers = res.getheaders()
            
            self.send_response(status)
            for each in headers:
                print(each)
                self.send_header(each[0], each[1])
            self.end_headers()
            self.wfile.write(content)

            if not already_cached:
                decide_to_cache(self.path, content)


def decide_to_cache(resource, data):
    global CACHE

    if getsizeof(CACHE) + len(data) < 20000000:
        CACHE[resource] = data
    # TODO: add pageviews.csv ranking comparison as third conditional here
    # if anything in the cache is less popular than this data, delete that and add this


def main():
    server = ThreadingHTTPServer((ADDRESS, PORT), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        ORIGIN.close()
        print('Stopped server')


main()