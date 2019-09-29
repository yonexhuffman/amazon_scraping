import scrapy
from isbn.items import AbeBook_Item
import re
from datetime import datetime
from .base_spider import BaseSpider
import logging
import time

class AbeSpider(BaseSpider):
    name = "ABE"
    log_name = name

    utc_now = datetime.utcnow()

    custom_settings = {
        'FEED_URI': name + utc_now.strftime('_%Y%m%d.csv'),
        'FEED_FORMAT': 'csv',
        'FEED_EXPORT_FIELDS': [
            'ISBN10',
            'itemPrice',
            'shippingPrice',
            'itemConditionLabel',
            'itemConditionCode',
            'coverLabel',
            'qtyAvailable',
            'seller',
            'sellerLocation',
            'starRating',
            'shippingStandardFirst',
            'shippingStandardAdditional',
            'shippingStandardMinSpeed',
            'shippingStandardMaxSpeed',
            'shippingExpediateFirst',
            'shippingExpediateAdditional',
            'shippingExpediateMinSpeed',
            'shippingExpediateMaxSpeed',
            'currentBatchCount',
            'recordIndex',
            'timestamp',
            'description'
        ],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start_requests(self):
        isbns = []          # initializing empty array for all requests

        # Query for selecting tasks to perform:
        query = ("SELECT AbeBooksCom_TaskTracking.isbn10, AbeBooksCom_TaskTracking.batchCount FROM solutus_db_dev.AbeBooksCom_TaskTracking where itemStatus=200 ORDER BY lastUpdated ASC")
        self.cursor.execute(query)
        #isbns = self.cursor.fetchall()

        # Looping through all the results from database:
        for isbn_row in self.cursor:
            isbn = isbn_row[0]
            lastBatchCount = isbn_row[1]
            currentBatchCount = lastBatchCount+1

            # time.sleep(1)
            # initial request to abebooks.com
            url = 'https://www.abebooks.com/servlet/SearchResults?sts=t&cm_sp=SearchF-_-home-_-Results&sortby=17&an=&tn=&kn=&isbn={}'.format(
                isbn)
            yield scrapy.Request(url=url, callback=self.parse,
                                 meta={
                                     'isbn': isbn,
                                     'currentBatchCount': currentBatchCount,
                                     'recordIndex': 0,
                                 },
                                 cookies={
                                     'ab_optim': 'showA',
                                     'selectedShippingRate': 'CAN',
                                     'cmTPSet': 'Y',
                                     'AbeShipTo': 'CAN',
                                     'abe_vc': 17
                                 },
                                 headers={
                                     'Referer': 'https://www.abebooks.com/?cm_sp=TopNav-_-Results-_-Logo'},
                                errback=self.errback_parse
                                 )

    def errback_parse(self, failure):
        self.logger.error(repr(failure))
        request = failure.request
        isbn = request.meta['isbn']
        currentBatchCount = request.meta['currentBatchCount']
        self.update_tasktracking(isbn, currentBatchCount, -1)

    def update_tasktracking(self, isbn, currentBatchCount, status):
        if currentBatchCount == -1:
            sql = "UPDATE AbeBooksCom_TaskTracking set lastUpdated = utc_timestamp(), itemStatus = %s, lastUpdatedWSID = %s where isbn10 = %s"
            param = (status, self.lastUpdatedWSID, isbn,)
        else:
            sql = "UPDATE AbeBooksCom_TaskTracking set lastUpdated = utc_timestamp(), itemStatus = %s,batchCount = %s, lastUpdatedWSID = %s where isbn10 = %s"
            param = (status, currentBatchCount, self.lastUpdatedWSID, isbn,)
        try:
            logging.info("isbn {} , currentBatchCount = {}, status {}".format(
                isbn, currentBatchCount, status))
            self.cursorInsert.execute(sql, param)
            self.count_proc()
        except Exception as e:
            logging.error('Error at %s', 'division', exc_info=e)
            pass

    def parse(self, response):
        condition_labels = ['New', 'Used']

        isbn = response.meta['isbn']
        currentBatchCount = response.meta['currentBatchCount']
        recordIndex = response.meta['recordIndex']
        # get search result from book list
        book_div_list = response.xpath('//div[contains(@class, "cf result")]')

        # status update
        status = 200
        if len(book_div_list) == 0:
            status = -1

        self.update_tasktracking(isbn, currentBatchCount, status)

        # loop every book
        # recordIndex = 0
        for book_div in book_div_list:
            recordIndex += 1
            result_detail_div = book_div.xpath(
                './/div[contains(@class, "result-detail")]')

            title = result_detail_div.xpath(
                './h2/a/span/text()').extract_first()   # is there a class we can use to xpath?
            bsa = result_detail_div.xpath(
                './div[@id="product-bsa"]/div/text()').extract()

            itemConditionLabel = ''
            itemConditionCode = 1  # For new
            coverLabelList = []

            for every_bsa in bsa:
                if every_bsa in condition_labels:
                    itemConditionLabel = every_bsa
                    if itemConditionLabel == 'Used':
                        itemConditionCode = 3
                coverLabelList.append(every_bsa)

            # if len(bsa) >= 1:
            #     itemConditionLabel = bsa[0]
            # if len(bsa) >= 2:
            #     coverLabel = bsa[1]

            quantity_text = result_detail_div.xpath(
                './p[@id="quantity"]/text()').extract_first()  # 'Quantity Available: 1'
            # re.sub(r'[^0-9]', "", quantity_text)
            quantity = self.parse_price_str(quantity_text)

            seller_div = result_detail_div.xpath(
                './div[contains(@class, "bookseller-info")]')
            seller = seller_div.xpath('./p[1]/a/text()').extract_first()
            sellerLocation = seller_div.xpath(
                './p[1]/span/text()').extract_first()
            sellerLocation = re.sub(r'[\(\)]', "", sellerLocation)

            rating = seller_div.xpath('./p[2]/a/img/@alt').extract_first()
            # re.sub(r'[^0-9]', "", rating)
            rating = self.parse_price_str(rating)

            # get price

            buybox_div = book_div.xpath(
                './/div[contains(@class, "srp-item-buybox")]')
            book_price = buybox_div.xpath(
                './/div[@class="srp-item-price"]/text()').extract_first()
            # re.sub(r'[^0-9\.]', "", book_price)
            book_price = self.parse_price_str(book_price)
            shipping_price = buybox_div.xpath(
                './/span[@class="srp-item-price-shipping"]/text()').extract_first()
            if shipping_price:
                # re.sub(r'[^0-9\.]', "", shipping_price)
                shipping_price = self.parse_price_str(shipping_price)
            else:
                shipping_price = 0

            # destination
            buylink_list = buybox_div.xpath(
                './/a[@class="srp-item-buybox-link"]/@href').extract()
            # @TODO
            buylink = buylink_list[1]
            vid_groups = re.match(r'.*vid=(.*?)$', buylink)

            # get book description
            book_description = book_div.xpath(
                './/p[contains(@class, "clear-all")]/span/text()').extract_first()
            # print(book_description)

            # itemConditionLabel
            # itemConditionLabel = itemConditionLabel[0:10]
            coverLabel = ','.join(coverLabelList)
            if vid_groups:
                vid = vid_groups[1]
                shipRateUrl = 'https://www.abebooks.com/servlet/ShipRates?vid=' + vid

                item = AbeBook_Item()
                item['ISBN10'] = isbn
                item['currentBatchCount'] = currentBatchCount
                item['itemPrice'] = book_price
                item['shippingPrice'] = shipping_price
                item['itemConditionLabel'] = itemConditionLabel
                item['itemConditionCode'] = itemConditionCode
                item['coverLabel'] = coverLabel
                item['qtyAvailable'] = quantity
                item['seller'] = seller
                item['sellerLocation'] = sellerLocation
                item['starRating'] = rating
                item['description'] = book_description
                item['recordIndex'] = recordIndex

                # scrap shipping price
                #
                yield scrapy.Request(url=shipRateUrl, callback=self.parse_shipping,
                                     dont_filter=True,  # force request even though it is duplicated url
                                     meta={
                                         'item': item,
                                         'proxy_index': response.request.meta['proxy_index'] # reuse same proxy for shipping
                                     },
                                     cookies={
                                         'ab_optim': 'showA',
                                         'selectedShippingRate': 'CAN',
                                         'cmTPSet': 'Y',
                                         'AbeShipTo': 'CAN',
                                         'abe_vc': 17
                                     },
                                     headers={'Referer': response.request.url},
                                     )
            else:
                print("no vid")

        next_link = response.xpath('//a[@id="topbar-page-next"]')
        if next_link:
            rel_url = next_link.xpath('./@href').extract_first()
            url = 'https://www.abebooks.com' + rel_url
            yield scrapy.Request(url=url, callback=self.parse,
                                 meta={
                                     'isbn': isbn,
                                     'currentBatchCount': currentBatchCount,
                                     'recordIndex': recordIndex
                                 },
                                 cookies={
                                     'ab_optim': 'showA',
                                     'selectedShippingRate': 'CAN',
                                     'cmTPSet': 'Y',
                                     'AbeShipTo': 'CAN',
                                     'abe_vc': 17
                                 },
                                 headers={'Referer': response.request.url},
                                 errback=self.errback_parse
                                 )
        pass

    def parse_shipping(self, response):
        item = response.meta['item']
        #file = open('3.html', 'w')
        # file.write(response.text)
        # file.close()

        # first business day
        shippingStandardSpeed = response.xpath(
            '//table[@class="data"]//tr[1]/td[2]/text()').extract_first()
        match_groups = re.match(
            r'([0-9]+?)[ \-]+?([0-9]+?) ', shippingStandardSpeed)
        if match_groups:
            item['shippingStandardMinSpeed'] = match_groups[1]
            item['shippingStandardMaxSpeed'] = match_groups[2]

        # second business day
        shippingExpediateSpeed = response.xpath(
            '//table[@class="data"]//tr[1]/td[2]/text()').extract_first()
        match_groups = re.match(
            r'([0-9]+?)[ \-]+?([0-9]+?) ', shippingExpediateSpeed)
        if match_groups:
            item['shippingExpediateMinSpeed'] = match_groups[1]
            item['shippingExpediateMaxSpeed'] = match_groups[2]

        # price
        shippingStandardFirst = response.xpath(
            '//table[@class="data"]//tr[2]/td[2]/text()').extract_first()
        item['shippingStandardFirst'] = re.sub(
            r'[^0-9\.]', "", shippingStandardFirst)

        shippingStandardAdditional = response.xpath(
            '//table[@class="data"]//tr[3]/td[2]/text()').extract_first()
        item['shippingStandardAdditional'] = re.sub(
            r'[^0-9\.]', "", shippingStandardAdditional)

        shippingExpediateFirst = response.xpath(
            '//table[@class="data"]//tr[2]/td[3]/text()').extract_first()
        item['shippingExpediateFirst'] = re.sub(
            r'[^0-9\.]', "", shippingExpediateFirst)

        shippingExpediateAdditional = response.xpath(
            '//table[@class="data"]//tr[3]/td[3]/text()').extract_first()
        item['shippingExpediateAdditional'] = re.sub(
            r'[^0-9\.]', "", shippingExpediateAdditional)

        now = datetime.utcnow()
        item['timestamp'] = now
        yield item

        #sql = "CALL `insertAbeBooksCom`(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, utc_timestamp())"
        insertCurrentSql = """INSERT INTO AbeBooksCom_Current (isbn10,itemPrice,shippingPrice,itemConditionLabel,itemConditionCode,coverLabel,
        qtyAvailable,seller,sellerLocation,starRating,shippingStandardFirst,shippingStandardAdditional,shippingStandardMinSpeed,
        shippingStandardMaxSpeed,shippingExpediateFirst,shippingExpediateAdditional,shippingExpediateMinSpeed,shippingExpediateMaxSpeed,
        batchCount, lastUpdatedWSID, lastUpdated) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, utc_timestamp())
    ON DUPLICATE KEY UPDATE  isbn10=%s,itemPrice=%s,shippingPrice=%s,itemConditionLabel=%s,itemConditionCode=%s,coverLabel=%s,
    qtyAvailable=%s,seller=%s,sellerLocation=%s,starRating=%s,shippingStandardFirst=%s,shippingStandardAdditional=%s,shippingStandardMinSpeed=%s,
    shippingStandardMaxSpeed=%s,shippingExpediateFirst=%s,shippingExpediateAdditional=%s,shippingExpediateMinSpeed=%s,
    shippingExpediateMaxSpeed=%s,batchCount= %s, lastUpdatedWSID=%s, lastUpdated=utc_timestamp();
	"""
        insertHistorianSql = """
    INSERT INTO AbeBooksCom_Historian (isbn10,itemPrice,shippingPrice,itemConditionLabel,itemConditionCode,coverLabel,
    qtyAvailable,seller,sellerLocation,starRating,shippingStandardFirst,shippingStandardAdditional,shippingStandardMinSpeed,
    shippingStandardMaxSpeed,shippingExpediateFirst,shippingExpediateAdditional,shippingExpediateMinSpeed,shippingExpediateMaxSpeed,
    batchCount,lastUpdatedWSID, lastUpdated, recordIndex) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, utc_timestamp(), %s);
            """
        insertParamItem = (item['ISBN10'], item['itemPrice'], item['shippingPrice'], item['itemConditionLabel'], item['itemConditionCode'],
                           item['coverLabel'], item['qtyAvailable'], item['seller'], item['sellerLocation'], item['starRating'],
                           item['shippingStandardFirst'], item['shippingStandardAdditional'], item[
                               'shippingStandardMinSpeed'], item['shippingExpediateMaxSpeed'], item['shippingExpediateFirst'],
                           item['shippingExpediateAdditional'], item['shippingExpediateMinSpeed'], item['shippingExpediateMaxSpeed'],  item['currentBatchCount'])
        try:
            insertParam = insertParamItem + (self.lastUpdatedWSID,)
            insertCurrentParam = insertParam * 2

            if item['recordIndex'] == 1:
                self.cursorInsert.execute(insertCurrentSql, insertCurrentParam)
            self.cursorInsert.execute(
                insertHistorianSql, insertParam + (item['recordIndex'],))
            self.count_proc()
        except Exception as e:
            logging.error('Error at %s', 'division', exc_info=e)
            pass
