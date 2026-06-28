import asyncio

try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import AES, PKCS1_OAEP
    from Crypto.Random import get_random_bytes

except:
    print("Unable to load modules, run: pip install -r requirements.txt")

class Encryption:
    def __init__(self, key_size=2048, key_size_bytes=32) -> None:
        self.key_size_bytes = key_size_bytes
        self.public_key, self.private_key = self.rsa_keypair(key_size)
        
        # in previous version of this code, i made the common key be generated once, but later realized that it would be better to make new common keys on each new connection

    
    #funcs for keys generation
    def rsa_keypair(self, key_size):
        #rsa blocks thread, but we need keys at starting
        key = RSA.generate(key_size)
        private_key = key.export_key(format='PEM').decode('utf-8')
        public_key = key.publickey().export_key(format='PEM').decode('utf-8')
        return public_key, private_key

    async def generate_common_key(self):
        return get_random_bytes(self.key_size_bytes)

    
    #encryptions
    async def encrypt_aes(self, common_key, plaintext_bytes):
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

    async def encrypt_rsa(self, public_key_pem, plaintext_bytes):
        """Encrypts data using the receiver's RSA Public Key string."""
        def _encrypt():
            recipient_key = RSA.import_key(public_key_pem)
            cipher_rsa = PKCS1_OAEP.new(recipient_key)
            return cipher_rsa.encrypt(plaintext_bytes)
        return await asyncio.to_thread(_encrypt)


    #decryptions
    async def decrypt_aes(self, common_key, ciphertext, nonce, tag):
        """
        Decrypts data using the shared common key.
        Returns: Decrypted bytes, or None if altered.
        """
        try:
            cipher = AES.new(common_key, AES.MODE_GCM, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext, tag)
        except ValueError:
            return None

    async def decrypt_rsa(self, private_key_pem, ciphertext):
        """Decrypts data using the receiver's RSA Private Key string."""
        def _decrypt():
            private_key = RSA.import_key(private_key_pem)
            cipher_rsa = PKCS1_OAEP.new(private_key)
            return cipher_rsa.decrypt(ciphertext)
        return await asyncio.to_thread(_decrypt)
