from connection import Connect


class Scraper(Connect):
    def __init__(self, log="simplescraper.log"):
        from logger import get_logger
        logger = get_logger(log, maxbytes=2147483648)
        Connect.__init__(self, logger)


class Browser(object):
    from cookies import Chrome, Firefox
    Chrome = Chrome
    Firefox = Firefox


class ProxyPool(object):
    from proxy_aggregators import Hidester
    Hidester = Hidester


class HTTPMethod(object):
    from enumerations import HTTPMethods
    GET = HTTPMethods.GET
    POST = HTTPMethods.POST