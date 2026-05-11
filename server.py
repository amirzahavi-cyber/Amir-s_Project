__author__ = 'Amir Zahavi'


import socket
import threading
from AsyncMessages import AsyncMessages
from send_recv_AES import SendRecvAes
from db import db
from user import User
import smtplib
from email.mime.text import MIMEText
import random
import traceback
from RSA_mode import RSA
from tcp_by_size import recv_by_size
import maps
import copy


SENDER_EMAIL = "amir.zahavi.home@gmail.com"
SENDER_PASSWORD = "ngnq ayrn kyww ynzi"
cnt_logedin = 0
lock = threading.Lock()
lock2 = threading.Lock()

class ClientThread(threading.Thread):

    def __init__(self, c_socket, db1, async_msg, rand_map):
        super().__init__(daemon=True)
        self.c_socket = c_socket
        self._stop_event = threading.Event()
        self.loggedin = False
        self.connected = True
        self.db1 = db1
        self.async_msg = async_msg
        self.username = ''
        self.code = ''
        self.user = None
        self.send_recv_AES = SendRecvAes(self.c_socket)
        self.mode = b''
        self.mode_stage = ""
        self.rsa_mode = None
        self.map = rand_map
        self.player_num = 0
        self.monster_tick = 0


    def run_thread(self):
        self.start()

    def stop(self):
        """Signal the thread to stop."""
        self._stop_event.set()

    def is_stopped(self):
        """Returns True if the thread has been signaled to stop."""
        return self._stop_event.is_set()

    def run(self):
        data = recv_by_size(self.c_socket)
        self.mode = data[:3]
        self.mode_stage = self.mode.decode()
        if self.mode == b'RSA':
            self.rsa_mode = RSA(self.c_socket)
            self.rsa_mode.generate_keys()
            self.rsa_mode.send_public_key()

        self.c_socket.settimeout(0.05)
        while self.connected:
            try:
                if self.mode_stage == "RSA":
                    self.send_recv_AES.key = self.rsa_mode.decrypt()
                    self.mode_stage = "AES"

                elif self.mode_stage == "AES":
                    data = self.send_recv_AES.recv_encrypted()
                    if data == b'':
                        print('client disconnected')
                        break
                    to_send = str(self.handle_msg(data))
                    if to_send == 'ACD':
                        break
                    if to_send == 'ASYNC' or to_send == '':
                        continue
                    if to_send[:3] in ('SIS', 'SIL', '1SP', 'POK', 'ERR'):
                        self.send_recv_AES.send_encrypted(to_send.encode())
                    else:
                        continue
            except socket.timeout:
                        msgs = self.async_msg.get_async_messages_to_send(self.c_socket)
                        for msg in msgs:
                            if type(msg) == bytes:
                                self.send_recv_AES.send_encrypted(msg)
                            elif type(msg) == str:
                                self.send_recv_AES.send_encrypted(msg.encode())
                        self.monster_tick += 1
                        if self.player_num == 1 and cnt_logedin == 2:
                            if self.monster_tick >= 8:
                                self.monster_tick = 0
                                self.move_monsters()
                            upd = self.build_upd()
                            self.async_msg.put_msg_to_all(upd)
                        continue
            except Exception as e:
                traceback.print_exc()
                break
        print('client died')
        self.async_msg.delete_socket(self.c_socket)
        self.async_msg.delete_user(self.username)

    def send_verification_code(self, recipient_email: str, code: str):
        subject = "Your Verification Code"
        body = f"Your 4-digit verification code is: {code}"
        print(code)
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())

    def move_monsters(self):
        opposites = {'U': 'D', 'D': 'U', 'L': 'R', 'R': 'L'}
        claimed = set()  # tiles claimed by monsters that already moved this tick

        # pre-claim current positions so monsters don't stack
        for i in range(len(self.map['monsters'])):
            x, y, _ = self.map['monsters'][i]
            claimed.add((x, y))

        for i in range(len(self.map['monsters'])):
            x, y, dest = self.map['monsters'][i]

            opposite = opposites[dest]
            dests = ['U', 'R', 'D', 'L']
            dests.remove(opposite)
            random.shuffle(dests)
            dests.append(opposite)
            dests.insert(0, dest)

            claimed.discard((x, y))  # remove own current pos so it's not blocking itself

            for d in dests:
                if d == 'U':
                    dest_x, dest_y = x, y - 1
                elif d == 'D':
                    dest_x, dest_y = x, y + 1
                elif d == 'L':
                    dest_x, dest_y = x - 1, y
                elif d == 'R':
                    dest_x, dest_y = x + 1, y

                if dest_y < 0 or dest_y >= len(self.map['grid']):
                    continue
                if dest_x < 0 or dest_x >= len(self.map['grid'][0]):
                    continue
                if (dest_x, dest_y) in claimed:
                    continue

                tile = self.map['grid'][dest_y][dest_x]
                if tile in ('E', 'F'):
                    self.map['monsters'][i] = (dest_x, dest_y, d)
                    claimed.add((dest_x, dest_y))
                    p1x, p1y = self.map['p1']
                    p2x, p2y = self.map['p2']
                    if (dest_x == p1x and dest_y == p1y) or (x == p1x and y == p1y):
                        self.async_msg.put_msg_to_all(f'HIT~1')
                    elif (dest_x == p2x and dest_y == p2y) or (x == p2x and y == p2y):
                        self.async_msg.put_msg_to_all(f'HIT~2')
                    break
            else:
                claimed.add((x, y))

    def update_after_spw(self, direction, x, y):
        if self.player_num == 1:
            other_x, other_y = int(self.map['p2'][0]), int(self.map['p2'][1])
        else:
            other_x, other_y = int(self.map['p1'][0]), int(self.map['p1'][1])
        mode = ''
        while True:
            if direction == 'U':
                dest_x, dest_y = x, y - 1
            elif direction == 'D':
                dest_x, dest_y = x, y + 1
            elif direction == 'L':
                dest_x, dest_y = x - 1, y
            elif direction == 'R':
                dest_x, dest_y = x + 1, y
            else:
                return

            if dest_y < 0 or dest_y >= len(self.map['grid']):
                return
            if dest_x < 0 or dest_x >= len(self.map['grid'][0]):
                return

            if ((dest_x == self.map['monsters'][0][0] and dest_y == self.map['monsters'][0][1]) or
                (dest_x == self.map['monsters'][1][0] and dest_y == self.map['monsters'][1][1])):
                return

            if dest_x == other_x and dest_y == other_y:
                return

            tile = self.map['grid'][dest_y][dest_x]

            if mode == '':
                if tile == 'E':
                    mode = 'place'
                elif tile == 'I':
                    mode = 'break'
                else:
                    return

            if mode == 'place':
                if tile != 'E':
                    return
                self.map['grid'][dest_y][dest_x] = 'I'
                with lock2:
                    self.map['changes'].add((dest_x, dest_y, 'I'))

            elif mode == 'break':
                if tile != 'I':
                    return
                self.map['grid'][dest_y][dest_x] = 'E'
                with lock2:
                    self.map['changes'].add((dest_x, dest_y, 'E'))
            x, y = dest_x, dest_y


    def can_move(self, direction):
        if self.player_num == 1:
            x, y = int(self.map['p1'][0]), int(self.map['p1'][1])
            other_x, other_y = int(self.map['p2'][0]), int(self.map['p2'][1])
        else:
            x, y = int(self.map['p2'][0]), int(self.map['p2'][1])
            other_x, other_y = int(self.map['p1'][0]), int(self.map['p1'][1])

        if direction == 'U':
            new_x, new_y = x, y - 1
        elif direction == 'D':
            new_x, new_y = x, y + 1
        elif direction == 'L':
            new_x, new_y = x - 1, y
        elif direction == 'R':
            new_x, new_y = x + 1, y
        else:
            return False, None, None

        # check boundaries
        if new_y < 0 or new_y >= len(self.map['grid']):
            return False, None, None
        if new_x < 0 or new_x >= len(self.map['grid'][0]):
            return False, None, None

        if new_x == other_x and new_y == other_y:
            return False, None, None

        for i in range(len(self.map['monsters'])):
            m_x, m_y = self.map['monsters'][i][1], self.map['monsters'][i][2]
            if new_x == m_x and new_y == m_y:
                self.async_msg.put_msg_to_all(f'HIT~{self.player_num}')
                return False, None, None

        tile = self.map['grid'][new_y][new_x]
        if tile in ('W', 'I'):
            return False, None, None


        return True, new_x, new_y

    def build_upd(self):
        p1 = self.map['p1']
        p1_field = f"{p1[0]},{p1[1]},{self.map['scores'][0]},{self.map['p1_dir']}"

        p2 = self.map['p2']
        p2_field = f"{p2[0]},{p2[1]},{self.map['scores'][1]},{self.map['p2_dir']}"

        monsters_field = ":".join(f"{m[0]},{m[1]}" for m in self.map['monsters'])

        with lock2:
            changes_field = ":".join(f"{x},{y},{tile}" for x, y, tile in self.map['changes'])
            self.map['changes'].clear()

        return f"UPD~{p1_field}~{p2_field}~{monsters_field}~{changes_field}"

    def build_first_upd(self):
        # Player 1
        p1 = self.map['p1']
        p1_field = f"{p1[0]},{p1[1]},{self.map['scores'][0]},{self.map['p1_dir']}"

        # Player 2
        p2 = self.map['p2']
        p2_field = f"{p2[0]},{p2[1]},{self.map['scores'][1]},{self.map['p2_dir']}"

        # Monsters
        monsters_field = ":".join(f"{m[0]},{m[1]}" for m in self.map['monsters'])

        # Full grid as map changes
        changes = []
        for row in range(len(self.map['grid'])):
            for col in range(len(self.map['grid'][row])):
                tile = self.map['grid'][row][col]
                changes.append(f"{col},{row},{tile}")
        changes_field = ":".join(changes)

        return f"UPD~{p1_field}~{p2_field}~{monsters_field}~{changes_field}"

    def handle_msg(self, data):
        global cnt_logedin
        if data[:3] == b'DSC':
            self.connected = False
            if self.loggedin:
                self.async_msg.put_msg_to_all(f'ACD~{self.username}')
                with lock:
                    cnt_logedin -= 1
            self.loggedin = False
            self.username = ''
            return 'ACD'

        if not self.loggedin:
            data = data.decode()
            fields = data.split('~')
            code = fields[0]

            if code == 'SNP':
                username = fields[1]
                password = fields[2]
                personal_data = fields[3].split(':')
                if not personal_data[3].isnumeric():
                    return 'ERR~02~Phone number can only include numbers'
                if not self.db1.is_user_exist(username):
                    self.code = str(random.randint(1000, 9999))
                    self.send_verification_code(personal_data[2], self.code)
                    user = User(username, personal_data[0], personal_data[1], personal_data[2], personal_data[3])
                    hashed_password, salt = user.hash_password(password)
                    user.set_password(hashed_password, salt)
                    self.user = user
                    return '1SP'
                else:
                    return 'ERR~04~Account already exists'

            if code == 'SP2':
                if fields[1] == self.code:
                    self.db1.update_db(self.user)
                    return 'SIS'
                else:
                    return 'ERR~05~Wrong password'

            if code == 'SAG':
                self.code = str(random.randint(1000, 9999))
                self.send_verification_code(self.user.email, self.code)
                return '1SP'

            if code == 'FGP':
                if self.db1.is_user_exist(fields[1]):
                    self.code = str(random.randint(1000, 9999))
                    self.send_verification_code(self.db1.get_user_email(fields[1]), self.code)
                    return ''
                else:
                    return 'ERR~06~User does not exist'

            if code == 'CKP':
                if fields[1] == self.code:
                    return 'POK'
                else:
                    return 'ERR~05~Wrong password'

            if code == 'NWP':
                username = fields[2]
                new_password = fields[1]
                hash_password, salt = User.hash_password(new_password)
                print(f"Looking up user: '{username}'")
                self.db1.get_user(username).set_password(hash_password, salt)
                return ''

            if code == 'LGN':
                if cnt_logedin >= 2:
                    return 'ERR~07~Too many logged in'
                username = fields[1]
                password = fields[2]
                if self.db1.is_user_exist(username):
                    hash_password, _ = User.hash_password(password, self.db1.get_user(username).salt)
                    if self.db1.get_user(username).hashed_password == hash_password:
                        self.loggedin = True
                        self.username = username
                        self.async_msg.put_msg_to_all(f'ACC~{username}')
                        self.async_msg.add_new_socket(self.c_socket, username)
                        for past_username in self.async_msg.sock_by_username.keys():
                            if past_username != username:
                                self.async_msg.put_msg_by_username(f'ACC~{past_username}', username)
                        upd = self.build_first_upd()
                        self.async_msg.put_msg_by_username(upd, username)
                        with lock:
                            cnt_logedin += 1
                        self.player_num = cnt_logedin
                        return f'SIL~{self.player_num}'
                return 'ERR~01~Wrong password or username'

        else:
            if data[:3] == b'MSG':
                data = data[4:]
                i = data.index(b'~')
                dst_username = data[:i].decode().strip('~')
                data = data[i:]
                if self.async_msg.check_is_exist_by_username(dst_username):
                    to_send = b'GMS~' + self.username.encode() + b'~' + data
                    self.async_msg.put_msg_by_username(to_send, dst_username)
                    return 'ASYNC'
                return 'ERR~03~Can not find destination username'

            if data[:3] == b'MOV':
                direction = data[4:].decode()
                self.map[f'p{self.player_num}_dir'] = direction
                can, new_x, new_y = self.can_move(direction)
                if can:
                    self.map[f'p{self.player_num}'] = (new_x, new_y)
                    if self.map['grid'][new_y][new_x] == 'F':
                        self.map['scores'][self.player_num-1] += 50
                        self.map['grid'][new_y][new_x] = 'E'
                        with lock2:
                            self.map['changes'].add((new_x, new_y, 'E'))
                return 'ASYNC'

            if data[:3] == b'SPW':
                direction = data[4:].decode()
                self.update_after_spw(direction, int(self.map[f'p{self.player_num}'][0]), int(self.map[f'p{self.player_num}'][1]))
                return 'ASYNC'
                



def main():
    db1 = db("users.pkl")
    print(db1)
    async_msg = AsyncMessages()
    rand_map = copy.deepcopy(maps.MAPS[random.randint(0, 1)])

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 4010))
    s.listen(20)

    threads = []
    while True:
        try:
            c, addr = s.accept()
            t = ClientThread(c, db1, async_msg, rand_map)
            t.run_thread()
            threads.append(t)
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Unexpected accept error: {e}")
            break

    for t in threads:
        t.join()
    s.close()


if __name__ == "__main__":
    main()
