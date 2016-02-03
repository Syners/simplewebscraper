import cookielib
import os
import re
import requests  # pip install requests[security]
import sys

from adapters import SSLAdapter
from enumerations import HTTPMethods, OperatingSystem
import abc
import urllib
from convert_response import ToJSON, ToXML
from settings import Defaults
import gzip
import StringIO
import zlib
import logging
from proxy_aggregators import ProxyPool
import platform
import shutil
import sqlite3

requests.packages.urllib3.disable_warnings()


class Proxy(object):
    def __init__(self, logger):
        self.__pool = {}
        self.logger = logger
        self.logger.setLevel(Defaults.logging_level)
        self.__use_per_proxy_count = Defaults.use_per_proxy_count
        self.__current_proxy = {}

    @property
    def proxy_pool(self):
        return self.__pool

    @proxy_pool.setter
    def proxy_pool(self, new_pool):
        if isinstance(new_pool, ProxyPool):
            new_pool = new_pool().generate_pool()

        if isinstance(new_pool, dict) and ("http" in new_pool or "https" in new_pool):
            for protocol, proxies in new_pool.iteritems():
                self.__pool[protocol] = []
                for proxy in proxies:
                    if not (proxy.lower().startswith("http://") or proxy.lower().startswith("https://")):
                        raise ValueError
                    else:
                        self.__pool[protocol].append({'proxy': proxy, 'count': 0})
        else:
            raise TypeError

    @property
    def use_per_proxy_count(self):
        return self.__use_per_proxy_count

    @use_per_proxy_count.setter
    def use_per_proxy_count(self, count):
        if isinstance(count, int):
            self.__use_per_proxy_count = count
        else:
            raise TypeError

    def current_proxy(self, increment=False):
        if increment:
            self.__current_proxy = self.__update_proxy()
        return self.__current_proxy

    def expire_proxy(self, protocol):
        proxy_to_expire = self.current_proxy()[protocol]
        self.proxy_pool[protocol].pop(self.__find_pool_index(protocol, proxy_to_expire))
        self.__current_proxy[protocol] = ""

    def __find_pool_index(self, protocol, proxy):
        return dict((d["proxy"], i) for (i, d) in enumerate(self.proxy_pool[protocol]))[proxy]

    def __update_proxy(self):
        proxy_group = dict(https="", http="")
        if not self.__current_proxy:
            for protocol, proxy in self.proxy_pool.iteritems():
                try:
                    proxy_group[protocol] = proxy[0]["proxy"]
                    proxy[0]['count'] += 1
                except IndexError:
                    pass
        else:
            if self.use_per_proxy_count != -1:
                for protocol, proxy in self.__current_proxy.iteritems():
                    if proxy:
                        pool_index = self.__find_pool_index(protocol, proxy)
                        if self.proxy_pool[protocol][pool_index]["count"] == self.use_per_proxy_count:
                            self.proxy_pool[protocol].pop(pool_index)
                            if self.proxy_pool[protocol]:
                                self.proxy_pool[protocol][0]["count"] += 1
                                proxy_group[protocol] = self.proxy_pool[protocol][0]["proxy"]
                        else:
                            self.proxy_pool[protocol][pool_index]["count"] += 1
                            proxy_group[protocol] = self.proxy_pool[protocol][pool_index]["proxy"]
                    else:
                        self.proxy_pool[protocol][0]["count"] += 1
                        proxy_group[protocol] = self.proxy_pool[protocol][0]["proxy"]
            else:
                proxy_group = self.__current_proxy
        return proxy_group


