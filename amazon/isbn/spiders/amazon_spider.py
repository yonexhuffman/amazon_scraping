import scrapy
from isbn.items import AmazonBook_Item
import re
from datetime import datetime
from .base_spider import BaseSpider  

class AmazonSpider(scrapy.Spider):
    name = "amazon"
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
        isbns = [
            '080442957X',
            # '199957950X',
            # '0851310419'
        ]
        for isbn in isbns:
            url = 'https://www.amazon.ca/gp/offer-listing/{}?ie=UTF8'.format(isbn)
            yield scrapy.Request(url=url, callback=self.parse, 
                meta = {
                    'isbn': isbn
                },
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:66.0) Gecko/20100101 Firefox/66.0',
                'Cache-Control': 'max-age=0',
                'Upgrade-Insecure-Requests': '1',
                'Accept-Encoding': 'gzip, deflate'
            },)

    def parse(self, response):
        #html_file = open('amazon.html', 'w')
        #html_file.write(response.body.decode("utf-8"))
        #return
        isbn = response.request.meta['isbn']
        sellinfo_node_list = response.xpath('//div[@id="olpOfferList"]//div[contains(@class, "olpOffer")]')
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
            item['itemCondition'] = condition
            item['seller'] = seller_name
            
            if seller_rating != -2 and seller_is_just_launched == 0:
                item['starRating'] = self.parseRating(seller_stars_rating)
                item['positiverating'] = self.parsePrice(seller_positive_rating)

            item['shippingLocation'] = shipping_location_text

            # print(item)
            yield item

        # check next button
        next_button_link = response.xpath('//ul[@class="a-pagination"]/li[@class="a-last"]/a/@href').extract_first()
        if next_button_link:
            next_page_link = 'https://www.amazon.ca' + next_button_link
            yield scrapy.Request(url=next_page_link, callback=self.parse, meta = {'isbn': isbn},
                headers = {'Referer': response.request.url},)
    
    def parsePrice(self, priceText):
        if priceText is None:
            return ""
        return re.sub(r"[^0-9\.]", "", priceText)

    # 
    def parseRating(self, ratingClassName):
        z = re.match(r'.*a\-star\-(.*?)$', ratingClassName)
        if z:
            rating = z.groups()
            return rating[0].replace('-', '.')
        return 0
        pass
        