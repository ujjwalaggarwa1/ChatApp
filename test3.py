#  this file is named test3 because the ai made the working file after many attempts, this was the third version that worked and this was the one i liked

import asyncio
import json
import sys
from networks import connectionManager
from encryptions import Encryption

async def send_text(writer, encryption_instance, common_key, text: str):
    ciphertext, nonce, tag = await encryption_instance.encrypt_aes(common_key, text.encode('utf-8'))
    packet = {
        "connect_request": 1,
        "msg": ciphertext.hex(),
        "nonce": nonce.hex(),
        "tag": tag.hex()
    }
    payload = json.dumps(packet) + "\n"
    writer.write(payload.encode('utf-8'))
    await writer.drain()

class InteractiveChatNode:
    def __init__(self, name: str):
        self.name = name
        self.crypto = Encryption()
        self.manager = connectionManager(name=name, encryption_instance=self.crypto)
        
        self.active_sessions = {}  # peer_id -> shared_key
        self.active_writers = {}   # peer_id -> writer
        self._pending_handshakes = set()

        # Hook the chat entry point
        original_chat = self.manager._continuous_chat
        
        async def hooked_chat(reader, writer, common_key, peer_tcp_port=None):
            peer = writer.get_extra_info('peername')
            peer_port = peer_tcp_port if peer_tcp_port is not None else peer[1]
            peer_id = (peer[0], peer_port)
            
            # Save the session details into our interactive state tracking arrays
            self.active_sessions[peer_id] = common_key
            self.active_writers[peer_id] = writer
            
            print(f"\n[SECURE] [Secure Link Active] Connected with {peer_id[0]}:{peer_id[1]}")
            print(">> ", end="", flush=True)
            
            # Forward execution back to the main.py engine
            try:
                await original_chat(reader, writer, common_key, peer_tcp_port)
            finally:
                # Clean up if the remote peer disconnects
                self.active_sessions.pop(peer_id, None)
                self.active_writers.pop(peer_id, None)
                print(f"\n[DISCONNECTED] Lost link with {peer_id[0]}:{peer_id[1]}")
                print(">> ", end="", flush=True)

        # Inject our session tracking hook into the engine instance
        self.manager._continuous_chat = hooked_chat

    async def ui_message_handler(self, peer_id, message: str):
        """Triggers whenever a secure message unblocks on the stream"""
        print(f"\n[MSG] [{peer_id[0]}:{peer_id[1]}]: {message}")
        print(">> ", end="", flush=True)

    async def run_node(self):

        print(f"[STARTING] Booting network socket engines for [{self.name}]...")
        server_task = asyncio.create_task(self.manager.start_server(port=0))
        await asyncio.sleep(0.5)
        
        print("\n" + "="*50)
        print(f"  NODE ACTIVE: {self.name} listening on port {self.manager.tcp_port}")
        print("  COMMANDS AVAILABLE:")
        print("    /list           - Show discovered local peers")
        print("    /connect <num>  - Connect to a peer index from the list")
        print("    /exit           - Shut down node")
        print("  Or simply type a message to send to everyone connected!")
        print("="*50 + "\n")

        while self.manager.running:
            command = await asyncio.to_thread(input, ">> ")
            command = command.strip()
            if not command:
                continue

            if command == "/exit":
                break

            elif command == "/list":
                print("\n[DISCOVERY] --- DISCOVERED PEERS ---")
                self.peer_map = list(self.manager.availability.items())
                if not self.peer_map:
                    print("No active peers broadcasting on subnet yet.")
                for idx, (peer_id, profile) in enumerate(self.peer_map):
                    status = "CONNECTED" if peer_id in self.active_sessions else "AVAILABLE"
                    print(f" [{idx}] {profile['peer_name']} at {peer_id[0]}:{peer_id[1]} [{status}]")
                print("---------------------------\n")

            elif command.startswith("/connect "):
                try:
                    idx = int(command.split(" ")[1])
                    peer_id, profile = self.peer_map[idx]
                    print(f"Initiating connection handshake with {profile['peer_name']}...")
                    
                    # Run the engine initiation call and protect it from garbage collection
                    task = asyncio.create_task(self.manager._initiate_tcp(peer_id[0], peer_id[1], {}))
                    self._pending_handshakes.add(task)
                    task.add_done_callback(self._pending_handshakes.discard)
                    
                except (IndexError, ValueError):
                    print("Invalid command structure. Use: /connect <index_number>")
                except Exception as e:
                    print(f"Connection attempt failed: {e}")

            else:
                if not self.active_writers:
                    print("[ERROR] You aren't linked to an active secure session line yet. Use /connect")
                    continue
                    
                dead_sessions = []
                for peer_id in list(self.active_writers.keys()):
                    success = await self.manager.send_message(peer_id[0], peer_id[1], command)
                    if not success:
                        dead_sessions.append(peer_id)
                        
                for dead in dead_sessions:
                    self.active_writers.pop(dead, None)
                    self.active_sessions.pop(dead, None)

        self.manager.running = False
        server_task.cancel()

if __name__ == "__main__":
    node_name = input("Enter identity name for this terminal node: ").strip()
    if not node_name:
        node_name = "Anonymous"
    try:
        asyncio.run(InteractiveChatNode(node_name).run_node())
    except KeyboardInterrupt:
        print("\nNode closed.")