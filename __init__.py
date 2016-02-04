import logging

from utilities.connection import Connect

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')

class Scraper(Connect):
    def __init__(self):
        logger = logging.getLogger(__name__)
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
