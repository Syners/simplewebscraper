from enumerations import HTTPMethods

#todo - Add blacklist sqlite db to prevent bad proxies from repeating

class ProxyPool(type):
	def __init__(cls, name, bases, d):
		type.__init__(cls, name, bases, d)
		cls._proxy_pool = dict()


class Hidester(object):
	__metaclass__ = ProxyPool

	def __init__(self):
		from connection import Connect

		self.__url = 'https://hidester.com/proxydata/php/data.php?mykey=data&offset=0&limit=1500&orderBy=latest_check&' \
					 'sortOrder=DESC&country=ALBANIA,ALGERIA,ANDORRA,ANGOLA,ARGENTINA,ARMENIA,AUSTRALIA,AUSTRIA,' \
					 'BANGLADESH,BELARUS,BELGIUM,BOLIVIA,CAMBODIA,BULGARIA,BRAZIL,CAMEROON,CHILE,CANADA,COLOMBIA,' \
					 'CROATIA,CZECH%20REPUBLIC,ECUADOR,EGYPT,ESTONIA,FRANCE,FINLAND,GEORGIA,GERMANY,GREECE,GUATEMALA,' \
					 'HONDURAS,HUNGARY,INDONESIA,ISRAEL,ITALY,JAPAN,KAZAKHSTAN,LEBANON,MACEDONIA,MALAYSIA,' \
					 'MALDIVES,MALI,MEXICO,MONTENEGRO,MYANMAR,NEPAL,NETHERLANDS,NEW%20ZEALAND,NIGERIA,NORWAY,PARAGUAY,' \
					 'PANAMA,PERU,PHILIPPINES,POLAND,ROMANIA,RUSSIAN%20FEDERATION,SATELLITE%20PROVIDER,SERBIA,SINGAPORE,' \
					 'SOUTH%20AFRICA,SPAIN,SWEDEN,TAIWAN,THAILAND,TRINIDAD%20AND%20TOBAGO,SWITZERLAND,TURKEY,UKRAINE' \
					 ',UNITED%20KINGDOM,UNITED%20STATES,VENEZUELA&port=&type=3&anonymity=7&ping=7&gproxy=2'
		self.scraper = Connect()

	def get_proxy_json(self):
		from convert_response import ToJSON
		self.scraper.url = self.__url
		self.scraper.HTTP_mode = HTTPMethods.GET
		return ToJSON(self.scraper.fetch())

	def generate_pool(self):
		proxies = self.get_proxy_json()
		proxy_pool = dict(https=[], http=[])
		for proxy in proxies:
			proxy_pool[proxy['type']].append("%s://%s:%s" % (proxy['type'], proxy['IP'], proxy['PORT']))
		return proxy_pool
