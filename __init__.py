from utilities.connection import Connect


class Scraper(Connect):
    def __init__(self, log="simplescraper.log"):
        from utilities.logger import get_logger
        logger = get_logger(log, maxbytes=2 * 1024 * 1024 * 1024)
        Connect.__init__(self, logger)


class Browser(object):
    from utilities.cookies import Chrome, Firefox
    Chrome = Chrome
    Firefox = Firefox


class ProxyPool(object):
    from utilities.proxy_aggregators import Hidester
    Hidester = Hidester


class HTTPMethod(object):
    from utilities.enumerations import HTTPMethods
    GET = HTTPMethods.GET
    POST = HTTPMethods.POST
