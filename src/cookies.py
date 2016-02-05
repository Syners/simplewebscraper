import cookielib
import glob
import json
import os
import platform
import shutil
import sqlite3
import sys
import time

from enumerations import OperatingSystem


class CookieJar(type):
    def __init__(cls, name, bases, d):
        type.__init__(cls, name, bases, d)
        user_platform = platform.system()
        if user_platform == "Linux":
            cls.platform = OperatingSystem.LINUX
        elif user_platform == "Windows":
            cls.platform = OperatingSystem.WINDOWS


class Chrome(object):
    __metaclass__ = CookieJar
    platform = None
    cookie_file = None
    copy_cookie_file = "chrome_cookies.sqlite"
    copy_cookie_txt = "chrome_cookies.txt"
    jar = cookielib.MozillaCookieJar()

    def __init__(self):
        self.detect_browser()
        if self.cookie_file:
            self.format_cookie()
            self.load()

    def detect_browser(self):
        cookie_file = None
        if self.platform == OperatingSystem.LINUX:
            cookie_file = os.path.expanduser("~/.config/google-chrome/Default/Cookies")
        elif self.platform == OperatingSystem.WINDOWS:
            cookie_file = os.path.expanduser("~/AppData/Local/Google/Chrome/User Data/Default/Cookies")
        if os.path.exists(cookie_file):
            self.cookie_file = cookie_file

    def format_cookie(self):

        shutil.copy2(self.cookie_file, self.copy_cookie_file)
        connection = sqlite3.connect(self.copy_cookie_file)
        cursor = connection.cursor()
        try:
            cursor.execute('SELECT host_key, path, secure, expires_utc, name, value, encrypted_value FROM cookies')
        except sqlite3.DatabaseError:
            raise Exception("Your SQLite3 package in your Python installation is out of date.  "
                            "Resolution: http://www.obsidianforensics.com/blog/upgrading-python-sqlite")
        with open(self.copy_cookie_txt, 'w') as file_object:
            file_object.write('# Netscape HTTP Cookie File\n'
                              '# http://www.netscape.com/newsref/std/cookie_spec.html\n'
                              '# This is a generated file!  Do not edit.\n')
            bool_list = ['FALSE', 'TRUE']
            decrypted = self.decrypt_cookie_db()

            for item in cursor.fetchall():
                value = decrypted(item[5], item[6])
                row = u'%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (
                    item[0], bool_list[item[0].startswith('.')], item[1], bool_list[item[2]], item[3], item[4], value)
                file_object.write(row)
        connection.close()

    def load(self):
        self.jar.load(self.copy_cookie_txt)
        os.remove(self.copy_cookie_file)
        os.remove(self.copy_cookie_txt)

    def decrypt_cookie_db(self):
        if self.platform == OperatingSystem.LINUX:
            import keyring
            from Crypto.Protocol.KDF import PBKDF2
            salt = b'saltysalt'
            length = 16
            # If running Chrome on OSX
            if sys.platform == 'darwin':
                my_pass = keyring.get_password('Chrome Safe Storage', 'Chrome')
                my_pass = my_pass.encode('utf8')
                iterations = 1003
                self.cookie_file = os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Cookies')

            # If running Chromium on Linux
            elif 'linux' in sys.platform:
                my_pass = 'peanuts'.encode('utf8')
                iterations = 1
                self.cookie_file = os.path.expanduser('~/.config/chromium/Default/Cookies')
            self.key = PBKDF2(my_pass, salt, length, iterations)
            return self.linux_decrypt_value

        elif self.platform == OperatingSystem.WINDOWS:
            return self.windows_decrypt_value

    def linux_decrypt_value(self, value, encrypted_value):
        if value or (encrypted_value[:3] != b'v10'):
            return value

        # Encrypted cookies should be prefixed with 'v10' according to the
        # Chromium code. Strip it off.
        encrypted_value = encrypted_value[3:]

        # Strip padding by taking off number indicated by padding
        # eg if last is '\x0e' then ord('\x0e') == 14, so take off 14.
        # You'll need to change this function to use ord() for python2.
        def clean(x):
            return x[:-ord(x[-1])].decode('utf8')

        from Crypto.Cipher import AES
        iv = b' ' * 16
        cipher = AES.new(self.key, AES.MODE_CBC, IV=iv)
        decrypted = cipher.decrypt(encrypted_value)
        return clean(decrypted)

    def windows_decrypt_value(self, null, value):
        try:
            import win32crypt
        except ImportError:
            raise Exception("You need to download Pywin32 for this import.  "
                            "Go to http://sourceforge.net/projects/pywin32/files/pywin32/Build%20220/"
                            " and download it for your version of Python.")
        return win32crypt.CryptUnprotectData(value, None, None, None, 0)[1]


