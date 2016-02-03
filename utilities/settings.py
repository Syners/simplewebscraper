from logging import INFO
import os

class Defaults(object):
    logging_level = INFO
    request_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/'
                      '19.0.1084.56 Safari/536.5',
        'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }
    download_path = os.getcwd()
    use_per_proxy_count = -1 #Infinite