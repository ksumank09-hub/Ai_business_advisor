"""
routes/auth.py
---------------
Registration, login, logout, and session-based auth guard.
"""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from database.database import db
from database.models import User

auth_bp = Blueprint("auth", __name__)


def login_required(view_func):
    """Decorator: redirect to login page if no user is in session, or if user not in DB."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        try:
            user = db.session.get(User, user_id)
            if not user:
                session.clear()
                flash("Your session has expired. Please log in again.", "warning")
                return redirect(url_for("auth.login"))
        except Exception:
            pass
        return view_func(*args, **kwargs)
    return wrapped


def admin_required(view_func):
    """Decorator: only allow users with role == 'admin'."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            flash("You do not have permission to view that page.", "danger")
            return redirect(url_for("dashboard.dashboard_home"))
        return view_func(*args, **kwargs)
    return wrapped


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # --- input validation ---
        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists.", "danger")
            return render_template("register.html")

        try:
            new_user = User(name=name, email=email, role="user")
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Something went wrong while creating your account. Please try again.", "danger")
            return render_template("register.html")

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        session["user_id"] = user.id
        session["user_name"] = user.name
        session["role"] = user.role
        flash(f"Welcome back, {user.name}!", "success")
        return redirect(url_for("dashboard.dashboard_home"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not new_password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template("forgot_password.html")

        if len(new_password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("forgot_password.html")

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("forgot_password.html")

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account found with this email address.", "danger")
            return render_template("forgot_password.html")

        try:
            user.set_password(new_password)
            db.session.commit()
            flash("Password reset successfully! Please log in with your new password.", "success")
            return redirect(url_for("auth.login"))
        except Exception:
            db.session.rollback()
            flash("An error occurred while resetting your password. Please try again.", "danger")
            return render_template("forgot_password.html")

    return render_template("forgot_password.html")
