# database.py

from flask_mysqldb import MySQL
import MySQLdb.cursors

mysql = MySQL()


def get_cursor():
    return mysql.connection.cursor(MySQLdb.cursors.DictCursor)


def commit():
    mysql.connection.commit()


def rollback():
    mysql.connection.rollback()