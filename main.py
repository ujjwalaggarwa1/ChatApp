import socket
import asyncio
import json
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Random import get_random_bytes



class connectionManager:
    def __init__(self, name:str, broad_port:int=5056, broad_frequency:int=3, buffer_size:int=1024 ) -> None:
        
        self.name:str = name
        self.host_name:str = socket.gethostname()
        self.ip:int = int(socket.gethostbyname(self.host_name))
        self.broad_port:int = broad_port
        self.tcp_port = None
        self.running:bool = True
        self.broad_frequency:int = broad_frequency
        self.buffer_size:int = buffer_size
        
    # makes the broadcast call on the network to tell other chats that this device is available.
    async def udp_broadcast(self, j_msg:str) -> None:
        
        while self.sock_port is None:
            await asyncio.sleep(0.1)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.ip, self.broad_port))
        sock.setblocking(False)
        
        loop = asyncio.get_running_loop()
        
        while self.running:
            try:
                # '255.255.255.255' marks the whole local network subnet
                await loop.sock_sendto(sock, j_msg.encode(), ('255.255.255.255', self.broad_port))
                await asyncio.sleep(self.broad_frequency)
            finally:
                sock.close()
    
    async def udp_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', self.broad_port))
        sock.setblocking(False)
        
        loop = asyncio.get_running_loop()
        connected_people = set()
        
        try:
            while True:
                data, addr = await loop.sock_recvfrom(sock, self.buffer_size)
                
                raw_msg = data.decode().strip()
                packet = json.loads(raw_msg)
                
                peer_port = packet.get("port")
                
                tup = (addr[0], peer_port)
                if tup in connected_people or tup==(self.ip, self.tcp_port):
                    continue
                else:
                    peer_name = packet.get("name")
                    device = packet.get("device")
                    public_key = packet.get("public_key")
                    
                    connected_people.add(tup)
                    
                    # asyncio.create_task(connect_to_peer(peer_ip, peer_tcp_port))
        finally:
            sock.close()
    
    
    
    async def connection(self, sock_port:int=0):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.ip, sock_port))
        sock.setblocking(False)
        
        self.sock_port = sock.getsockname()[1]
        
        loop = asyncio.get_running_loop()

class Encryption:
    def __init__(self, key_size=2048, key_size_bytes=32) -> None:
        self.key_size_bytes = key_size_bytes
        self.public_key, self.private_key = self.rsa_keypair(key_size)
        
    # in previous version of this code, i made the common key be generated once, but later realized that it would be better to make new common keys on each new connection

    #funcs for keys generation
    def rsa_keypair(self, key_size):
        key = RSA.generate(key_size)
        private_key = key.export_key(format='PEM').decode('utf-8')
        public_key = key.publickey().export_key(format='PEM').decode('utf-8')
        return public_key, private_key

    def generate_common_key(self):
        return get_random_bytes(self.key_size_bytes)

    
    #encryptions
    def encrypt_symmetric(self, common_key, plaintext_bytes):
        """
        Encrypts data using a shared common key
        - ciphertext: it is the encrypted text
        - nonce: works like salt in hashing
        - tag: to check that data received is not tampered with
        
        Returns: (ciphertext, nonce, tag)
        """
        cipher = AES.new(common_key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext_bytes)
        return ciphertext, cipher.nonce, tag

    def encrypt_asymmetric(self, public_key_pem, plaintext_bytes):
        """Encrypts data using the receiver's RSA Public Key string."""
        recipient_key = RSA.import_key(public_key_pem)
        cipher_rsa = PKCS1_OAEP.new(recipient_key)
        return cipher_rsa.encrypt(plaintext_bytes)


    #decryptions
    def decrypt_symmetric(self, common_key, ciphertext, nonce, tag):
        """
        Decrypts data using the shared common key.
        Returns: Decrypted bytes, or None if altered.
        """
        try:
            cipher = AES.new(common_key, AES.MODE_GCM, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext, tag)
        except ValueError:
            return None

    def decrypt_asymmetric(self, private_key_pem, ciphertext):
        """Decrypts data using the receiver's RSA Private Key string."""
        private_key = RSA.import_key(private_key_pem)
        cipher_rsa = PKCS1_OAEP.new(private_key)
        return cipher_rsa.decrypt(ciphertext)


# since data can be corrupted or lost, some of the recent messages are cached here
class MemoryCache:
    def __int__(self, storage_time:int=180):
        self.cache = {}
        self.storage_time:int = storage_time
        
    # def 
    
    
cache_register = set()

async def main():
    pass


#workflow:- main- start- tcp_connection_port- 
#                        udp_broadcaster- public key, tcp_port
#                        udp_listener- confirmation- connection- tcp_connection- secure key
#                        tcp_receiver_port- gets the connection, wait for confirmation