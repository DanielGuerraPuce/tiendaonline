import os
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
from config import Config
from models import db, Producto, ProductoDigital, ProductoPerecible, ProductoFisico, Usuario
from auth import login_requerido, rol_requerido
from werkzeug.utils import secure_filename

# Carga las variables del archivo .env
load_dotenv()

app = Flask(__name__)

# --- CONFIGURACIÓN DE POSTGRESQL USANDO EL .ENV ---
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
# -------------------------------------------------

db.init_app(app)


def guardar_imagen(archivo):
    if not archivo or not archivo.filename:
        return None
    extension = archivo.filename.rsplit(".", 1)[-1].lower() if "." in archivo.filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("La imagen debe ser PNG, JPG, JPEG, GIF o WEBP.")
    nombre = secure_filename(archivo.filename)
    nombre = f"{uuid4().hex}_{nombre}"
    archivo.save(os.path.join(app.config["UPLOAD_FOLDER"], nombre))
    return nombre


def actualizar_imagen(producto):
    imagen = guardar_imagen(request.files.get("imagen"))
    if imagen:
        producto.imagen = imagen


@app.route("/")
def inicio():
    productos = Producto.query.filter_by(activo=True).all()
    return render_template("index.html", productos=productos)


@app.route("/producto/<int:producto_id>")
def detalle_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    return render_template("detalle.html", producto=producto)


@app.route("/productos/nuevo/fisico", methods=["GET", "POST"])
@rol_requerido("admin")
def nuevo_producto_fisico():
    if request.method == "POST":
        try:
            producto = ProductoFisico(
                codigo=request.form["codigo"],
                nombre=request.form["nombre"],
                precio_base=float(request.form["precio_base"]),
                stock=int(request.form["stock"]),
                peso_kg=float(request.form["peso_kg"]),
                costo_envio_por_kg=float(request.form["costo_envio_por_kg"])
            )
            actualizar_imagen(producto)
            db.session.add(producto)
            db.session.commit()
            flash(f"Producto físico {producto.nombre} creado correctamente.", "success")
            return redirect(url_for("inicio"))
        except ValueError:
            flash("Revisa que los campos numéricos tengan valores válidos.", "danger")
        except Exception:
            db.session.rollback()
            flash("Ocurrió un error. Verifica que el código no esté repetido.", "danger")
            
    return render_template("nuevo_fisico.html")


@app.route("/productos/nuevo/digital", methods=["GET", "POST"])
@rol_requerido("admin")
def nuevo_producto_digital():
    if request.method == "POST":
        try:
            producto = ProductoDigital(
                codigo=request.form["codigo"],
                nombre=request.form["nombre"],
                precio_base=float(request.form["precio_base"]),
                stock=int(request.form["stock"]),
                licencia=request.form["licencia"],
            )
            actualizar_imagen(producto)
            db.session.add(producto)
            db.session.commit()
            flash(f"Producto digital '{producto.nombre}' creado correctamente.", "success")
            return redirect(url_for("inicio"))
        except ValueError:
            flash("Revisa que los campos numéricos tengan valores válidos.", "danger")
        except Exception:
            db.session.rollback()
            flash("Ocurrió un error. Verifica que el código no esté repetido.", "danger")

    return render_template("nuevo_digital.html")


@app.route("/productos/nuevo/perecible", methods=["GET", "POST"])
@rol_requerido("admin")
def nuevo_producto_perecible():
    if request.method == "POST":
        try:
            producto = ProductoPerecible(
                codigo=request.form["codigo"],
                nombre=request.form["nombre"],
                precio_base=float(request.form["precio_base"]),
                stock=int(request.form["stock"]),
                dias_para_vencer=int(request.form["dias_para_vencer"]),
            )
            actualizar_imagen(producto)
            db.session.add(producto)
            db.session.commit()
            flash(f"Producto perecible '{producto.nombre}' creado correctamente.", "success")
            return redirect(url_for("inicio"))
        except ValueError:
            flash("Revisa que los campos numéricos tengan valores válidos.", "danger")
        except Exception:
            db.session.rollback()
            flash("Ocurrió un error. Verifica que el código no esté repetido.", "danger")

    return render_template("nuevo_perecible.html")


@app.route("/producto/<int:producto_id>/editar", methods=["GET", "POST"])
@rol_requerido("admin")
def editar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)

    if request.method == "POST":
        try:
            # Nota: Quitamos las comas al final de cada asignación para evitar crear tuplas
            producto.nombre = request.form["nombre"]
            producto.precio_base = float(request.form["precio_base"])
            producto.stock = int(request.form["stock"])
            actualizar_imagen(producto)
            
            db.session.commit()
            flash(f"Producto {producto.nombre} actualizado correctamente.", "success")
            return redirect(url_for("detalle_producto", producto_id=producto.id))
        except ValueError:
            flash("Revisa que los campos sean válidos.", "danger")
        except Exception:
            db.session.rollback()
            flash("Ocurrió un error al actualizar el producto.", "danger")

    return render_template("editar.html", producto=producto)


@app.route("/productos/<int:producto_id>/eliminar", methods=["POST"])
@rol_requerido("admin")
def eliminar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    producto.activo = False
    db.session.commit()
    flash(f"Producto '{producto.nombre}' desactivado del catálogo.", "success")
    return redirect(url_for("inicio"))


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        if Usuario.query.filter_by(email=email).first():
            flash("Ya existe una cuenta con ese correo.", "danger")
            return render_template("registro.html")

        usuario = Usuario(
            nombre=request.form["nombre"],
            email=email,
            rol="cliente",
        )
        usuario.set_password(request.form["password"])
        db.session.add(usuario)
        db.session.commit()

        flash("Cuenta creada correctamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.check_password(password):
            session["usuario_id"] = usuario.id
            session["usuario_nombre"] = usuario.nombre
            session["usuario_rol"] = usuario.rol
            flash(f"¡Bienvenido, {usuario.nombre}!", "success")
            return redirect(url_for("inicio"))
        else:
            flash("Correo o contraseña incorrectos.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("inicio"))


@app.route("/carrito/agregar/<int:producto_id>", methods=["POST"])
@login_requerido
def agregar_carrito(producto_id):
    producto = Producto.query.filter_by(id=producto_id, activo=True).first_or_404()
    carrito = session.get("carrito", {})
    clave = str(producto_id)
    carrito[clave] = carrito.get(clave, 0) + 1
    session["carrito"] = carrito
    flash(f"{producto.nombre} se agregó al carrito.", "success")
    return redirect(request.referrer or url_for("inicio"))


@app.route("/carrito")
@login_requerido
def ver_carrito():
    carrito = session.get("carrito", {})
    items = []
    total = 0.0
    for clave, cantidad in carrito.items():
        producto = Producto.query.filter_by(id=int(clave), activo=True).first()
        if producto and cantidad > 0:
            subtotal = producto.precio_final() * cantidad
            total += subtotal
            items.append({"producto": producto, "cantidad": cantidad, "subtotal": subtotal})
    return render_template("carrito.html", items=items, total=total)


@app.route("/carrito/eliminar/<int:producto_id>", methods=["POST"])
@login_requerido
def eliminar_carrito(producto_id):
    carrito = session.get("carrito", {})
    clave = str(producto_id)
    if clave in carrito:
        del carrito[clave]
        session["carrito"] = carrito
        flash("Producto quitado del carrito.", "success")
    return redirect(url_for("ver_carrito"))


if __name__ == "__main__":
    app.run(debug=True)