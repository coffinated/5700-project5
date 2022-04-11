'''
This file runs the HTTP service on the replica nodes for project 5.
'''

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ORIGIN = 'cs5700cdnorigin.ccs.neu.edu'
ADDRESS = '50.116.41.109'
PORT = 40010

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/grading/beacon':
            self.send_response(204)
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            self.wfile.write(bytes('Here is some fake content!', 'utf-8'))

def main():
    server = ThreadingHTTPServer((ADDRESS, PORT), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print('Stopped server')


main()