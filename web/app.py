from flask import Flask, request, render_template, redirect, send_file, session, abort
from ftplib import FTP, error_perm
from werkzeug.utils import secure_filename
from functools import wraps
from io import BytesIO
import os
import logging
from logging.handlers import WatchedFileHandler
import base64
import hmac
import hashlib

app = Flask(__name__)
app.secret_key = "usb_auth_project_key"

FTP_HOST = "127.0.0.1"
FTP_PORT = 21

LOG_FILE = "/opt/usb_auth/logs/auth.log"

handler = WatchedFileHandler(LOG_FILE)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

app.logger.setLevel(logging.INFO)
app.logger.addHandler(handler)


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            app.logger.warning(
                "SECURITY_ACCESS_DENIED ip=%s path=%s",
                request.remote_addr,
                request.path,
            )
            return redirect("/")
        return func(*args, **kwargs)
    return wrapper


def get_ftp():
    ftp = FTP()
    ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
    ftp.login(session["user"], session["pass"])
    return ftp


@app.route("/")
def index():
    return render_template("login.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/login/start", methods=["POST"])
def login_start():
    username = request.form.get("username")

    if not username:
        return "Missing username", 400

    challenge = base64.b64encode(os.urandom(32)).decode()

    session["challenge"] = challenge
    session["pending_user"] = username

    app.logger.info(
        "LOGIN_START user=%s ip=%s",
        username,
        request.remote_addr,
    )

    return {"challenge": challenge}


@app.route("/login/verify", methods=["POST"])
def login_verify():
    data = request.json

    username = data.get("username")
    password = data.get("password")
    response = data.get("response")

    challenge = session.get("challenge")

    if not challenge:
        return "Missing challenge", 400

    try:
        with open(f"/etc/webauthn/users/{username}.secret") as f:
            secret = f.read().strip()
    except Exception:
        app.logger.error("HMAC_SECRET_LOAD_FAIL user=%s", username)
        return "Auth failed", 401

    expected = base64.b64encode(
        hmac.new(
            secret.encode(),
            challenge.encode(),
            hashlib.sha256
        ).digest()
    ).decode()

    if not hmac.compare_digest(expected, response):
        app.logger.warning("HMAC_FAIL user=%s ip=%s", username, request.remote_addr)
        return "Auth failed", 401

    try:
        ftp = FTP()
        ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
        ftp.login(username, password)
        ftp.quit()
    except Exception:
        app.logger.error("FTP_AUTH_FAIL user=%s", username)
        return "FTP auth failed", 401

    session.clear()
    session["user"] = username
    session["pass"] = password

    app.logger.info("LOGIN_SUCCESS user=%s", username)

    return {"status": "ok"}


@app.route("/files")
@login_required
def files():
    try:
        ftp = get_ftp()
        file_list = ftp.nlst()
        ftp.quit()

        return render_template("dashboard.html", files=file_list)

    except Exception as e:
        app.logger.error("FILES_ERROR user=%s err=%s", session.get("user"), str(e))
        return "Error loading files", 500


@app.route("/upload", methods=["POST"])
@login_required
def upload():
    if "file" not in request.files:
        return "No file", 400

    file = request.files["file"]

    if file.filename == "":
        return "Empty filename", 400

    filename = secure_filename(file.filename)

    try:
        ftp = get_ftp()
        ftp.storbinary(f"STOR {filename}", file.stream)
        ftp.quit()

        return redirect("/files")

    except Exception as e:
        app.logger.error("UPLOAD_FAIL user=%s", session.get("user"))
        return "Upload failed", 500


@app.route("/download/<path:filename>")
@login_required
def download(filename):
    if ".." in filename or filename.startswith("/"):
        abort(400)

    try:
        ftp = get_ftp()

        buffer = BytesIO()
        ftp.retrbinary(f"RETR {filename}", buffer.write)
        ftp.quit()

        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=os.path.basename(filename),
        )

    except error_perm:
        return "FTP error", 500


@app.route("/delete/<path:filename>", methods=["POST"])
@login_required
def delete(filename):
    if ".." in filename or filename.startswith("/"):
        abort(400)

    try:
        ftp = get_ftp()
        ftp.delete(filename)
        ftp.quit()

        return redirect("/files")

    except Exception:
        return "Delete failed", 500


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.errorhandler(404)
def not_found(e):
    app.logger.warning("404 path=%s", request.path)
    return "Not found", 404


@app.errorhandler(500)
def server_error(e):
    app.logger.error("500 error")
    return "Server error", 500


if __name__ == "__main__":
    app.logger.info("SERVER_START port=8080")
    app.run(host="0.0.0.0", port=8080)
