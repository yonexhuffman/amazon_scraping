import scrapy
from isbn.items import UCBC_Item
import logging
from datetime import datetime
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider
from .base_spider import BaseSpider  

class UCBC_spider(BaseSpider):
    name = "UCBC"
    log_name = name

    store_if_fail = False

    utc_now = datetime.utcnow()
    
    custom_settings = {
        'FEED_URI': name + utc_now.strftime('_%Y%m%d.csv'),
        'FEED_FORMAT': 'csv',
        'FEED_EXPORT_FIELDS': [
            'ISBN10',
            'title',
            'author',
            'qty',
            'avgPrice',
            'lowestPrice',
            'lastUpdated'
        ],
    }

    curr_timestamp = ''

    yet = False

    # @classmethod
    # def from_crawler(cls, crawler, *args, **kwargs):
    #     from_crawler = super(UCBC_spider, cls).from_crawler
    #     spider = from_crawler(crawler, *args, **kwargs)
    #     crawler.signals.connect(spider.spider_idle, signal=scrapy.signals.spider_idle)
    #     return spider

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #dispatcher.connect(self.spider_idle, scrapy.signals.spider_idle)
        # pass

    def start_requests(self):
        sql = "select utc_timestamp() as curr_timestamp"
        self.cursor.execute(sql)
        curr_timestamps = self.cursor.fetchone()
        self.curr_timestamp = curr_timestamps[0]
        
        with open('curr_timestamp', 'w') as f:
            f.write(self.curr_timestamp.strftime("%Y-%m-%d %H:%M:%S"))

        for isbn in range(100, 999):
            yield self.start_request_with_isbn(isbn, (1000 - isbn))
        
    def start_request_with_isbn(self, isbn, priority):
        url = 'http://pc8.su.ucalgary.ca/search/index.cfm?formreturn=yes'
        logging.info("UCBC start search with number : " + str(isbn))
        return scrapy.FormRequest(url, callback=self.parse,
                                    headers={'Referer':'http://pc8.su.ucalgary.ca/search/index.cfm?formreturn=yes'},
                                    formdata={
                                        'title': '',
                                        'author': '',
                                        'isbn' : str(isbn)
                                    },
                                    meta = {
                                        'priority': priority,
                                        'isbn' : str(isbn)
                                    },
                                    priority = priority
                                    )

    def parse(self, response):
        priority = response.meta['priority']
        lists = response.xpath('./body/table/tr[3]/td/table[3]//table//tr')[1:]
        # with open('temp.html','wb') as f:
        #     f.write(response.body)

        if len(lists) == 0 and self.store_if_fail:
            self.store_with_fail(response.meta['isbn'])
            return

        for str_row in lists:
            detail_link = str_row.xpath('td[3]/span/a/@href').extract_first()
            detail_url = "http://pc8.su.ucalgary.ca/search/" + detail_link
            yield scrapy.FormRequest(detail_url, callback=self.parse_detail,
                                     headers={'Referer': response.request.url}, priority = priority)

            # isbn = ''.join(str_row.xpath('td[2]/b/a/text()').extract())
            # title = ''.join(str_row.xpath('td[3]/span/a/text()').extract())
            # author = ''.join(str_row.xpath('td[4]/i/text()').extract())

            # item = UcGalary2Book()
            # item['ISBN10'] = isbn
            # item['title'] = title
            # item['author'] = author
            # yield item
    def parse_detail(self, response):
        book_details = response.xpath('//table//table//table//tr')[1:]
        for book_detail in book_details:
            isbn   = ''.join(book_detail.xpath('td[1]//text()').extract()).strip()
            book_title = ''.join(book_detail.xpath('td[2]/span/@title').extract()).strip()
            if len(book_title) == 0:
                book_title = ''.join(book_detail.xpath('td[2]//text()').extract()).strip()
            author = ''.join(book_detail.xpath('td[3]//text()').extract()).strip()
            qty = ''.join(book_detail.xpath('td[4]//text()').extract()).strip()
            avgPrice = ''.join(book_detail.xpath('td[5]//text()').extract()).strip()
            lowestPrice = ''.join(book_detail.xpath('td[6]//text()').extract()).strip()

            item = UCBC_Item()
            item['ISBN10'] = isbn
            item['title'] = book_title
            item['author'] = author
            item['qty'] = qty
            item['avgPrice'] = self.parse_price_str(avgPrice)
            item['lowestPrice'] = self.parse_price_str(lowestPrice)
            item['lastUpdated'] = datetime.utcnow()
            yield item

            sql = "CALL `enternity`.`insertUCBC`(%s, %s, %s, %s, %s, %s, 0, %s)"
            try:
                self.cursorInsert.execute(sql, (item['ISBN10'],
                 item['title'], item['author'], item['qty'],
                 item['avgPrice'],item['lowestPrice'], self.lastUpdatedWSID))
                self.count_proc()
            except:
                pass
        pass
        
    def store_with_fail(self, isbn):
        logging.info("isbn " + isbn + " isn't exist")
        sql = "CALL `enternity`.`insertUCBC`(%s, %s, %s, %s, %s, %s, 0, %s)"
        try:
            self.cursorInsert.execute(sql, (isbn,
                '', '', 0,
                0,0, self.lastUpdatedWSID))
            self.count_proc()
        except Exception as e:
            logging.error('Error at %s', 'division', exc_info=e)
            pass
        logging.info("insert fail log done")

    # def spider_idle(self):
    #     print ("idle1")
    #     if not self.yet:
    #         self.yet = True
    #         self.crawler.engine.crawl(self.start_new_requests(), self)
    #         raise DontCloseSpider("..I prefer live spiders")
    #     pass