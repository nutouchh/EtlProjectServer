import pandas as pd
from sqlalchemy import create_engine
from django.conf import settings

class Loader:
    def load(self, df):

        db_conf = settings.DATABASES['reports']

        user = db_conf['USER']
        password = db_conf['PASSWORD']
        host = db_conf['HOST']
        port = db_conf.get('PORT', '1433')
        name = db_conf['NAME']
        driver = db_conf['OPTIONS']['driver']

        conn_str = (
            f"mssql+pyodbc://{user}:{password}@{host}:{port}/{name}"
            f"?driver={driver.replace(' ', '+')}"
        )

        engine = create_engine(conn_str)

        df.to_sql('sales', con=engine, if_exists='append', index=False)
