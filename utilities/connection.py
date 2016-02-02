import cookielib
import os

import requests  # pip install requests[security]
from adapters import SSLAdapter
from httpmethods import Methods
import abc
import urllib
from utilities.convert_response import ToJSON, ToXML
from utilities.settings import Defaults
import logging
import gzip
import StringIO
import zlib

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
requests.packages.urllib3.disable_warnings()


class Connect(object):
    def __init__(self, logger=logging.getLogger(__name__)):
        self.proxy_flag = Defaults.proxy_flag
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
        modes = [Methods.GET, Methods.POST, Methods.DELETE, Methods.PUT]
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

        if self.HTTP_mode == Methods.GET:
            connection = Get(self)
        elif self.HTTP_mode == Methods.POST:
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
                content = gzip.GzipFile(fileobj=StringIO.StringIO(content)).read()
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
        return self.convert(
            self.connection.requestSession.get(url, cookies=self.connection.jar, headers=self.connection.headers,
                                               proxies={},
                                               verify=False, timeout=(10.0, 10.0), stream=True))


class Post(AbstractConnection):
    def __init__(self, connection_object):
        super(Post, self).__init__(connection_object)
        self.connection = connection_object

    def format_parameters(self, params):
        return params

    def connect(self):
        url = self.connection.url
        return self.convert(self.connection.requestSession.post(url,
                                                                data=self.format_parameters(self.connection.parameters),
                                                                cookies=self.connection.jar,
                                                                headers=self.connection.headers, proxies={},
                                                                verify=False,
                                                                timeout=(10.0, 10.0)))

        # data = urllib.urlencode(formData)
        # self.connection.requestSession.post(url, params=data, cookies=self.jar, headers=self.headers,
        #                                     proxies=proxyDict, verify=False, timeout=(10.0, 10.0))
