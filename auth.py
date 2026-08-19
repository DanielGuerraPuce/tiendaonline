from functools import wraps

from flask import flash, redirect, session, url_for


def login_requerido(func):
    @wraps(func)
    def decorada(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debes iniciar sesión para acceder a esa página.", "danger")
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return decorada


def rol_requerido(rol):
    def decorador(func):
        @wraps(func)
        def decorada(*args, **kwargs):
            if "usuario_id" not in session:
                flash("Debes iniciar sesión para acceder a esa página.", "danger")
                return redirect(url_for("login"))
            if session.get("usuario_rol") != rol:
                flash("No tienes permisos para acceder a esa página.", "danger")
                return redirect(url_for("inicio"))
            return func(*args, **kwargs)

        return decorada

    return decorador
