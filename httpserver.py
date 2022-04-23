#! /usr/bin/env python3

'''
This file runs the HTTP service on the replica nodes for project 5.
'''

import argparse
import gzip
import shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.client import HTTPConnection, HTTPException, RemoteDisconnected
import queue
from csv import reader
from signal import signal, SIGTERM, SIGINT
from threading import Thread
from time import strftime, time
from urllib.parse import quote
from urllib.request import urlopen

SERVER: ThreadingHTTPServer
ORIGIN: HTTPConnection
# TODO: make sure this is acceptable
ADDRESS = urlopen('https://api.ipify.org/').read().decode('utf8')
CACHE = {}
TOT_CACHED = 0


'''
Helper function for handling interrupts and closing gracefully
'''
def close_server(signum, frame):
    SERVER.server_close()
    ORIGIN.close()
    print(f"Stopped server at {strftime('%c')}")
    exit(0)


'''
TODO: Still tweaking this process
'''
def warm_disk_cache():
    shutil.unpack_archive('zip', './disk_cache/')


'''
Helper function for sending a GET request to the origin server for the resource specified
and using the connection passed in.
TODO: probably don't keep the exit(1) statements for final submission, just for debugging
'''
def fetch_from_origin(resource, conn: HTTPConnection):
    try:
        conn.request('GET', resource)
    except RemoteDisconnected as dis_err:
        print(f'{dis_err} - trying to reconnect')
        conn.connect()
        conn.request('GET', resource)
    except HTTPException as he:
        print(f'Hit exception {he} trying to fetch resource {resource} from server, exiting')
        exit(1)
    res = conn.getresponse()
    if res.status == 200:
        content = res.read()
    else:
        print(f'Received status {res.status} trying to fetch resource {resource} from server, exiting')
        exit(1)
    status = res.status
    # TODO: set headers explicitly instead of forwarding the origin's headers??
    headers = res.getheaders()
    return (status, content, headers)


'''
This class defines our handling of GET requests at the web server. Aside from the /grading/beacon
special case, when we receive a request, we look for it in our cache. If it's there, we return the
cached content; if not, we request the resource from the origin server and return that content.
'''
class handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        global CACHE

        if self.path == '/grading/beacon':
            self.send_response(204)
            self.end_headers()

        # TODO: this is for testing, DELETE
        elif self.path.startswith('/origin'):
            (status, content, headers) = fetch_from_origin(self.path[7:], ORIGIN)
            self.send_response(status)
            for each in headers:
                self.send_header(each[0], each[1])
            self.end_headers()
            self.wfile.write(content)

        # TODO: this is for testing, DELETE
        elif self.path.startswith('/compressed'):
            with open(f"{self.path.split('/')[2]}.txt.gz", 'rb') as f:
                # first line in file provides length of content
                length = f.readline()
                self.send_response(200)
                headers = [('Content-Type', 'text/html'), ('Content-Length', length.decode())]
                for each in headers:
                    self.send_header(each[0], each[1])
                self.end_headers()

                shutil.copyfileobj(f, self.wfile)

        else:
            # if the path is in the cache map, we have at least started or tried to cache it
            if self.path in CACHE:
                if CACHE[self.path]:
                    status = 200
                    content = gzip.decompress(CACHE[self.path])
                    headers = [('Content-Type', 'text/html'), ('Content-Length', str(len(content)))]
                # if key is in cache but value is None, fetch content and delete the key from 
                # cache map to prevent this happening again
                else:
                    (status, content, headers) = fetch_from_origin(self.path, ORIGIN)
                    del CACHE[self.path]
            # if not, fetch content from origin
            else:
                (status, content, headers) = fetch_from_origin(self.path, ORIGIN)
            
            self.send_response(status)
            for each in headers:
                self.send_header(each[0], each[1])
            self.end_headers()
            self.wfile.write(content)


