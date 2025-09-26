# models.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from Conexion.conexion import get_db_connection  # <- OJO: ruta correcta al archivo Conexion/conexion.py

class User(UserMixin):
    def __init__(self, id, nombre, email):
        self.id = id
        self.nombre = nombre
        self.email = email

    def get_id(self):
        return str(self.id)

# ---------- helpers MySQL que devuelven dict ----------
def get_user_by_id(uid: int):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, nombre, email, password_hash FROM usuarios WHERE id = %s",
        (uid,)
    )
    row = cur.fetchone()
    cur.close(); conn.close()
    return row  # dict o None

def get_user_by_email(email: str):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, nombre, email, password_hash FROM usuarios WHERE email = %s",
        (email,)
    )
    row = cur.fetchone()
    cur.close(); conn.close()
    return row  # dict o None

def create_user(nombre: str, email: str, password: str):
    pwd = generate_password_hash(password)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO usuarios (nombre, email, password_hash) VALUES (%s, %s, %s)",
        (nombre, email, pwd)
    )
    conn.commit()
    cur.close(); conn.close()
