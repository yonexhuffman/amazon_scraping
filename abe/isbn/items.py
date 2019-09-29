# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class TutorialItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class AbeBook_Item(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    ISBN10  = scrapy.Field()
    itemPrice = scrapy.Field()
    shippingPrice = scrapy.Field()
    itemConditionLabel = scrapy.Field()
    itemConditionCode = scrapy.Field()
    coverLabel = scrapy.Field()
    qtyAvailable = scrapy.Field()
    seller = scrapy.Field()
    sellerLocation = scrapy.Field()
    starRating = scrapy.Field()
    shippingStandardFirst = scrapy.Field()
    shippingStandardAdditional = scrapy.Field()
    shippingStandardMinSpeed = scrapy.Field()
    shippingStandardMaxSpeed = scrapy.Field()
    shippingExpediateFirst = scrapy.Field()
    shippingExpediateAdditional = scrapy.Field()
    shippingExpediateMinSpeed = scrapy.Field()
    shippingExpediateMaxSpeed = scrapy.Field()
    currentBatchCount = scrapy.Field()
    recordIndex = scrapy.Field()
    description = scrapy.Field()
    timestamp = scrapy.Field()