'''
Each fetcher thread opens a connection to the origin server and starts requesting items from the
queue. If the get_content() function returned None, it means the cache limit has been reached, so
the thread clears the rest of the working queue. The fetching threads all cease looping when the 
queue is empty.
'''
def content_fetcher(cq: queue.Queue, origin):
    global CACHE
    global TOT_CACHED
    # each fetcher thread gets its own server connection
    try:
        originconn = HTTPConnection(origin, 8080)
    except HTTPException as he:
        print(f'Could not connect to origin, exception: {he}\nExiting')
        exit(1)

    while not cq.empty():
        try:
            # pop the next resource off the queue
            resource = cq.get(False)
        except queue.Empty:
            # this shouldn't happen since we check for empty but just in case some threading
            # shenanigans happen, check for it here too
            break

        # if it was already cached, move onto next
        if CACHE.get(resource):
            continue

        (_, content, _) = fetch_from_origin(resource, originconn)
        content = gzip.compress(content)
        # cache up to 20 MB in memory (minus 100 KB wiggle room for stack)
        if TOT_CACHED + len(content) + len(resource) <= 19900000:
            CACHE[resource] = content
            TOT_CACHED += len(content) + len(resource)
        else:
            cq.queue.clear()


    originconn.close()


'''
This waits on the fetcher threads in order to report back on how long the cache process took and
how many items we cached.
TODO: Delete for final submission as we won't need to print these out
'''
def wait_for_cache_filled(workers, start):
    global TOT_CACHED
    for thread in workers:
        thread.join()

    print(f'Cache has been filled with {len(CACHE.keys())} items ({TOT_CACHED} bytes) in {time()-start} seconds!', flush=True)


'''
This function reads the pageveiws.csv information into a Queue, which is a thread safe data 
structure for several content fetching threads to work from as they populate our cache. We start
5 threads to fetch content, and another thread to wait on those threads in the background and 
report back on how long it took (TODO: can delete the latter before final submission).
'''
def warm_cache():
    cache_q = queue.Queue()
    fetchers = []
    start = time()

    with open('pages_to_cache.csv', newline='') as pop_dist:
        pop_reader = reader(pop_dist)
        for row in pop_reader:
            cache_q.put_nowait(quote('/' + row[0]))

    for i in range(3):
        fetchers.append(Thread(target=content_fetcher, args=(cache_q, ORIGIN.host)))
        fetchers[i].start()

    wait_for_cache_filled(fetchers, start)


'''
Our main function takes two arguments, port and origin, and uses them to determine which local
port to serve from and where the origin server is that it should connect to for content. At
startup, we call our cache warming function and immediately start the server up. The server 
should start accepting requests while several worker threads begin fetching cache content in
the background. The server runs indefinitely until a KeyboardInterrupt is received, then it closes
and shuts down its connection to the origin server.
'''
def main():
    global SERVER
    global ORIGIN

    # accept and parse command line arguments
    parser = argparse.ArgumentParser(description='Start HTTP replica server using specified local'
                                                 ' port and origin server')
    parser.add_argument('-p', '--port', type=int, required=True)
    parser.add_argument('-o', '--origin', required=True)
    args = parser.parse_args()

    try:
        # this connection to the origin server is for serving incoming requests
        ORIGIN = HTTPConnection(args.origin, 8080)
    except HTTPException as he:
        print(f'Could not connect to origin, exception: {he}\nExiting')
        exit(1)

    SERVER = ThreadingHTTPServer((ADDRESS, args.port), handler)
    SERVER.protocol_version = 'HTTP/1.1'
    # start server and cache warming threads in try-except clause to allow for ctrl-C exit
    try:
        cache_thread = Thread(target=warm_cache, daemon=True)
        cache_thread.start()
        warm_disk_cache()
        SERVER.serve_forever()
    except KeyboardInterrupt:
        close_server(SIGINT, None)


signal(SIGTERM, close_server)
main()