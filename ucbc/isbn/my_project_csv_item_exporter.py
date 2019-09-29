from scrapy.conf import settings
from scrapy.exporters import CsvItemExporter

class MyProjectCsvItemExporter(CsvItemExporter):

    def __init__(self, *args, **kwargs):
        if args[0].tell() > 0:
            kwargs['include_headers_line'] = False

        super(MyProjectCsvItemExporter, self).__init__(*args, **kwargs)