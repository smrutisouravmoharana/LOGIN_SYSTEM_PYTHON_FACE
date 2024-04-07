import mysql.connector


class MySqlConnection:
    def __init__(self):
        self.conn = mysql.connector.connect(host="localhost",
    user = "root",
    password = "Orive@123",
    database = "orivehrm")
        self.cur = self.conn.cursor()
    def insert(self, sql_query, values):
        self.cur.execute(sql_query, values)
        self.conn.commit()
    def read(self, sql_query):
        self.cur.execute(sql_query)
        rows = self.cur.fetchall()
        return rows
    def create(self, sql_query):
        self.cur.execute(sql_query)
        self.conn.commit()
    def update(self, sql_query, values):
        self.cur.execute(sql_query, values)
        self.conn.commit()
    def delete(self, sql_query, values):
        self.cur.execute(sql_query, values)
        self.conn.commit()
    def close(self):
        self.cur.close()
        self.conn.close()
conn = MySqlConnection()

