import socket
import asyncio
import time
import json
import Logger

Logger.setup_logging(backup_count=1)
logger = Logger.get_module_logger("Networks")

'''
json data send example:

broadcast_json= {
    tcp_port: "port",
    name: "name",
    device: "device"
}

data_first_tcp_link = {
    connect_request: 1,
    common_key: 'key encrypted with public key'
}

data_accept_tcp = {
    connect_request = 1,
    msg = 'message encrypted with common key' #cipher_text,
    nonce = 'nonce',
    tag = 'tag'
}


'''


class connectionManager:
    '''
    Builds the network connections and maganegs the network from making the device available for other devices to managing connections.
    '''
    
    def __init__(self, name:str, encryption_instance, broad_port:int=5056, broad_frequency:int=3, buffer_size:int=1024) -> None:
        
        self.name:str = name
        self.encry = encryption_instance
        self.host_name:str = socket.gethostname()
        self.ip = (socket.gethostbyname(self.host_name))
        self.broad_port:int = broad_port
        self.tcp_port = None
        self.running:bool = False
        self.broad_frequency:int = broad_frequency
        self.buffer_size:int = buffer_size
        self.availability = {}
        
        self.pending_handshake = None
        self.handshake_signal = asyncio.Event()
        self.handshake_approved = False
        self.active_sessions = {}
        self.on_session_established = None
        self.on_session_closed = None
        self.on_message_received = None
        
        
    # all the functions are clear by their name, still added some documentary
    
    async def _udp_broadcast(self) -> None:
        '''makes the broadcast call on the network to tell other chats that this device is available.'''
        while self.tcp_port is None:
            await asyncio.sleep(0.1)
        
        raw_msg = {
            'tcp_port': self.tcp_port,
            'name': self.name,
            'device': self.host_name
        }
        
        j_msg = json.dumps(raw_msg)
        
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # sock.bind((self.ip, self.broad_port)) this was throwing an error
        sock.setblocking(False)
        
        loop = asyncio.get_running_loop()
        
        logger.info("Starting Broadcast")
        try:
            while self.running:
                # '255.255.255.255' marks the whole local network subnet
                await loop.sock_sendto(sock, j_msg.encode(), ('255.255.255.255', self.broad_port))
                await asyncio.sleep(self.broad_frequency)
        except Exception as e:
            logger.exception(f"Exception occurred\n\t{e}")
        finally:
            logger.info("shutting broadcast")
            sock.close()
    
    async def _udp_listener(self):
        '''listens to all other available devices'''
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', self.broad_port))
        sock.setblocking(False)
        
        loop = asyncio.get_running_loop()

        logger.info('starting listener')
        try:
            while self.running:
                data, addr = await loop.sock_recvfrom(sock, self.buffer_size)
                
                raw_msg = data.decode().strip()
                packet = json.loads(raw_msg)
                
                peer_port = packet.get("tcp_port")
                peer_ip = addr[0]
                
                peer_id = (peer_ip, peer_port)
                
                if peer_id in self.availability or peer_id==(self.ip, self.tcp_port):
                    continue
                else:
                    current_time = time.time()
                    
                    self.availability[peer_id] = {
                        "peer_name" : packet.get("name"),
                        "device" : packet.get("device"),
                        "peer_tcp_port" : packet.get("tcp_port"),
                        "last_seen" : current_time,
                        "safe_id": str(peer_id).replace('.', '').replace(':', '_').replace('(','').replace(')','').replace("'","").replace('"', '').replace(" ","").replace(",", "")
                    }
                    
                    # asyncio.create_task(connect_to_peer(peer_ip, peer_tcp_port))
        except Exception as e:
            logger.exception(f"Exception occurred\n\t{e}")
        finally:
            logger.info('Closing listener')
            sock.close()
    
    async def _bg_connection_clearer(self):
        '''Periodically removes peers who haven't broadcasted in 5 seconds.'''
        while self.running:
            await asyncio.sleep(1) 
            current_time = time.time()
            # collected keys to delete first to avoid  errors
            dead_peers = []
            
            for peer_id, profile in self.availability.items():
                if current_time - profile["last_seen"] > 5:
                    dead_peers.append(peer_id)
                    
            for peer_id in dead_peers:
                self.availability.pop(peer_id)
    
    async def _receive_tcp(self, reader, writer):
        logger.info('TCP connection request received')
        
        peer = writer.get_extra_info('peername')
        peer_ip = peer[0]
        peer_tcp_port = None
        peer_name = "Unknown Node"
        
        try:
            # Read identity & public key packet first
            raw_packet = await reader.readline()
            if not raw_packet:
                writer.close()
                await writer.wait_closed()
                return
            
            key_packet = json.loads(raw_packet.decode('utf-8').strip())
            peer_public_key = key_packet.get("public_key")
            peer_name = key_packet.get("name", "Unknown Node")
            peer_tcp_port = key_packet.get("tcp_port")
            
            peer_id = (peer_ip, peer_tcp_port) if peer_tcp_port else peer
            
            self.handshake_signal.clear()
            self.pending_handshake = {"name": peer_name, "ip": peer_ip, "port": peer_tcp_port}
            self.handshake_approved = False

            await self.handshake_signal.wait()

            if not self.handshake_approved:
                writer.close()
                await writer.wait_closed()
                return
            
            common_key = await self.encry.generate_common_key()
            
            # Encrypt common key with other person's public key
            encrypted_common = await self.encry.encrypt_rsa(peer_public_key, common_key)
            
            data_first_tcp_link = {
                "connect_request": 1,
                "common_key": encrypted_common.hex()
            }
            
            payload = json.dumps(data_first_tcp_link) + "\n"
            writer.write(payload.encode('utf-8'))
            await writer.drain()
            
            # Register the session
            self.active_sessions[peer_id] = {
                "writer": writer,
                "common_key": common_key,
                "peer_name": peer_name
            }
            if self.on_session_established:
                self.on_session_established(peer_ip, peer_tcp_port or peer[1], peer_name)
            
            # make the continuous chat
            await self._continuous_chat(reader, writer, common_key, peer_tcp_port or peer[1])
            
        except Exception as e:
            logger.exception(f"Exception occurred\n\t{e}")
        finally:
            logger.info("Closing receive_tcp")
            peer_id = (peer_ip, peer_tcp_port) if 'peer_tcp_port' in locals() and peer_tcp_port else peer
            self.active_sessions.pop(peer_id, None)
            if self.on_session_closed:
                self.on_session_closed(peer_ip, peer_tcp_port or peer[1])
            writer.close()
            await writer.wait_closed()
    
    async def _initiate_tcp(self, peer_ip, peer_port, peer_packet):
        logger.info("initiating tcp request")
        try:
            reader, writer = await asyncio.open_connection(peer_ip, peer_port)
            
            pub_key_packet = {
                "public_key": self.encry.public_key,
                "name": self.name,
                "tcp_port": self.tcp_port
            }
            payload = json.dumps(pub_key_packet) + "\n"
            writer.write(payload.encode('utf-8'))
            await writer.drain()
            
            # receives the common key if connection was successful
            raw_res = await reader.readline()
            if not raw_res:
                return 'connection denied'
            response = json.loads(raw_res.decode())
            
            if response.get("connect_request") == 1:
                raw_common_key = bytes.fromhex(response.get("common_key"))
                common_key = await self.encry.decrypt_rsa(self.encry.private_key, raw_common_key)
                
                # Fetch peer_name from self.availability:
                peer_profile = self.availability.get((peer_ip, peer_port))
                peer_name = peer_profile.get("peer_name", "Unknown Node") if peer_profile else "Unknown Node"
                
                # Register the session
                self.active_sessions[(peer_ip, peer_port)] = {
                    "writer": writer,
                    "common_key": common_key,
                    "peer_name": peer_name
                }
                if self.on_session_established:
                    self.on_session_established(peer_ip, peer_port, peer_name)
                
                try:
                    await self._continuous_chat(reader, writer, common_key, peer_port)
                finally:
                    self.active_sessions.pop((peer_ip, peer_port), None)
                    if self.on_session_closed:
                        self.on_session_closed(peer_ip, peer_port)
            else:
                return 'connection denied'
        except Exception as e:
            logger.exception(f"Exception occurred\n\t{e}")
            return 'connection denied'

    async def _continuous_chat(self, reader, writer, common_key, peer_tcp_port=None):
        '''The Continuous talk loop holding the open line session'''
        
        logger.info("backend chat instance made")
        peer = writer.get_extra_info('peername')
        peer_ip = peer[0]
        peer_port = peer_tcp_port if peer_tcp_port is not None else peer[1]
        
        try:
            while True:
                raw_data = await reader.readline()
                if not raw_data:
                    # break
                    await asyncio.sleep(1)
                    continue
                
                packet = json.loads(raw_data.decode('utf-8'))
                
                # Format matching your specification: data_accept_tcp
                if packet.get("connect_request") == 1:
                    ciphertext = bytes.fromhex(packet.get("msg"))
                    nonce = bytes.fromhex(packet.get("nonce"))
                    tag = bytes.fromhex(packet.get("tag"))
                    
                    # Decrypting
                    plain_bytes = await self.encry.decrypt_aes(common_key, ciphertext, nonce, tag)
                    if plain_bytes:
                        text = plain_bytes.decode('utf-8')
                        if self.on_message_received:
                            self.on_message_received(peer_ip, peer_port, text)
                        else:
                            print(f"\n[{peer}]: {text}")
                        
        except ConnectionError as e:
            logger.exception(f"Exception occurred\n\t{e}")
        except Exception as e:
            logger.exception(f"Exception occurred\n\t{e}")
        finally:
            logger.info("backend chat instance CLOSED")
            writer.close()
            await writer.wait_closed()
    
    async def send_message(self, peer_ip: str, peer_port: int, text: str) -> bool:
        '''Encrypts and sends a secure message to a peer'''
        session = self.active_sessions.get((peer_ip, peer_port))
        if not session:
            logger.warning(f"No active session for {(peer_ip, peer_port)}")
            return False
        
        writer = session["writer"]
        common_key = session["common_key"]
        
        try:
            ciphertext, nonce, tag = await self.encry.encrypt_aes(common_key, text.encode('utf-8'))
            packet = {
                "connect_request": 1,
                "msg": ciphertext.hex(),
                "nonce": nonce.hex(),
                "tag": tag.hex()
            }
            payload = json.dumps(packet) + "\n"
            writer.write(payload.encode('utf-8'))
            await writer.drain()
            return True
        except Exception as e:
            logger.exception(f"Failed to send message to {(peer_ip, peer_port)}: {e}")
            return False

    async def connection(self, sock_port:int=0):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.ip, sock_port))
        sock.setblocking(False)
        
        self.sock_port = sock.getsockname()[1]
        
        loop = asyncio.get_running_loop()
    
    
    async def start_server(self, port: int = 0):
        self.running = True
        server = await asyncio.start_server(self._receive_tcp, self.ip, port, limit=self.buffer_size)
        self.tcp_port = server.sockets[0].getsockname()[1]
        
        logger.info("Starting the backend server.")
        
        try:
            await asyncio.gather(
                server.serve_forever(),
                self._udp_broadcast(),
                self._udp_listener(),
                self._bg_connection_clearer()
            )
        except asyncio.CancelledError:
            logger.info("[Shutdown]: Background engine tasks canceled.")
            print("[Shutdown]: Background engine tasks canceled.")
        except Exception as e:
            logger.exception(f"Exception occurred\n\t{e}")
            print(f"[Runtime Error]: Server loop encountered an exception: {e}")
        finally:
            self.running = False


#workflow:- main- tcp_connection_port- 
#                 _udp_broadcaster- public key, tcp_port
#                 _udp_listener- confirmation- connection- tcp_connection- secure key
#                 tcp_receiver_port- gets the connection, wait for confirmation





# While researching on how other applications manage cache, i got to know that tcp will deliver the messages and does the purpose of this class automatically so the idea is dropped

# since data can be corrupted or lost, some of the recent messages are cached here
'''

class MemoryCache:
    """
    ```python
        cache= {
            msg: 'encrypted_msg',
            
        }
    """
    def __int__(self, storage_time:int=180):
        self.cache = {}
        self.storage_time:int = storage_time
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
    async def _periodic_cleanup(self, cleanUpTime:int=10):
        """Background loop that periodically clears expired cache keys."""
        while True:
            await asyncio.sleep(cleanUpTime)
            now = time.time()
            expired_keys = [
                msg_id for msg_id, entry in self.cache.items()
                if now - entry["timestamp"] > self.storage_time
            ]
            for msg_id in expired_keys:
                del self.cache[msg_id]
    
'''