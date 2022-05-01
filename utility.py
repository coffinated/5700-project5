import socket
import math
import re
import maxminddb
import urllib
import urllib.request
import json
class LocationHelper():
    def __init__(self):
        #self.reader = maxminddb.open_database('./GeoLite2-City_20220426/GeoLite2-City.mmdb')
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
        self.replicas = [
            socket.gethostbyname(f'p5-http-{l}.5700.network') for l in letters
        ]
        self.replica_locs = {
            x:self.get_location(x) for x in self.replicas
        }


    def get_location1(self, ip_addr):
        #answer = self.reader.get(ip_addr)
        url = 'http://ipinfo.io/'+ip_addr+'?token=5548847374ffad'
        response = urllib.request.urlopen(url).read()
        parsed_resp = json.loads(response)
        location = parsed_resp['loc'].split(',')

        return location

    def get_location(self, ip_addr):
        answer = self.reader.get(ip_addr)
        # print(answer, flush=True)
        location = (answer['location']['latitude'], answer['location']['longitude'])
        return location 
        
      
    def calculate_distance(self, location1, location2):
        lat1,lon1 = location1
        lat2,lon2 = location2
        lat1 = float(lat1)
        lon1 = float(lon1)

        lat2 = float(lat2)
        lon2 = float(lon2)


        p = 0.017453292519943295
        a = 0.5 - math.cos((lat2 - lat1) * p)/2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p))/2
        return 12742 * math.asin(math.sqrt(a))


    def find_closest_server(self, client_ip):
        replica_map = {}
        distance = {}

        client_location = self.get_location(client_ip)

        for ip in self.replicas:
            loc = self.get_location(ip)
            replica_map[ip] = loc
        for server, s_loc in self.replica_locs.items():
            distance[server] = self.calculate_distance(client_location, s_loc)
        closest_server = min(distance, key = distance.get)
        print(closest_server)
        return closest_server


    def is_private(self,client_addr):
        priv_lo = re.compile("^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
        priv_24 = re.compile("^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
        priv_20 = re.compile("^192\.168\.\d{1,3}.\d{1,3}$")
        priv_16 = re.compile("^172.(1[6-9]|2[0-9]|3[0-1]).[0-9]{1,3}.[0-9]{1,3}$")
        if priv_lo.match(client_addr) or priv_24.match(client_addr) or priv_20.match(client_addr) or priv_16.match(client_addr):
            return True
        return False




	
	
