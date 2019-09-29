import scrapy
from isbn.items import UCBC_Item
import logging
from datetime import datetime
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider
from .UCBC_spider import UCBC_spider  

class UCBC2_spider(UCBC_spider):
    name = "UCBC2"
    log_name = "UCBC"
    store_if_fail = True

    #timestamp = datetime.utcnow()

    utc_now = datetime.utcnow()

    custom_settings = {
        'FEED_URI': 'UCBC' + utc_now.strftime('_%Y%m%d.csv'),
        'FEED_FORMAT': 'csv'
    }

    def start_requests(self):
        timestamp_str = ''
        with open('curr_timestamp', 'r') as f:
            timestamp_str = f.read()
            #self.timestamp = datetime.fromisoformat(timestamp_str)
            self.timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

        sql = "select isbn10 FROM UCBC_Current WHERE lastUpdated < %s"
        self.cursor.execute(sql, (timestamp_str,))

        # for row in self.cursor:
        #     update_isbns.append(row[0])
        #yield self.start_request_with_isbn('123456789', 1)

        max_records = 1000000
        curr_record = 0
        for isbn in self.cursor:
            curr_record+= 1
            yield self.start_request_with_isbn(isbn[0], max_records - curr_record)

        