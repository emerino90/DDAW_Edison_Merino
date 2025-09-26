# app.py
# ============================================
# Inventario (SQLite) + Login (MySQL, Flask-Login)
# Semana 14 (Edison): base de datos MySQL -> desarrollo_web_edison
# ============================================

from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path

# ---- Login / Auth ----
from flask_login import (
    LoginManager, login_user, login_required, logout_user, current_user
)
from werkzeug.security import check_password_hash

# ---- Conexión MySQL y capa de usuarios ----
from models import User, get_user_by_id, get_user_by_email, create_user

# ---- Formularios (Flask-WTF) ----
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length, NumberRange, Email

# ============================================
# App & Config
# ============================================
app = Flask(__name__)
app.config["SECRET_KEY"] = "cambia_esta_clave_super_secreta"

# ============================================
# LoginManager (Flask-Login)
# ============================================
login_manager = LoginManager(app)
login_manager.login_view = "auth_login"
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id: str):
    row = get_user_by_id(int(user_id))  # dict o None
    if not row:
        return None
    return User(row["id"], row["nombre"], row["email"])  # objeto User para Flask-Login

# ============================================
# SQLite (Inventario)
# ============================================
DB_PATH = Path("inventario.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS productos(
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre   TEXT NOT NULL,
                precio   REAL NOT NULL CHECK(precio>=0),
                cantidad INTEGER NOT NULL CHECK(cantidad>=0)
            )
        """)
        conn.commit()

# ---------- Formularios ----------
class ProductoForm(FlaskForm):
    nombre   = StringField("Nombre", validators=[DataRequired(), Length(min=2, max=50)])
    precio   = DecimalField("Precio", places=2, validators=[DataRequired(), NumberRange(min=0)])
    cantidad = IntegerField("Cantidad", validators=[DataRequired(), NumberRange(min=0)])
    enviar   = SubmitField("Guardar")

class DeleteForm(FlaskForm):
    enviar = SubmitField("Eliminar")

# Formularios de autenticación
class RegisterForm(FlaskForm):
    nombre = StringField("Nombre", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(min=6, max=128)])
    enviar = SubmitField("Crear cuenta")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(min=6, max=128)])
    enviar = SubmitField("Iniciar sesión")

# ============================================
# Rutas INVENTARIO (SQLite)
# ============================================
@app.route("/")
@login_required
def home():
    with get_conn() as conn:
        filas = conn.execute(
            "SELECT id,nombre,precio,cantidad FROM productos ORDER BY id"
        ).fetchall()
    total_items = sum(r["cantidad"] for r in filas)
    total_valor = sum(r["cantidad"] * r["precio"] for r in filas)
    return render_template(
        "index.html",
        productos=filas,
        delete_form=DeleteForm(),
        total_items=total_items,
        total_valor=total_valor,
        titulo="Inventario (SQLite)"
    )

@app.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    form = ProductoForm()
    if form.validate_on_submit():
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO productos(nombre,precio,cantidad) VALUES (?,?,?)",
                (form.nombre.data.strip(), float(form.precio.data), int(form.cantidad.data))
            )
            conn.commit()
        flash("Producto creado.", "success")
        return redirect(url_for("home"))
    return render_template("product_form.html", form=form, titulo="Nuevo producto")

@app.route("/editar/<int:pid>", methods=["GET", "POST"])
@login_required
def editar(pid: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
    if not row:
        flash("Producto no encontrado.", "warning")
        return redirect(url_for("home"))

    form = ProductoForm()
    if request.method == "GET":
        form.nombre.data = row["nombre"]
        form.precio.data = row["precio"]
        form.cantidad.data = row["cantidad"]

    if form.validate_on_submit():
        with get_conn() as conn:
            conn.execute(
                "UPDATE productos SET nombre=?, precio=?, cantidad=? WHERE id=?",
                (form.nombre.data.strip(),
                 float(form.precio.data),
                 int(form.cantidad.data),
                 pid)
            )
            conn.commit()
        flash("Producto actualizado.", "success")
        return redirect(url_for("home"))

    return render_template("product_form.html", form=form, titulo=f"Editar (ID {pid})")

@app.route("/eliminar/<int:pid>", methods=["POST"])
@login_required
def eliminar(pid: int):
    form = DeleteForm()
    if form.validate_on_submit():
        with get_conn() as conn:
            conn.execute("DELETE FROM productos WHERE id=?", (pid,))
            conn.commit()
        flash(f"Producto ID {pid} eliminado.", "info")
    else:
        flash("Solicitud inválida.", "warning")
    return redirect(url_for("home"))

@app.route("/buscar")
@login_required
def buscar():
    q = (request.args.get("q") or "").strip().lower()
    with get_conn() as conn:
        filas = conn.execute("SELECT * FROM productos ORDER BY id").fetchall()
    resultados = [p for p in filas if q in p["nombre"].lower()] if q else []
    total_items = sum(p["cantidad"] for p in resultados)
    total_valor = sum(p["cantidad"] * p["precio"] for p in resultados)
    return render_template(
        "index.html",
        productos=resultados,
        delete_form=DeleteForm(),
        total_items=total_items,
        total_valor=total_valor,
        q=q,
        titulo="Inventario (SQLite)"
    )

# ============================================
# Rutas AUTH (MySQL + Flask-Login)
# ============================================
@app.route("/auth/register", methods=["GET", "POST"])
def auth_register():
    if current_user.is_authenticated:
        return redirect(url_for("panel"))
    form = RegisterForm()
    if form.validate_on_submit():
        if get_user_by_email(form.email.data.strip()):
            flash("Ese email ya está registrado.", "warning")
        else:
            create_user(
                form.nombre.data.strip(),
                form.email.data.strip(),
                form.password.data
            )
            flash("Cuenta creada. Ahora inicia sesión.", "success")
            return redirect(url_for("auth_login"))
    return render_template("auth_register.html", form=form, titulo="Crear cuenta")

@app.route("/auth/login", methods=["GET", "POST"])
def auth_login():
    if current_user.is_authenticated:
        return redirect(url_for("panel"))
    form = LoginForm()
    if form.validate_on_submit():
        row = get_user_by_email(form.email.data.strip())  # dict
        if (not row) or (not row.get("password_hash")) or (not check_password_hash(row["password_hash"], form.password.data)):
            flash("Credenciales inválidas.", "danger")
        else:
            user = User(row["id"], row["nombre"], row["email"])  # OBJETO User
            login_user(user, remember=True)
            flash(f"Bienvenido, {user.nombre}.", "success")
            next_url = request.args.get("next") or url_for("panel")
            return redirect(next_url)
    return render_template("auth_login.html", form=form, titulo="Iniciar sesión")

@app.route("/auth/logout")
@login_required
def auth_logout():
    nombre = current_user.nombre
    logout_user()
    flash(f"Hasta luego, {nombre}.", "info")
    return redirect(url_for("auth_login"))

@app.route("/panel")
@login_required
def panel():
    return render_template("panel.html", titulo="Panel")

# ============================================
# Entrada
# ============================================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
