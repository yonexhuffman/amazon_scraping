
import mysql.connector
import scrapy
from scrapy.item import Item
from scrapy.http import Request
from scrapy.exceptions import CloseSpider
from scrapy import signals
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging
from scrapy.xlib.pydispatch import dispatcher
import pydispatch
from decimal import Decimal
from re import sub
from datetime import datetime

class BaseSpider(scrapy.Spider):
    lastUpdatedWSID = 0
    nCount = 0
    name = ''
    log_name = ''

    custom_settings = {
        'FEED_URI': 'base' + datetime.today().strftime('_%Y%m%d.csv'),
        'FEED_FORMAT': 'csv'
    }

    def __init__(self, *args, **kwargs):
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        log_filename = datetime.now().strftime(self.log_name + '_%Y%m%d.log')
        #csv_filename = datetime.now().strftime(self.name + '_%Y%m%d.csv')
        #settings.set('LOG_FILE', log_filename)
        configure_logging({'LOG_FILE': log_filename})

        #'FEED_FORMAT': 'csv', 'FEED_URI': 'UCBC.csv'

        self.connectDB()

    def connectDB(self):            
        settings=get_project_settings()
        DB_CREDS = settings.get('DB_CREDS')
        self.lastUpdatedWSID = settings.get('LAST_UPDATED_WSID', 0)
        self.cnx = mysql.connector.connect(user=DB_CREDS['user'], password=DB_CREDS['pass'], database=DB_CREDS['db'],
            host=DB_CREDS['host'])
        self.cursor = self.cnx.cursor()
        self.cursorInsert = self.cnx.cursor(buffered=True)
    
    def spider_closed(self, spider):
        self.cnx.commit()
        self.cnx.close()

    def parse_price_str(self, priceText):
        if priceText == 'N/A':
            return Decimal(0)
        return Decimal(sub(r'[^\d.]', '', priceText))
    
    def count_proc(self):
        self.nCount = self.nCount + 1
        if self.nCount % 10 == 0:
            self.cnx.commit()

    # @classmethod
    # def from_crawler(cls, crawler, *args, **kwargs):
    #     settings = crawler.settings
    #     return cls(settings)