class Connect(Proxy):
    def __init__(self, logger=logging.getLogger(__name__)):
        Proxy.__init__(self, logger)
        self.jar = cookielib.CookieJar()
        self.requestSession = requests.Session()
        self.requestSession.mount('https://', SSLAdapter())
        self.logger = logger
        self.logger.setLevel(Defaults.logging_level)

        self.__HTTP_mode_value = None
        self.__parameters = {}
        self.__url = ""
        self.__headers = self.requestSession.headers
        self.headers = Defaults.request_headers
        self.__response_headers = {}
        self.__download_path = Defaults.download_path

    @property
    def HTTP_mode(self):
        return self.__HTTP_mode_value

    @HTTP_mode.setter
    def HTTP_mode(self, mode):
        modes = [HTTPMethods.GET, HTTPMethods.POST, HTTPMethods.DELETE, HTTPMethods.PUT]
        if mode in modes:
            self.__HTTP_mode_value = mode

    @property
    def url(self):
        return self.__url

    @url.setter
    def url(self, url_name):
        self.__url = url_name

    @property
    def headers(self):
        return self.__headers

    @headers.setter
    def headers(self, new_header):
        if not isinstance(new_header, dict):
            raise TypeError
        self.__headers.update(new_header)

    @property
    def parameters(self):
        return self.__parameters

    @parameters.setter
    def parameters(self, params):
        if not isinstance(params, dict):
            raise TypeError
        self.__parameters = params

    @property
    def download_path(self):
        return self.__download_path

    @download_path.setter
    def download_path(self, path):
        self.__download_path = path

    def fetch(self):
        if not self.url:
            raise Exception

        if self.HTTP_mode == HTTPMethods.GET:
            connection = Get(self)
        elif self.HTTP_mode == HTTPMethods.POST:
            connection = Post(self)
        else:
            raise KeyError

        return connection.connect()


class AbstractConnection(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, connection_object):
        self.connection = connection_object

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def format_parameters(self, params):
        pass

    def download_file(self, content_type, content, **kwargs):
        filename = self.connection.url.split('/')[-1]
        extension = content_type.split('/')[1].lower()
        if '.' not in filename.lower():
            filename += '.%s' % extension
        if kwargs.pop('zip', False):
            data = StringIO.StringIO(content).read()
        else:
            data = content
        with open(os.path.abspath(os.path.join(self.connection.download_path, filename)), 'wb+') as objFile:
            objFile.write(data)

    def convert(self, response):
        content = None
        if response.headers:
            content = response.content
            if response.headers.get('Content-Encoding') == 'gzip':
                try:
                    content = gzip.GzipFile(fileobj=StringIO.StringIO(content)).read()
                except IOError:
                    content = content
            elif response.headers.get('Content-Encoding') == 'deflate':
                content = zlib.decompress(content)
            content_type = response.headers['content-type']
            if 'application/json' in content_type:
                content = ToJSON(content)
            elif 'text/xml' in content_type:
                content = ToXML(content)
            elif 'image/' in content_type:
                self.download_file(content_type, content)
            elif 'application/' in content_type:
                self.download_file(content_type, content, zip=True)

        return content


class Get(AbstractConnection):
    def __init__(self, connection_object):
        super(Get, self).__init__(connection_object)

    def format_parameters(self, params):
        params = self.connection.parameters
        if params:
            return "?%s" % urllib.urlencode(params)
        else:
            return ""

    def connect(self):
        url = self.connection.url
        url += self.format_parameters(self.connection.parameters)

        while 1:
            try:
                results = self.convert(
                    self.connection.requestSession.get(url, cookies=self.connection.jar,
                                                       headers=self.connection.headers,
                                                       proxies=self.connection.current_proxy(True),
                                                       verify=False, timeout=Defaults.connection_timeout_length,
                                                       stream=True))
                break
            except (
                    requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout,
                    requests.exceptions.TooManyRedirects, requests.exceptions.SSLError):
                protocol = re.match("(\w+)://", url).group(1)
                self.connection.expire_proxy(protocol)
        return results


class Post(AbstractConnection):
    def __init__(self, connection_object):
        super(Post, self).__init__(connection_object)
        self.connection = connection_object

    def format_parameters(self, params):
        return params

    def connect(self):
        url = self.connection.url

        while 1:
            try:
                results = self.convert(self.connection.requestSession.post(url,
                                                                           data=self.format_parameters(
                                                                               self.connection.parameters),
                                                                           cookies=self.connection.jar,
                                                                           headers=self.connection.headers,
                                                                           proxies=self.connection.current_proxy(True),
                                                                           verify=False,
                                                                           timeout=Defaults.connection_timeout_length))
                break
            except (
                    requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout,
                    requests.exceptions.TooManyRedirects, requests.exceptions.SSLError):
                protocol = re.match("(\w+)://", url).group(1)
                self.connection.expire_proxy(protocol)
        return results
        # data = urllib.urlencode(formData)
        # self.connection.requestSession.post(url, params=data, cookies=self.jar, headers=self.headers,
        #                                     proxies=proxyDict, verify=False, timeout=(10.0, 10.0))


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

    def __init__(self):
        pass


if __name__ == "__main__":
    Chrome()
