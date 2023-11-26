import psycopg2
connect = psycopg2.connect(dbname='hackatondb', user='postgres',
                           password='123321', host='localhost')
cursor = connect.cursor()