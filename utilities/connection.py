import cookielib
import os
import re
import requests  # pip install requests[security]
from adapters import SSLAdapter
from enumerations import HTTPMethods
import abc
import urllib
from convert_response import ToJSON, ToXML
from settings import Defaults
import gzip
import StringIO
import zlib
import logging
from proxy_aggregators import ProxyPool
from ccookies import CookieJar
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
    def cookies(self):
        return self.jar

    @cookies.setter
    def cookies(self, cookie_object):
        if isinstance(cookie_object, CookieJar):
            self.jar = cookie_object().jar

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


