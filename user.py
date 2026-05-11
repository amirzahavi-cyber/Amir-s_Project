author = "Amir Zahavi"

import os
import hashlib


class User:
    def __init__(self, username, first_name, last_name, email, phone):
        self.username = username
        self.hashed_password = ''
        self.salt = ''
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.is_admin = False

    def __str__(self):
        return f'{self.username}, {self.first_name} {self.last_name}, email: {self.email}, phone: {self.phone}'

    def set_password(self, hashed_password, salt):
        self.hashed_password = hashed_password
        self.salt = salt

    @staticmethod
    def hash_password(password, salt = None):
        if not salt:
            salt = os.urandom(16).hex()
        return User.hash_item(salt + password), salt

    @staticmethod
    def hash_item(item):
        m = hashlib.sha256()
        m.update(item.encode())
        return m.hexdigest()