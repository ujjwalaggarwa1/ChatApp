import asyncio
from networks import connectionManager
from encryptions import Encryption

    
    
async def main():
    name = input("Enter Your Name: ")
    print("Building dependencies. . .")
    encry = Encryption()
    conn = connectionManager(name, encry)
    print('Done.\n')
    
    public_key = encry.public_key
    private_key = encry.private_key

    print(conn.host_name)
    print(conn.tcp_port)
    print(public_key)
    print(private_key)
    
if __name__ == "__main__":
    asyncio.run(main())
