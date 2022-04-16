import sys


class DNSpacket:

    def __init__(self):
        self.id = randint(0, 65535)
        self.flags = 0
        self.qcount = 0
        self.acount = 0
        self.nscount = 0
        self.arcount = 0
        self.qname = ''
        self.qtype = 0
        self.q_class = 0
        self.aname = 0
        self.atype = 0
        self.a_class = 0
        self.ttl = 0
        self.length = 0
        self.data = ''

    def generate_question(self, domain):
        #using given domain to generate the query section for the DNS packet, and the common section
        self.qname = domain
        packet = struct.pack('!HHHHHH', self.id, self.flags, self.qcount,
                             self.acount, self.nscount, self.arcount)
        packet += ''.join(chr(len(x)) + x for x in self.qname.split('.'))
        packet += '\x00'
        packet += struct.pack('!HH', self.qtype, self.q_class)
        return packet
    def generate_answer(self, domain, ip_addr):
    #Given a domain and replica IP address, construct the DNS answer that will be sent to the client.
        self.acount = 1 # One answer will be returned
        self.flags = 0x8180 
        packet = self.generate_question(domain)
        self.aname = 0xC00C # Pointer to qname label
        self.atype = 0x0001 # The A record for the domain name
        self.a_class = 0x0001 # Internet (IP)
        self.ttl = 60 # 32-bit value
        self.length = 4 # IP address is 32 bits or 4 bytes, but the length field is 16 bits.
        self.data = ip_addr
        packet += struct.pack('!HHHLH4s', self.aname, self.atype, self.a_class,
                          self.ttl, self.length, socket.inet_aton(self.data))
        return packet
    
class DNSserver:

    def __init__(self,port,name):
        self.name = name
        self.port = port
        self.myip =self.get_ip_address()
        

    def get_ip_address(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('cs5700cdnproject.ccs.neu.edu', 80))
        ip = s.getsockname()
        s.close()
        return ip
