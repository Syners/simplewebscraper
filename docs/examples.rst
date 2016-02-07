Examples
========


GET request
-----------
A generic GET request.

.. code-block:: python

    from simplewebscraper import HTTPMethod, Scraper
    my_scraper = Scraper()
    my_scraper.HTTP_mode = HTTPMethod.GET
    my_scraper.url = "http://learnwebscraping.com"
    results = my_scraper.fetch()


GET request with parameters
---------------------------
Parameters will be automatically URL encoded and appended the end of the url provided.

.. code-block:: python

    from simplewebscraper import HTTPMethod, Scraper
    my_scraper = Scraper()
    my_scraper.HTTP_mode = HTTPMethod.GET
    my_scraper.parameters = {'param1': "value",
                             "param2": "value"}
    my_scraper.url = "http://learnwebscraping.com"
    results = my_scraper.fetch()


POST request
------------
A generic POST request.

.. code-block:: python

    from simplewebscraper import HTTPMethod, Scraper
    my_scraper = Scraper()
    my_scraper.HTTP_mode = HTTPMethod.POST
    my_scraper.parameters = {'param1': "value",
                             "param2": "value"}
    my_scraper.url = "http://learnwebscraping.com"
    results = my_scraper.fetch()

Proxy use
---------
Proxies can be allocated 1 of 2 ways.  The first way is to use the ProxyPool class which has built in proxy aggregators.  By
indicating that you want to use the first example, it will retrieve and populate your Proxy pool with up to date proxies
.  If however, you want to provide your own you can use example 2 where you provide a dictionary in that format.  Both
methods allow you to set the number of times a single proxy can be used.  By default its approximately 100,000, but you
can modify this number by following the sample code.

.. code-block:: python

    from simplewebscraper import HTTPMethod, Scraper, ProxyPool
    my_scraper = Scraper()
    my_scraper.HTTP_mode = HTTPMethod.GET
    my_scraper.use_per_proxy_count = 5 #Number of times the proxy will be used before rotating
    my_scraper.proxy_pool = ProxyPool.Hidester #Retrieves proxies and generates a proxy pool for you.
    my_scraper.url = "https://learnwebscraping.com"
    results = my_scraper.fetch()

.. code-block:: python

    from simplewebscraper import HTTPMethod, Scraper
    my_scraper = Scraper()
    my_scraper.HTTP_mode = HTTPMethod.GET
    my_scraper.use_per_proxy_count = 5 #Number of times the proxy will be used before rotating
    my_scraper.proxy_pool = {
                                "https": ["https://1.2.3.4:1234",],
                                "http": ["http://1.2.3.4:1234",]
                            }
    my_scraper.url = "https://learnwebscraping.com"
    results = my_scraper.fetch()


Modify request headers
----------------------
Sometimes modifying the request headers is very important to successfully scrape. By default your request headers will
look like this:

.. code-block:: python

    {'Connection': 'keep-alive', 'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.56 Safari/536.5'}

To modify your request headers follow this example:

.. code-block:: python

    from simplewebscraper import HTTPMethod, Scraper
    my_scraper = Scraper()
    my_scraper.HTTP_mode = HTTPMethod.GET
    my_scraper.url = "https://learnwebscraping.com"
    my_scraper.headers = {"User-Agent":"Some User agent string"}
    results = my_scraper.fetch()

Keep in mind that when changing the headers, it merges and overwrites fields.  It will not delete any entries in your headers if you only provide a select number of fields.

Parsing the results
-------------------
Depending on the data you scraped, the data returned will be a different data type.  The type is dependent on the content-type in the HTTP response header.

The data is handled the following ways based on the content-type:

=============  ========  ===============================================================
Content Type   Returned  Notes
=============  ========  ===============================================================
application/*  None      This will be downloaded to <workingdirectory>/<domain>/filename
image/*        None      This will be downloaded to <workingdirectory>/<domain>/filename
video/*        None      This will be downloaded to <workingdirectory>/<domain>/filename
text/*         String
=============  ========  ===============================================================

Exceptions:

================  ===========
Content Type      Returned
================  ===========
text/xml          XML Object
application/json  JSON Object
================  ===========

To inspect the content-type of the response header follow this example:

.. code-block:: python

    from simplewebscraper import HTTPMethod, Scraper
    my_scraper = Scraper()
    my_scraper.HTTP_mode = HTTPMethod.GET
    my_scraper.url = "https://learnwebscraping.com"
    my_scraper.fetch()

    print my_scraper.response_headers

