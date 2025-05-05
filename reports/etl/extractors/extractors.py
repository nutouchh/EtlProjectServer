import pandas as pd

class ExcelExtractor:
    def extract(self, path):
        return pd.read_excel(path, dtype='object')

class OldExcelExtractor:
    def extract(self, path):
        return pd.read_excel(path, dtype='object', engine='xlrd')


class CSVExtractor:
    def extract(self, path):
        return pd.read_csv(path, dtype='object')