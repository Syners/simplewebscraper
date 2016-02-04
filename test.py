from simplewebscraper import Browser, ProxyPool, HTTPMethod, Scraper

if __name__ == "__main__":
    my_scraper = Scraper()
    my_scraper.HTTP_mode = HTTPMethod.GET
    # test.use_per_proxy_count = 5
    # my_scraper.proxy_pool = ProxyPool.Hidester #{"https": ["https://212.119.246.138:8080"],"http": []}
    my_scraper.cookies = Browser.Chrome  # Chrome or Firefox
    # my_scraper.url = "https://myip.dnsdynamic.org"
    my_scraper.url = "http://cfb.blob.core.windows.net/conceptfeedback/concepts/fullsize/52ea9738-22b4-47cc-8159-78dbf317e43d.jpg"
    # my_scraper.download_path = "C:\\"
    my_scraper.fetch()