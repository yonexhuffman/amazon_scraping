import scrapy
from asn1crypto.util import extended_date
import csv
import re
from isbn.items import UCCL_Item
from decimal import Decimal
from re import sub
from statistics import mean
from datetime import datetime
from .base_spider import BaseSpider  

#class CalgaryBook_spider(BaseSpider):
class UCCL_spider(BaseSpider):
    name = "UCCL" #ucbc
    log_name = name
    nCount = 0
    batchNum = 0

    custom_settings = {
        'FEED_URI': name + datetime.today().strftime('_%Y%m%d.csv'),
        'FEED_FORMAT': 'csv'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start_requests(self):

        sql = "select IFNULL(max(batchNum), 0) as max_batch_num from CanadianUniversityTextList"
        self.cursor.execute(sql)
        batch_result = self.cursor.fetchone()
        self.batchNum = batch_result[0] + 1
        
        url = 'https://www.calgarybookstore.ca/buy_textbooks.asp'
        yield scrapy.Request(url=url, callback=self.parse_departments)

    def parse_departments(self, response):
        sel_term_list = response.xpath('//div[@id="course-selector"]//select[@id="fTerm"]//option')[1:]

        for sel_term in sel_term_list:
            value = ''.join(sel_term.xpath('@value').extract()).split('|')
            term_name = ''.join(sel_term.xpath('text()').extract())

            url = 'https://www.calgarybookstore.ca/textbooks_xml.asp?control=campus&campus={}&term={}'.format(value[0], value[1])
            yield scrapy.Request(url=url, callback=self.parse_course,
                                 headers={
                                 'Referer': 'https://www.calgarybookstore.ca/buy_textbooks.asp'},
                                 meta={'campus_id':value[0],
                                       'term_id': value[1],
                                       'term_name': term_name}
                                )
            #if self.nCounter > 10:
            #    break

    def parse_course(self, response):
        dep_list = response.xpath('//department')

        for dep in dep_list:
            dep_id = ''.join(dep.xpath('@id').extract())
            dep_abrev = ''.join(dep.xpath('@abrev').extract())
            dep_name = ''.join(dep.xpath('@name').extract())
            url = 'https://www.calgarybookstore.ca/textbooks_xml.asp?control=department&dept={}&term={}'.format(dep_id, response.request.meta['term_id'])

            yield scrapy.Request(url=url, callback=self.parse_section,
                                 headers={
                                     'Referer': 'https://www.calgarybookstore.ca/buy_textbooks.asp'},
                                 meta={'campus_id': response.request.meta['campus_id'],
                                       'term_id': response.request.meta['term_id'],
                                       'dep_id': dep_id,
                                       'term_name':response.request.meta['term_name'],
                                       'dep_abrev':dep_abrev,
                                       'dep_name':dep_name}
                                 )


    def parse_section(self, response):
        course_list = response.xpath('//course')
        for course in course_list:
            course_id = ''.join(course.xpath('@id').extract())
            course_name = ''.join(course.xpath('@name').extract())
            url = 'https://www.calgarybookstore.ca/textbooks_xml.asp?control=course&course={}&term={}'.format(course_id,
                                                                                                                response.request.meta['term_id'])
            yield scrapy.Request(url=url, callback=self.parse_files,
                                 headers={
                                     'Referer': 'https://www.calgarybookstore.ca/buy_textbooks.asp'},
                                 meta={'campus_id': response.request.meta['campus_id'],
                                       'term_id': response.request.meta['term_id'],
                                       'dep_id': response.request.meta['dep_id'],
                                       'term_name': response.request.meta['term_name'],
                                       'dep_abrev': response.request.meta['dep_abrev'],
                                       'dep_name': response.request.meta['dep_name'],
                                       'course_id': course_id,
                                       'course_name': course_name}
                                 )

    def parse_files(self, response):
        # with open('temp.html', 'wb') as f:
        #    f.write(response.body)
        section_list = response.xpath('//section')
        for section in section_list:
            section_id = ''.join(section.xpath('@id').extract())
            section_name = ''.join(section.xpath('@name').extract())
            section_instructor = ''.join(section.xpath('@instructor').extract())
            url = 'https://www.calgarybookstore.ca/textbook_express.asp?mode=2&step=2'

            yield scrapy.FormRequest(url, callback=self.parse_books,
                                 headers={'Referer': 'https://www.calgarybookstore.ca/buy_textbooks.asp'},
                                 formdata={
                                     'tbe-block-mode': '0',
                                     'selTerm': '{}|{}'.format(response.request.meta['campus_id'],
                                                               response.request.meta['term_id']),
                                     'selDept': '-1',
                                     'generate-book-list': 'Get Your Books',
                                     'sectionIds': section_id
                                 },
                                 meta={'campus_id': response.request.meta['campus_id'],
                                       'term_id': response.request.meta['term_id'],
                                       'dep_id': response.request.meta['dep_id'],
                                       'term_name': response.request.meta['term_name'],
                                       'dep_abrev': response.request.meta['dep_abrev'],
                                       'dep_name': response.request.meta['dep_name'],
                                       'course_id': response.request.meta['course_id'],
                                       'course_name': response.request.meta['course_name'],
                                       'section_id': section_id,
                                       'section_name': section_name,
                                       'section_instructor': section_instructor}
                                 )

        pass

    
    def parse_books(self, response):

        row_list = response.xpath('//div[@id="course-bookdisplay"]//table[@class="data hasrentals"]/tbody/tr[contains(@class, "course-")]')
        # if len(row_list) == 0:
        #    return
        #with open('temp.html', 'wb') as f:
        #    f.write(response.body)
        season_list = ['Winter', 'Spring', 'Summer', 'Fall']

        for book in row_list:
            book_detail = book.xpath('td[@class="book-desc"]')
            book_desc = ''.join(book_detail.xpath('span[@class="book-title"]/text()').extract())
            if book_desc == "No Textbooks Required":
                break

            book_author = ''.join(book_detail.xpath('span[@class="book-meta book-author"]/text()').extract())
            book_isbn = ''.join(book_detail.xpath('span[@class="book-meta book-isbn"]/span[@class="isbn"]/text()').extract())
            book_copyright = ''.join(book_detail.xpath('span[@class="book-meta book-copyright"]/text()').extract())
            book_edition = ''.join(book_detail.xpath('span[@class="book-meta book-edition"]/text()').extract())
            book_binding = ''.join(book_detail.xpath('span[@class="book-meta book-binding"]/text()').extract())
            book_status = book_detail.xpath('p[@class="book-req"]/text()').extract_first()

            book_detail = book.xpath('td[@class="book-pref"]')
            list_price = ''.join(book_detail.xpath('dl[@class="rental-price-info"]/dd[@class="list-price"]/span/text()').extract())

            #list_price = ''.join(book_detail.xpath('dl[@class="rental-price-info"]/dd[@class="list-price"]/span/text()').extract())
            price_list = book_detail.xpath('table[@class="rental-price-list"]//tr')

            newPrice = "0"
            usedPrice = "0"
            for price_info in price_list:
                labels = price_list[0].xpath('.//label/text()').extract()
                if len(labels) == 2:
                    if labels[0] == 'New':
                        newPrice = labels[1]
                    elif labels[0] == 'Used':
                        usedPrice = labels[1]
            
            newPrice = self.parse_price_str(newPrice)
            usedPrice = self.parse_price_str(usedPrice)

            price_list = [newPrice, usedPrice]
            new_price_list = filter(lambda val: val != 0, price_list)
            avgPrice = mean(new_price_list)

            book = UCCL_Item()
            #book['termID'] = '{}|{}'.format(response.request.meta['campus_id'], response.request.meta['term_id'])
            book['termID'] = response.request.meta['term_id']
            
            termName = response.request.meta['term_name']
            # split term name
            match_groups = re.match(r'(.*) ([0-9]+)', termName)
            if match_groups:
                book['termName'] = match_groups[0]
                book['termYear'] = match_groups[2]
            
            #if any(season in book['termName'] for season in season_list):
            #    book['Semester'] = season
            #    book['SemesterID'] = response.request.meta['campus_id']
            match_season = re.findall('Spring|Summer|Fall|Winter', book['termName'])

            if match_season:
                book['Semester'] = match_season[0]
                book['SemesterID'] = season_list.index(book['Semester']) + 1
            else:
                book['Semester'] = ''
                book['SemesterID'] = 0

            #book['SemesterID'] = response.request.meta['campus_id']

            book['departmentID'] = response.request.meta['dep_id']
            #book['department'] = '{}-{}'.format(response.request.meta['dep_abrev'], response.request.meta['dep_name'])
            book['department'] = response.request.meta['dep_abrev']
            book['courseID'] = response.request.meta['course_id']
            book['course'] = '{} {}'.format(response.request.meta['dep_name'], response.request.meta['course_name'])
            book['sectionID'] = response.request.meta['section_id']
            book['section'] = response.request.meta['section_name']
            book['title'] = book_desc
            book['authors'] = book_author

            book['ISBN10'] = ''
            book['ISBN13'] = ''
            if len(book_isbn) == 10:
                book['ISBN10'] = book_isbn
            elif len(book_isbn) == 13:
                book['ISBN13'] = book_isbn
            book['copyright'] = book_copyright
            book['edition'] = book_edition
            book['binding'] = book_binding
            book['listPrice'] = self.parse_price_str(list_price)
            book['status'] = book_status
            book['newPrice'] = newPrice
            book['usedPrice'] = usedPrice
            book['avgPrice'] = avgPrice

            batchNum = "0"
            yield book

            sql = """INSERT INTO `enternity`.`CanadianUniversityTextList`
            (`School`, `Year`, `TermName`, TermID, Semester, SemesterID ,
            DepartmentName, DepartmentID, CourseName, CourseID, CourseCode, SectionName, 
            SectionID, InstructorName, CourseIndex, ISBN10,ISBN13, 
            NewPrice, UsedPrice, NewAvgBuyPrice, ListedPrice, `Status`, batchNum, lastUpdatedWSID, lastUpdated ) 
            VALUES('University of Calgary', %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, utc_timestamp())"""
            
            try:
                self.cursor.execute(sql, (book['termYear'], book['termName'], book['termID'], book['Semester'],book['SemesterID'],
                book['department'], book['departmentID'], book['course'], book['courseID'], response.request.meta['course_name'], book['section'],
                book['sectionID'], book['title'], response.request.meta['campus_id'], book['ISBN10'], book['ISBN13'],
                book['newPrice'], book['usedPrice'], book['avgPrice'], book['listPrice'], book['status'], self.batchNum, self.lastUpdatedWSID
                ))
                self.count_proc()
            except:
                pass
            
