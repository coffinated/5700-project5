#! /usr/bin/env python3

'''
This file runs the HTTP service on the replica nodes for project 5.
'''

from signal import signal, SIGTERM, SIGINT
import argparse
from threading import Thread
import gzip
import shutil
from csv import reader
import queue
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.client import HTTPConnection, HTTPException, RemoteDisconnected
from time import strftime, time
from urllib.parse import quote
from urllib.request import urlopen
import subprocess

SERVER: ThreadingHTTPServer
ORIGIN: HTTPConnection
ADDRESS = urlopen('https://api.ipify.org/').read().decode('utf8')
MEM_CACHE = {}
DISK_CACHE = {}
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
        global MEM_CACHE
        global DISK_CACHE

        # special grading endpoint
        if self.path == '/grading/beacon':
            self.send_response(204)
            self.end_headers()

        # special endpoint for DNS server to ask for client-server latency
        elif self.path.startswith('/latency'):
            addr = ''
            rtt = 0
            # check for correctly formatted request, send back 400 if not
            if len(self.path.split('?')) > 1:
                q_string = self.path.split('?')[1]
                if q_string.split('=')[0] == 'addr':
                    addr = q_string.split('=')[1]
                else:
                    self.send_error(400, 'Requests to /latency should include \"?addr=[IPv4 address]\"')
            else:
                self.send_error(400, 'Requests to /latency should include \"?addr=[IPv4 address]\"')
            
            # get latency to provided addr from this machine using scamper:
            # by default, scamper pings 4 times, 1 second apart
            sc_proc = subprocess.Popen(['scamper', '-c', 'ping', '-i', addr],
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE)
            try:
                out, err = sc_proc.communicate(timeout=6)
            except subprocess.TimeoutExpired:
                sc_proc.kill()
                out, err = sc_proc.communicate()

            if sc_proc.returncode == 0:
                out = out.decode().split('\n')
                if len(out) < 5:
                    self.send_error(500, f'Could not get latency for {addr}', f'Output from scamper: {out}')
                else:
                    # expected scamper output final line should look like this:
                    #    round-trip min/avg/max/stddev = 21.302/23.791/28.526/2.912 ms
                    # so we get avg by taking 4th index from '/'-delimited list
                    rtt = out[7].split('/')[4]
                    self.send_response(200)
                    content = bytes(rtt, 'ascii') + b'\n'
                    self.send_header('Content-Length', len(content))
                    self.end_headers()
                    self.wfile.write(content)
            else:
                self.send_error(500, f'Could not get latency for {addr}', f'Stderr from scamper: {err}')

        # special health check endpoint to let run script know server is ready for requests
        elif self.path == '/ready':
            # start accepting requests once we've cached 10 items
            if len(MEM_CACHE) >= 10:
                self.send_response(204)
                self.end_headers()
            else:
                self.send_error(503)

        else:
            # if the path is in the mem_cache map, we have at least started or tried to cache it
            if self.path in MEM_CACHE:
                if MEM_CACHE[self.path]:
                    status = 200
                    content = gzip.decompress(MEM_CACHE[self.path])
                    headers = [('Content-Type', 'text/html'), ('Content-Length', str(len(content)))]
                # if key is in cache but value is None, caching is in progress, just fetch again
                # here as this shouldn't happen too often
                else:
                    (status, content, headers) = fetch_from_origin(self.path, ORIGIN)

                self.send_response(status)
                for each in headers:
                    self.send_header(each[0], each[1])
                self.end_headers()
                self.wfile.write(content)

            # otherwise, if it's in the disk_cache map, read from file on disk
            elif self.path in DISK_CACHE:
                with gzip.open(f"./disk_cache/{self.path.split('/')[1]}.txt.gz", 'rb') as f:
                    # first line in file provides length of content
                    length = f.readline()
                    self.send_response(200)
                    headers = [('Content-Type', 'text/html'), ('Content-Length', length.decode().strip())]
                    for each in headers:
                        self.send_header(each[0], each[1])
                    self.end_headers()

                    shutil.copyfileobj(f, self.wfile)

            # if not cached, fetch content from origin
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
    global MEM_CACHE
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
        if MEM_CACHE.get(resource):
            continue

        (_, content, _) = fetch_from_origin(resource, originconn)
        content = gzip.compress(content)
        # cache up to 20 MB in memory (minus 100 KB wiggle room for stack)
        if TOT_CACHED + len(content) + len(resource) <= 19900000:
            MEM_CACHE[resource] = content
            TOT_CACHED += len(content) + len(resource)
        # queue should fit entirely, we shouldn't ever reach this, but just in case
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

    print(f'Cache has been filled with {len(MEM_CACHE.keys())} items ({TOT_CACHED} bytes) in {time()-start} seconds!', flush=True)


'''
This function prepares caches on disk and in memory. First, it unzips the disk_cache.zip file 
which gets deployed along with the code to the web server replicas, populating the current 
directory with the on-disk cache contents. It then reads the disk_cache.csv file so that it has a 
map of the contents cached to disk. Next, it reads the memory_cache.csv information into a Queue, 
which is a thread safe data structure for several content fetching threads to work from as they 
populate our cache. We start 3 threads to fetch content, and wait on those threads and 
report back on how long it took (TODO: can delete the latter before final submission).
'''
def warm_cache():
    global DISK_CACHE
    print('Reading disk cache list', flush=True)
    with open('disk_cache.csv', newline='') as disk_pages:
        tier2_reader = reader(disk_pages)
        for row in tier2_reader:
            # we just need to be able to see that the key is in the dict, all values = True
            DISK_CACHE[quote('/' + row[0])] = True

    cache_q = queue.Queue()
    fetchers = []
    start = time()

    print('Reading memory cache list', flush=True)
    with open('memory_cache.csv', newline='') as mem_pages:
        tier1_reader = reader(mem_pages)
        for row in tier1_reader:
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
        SERVER.serve_forever()
    except KeyboardInterrupt:
        close_server(SIGINT, None)


signal(SIGTERM, close_server)
main()