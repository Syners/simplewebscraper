from logging import INFO
import os

class Defaults(object):
    logging_level = INFO
    proxy_flag = False
    request_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/'
                      '19.0.1084.56 Safari/536.5',
        'Content-type': 'application/x-www-form-urlencoded'
    }
    download_path = os.getcwd()
