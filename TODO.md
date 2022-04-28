# Project 5 To-do

### Official project guidelines: https://david.choffnes.com/classes/cs4700sp22/project5.php

Components
 - DNS redirection
    - [ ] based on geolocation at first
      - [ ] can use GeoIP database - need to download database to DNS node? https://dev.maxmind.com/geoip/geolocate-an-ip/databases (try to find lightest-weight db they offer since we don't need super fine-grained location data)
    - [ ] later add active observation of request performance
    - [ ] if time, add passive observation?
    - [ ] maintain mapping of clients to replicas
    - [x] can use dnslib (https://github.com/paulc/dnslib) to build/parse DNS response/request packets
 - web server
    - [x] respond to request for '/grading/beacon' with 204 response code
    - [x] get content from cache if it's there, from origin if not
    - [x] maintain limited cache (20MB) based on popularity of content
      - [x] use threading to warm the cache asynchronously
      - [x] use compression to cache more pages
      - [x] can also store cache on disk (another 20MB), ship with deploy script
    - [x] call server using `./httpserver -p <port> -o <origin>`
    - [ ] add health check endpoint for startup
    - [x] measure latency with client (using scamper? https://www.caida.org/catalog/software/scamper/ -- python tools: https://github.com/cmand/scamper)
      - [x] share that info with DNS server over HTTP
 - scripts (use SSH key-based authentication)
    - [x] deployCDN
      - [x] edit to include all replicas
      - [x] deploy cache files as well
      - [ ] and geoIP db?
    - [x] runCDN
      - [x] edit to include all replicas
      - [ ] add health check for web servers
    - [x] stopCDN
      - [x] edit to include all replicas
