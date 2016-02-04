import StringIO
import abc
import cookielib
import gzip
import logging
import os
import re
import urllib
import zlib

import errno
import requests  # pip install requests[security]
import json

from adapters import SSLAdapter
from convert_response import ToJSON, ToXML
from cookies import CookieJar
from db_manager import ProxyDB
from proxy_aggregators import ProxyPool
from settings import Defaults
from enumerations import HTTPMethods

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
            self.logger.info("Generating ProxyPool from %s." % new_pool.__name__)
            new_pool = new_pool().generate_pool()
            self.logger.info("ProxyPool ready")
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
                proxy_group[protocol] = proxy[0]["proxy"]
                try:
                    proxy_group[protocol] = proxy[0]["proxy"]
                    proxy[0]['count'] += 1
                except IndexError:
                    pass
        else:
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
    def cookies(self):
        return self.jar

    @cookies.setter
    def cookies(self, cookie_object):
        if isinstance(cookie_object, CookieJar):
            self.jar = cookie_object().jar
            self.logger.info("%s cookies loaded." % cookie_object.__name__)

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
        if os.path.exists(path):
            self.__download_path = path
        else:
            raise ValueError("Not a valid directory.")

    def fetch(self):
        if not self.url:
            raise Exception("Please supply a URL to fetch.")

        if self.HTTP_mode == HTTPMethods.GET:
            connection = Get(self)
        elif self.HTTP_mode == HTTPMethods.POST:
            connection = Post(self)
        else:
            raise KeyError("Please enter a valid HTTP method.  GET or POST.")

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

        domain = re.match(r"^.*://(.*)",self.connection.url).group(1).split('/')[0]

        filename = "%s/%s" % (domain,filename)
        if not os.path.exists(os.path.dirname(filename)):
            try:
                os.makedirs(os.path.dirname(filename))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

        path = os.path.abspath(os.path.join(self.connection.download_path, filename))
        with open(path, 'wb+') as objFile:
            objFile.write(data)
        self.connection.logger.info("Content parsed. File downloaded to \"%s\"." % path)

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
                if isinstance(content, json):
                    self.connection.logger.info("Content parsed. JSON object returned.")
                else:
                    self.connection.logger.info("Content parsed. JSON conversion failed.  String returned.")
            elif 'text/xml' in content_type:
                content = ToXML(content)
                self.connection.logger.info("Content parsed. XML object returned.")
            elif 'image/' in content_type:
                self.download_file(content_type, content)
                content = None
            elif 'application/' in content_type:
                self.download_file(content_type, content, zip=True)
                content = None

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
        protocol = re.match("(\w+)://", url).group(1)
        results = None
        while 1:
            proxies = self.connection.current_proxy(True)
            if len(proxies['http']) > 0 or len(proxies['https']) > 0:
                self.connection.logger.info("GET: %s via Proxy - %s." % (url, proxies[protocol]))
            else:
                self.connection.logger.info("GET: %s." % url)
            try:
                results = self.convert(
                    self.connection.requestSession.get(url, cookies=self.connection.jar,
                                                       headers=self.connection.headers,
                                                       proxies=proxies,
                                                       verify=False, timeout=Defaults.connection_timeout_length,
                                                       stream=True))
                self.connection.logger.info("GET: Successful.")
                break
            except (
                    requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout,
                    requests.exceptions.TooManyRedirects, requests.exceptions.SSLError):
                self.connection.logger.info("GET: Failed.")
                ProxyDB().blacklist_socket(protocol, proxies[protocol])
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
        protocol = re.match("(\w+)://", url).group(1)
        results = None
        while 1:
            proxies = self.connection.current_proxy(True)
            if len(proxies['http']) > 0 or len(proxies['https']) > 0:
                self.connection.logger.info("POST: %s via Proxy - %s." % (url, proxies[protocol]))
            else:
                self.connection.logger.info("POST: %s." % url)
            try:
                results = self.convert(self.connection.requestSession.post(url,
                                                                           data=self.format_parameters(
                                                                               self.connection.parameters),
                                                                           cookies=self.connection.jar,
                                                                           headers=self.connection.headers,
                                                                           proxies=proxies,
                                                                           verify=False,
                                                                           timeout=Defaults.connection_timeout_length))
                self.connection.logger.info("POST: Successful.")
                break
            except (
                    requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout,
                    requests.exceptions.TooManyRedirects, requests.exceptions.SSLError):
                self.connection.logger.info("POST: failed.")
                ProxyDB().blacklist_socket(protocol, proxies[protocol])
                self.connection.expire_proxy(protocol)
        return results
