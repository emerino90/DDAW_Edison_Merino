# Conexion/conexion.py
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="desarrollo_web_edison",
        auth_plugin="mysql_native_password",
    )
