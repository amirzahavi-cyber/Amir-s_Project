author = "Amir Zahavi"

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from  tcp_by_size import send_with_size, recv_by_size


class RSA:
    def __init__(self, sock):
        self._private_key = None
        self._public_key = None
        self.socket = sock


    def generate_keys(self):
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self._public_key = self._private_key.public_key()

    def ask_for_public_key(self):
        to_send = b'RSA'
        send_with_size(self.socket, to_send)

    def send_public_key(self):
        key_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        to_send = b'PKY~' + key_bytes
        send_with_size(self.socket, to_send)

    def recv_public_key(self):
        data = recv_by_size(self.socket)
        if data[:3] == b'PKY':
            self._public_key = serialization.load_der_public_key(data[4:])
        return self._public_key

    def encrypt(self, key: bytes):
        if not self._public_key:
            raise ValueError("No public key available.")
        to_send = b'AES~' + self._public_key.encrypt(
            key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        send_with_size(self.socket, to_send)

    def decrypt(self) -> bytes:
        data = recv_by_size(self.socket)
        if data[:3] == b'AES':
            encrypted_key = data[4:]
        if not self._private_key:
            raise ValueError("No private key available.")
        return self._private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
