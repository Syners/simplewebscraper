from simplewebscraper import Browser, HTTPMethod, Scraper, ProxyPool

if __name__ == "__main__":

    example_GET = True
    example_GET_parameters = True
    example_POST = False
    example_Proxy = False
    example_cookie_import = False

    if example_GET:
        my_scraper = Scraper()
        my_scraper.HTTP_mode = HTTPMethod.GET
        my_scraper.url = "https://myip.dnsdynamic.org"
        print my_scraper.fetch()

    if example_GET_parameters:
        my_scraper = Scraper()
        my_scraper.HTTP_mode = HTTPMethod.GET
        my_scraper.parameters = {'InData': "75791",
                                 "submit": "Search"}
        my_scraper.url = "http://www.melissadata.com/lookups/GeoCoder.asp"
        print my_scraper.fetch()

    if example_POST:
        my_scraper = Scraper()
        my_scraper.HTTP_mode = HTTPMethod.POST
        my_scraper.parameters = {"email": "example@gmail.com",
                                 "pass": "samplepassword"}
        my_scraper.url = "https://www.dnsdynamic.org/auth.php"
        print my_scraper.fetch()

    if example_Proxy:
        my_scraper = Scraper()
        my_scraper.HTTP_mode = HTTPMethod.GET
        my_scraper.use_per_proxy_count = 5
        my_scraper.proxy_pool = ProxyPool.Hidester  #You can provide a group of proxies like this as well {"https": ["https://212.119.246.138:8080"],"http": []}
        my_scraper.url = "https://myip.dnsdynamic.org"
        print my_scraper.fetch()

    if example_cookie_import:
        my_scraper = Scraper()
        my_scraper.HTTP_mode = HTTPMethod.GET
        my_scraper.cookies = Browser.Chrome  # Chrome or Firefox
        my_scraper.url = "https://myip.dnsdynamic.org"
        print my_scraper.fetch()
