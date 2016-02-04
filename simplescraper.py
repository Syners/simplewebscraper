from utilities.connection import Connect
from enumerations import HTTPMethods
import logging
from utilities.proxy_aggregators import Hidester
from utilities.cookies import Chrome, Firefox

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')


class Scraper(Connect):
    def __init__(self):
        logger = logging.getLogger(__name__)
        Connect.__init__(self, logger)


# if __name__ == "__main__":
#     my_scraper = Scraper()
#     my_scraper.HTTP_mode = HTTPMethods.GET
#     # test.use_per_proxy_count = 5
#     my_scraper.proxy_pool = Hidester
#     # test.proxy_pool = {"https": ["https://212.119.246.138:8080"],"http": []}
#     my_scraper.cookies = Firefox  # Chrome or Firefox
#     my_scraper.url = "https://myip.dnsdynamic.org"
#     my_scraper.fetch()
