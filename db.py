author = "Amir Zahavi"

import os.path
import pickle
import threading


class db:
    def __init__(self, file_name):
        self.lock = threading.Lock()
        self.file_name = file_name
        if not os.path.isfile(self.file_name):
            self.d = {}
            with open(file_name, 'wb') as f:
                pickle.dump(self.d, f)
        else:
            with open(file_name, "rb") as f:
                self.d = pickle.load(f)

    def __str__(self):
        s = f'\n-------DB({len(self.d)})---------\n'
        for k, v in self.d.items():
            s += f'\t {v}\n'
        return s

    def update_db(self, user):
        with self.lock:
            self.d[user.username] = user
            with open(self.file_name, 'wb') as f:
                pickle.dump(self.d, f)

    def get_user_email(self, username):
        if username in self.d.keys():
            return self.d[username].email
        return ''

    def get_user(self, username):
        if username in self.d.keys():
            return self.d[username]


    def is_user_exist(self, username):
        if username in self.d.keys():
            return True
        return False

