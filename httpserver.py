#! /usr/bin/env python3

'''
This file runs the HTTP service on the replica nodes for project 5.
'''

import argparse
from asyncio import Task, create_task, gather, run
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.client import HTTPConnection, HTTPException
import queue
from sys import getsizeof
from csv import reader
from time import time
from urllib.parse import quote

ORIGIN: HTTPConnection
# TODO: get address dynamically since we'll want to upload same code to all replicas
ADDRESS = '50.116.41.109'
CACHE = {}


class handler(BaseHTTPRequestHandler):
    async def await_cache_item(self, key):
        return await CACHE[key]

    def do_GET(self):
        if self.path == '/grading/beacon':
            self.send_response(204)
            self.end_headers()
        else:
            # if the path is in the cache map, we have at least started or tried to cache it
            if CACHE.get(self.path):
                # wait in case it is currently being requested
                if isinstance(CACHE[self.path], Task):
                    run(self.await_cache_item(self.path))

                if CACHE[self.path]:
                    status = 200
                    content = CACHE[self.path]
                    headers = [('Content-Type', 'text/html'), ('Content-Length', str(len(content)))]
                # if value after await is None, there wasn't enough room left to cache it, must 
                # request it now and remove from cache map so we don't do this again
                else:
                    ORIGIN.request('GET', self.path)
                    res = ORIGIN.getresponse()
                    status = res.status
                    content = res.read()
                    headers = res.getheaders()
                    del CACHE[self.path]
            else:
                # TODO: determine whether content should be cached based on popularity
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


async def get_content(resource):
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
        return content
    else:
        return None


async def content_fetcher(cq: queue.Queue):
    global CACHE

    while not cq.empty():
        try:
            resource = cq.get(False)
        # this shouldn't happen since we check for empty but just in case some threading
        # shenanigans happen, check for it here too
        except queue.Empty:
            break

        # if it was already cached, move onto next
        if CACHE.get(resource):
            continue
        # create async task so that server request handler can see we're currently fetching this
        # resource if it happens to get a request for it at the same time
        CACHE[resource] = create_task(get_content(resource))
        await CACHE[resource]

        # getter returns None if cache limit reached, check for that and clear the queue if so
        if not CACHE[resource]:
            cq.queue.clear()


async def wait_for_cache_filled(workers, start):
    for each in workers:
        await each

    print(f'Cache has been filled with {len(CACHE.keys)} items in {time()-start} seconds!')

async def warm_cache():
    print('Populating cache!')

    cache_q = queue.Queue()
    fetchers = []
    start = time()

    with open('pageviews.csv', newline='') as pop_dist:
        pop_reader = reader(pop_dist)
        for row in pop_reader:
            cache_q.put_nowait(quote('/' + row[0]))

    for i in range(3):
        fetchers.append(create_task(content_fetcher(cache_q)))

    create_task(wait_for_cache_filled(fetchers, start))


def main():
    global ORIGIN
    parser = argparse.ArgumentParser(description='Start HTTP replica server using specified local'
                                                 ' port and origin server')
    parser.add_argument('-p', '--port', type=int, required=True)
    parser.add_argument('-o', '--origin', required=True)
    args = parser.parse_args()
    try:
        ORIGIN = HTTPConnection(args.origin, 8080)
    except HTTPException as he:
        print(f'Could not connect to origin, exception: {he}\nExiting')
        exit(1)

    run(warm_cache())
    print('Warming cache, meanwhile starting server...')

    server = ThreadingHTTPServer((ADDRESS, args.port), handler)
    try:
        server.serve_forever()
        print('Ready to serve!')
    except KeyboardInterrupt:
        server.server_close()
        ORIGIN.close()
        print('Stopped server')


main()