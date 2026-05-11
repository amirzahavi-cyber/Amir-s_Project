author = "Amir Zahavi"

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from  tcp_by_size import send_with_size, recv_by_size
import traceback


AES_DEBUG = True


class SendRecvAes:
    def __init__(self, sock):
        self.key = b''
        self.cipher_e = None
        self.cipher_d = None
        self.socket = sock

    def create(self):
        self.key = get_random_bytes(16)

    def recv_key(self):
        return recv_by_size(self.socket)

    def send_encrypted(self, data):

        iv = get_random_bytes(16)
        #print(f'in send encrypted data = {data}, iv = {iv}, key = {self.key}')

        self.cipher_e = AES.new(self.key, AES.MODE_CBC, iv)

        ciphertext = self.cipher_e.encrypt(pad(data, AES.block_size))
        to_send = iv + ciphertext
        if AES_DEBUG and len(ciphertext) > 0:
            to_show = data
            if type(to_show) == bytes:
                try:
                    to_show = to_show.decode()
                except (UnicodeDecodeError, AttributeError):
                    pass
            if to_show[:3] == 'HIT':
                print(f"\nSent(AES)({len(to_show)})>>>{to_show}@@@@@@@")


        send_with_size(self.socket, to_send)

    def recv_encrypted(self):
        ciphertext = recv_by_size(self.socket)

        iv = ciphertext[:16]
        ciphertext = ciphertext[16:]
        self.cipher_d = AES.new(self.key, AES.MODE_CBC, iv)

        plaintext = unpad(self.cipher_d.decrypt(ciphertext), AES.block_size)
        if AES_DEBUG and len(plaintext) > 0:
            data_to_print = plaintext
            if type(data_to_print) == bytes:
                try:
                    data_to_print = data_to_print.decode()
                except (UnicodeDecodeError, AttributeError):
                    pass
            if plaintext[:3] == b'HIT':
                print(f"\nReceive(AES)({len(plaintext)})>>>{data_to_print}")
        return plaintext
