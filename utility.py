import socket
import struct
import math
import urllib
import urllib.request
import json
import re
def get_location(ip_addr):
    url = 'http://ipinfo.io/'+ip_addr+'?token=5548847374ffad'
    response = urllib.request.urlopen(url).read()
    parsed_resp = json.loads(response)
    location = parsed_resp['loc'].split(',')

    return location

def calculate_distance(location1,location2):
    lat1,lon1 = location1
    lat2,lon2 = location2
    lat1 = float(lat1)
    lon1 = float(lon1)

    lat2 = float(lat2)
    lon2 = float(lon2)


    p = 0.017453292519943295
    a = 0.5 - math.cos((lat2 - lat1) * p)/2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p))/2
    return 12742 * math.asin(math.sqrt(a));

replica_server_ip = {'52.62.170.156','13.234.54.32','15.223.19.203','54.207.206.161','54.215.100.111','54.251.196.47'}

def find_cloest_server(client_location):
    replica_map = {}
    distance = {}

    for ip in replica_server_ip:
        loc = get_location_from_ip(ip)
        replica_map[ip] = loc
    for key in replica_map:
        distance[key] = calculate_distance(client_location,replica_map[key])
    cloest_server = min(distance, key = distance.get)
    print(cloest_server)
    return cloest_server

priv_lo = re.compile("^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
priv_24 = re.compile("^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
priv_20 = re.compile("^192\.168\.\d{1,3}.\d{1,3}$")
priv_16 = re.compile("^172.(1[6-9]|2[0-9]|3[0-1]).[0-9]{1,3}.[0-9]{1,3}$")

def is_private(client_addr):
    if lo.match(client_addr) or p_24.match(client_addr) or p_20.match(client_addr) or p_16.match(client_addr):
        return True
    return False

