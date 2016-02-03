from utilities.connection import Connect

from httpmethods import Methods
import logging

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')


class Scraper(Connect):
	def __init__(self):
		logger = logging.getLogger(__name__)
		Connect.__init__(self, logger)


if __name__ == "__main__":
	# test = Scraper()
	# test.HTTP_mode = Methods.GET
	# test.url = "https://api.github.com/users/mralexgray/repos"
	# test.fetch()


	# test = Scraper()
	# test.HTTP_mode = Methods.GET
	# test.url = "https://www.dnsdynamic.org"
	# test.fetch()
	#
	# test.HTTP_mode = Methods.POST
	# test.url = "https://www.dnsdynamic.org/auth.php"
	# test.parameters = {'email': 'alexander.ward1@gmail.com',
	#                    'pass': 'alex3412'}
	# test.headers = {}
	# test.fetch()


	# test = Scraper()
	# test.HTTP_mode = Methods.GET
	# test.url = "http://imgsv.imaging.nikon.com/lineup/lens/zoom/normalzoom/af-s_dx_18-140mmf_35-56g_ed_vr/img/sample/sample1_l.jpg"
	# test.fetch()

	test = Scraper()
	test.HTTP_mode = Methods.GET
	test.use_per_proxy_count = 3
	test.proxy_pool = {"https": ["https://107.17.100.254:8080", "https://107.17.100.254:8081"],
	                   "http": ["http://1.1.1.1"]}
	test.url = "https://myip.dnsdynamic.org"
	print test.proxy_pool
	# print test.fetch()

