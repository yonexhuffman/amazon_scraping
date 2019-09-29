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

class AmazonBook_Item(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    ISBN10  = scrapy.Field()
    itemPrice = scrapy.Field()
    shippingPrice = scrapy.Field()
    itemCondition = scrapy.Field()
    seller = scrapy.Field()
    starRating = scrapy.Field()
    positiverating = scrapy.Field()
    minArrivalDate = scrapy.Field()
    maxArrivalDate = scrapy.Field()
    shippingLocation = scrapy.Field()
    lastScanTime = scrapy.Field()
    lastUpdatedWSID = scrapy.Field()

class SMTB_Item(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    ISBN10 = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    location = scrapy.Field()
    price = scrapy.Field()
    lastUpdated = scrapy.Field()
    schoolId = scrapy.Field()


class UCCL_Item(scrapy.Item):
    batchIndex = scrapy.Field()
    termID = scrapy.Field()
    termName = scrapy.Field()
    termYear = scrapy.Field()
    departmentID = scrapy.Field()
    department = scrapy.Field()
    courseID = scrapy.Field()
    course = scrapy.Field()
    sectionID = scrapy.Field()
    section = scrapy.Field()
    title = scrapy.Field()
    authors = scrapy.Field()
    ISBN10 = scrapy.Field()
    ISBN13 = scrapy.Field()
    copyright = scrapy.Field()
    edition = scrapy.Field()
    binding = scrapy.Field()
    listPrice = scrapy.Field()
    newPrice = scrapy.Field()
    usedPrice = scrapy.Field()
    avgPrice = scrapy.Field()
    req = scrapy.Field()
    lastUpdated = scrapy.Field()
    status = scrapy.Field()
    Semester = scrapy.Field()
    SemesterID = scrapy.Field()

class UCBC_Item(scrapy.Item):
    ISBN10 = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    qty = scrapy.Field()
    avgPrice = scrapy.Field()
    lowestPrice = scrapy.Field()
    lastUpdated = scrapy.Field()
    
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