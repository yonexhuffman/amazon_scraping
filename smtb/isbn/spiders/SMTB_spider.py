import scrapy
from isbn.items import SMTB_Item
import csv
import mysql.connector
from scrapy.utils.project import get_project_settings
from re import sub
import re
from decimal import Decimal
from scrapy import signals
from datetime import datetime
from .base_spider import BaseSpider  

#class SellSpider(BaseSpider):
class SMTB_spider(BaseSpider):
    name = "SMTB"
    log_name = name
    nCount = 0

    custom_settings = {
        'FEED_URI': name + datetime.today().strftime('_%Y%m%d.csv'),
        'FEED_FORMAT': 'csv'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start_requests(self):
        query = ("SELECT isbn10 FROM SMTB_Task")
        self.cursor.execute(query)

        url = 'http://www.sellmytextbooks.org/members/191/index.cfm?index=QUOTE'     
        count = 1   
        isbns = self.cursor.fetchall()
        for isbn in isbns:
            count = count + 1
            #if count > 2:
            #    break
            yield scrapy.FormRequest(url, callback=self.parse,
                                     headers={'Referer':'http://www.sellmytextbooks.org/members/191/index.cfm?index=SELL'},
                                     formdata={
                                         'ISBN' : isbn,
                                         'Submit': 'Check Price >>'
                                     },
                                     meta = {
                                         'isbn': isbn
                                     }
                                    )

    def parse(self, response):
        lists = response.xpath('//table//table//table//table')
        
        # there is no such a book
        if not lists:
            return

        # scrap from the book information
        pdf_title = ''.join(lists[0].xpath('tr[1]/td[2]/strong/text()').extract()).strip()
        if pdf_title:
            pdf_title = pdf_title.strip()
        pdf_author = ''.join(lists[0].xpath('tr[2]/td[2]/strong/text()').extract())
        if pdf_author:
            pdf_author = pdf_author.strip()
        pdf_isbn = ''.join(lists[0].xpath('tr[3]/td[2]/strong/text()').extract())

        book_list = []
        # scrap all schools price information
        tr_rows = lists[1].xpath('tr')[1:]
        for str_row in tr_rows:
            info = []
            info.append(str_row.xpath('td[2]/strong/text()').extract())
            info.append(str_row.xpath('td[3]/strong/text()').extract())
            info.append(str_row.xpath('td[3]//a/@href').extract_first())
            book_list.append(info)

        for book in book_list:
            item = SMTB_Item()
            item['ISBN10'] = pdf_isbn
            item['title'] = pdf_title
            item['author'] = pdf_author
            item['location'] = ''.join(book[1])
            item['price'] = ''.join(book[0])
            item['price'] = self.parse_price_str(item['price']) #Decimal(sub(r'[^\d.]', '', item['price']))
            linkHref = book[2]
            match_groups = re.match(r'.*walkin_id=([0-9]+)', linkHref)
            if match_groups:
                item['schoolId'] = match_groups[1]

            yield item
            sql = "CALL `enternity`.`insertSMTB`(%s, %s, %s, 0, '', %s, %s, %s)"
            try:
                self.cursorInsert.execute(sql, (item['ISBN10'], item['title'], item['author'], item['price'],item['schoolId'], self.lastUpdatedWSID))
                self.count_proc()
            except:
                print ("item isbn: %s, school Id %s was duplicated" % (item['ISBN10'], item['schoolId']))
                pass

