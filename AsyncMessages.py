author = "Amir Zahavi"
import threading
from collections import defaultdict
class AsyncMessages:

    def __init__(self):
        self.lock_async_msgs = threading.Lock()
        self.async_msgs = defaultdict(list)
        self.sock_by_username = {}

    def add_new_socket(self, new_client_sock, username):
        """
            call to this method right after socket accept with client socket
        """
        with self.lock_async_msgs:
            self.async_msgs[new_client_sock] = []
            self.sock_by_username[username] = new_client_sock

    def delete_socket(self, sock):
        """
            call when disconnect
        """
        del self.async_msgs[sock]

    def delete_user(self, username):
        if username in self.sock_by_username.keys():
            del self.sock_by_username[username]

    def check_is_exist(self, sock):
        for key in self.async_msgs.keys():
            if sock == key:
                return True
        return False

    def check_is_exist_by_username(self, username):
        if username in self.sock_by_username.keys():
            if self.sock_by_username[username] in self.async_msgs.keys():
                return True
        return False

    def put_msg_by_username(self, data, username):
        try:
            with self.lock_async_msgs:
                self.async_msgs[self.sock_by_username[username]].append(data)
            return 'success'
        except Exception:
            return 'error:Can not find destination username'

    def put_msg_to_all(self, data):
        self.lock_async_msgs.acquire()
        for u in self.sock_by_username.keys():
            self.async_msgs[self.sock_by_username[u]].append(data)
        self.lock_async_msgs.release()
            

    def get_async_messages_to_send(self, my_sock):
        msgs = []
        if self.async_msgs[my_sock]:
            self.lock_async_msgs .acquire()
            msgs =  self.async_msgs[my_sock]
            self.async_msgs[my_sock] = []
            self.lock_async_msgs .release()
        return msgs
