import scrapy
from isbn.items import AmazonBook_Item
import re
from datetime import datetime
from .base_spider import BaseSpider  
import logging

class AmazonSpider(BaseSpider):
    name = "amazon_test"
    log_name = name
    custom_settings = {
        'FEED_URI': name + datetime.today().strftime('%Y%m%d.csv'),
        'FEED_FORMAT': 'csv',
        'FEED_EXPORT_FIELDS': [
            'ISBN10',
            'itemPrice',
            'shippingPrice',
            'itemCondition',
            'seller',
            'starRating',
            'positiverating',
            'minArrivalDate',
            'maxArrivalDate',
            'shippingLocation',
            'lastScanTime',
            'lastUpdatedWSID'
        ],
    }
    
    def start_requests(self):
        # isbns = [
        #     '080442957X',
        #     # '199957950X',
        #     # '0851310419'
        # ]
        
        query = ("SELECT isbn10 FROM abebookscom_tasktracking where itemStatus=200 ORDER BY lastUpdated ASC")
        self.cursor.execute(query)
        abe_isbn_rows = self.cursor

        last_query = ("SELECT isbn10 FROM amazonca_tasktracking ORDER BY isbn10 DESC LIMIT 1")
        self.cursor.execute(last_query)
        amazon_isbn_lastrecord = self.cursor
        for last_record in amazon_isbn_lastrecord:
            amazon_last_isbn = last_record[0]
            break
        
        list_count = 1
        list_index = 0

        b_scrapy_start = False
        for isbn_row in abe_isbn_rows:
            if list_index > list_count:
                break
            
            isbn = isbn_row[0]            
            if isbn != amazon_last_isbn:
                continue
            else:
                b_scrapy_start = True
                # continue

            if b_scrapy_start != False:
                continue
            url = 'https://www.amazon.ca/gp/offer-listing/{}?ie=UTF8'.format(isbn)
            list_index = list_index + 1
            yield scrapy.Request(url=url, callback=self.parse, 
                meta = {
                    'isbn': isbn 
                },
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:66.0) Gecko/20100101 Firefox/66.0',
                    'Cache-Control': 'max-age=0',
                    'Upgrade-Insecure-Requests': '1',
                    'Accept-Encoding': 'gzip, deflate'
                },
                errback=self.errback_parse)
    
    def errback_parse(self, failure):
        self.logger.error(repr(failure))
        request = failure.request
        isbn = request.meta['isbn']
        self.update_tasktracking(isbn, -1)
        print('isbn-->' + isbn + '-----' + 'status = -1')
        
    def update_tasktracking(self, isbn, status):
        sql = "INSERT INTO amazonca_tasktracking(isbn10 , lossSupplyPrice , availableQty , fluctuationIndex , riskIndex , itemStatus , lastUpdatedWSID , lastUpdated) VALUES (%s , %s , %s , %s , %s , %s , %s , utc_timestamp()) ON DUPLICATE KEY UPDATE isbn10=%s , lossSupplyPrice=%s , availableQty=%s , fluctuationIndex=%s , riskIndex=%s , itemStatus=%s , lastUpdatedWSID=%s , lastUpdated=utc_timestamp()"
        param = (isbn , '' , '' , '' , '' , status , self.lastUpdatedWSID)
        try:
            logging.info("isbn {} , status {}".format(isbn, status))
            self.cursorInsert.execute(sql, param)
            self.count_proc()
        except Exception as e:
            logging.error('Error at %s', 'division', exc_info=e)
        
    def parse(self, response):
        isbn = response.request.meta['isbn']
        sellinfo_node_list = response.xpath('//div[@id="olpOfferList"]//div[contains(@class, "olpOffer")]')
        # status update
        status = 200
        if len(sellinfo_node_list) == 0:
            status = -1
        print('RequestURL-->' + response.url)
        print('ResponseStatus-->' + str(status))
        self.update_tasktracking(isbn , status)

        for sellinfo in sellinfo_node_list:
            # price
            price_col_node = sellinfo.xpath('./div[contains(@class, "olpPriceColumn")]')
            price = price_col_node.xpath('./span[contains(@class, "olpOfferPrice")]/text()').extract_first().strip()
            shipping_price = price_col_node.xpath('./p[@class="olpShippingInfo"]//span[@class="olpShippingPrice"]/text()').extract_first()

            # item condition
            condition_col_node = sellinfo.xpath('./div[contains(@class, "olpConditionColumn")]')
            condition = condition_col_node.xpath('./div/span/text()').extract_first().strip()
            condition = re.sub(r'[^a-zA-Z0-9 \-]', "", condition)
            condition = re.sub('\s+', ' ', condition).strip()

            # conditionComment = condition_col_node.xpath('./div[contains(@class , "comments")]/div[contains(@class , "expandedNote")]/text()').extract_first()
            
            #seller information
            seller_col_node = sellinfo.xpath('./div[contains(@class, "olpSellerColumn")]')

            seller_name_node = seller_col_node.xpath('.//h3[contains(@class, "olpSellerName")]')
            img_alt = seller_name_node.xpath('./img/@alt').extract_first()
            
            if not img_alt:
                seller_is_amazon = 0
                seller_link_node = seller_name_node.xpath('./span/a')
                seller_link = seller_link_node.xpath('./@href').extract_first()
                seller_name = seller_link_node.xpath('./text()').extract_first()

                # check the just launched seller
                justlanched_node = seller_col_node.xpath('./p/b[@class="olpJustLaunched"]')
                if justlanched_node:
                    seller_rating = 0
                    seller_is_just_launched = 1
                else:
                    seller_rating = -1
                    seller_is_just_launched = 0
                    seller_stars_rating = seller_col_node.xpath('./p/i/@class').extract_first() # 'a-icon a-icon-star a-star-4-5'
                    seller_positive_rating = seller_col_node.xpath('./p/a/b/text()').extract_first() # '86% positive'
                    seller_num_rating = ''.join(seller_col_node.xpath('./p/text()').extract()).strip()

            else:
                seller_rating = -2
                seller_name = img_alt
                seller_is_amazon = 1

            # delivery information
            delivery_col_node = sellinfo.xpath('./div[contains(@class, "olpDeliveryColumn")]')
            delivery_info_lis = delivery_col_node.xpath('.//li')
            shipping_location_text = ''
            for delivery_info_li in delivery_info_lis:
                delivery_info = ''.join(delivery_info_li.xpath('.//text()').extract()).strip()
                shipping_location_text = delivery_info
                break
                            
            item = AmazonBook_Item()
            item['ISBN10'] = response.request.meta['isbn']
            item['itemPrice'] = self.parsePrice(price)
            item['shippingPrice'] = self.parsePrice(shipping_price)
            # item['conditionComment'] = conditionComment
            item['conditionComment'] = condition
            item['itemCondition'] = self.parseItemCondition(condition)
            item['seller'] = seller_name
            item['starRating'] = 0
            item['positiverating'] = 0
            if seller_rating != -2 and seller_is_just_launched == 0:
                item['starRating'] = self.parseRating(seller_stars_rating)
                item['positiverating'] = self.parsePrice(seller_positive_rating)

            item['shippingLocation'] = self.parseShippingLocation(shipping_location_text)
            item['lastScanTime'] = str(self.utc_now)
            item['lastUpdatedWSID'] = str(self.lastUpdatedWSID)
            yield item
            self.insertData(item)

        # check next button
        next_button_link = response.xpath('//ul[@class="a-pagination"]/li[@class="a-last"]/a/@href').extract_first()
        if next_button_link:
            next_page_link = 'https://www.amazon.ca' + next_button_link
            yield scrapy.Request(url=next_page_link, callback=self.parse, meta = {'isbn': isbn},
                headers = {'Referer': response.request.url},)
    
    def insertData(self , item):
        # insertCurrentSql = """ INSERT INTO amazonca_current (isbn10,itemPrice,shippingPrice,itemCondition,conditionComment,qtyAvailable,seller,starRating,positiveRating,minShippingSpeed,maxShippingSpeed,shippingLocation,lastUpdatedWSID, lastUpdated) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE isbn10=%s,itemPrice=%s,shippingPrice=%s,itemCondition=%s,conditionComment=%s,qtyAvailable=%s,seller=%s,starRating=%s,positiveRating=%s,minShippingSpeed=%s,maxShippingSpeed=%s,shippingLocation=%s,lastUpdatedWSID=%s, lastUpdated=%s; """
        insertCurrentSql = """ INSERT INTO amazonca_current (ama_book_id,isbn10,itemPrice,shippingPrice,itemCondition,conditionComment,qtyAvailable,seller,starRating,positiveRating,minShippingSpeed,maxShippingSpeed,shippingLocation,lastUpdatedWSID, lastUpdated) VALUES ('', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s); """

        insertHistorianSql = """ INSERT INTO amazonca_historian (ama_book_his_id,isbn10,itemPrice,shippingPrice,itemCondition,conditionComment,qtyAvailable,seller,starRating,positiveRating,minShippingSpeed,maxShippingSpeed,shippingLocation,lastUpdatedWSID, lastUpdated) VALUES ('', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s); """

        insertParamItem = (item['ISBN10'],item['itemPrice'],item['shippingPrice'],item['itemCondition'],item['conditionComment'],'',item['seller'],item['starRating'],item['positiverating'],'0','0',item['shippingLocation'],item['lastUpdatedWSID'],item['lastScanTime'])
        
        is_existParam = (item['ISBN10'],item['itemPrice'],item['shippingPrice'],item['itemCondition'],item['conditionComment'],item['seller'],item['starRating'],item['positiverating'],item['shippingLocation'],item['lastUpdatedWSID'])
        is_existQuery = ("SELECT COUNT(*) AS count FROM amazonca_current WHERE isbn10=%s,itemPrice=%s,shippingPrice=%s,itemCondition=%s,conditionComment=%s,seller=%s,starRating=%s,positiveRating=%s,shippingLocation=%s,lastUpdatedWSID=%s")
        self.cursor.execute(is_existQuery)
        exist_records_count = self.cursor
        exist_count = 0
        for record in exist_records_count:
            exist_count = record[0]
            break        

        try:
            insertParam = insertParamItem
            insertHisParam = insertParamItem
            if exist_count == 0:
                self.cursorInsert.execute(insertCurrentSql, insertParam)
                self.cursorInsert.execute(insertHistorianSql, insertHisParam)
                self.count_proc()
        except Exception as e:
            logging.error('Error at %s', 'division', exc_info=e)

    def parsePrice(self, priceText):
        if priceText is None:
            return ""
        return re.sub(r"[^0-9\.]", "", priceText)

    def parseRating(self, ratingClassName):
        z = re.match(r'.*a\-star\-(.*?)$', ratingClassName)
        if z:
            rating = z.groups()
            return rating[0].replace('-', '.')
        return 0
    
    def parseItemCondition(self , condition):
        condition_labels = ['Used - Good' , 'Used - Acceptable' , 'Used - Very Good' , 'New']
        itemConditionCode = -1
        if condition.find('Used') == -1:
            if condition.find('New') != -1:
                itemConditionCode = 11
        else:
            if condition == 'Used - Very Good':
                itemConditionCode = 2
            elif condition == 'Used - Good':
                itemConditionCode = 3
            elif condition == 'Used - Acceptable':
                itemConditionCode = 4
            else:
                itemConditionCode = 1
        if condition.find('LIKE NEW') != -1:
            itemConditionCode = 1
        elif condition.find('Very Good') != -1:
            itemConditionCode = 2
        elif condition.find('Good') != -1:
            itemConditionCode = 3
        elif condition.find('Acceptable') != -1:
            itemConditionCode = 4
        # return condition + '----------' + str(itemConditionCode)      
        return itemConditionCode
    
    def parseShippingLocation(self , shipping_location_text):
        splited_strings = shipping_location_text.split('.' , 1)
        parsed_shipping_location_text = ''
        if shipping_location_text.find('Ships from') != -1:
            parsed_shipping_location_text = shipping_location_text
            if len(splited_strings) > 0:
                parseString = splited_strings[0]
                if parseString.find(', ') != -1:
                    parsed_shipping_location_text = parseString.split(', ')[1]
                else:
                    parsed_shipping_location_text = parseString.replace("Ships from " , "")
        return parsed_shipping_location_text

    # def selenium_request(self , url , isbn):        
    #     # options = webdriver.ChromeOptions()
    #     # options.add_argument('headless')
    #     # options.add_argument('window-size=1920x1080')
    #     # options.add_argument("disable-gpu")
    #     # driver = webdriver.Chrome('C:/chromedriver.exe' , chrome_options=options)
    #     cookies = [
    #         { 'name': 'x-wl-uid' , 'value': '1tPgxDp+NqrwovBLa8X0mzVUZKGNYbwGJYGa4jeGeMmJS8k72T82FlMm45gl7J7ZBUPKNBYhjLhc=' , 'domain': '.amazon.ca' , 'path': '/' } , 
    #         { 'name': 'session-id-time' , 'value': '2082787201l' , 'domain': '.amazon.ca' , 'path': '/' } , 
    #         { 'name': 'session-id' , 'value': '143-5891381-0076228' , 'domain': '.amazon.ca' , 'path': '/' } , 
    #         { 'name': 'ubid-acbca' , 'value': '133-4689538-3444737' , 'domain': '.amazon.ca' , 'path': '/' } , 
    #         { 'name': 'session-token' , 'value': '18Qa5K0piKf8EE32dDD5KnjjYNhy640ZJ+e8DWvu8F767EdGw6qtGQLRNhW8gNonb+lhrvdxm5Wbitw4LrpSRsWeEryuvP8Ue62x0Vb925Sv15WTXpDc7fK2diZmakeamYq4DWJzZ1cnvB1CkY0m9L1ocx6LaetG5oV1+1SFXZ2kfIoW79OvYolumV1Vtmdozih8AcuxvXlvEpVPSBQTFY8zgs8+u0undc3ndqVZwYj28D+g9EyXm579blVaQYPg' , 'domain': '.amazon.ca' , 'path': '/' } , 
    #         { 'name': 'csm-hit' , 'value': 'tb:1CB8JATZ3GGA1M52Y9N0+s-5BHPNGMZ9AFN3548RPR4|1560129049626&t:1560129049626&adb:adblk_no' , 'domain': 'www.amazon.ca' , 'path': '/' }
    #     ]
    #     driver = webdriver.Chrome('C:/chromedriver.exe')
    #     driver.delete_all_cookies()
    #     try:
    #         driver.get(url)
    #         driver.implicitly_wait(1)
    #         for cookie in cookies:
    #             buffer_cookie = {'name': cookie['name'] , 'value': cookie['value'] , 'domain': cookie['domain'] , 'path': cookie['path'], 'secure':False}
    #             driver.add_cookie(buffer_cookie)                
    #         driver.get(url)
    #         driver.implicitly_wait(1)
    #         self.parseSeleniumDriver(driver , isbn)
    #     except TimeoutException:
    #         driver.close()
    #         print('Session Time Out !')
    #         print("Don't worry about it. Please execute the command.")
    
    # def parseSeleniumDriver(self , driver , isbn):
    #     sellinfo_node_list = driver.find_elements_by_xpath('//div[@id="olpOfferList"]//div[contains(@class, "olpOffer")]')
    #     list_index = 0
    #     for sellinfo in sellinfo_node_list:
    #         # price
    #         price_col_node = sellinfo.find_element_by_xpath('./div[contains(@class, "olpPriceColumn")]')
    #         price = price_col_node.find_element_by_xpath('./span[contains(@class, "olpOfferPrice")]').text.strip()

    #         print(price)
            