class Firefox(object):
    __metaclass__ = CookieJar
    platform = None
    cookie_file = None
    copy_cookie_file = "ff_cookies.sqlite"
    copy_cookie_txt = "ff_cookies.txt"
    jar = cookielib.MozillaCookieJar()

    def __init__(self):
        self.detect_browser()
        if self.cookie_file:
            self.format_cookie()
            self.load()

    def detect_browser(self):
        cookie_file = None
        if self.platform == OperatingSystem.LINUX:
            cookie_file = os.path.expanduser('~/.mozilla/firefox/*.default/cookies.sqlite')
        elif self.platform == OperatingSystem.WINDOWS:
            cookie_file = \
                (
                    glob.glob(
                        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Mozilla Firefox/profile/cookies.sqlite')) or
                    glob.glob(
                        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''),
                                     'Mozilla Firefox/profile/cookies.sqlite')) or
                    glob.glob(
                        os.path.expanduser(r'~\AppData\Roaming\Mozilla\Firefox\Profiles\*.default\cookies.sqlite')))
            if cookie_file:
                cookie_file = cookie_file[0]
        if os.path.exists(cookie_file):
            self.cookie_file = cookie_file

    def format_cookie(self):
        bool_list = ['FALSE', 'TRUE']
        shutil.copy2(self.cookie_file, self.copy_cookie_file)
        connection = sqlite3.connect(self.copy_cookie_file)
        cursor = connection.cursor()
        try:
            cursor.execute('SELECT host, path, isSecure, expiry, name, value FROM moz_cookies')
        except sqlite3.DatabaseError:
            raise Exception("Your SQLite3 package in your Python installation is out of date.  "
                            "Resolution: http://www.obsidianforensics.com/blog/upgrading-python-sqlite")
        with open(self.copy_cookie_txt, 'w') as file_object:
            file_object.write('# Netscape HTTP Cookie File\n'
                              '# http://www.netscape.com/newsref/std/cookie_spec.html\n'
                              '# This is a generated file!  Do not edit.\n')

            for item in cursor.fetchall():
                row = '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (item[0], bool_list[item[0].startswith('.')],
                                                        item[1], bool_list[item[2]], item[3], item[4], item[5])
                file_object.write(row)

            session_cookie_path = os.path.join(os.path.dirname(self.cookie_file), 'sessionstore.js')
            if os.path.exists(session_cookie_path):
                try:
                    json_data = json.loads(open(session_cookie_path, 'rb').read().strip('()'))
                except:
                    pass
                else:
                    if 'windows' in json_data:
                        for window in json_data['windows']:
                            if 'cookies' in window:
                                for cookie in window['cookies']:
                                    row = "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (cookie.get('host', ''),
                                                                            bool_list[
                                                                                cookie.get('host', '').startswith('.')], \
                                                                            cookie.get('path', ''), False,
                                                                            str(int(time.time()) + 3600 * 24 * 7), \
                                                                            cookie.get('name', ''),
                                                                            cookie.get('value', ''))
                                    file_object.write(row)
        connection.close()

    def load(self):
        self.jar.load(self.copy_cookie_txt)
        os.remove(self.copy_cookie_file)
        os.remove(self.copy_cookie_txt)
