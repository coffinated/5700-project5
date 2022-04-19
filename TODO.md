# Project 5 To-do

### Official project guidelines: https://david.choffnes.com/classes/cs4700sp22/project5.php

Components
 - DNS redirection
    - [ ] based on geolocation at first (can use GeoIP database - need to sign up for license and install geoip2 client library?: https://dev.maxmind.com/geoip/geolocate-an-ip/web-services?lang=en#official-api-clients)
    - [ ] later add active observation of request performance
    - [ ] also consider server load
    - [ ] also consider which server has data cached
    - [ ] if time, add passive observation?
    - [ ] maintain mapping of clients to replicas
    - [ ] can use dnslib (https://github.com/paulc/dnslib) to build/parse DNS response/request packets
 - web server
    - [x] respond to request for '/grading/beacon' with 204 response code
    - [x] get content from cache if it's there, from origin if not
    - [x] maintain limited cache (20MB) based on popularity of content
      - [x] use threading to warm the cache asynchronously
      - [ ] store some of cache on disk?
    - [x] call server using `./httpserver -p <port> -o <origin>`
    - [ ] measure latency with client (using scamper? https://www.caida.org/catalog/software/scamper/ -- python tools: https://github.com/cmand/scamper), share that info with DNS server over HTTP
 - scripts (use SSH key-based authentication)
    - [ ] deployCDN
    - [ ] runCDN
    - [ ] stopCDN
