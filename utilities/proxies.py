from utilities.settings import Defaults
import socket
import re
from bs4 import BeautifulSoup
import logging


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

	def __update_proxy(self):
		proxy_group = dict(https="", http="")
		if not self.__current_proxy:
			for protocol, proxy in self.proxy_pool.iteritems():
				try:
					proxy_group[protocol] = proxy[0]["proxy"]
					proxy[0]['count'] +=1
				except IndexError:
					pass
		else:
			if self.use_per_proxy_count != -1:
				for protocol, proxy in self.__current_proxy.iteritems():
					if proxy:
						pool_index = dict((d["proxy"], i) for (i, d) in enumerate(self.proxy_pool[protocol]))[proxy]

						if self.proxy_pool[protocol][pool_index]["count"] == self.use_per_proxy_count:
							self.proxy_pool[protocol].pop(pool_index)
							if self.proxy_pool[protocol]:
								self.proxy_pool[protocol][0]["count"] += 1
								proxy_group[protocol] = self.proxy_pool[protocol][0]["proxy"]
						else:
							self.proxy_pool[protocol][pool_index]["count"] += 1
							proxy_group[protocol] = self.proxy_pool[protocol][pool_index]["proxy"]
			else:
				proxy_group = self.__current_proxy
		return proxy_group

class getHideMyAssProxies(object):
	"""
	  Anonymity levels - applies for http/https proxies only.
	* Level 1: No anonymity; remote host knows your IP and knows you are using proxy.
	* Level 4: Low anonymity; remote host does not know your IP, but it knows you are using proxy.
	* Level 8: Medium anonymity; remote host knows you are using proxy, and thinks it knows your IP, but this is not yours (this is usually a multihomed proxy which shows its inbound interface as REMOTE_ADDR for a target host).
	* Level 16: High anonymity; remote host does not know your IP and has no direct proof of proxy usage (proxy-connection family header strings). If such hosts do not send additional header strings it may be considered as high-anonymous. If a high-anonymous proxy supports keep-alive you can consider it to be extremely-anonymous. However, such a host is highly possible to be a honey-pot.
	"""

	def __init__(self, connectHandle):
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.INFO)
		self.connectObject = connectHandle
		self.proxies = {'HTTP': {'Anon': {'None': [],
		                                  'Low': [],
		                                  'Medium': [],
		                                  'High': [],
		                                  'High +KA': []
		                                  }},
		                'HTTPS': {'Anon': {'None': [],
		                                   'Low': [],
		                                   'Medium': [],
		                                   'High': [],
		                                   'High +KA': []
		                                   }},
		                'SOCKS4/5': {'Anon': {'None': [],
		                                      'Low': [],
		                                      'Medium': [],
		                                      'High': [],
		                                      'High +KA': []
		                                      }}}
		self.get_table()
		if "We apologize. hidemyass.com is experiencing technical difficulties, please try back later." not in str(
				self.soup):
			self.parse_table()
		else:
			self.logger.warning("HideMyAss proxies temporarily unavailable.  Please try again in a few minutes.")

	def clean_text(self, text):
		return str(text.strip('\n'))

	def is_valid_ipv4_address(self, address):
		try:
			socket.inet_pton(socket.AF_INET, address)
		except AttributeError:
			try:
				socket.inet_aton(address)
			except socket.error:
				return False
			return address.count('.') == 3
		except socket.error:
			return False

		return True

	def get_table(self):
		self.connectObject.setDomain("http://proxylist.hidemyass.com/")
		self.soup = BeautifulSoup(self.connectObject.scrape())

	def parse_table(self):
		for table in self.soup.find_all('table', class_="hma-table"):
			trs = table.select('tbody > tr')
			cssDict = {'none': [], 'inline': []}

			try:
				for tr in trs:
					try:
						tds = tr.select('td')
						ip = tds[1]
					except:
						pass

					for style in [str(x) for x in ip.find('style').text.split('\n') if x]:
						try:
							class_, value = re.findall('\.(.*?)\{display:(.*?)\}', style)[0]
							cssDict[value].append(class_)
						except:
							pass

					rogueValues = re.findall('(\d{1,3}|\.|\.\d{1,3}|\d{1,3}\.)<s', str(ip))
					superrogueValues = re.findall('</span>(\d{1,3}|\.|\.\d{1,3})</span>', str(ip))

					ipAddr = []
					for span in ip.select('span > span'):
						if 'none' not in str(span):
							if span.text:
								if 'class' in str(span):
									cssClass = re.search('class="(.*?)"', str(span)).group(1)
									if cssClass not in cssDict['none']:
										ipAddr.append(str(span.text))
								else:
									ipAddr.append(str(span.text))

					previous = 'Dot'
					newIP = []
					try:
						for section in ipAddr:
							if section == '.':
								if previous == 'Dot':
									if rogueValues:
										newIP.append(rogueValues.pop(0))
									else:
										if superrogueValues:
											newIP.append(superrogueValues.pop(0))
								previous = 'Dot'
							else:
								if previous == 'Num':
									newIP.append(rogueValues.pop(0))
								previous = 'Num'
							newIP.append(section)
						if newIP[-1] == '.':
							if rogueValues:
								newIP.append(rogueValues.pop(0))
							else:
								if superrogueValues:
									newIP.append(superrogueValues.pop(0))
						if len(rogueValues) > 0:
							if rogueValues[-1] == '.':
								for value in rogueValues:
									newIP.insert(-1, value)
						for superrogueValue in superrogueValues:
							newIP.append(superrogueValue)

						ip = "".join(newIP)

						if self.is_valid_ipv4_address(ip):
							country = self.clean_text(tds[3].text)
							self.proxies[self.clean_text(tds[6].text)]['Anon'][self.clean_text(tds[7].text)].append(
								{'Socket':
									 ip + ":%s" % self.clean_text(tds[2].text), 'Country': country})

					except:
						pass
			except:
				pass
