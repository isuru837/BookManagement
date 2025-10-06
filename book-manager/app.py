import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import sqlite3
from pathlib import Path
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "books.db"
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"

app = Flask(__name__)
app.secret_key = "replace-this-with-a-random-secret"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Allowed image types
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not DB_PATH.exists():
        conn = get_db_connection()
        conn.execute(
            """
            CREATE TABLE books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                front_image TEXT,
                back_image TEXT
            )
            """
        )
        conn.commit()
        conn.close()

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    conn = get_db_connection()
    if q:
        query = f"%{q}%"
        rows = conn.execute(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ? ORDER BY id DESC",
            (query, query),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("index.html", books=rows, q=q)

@app.route("/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        year = request.form.get("year", "").strip()

        front_img = request.files.get("front_image")
        back_img = request.files.get("back_image")

        if not title or not author:
            flash("Title and author are required.", "danger")
            return redirect(url_for("add_book"))

        # handle image uploads
        front_filename = None
        back_filename = None

        if front_img and allowed_file(front_img.filename):
            front_filename = secure_filename(front_img.filename)
            front_img.save(os.path.join(app.config["UPLOAD_FOLDER"], front_filename))

        if back_img and allowed_file(back_img.filename):
            back_filename = secure_filename(back_img.filename)
            back_img.save(os.path.join(app.config["UPLOAD_FOLDER"], back_filename))

        try:
            year_int = int(year) if year else None
        except ValueError:
            flash("Year must be a number.", "danger")
            return redirect(url_for("add_book"))

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO books (title, author, year, front_image, back_image) VALUES (?, ?, ?, ?, ?)",
            (title, author, year_int, front_filename, back_filename),
        )
        conn.commit()
        conn.close()
        flash("Book added successfully.", "success")
        return redirect(url_for("index"))

    return render_template("add.html")

@app.route("/edit/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        year = request.form.get("year", "").strip()
        front_img = request.files.get("front_image")
        back_img = request.files.get("back_image")

        if not title or not author:
            flash("Title and author are required.", "danger")
            return redirect(url_for("edit_book", book_id=book_id))

        try:
            year_int = int(year) if year else None
        except ValueError:
            flash("Year must be a number.", "danger")
            return redirect(url_for("edit_book", book_id=book_id))

        front_filename = book["front_image"]
        back_filename = book["back_image"]

        # handle new uploads
        if front_img and allowed_file(front_img.filename):
            front_filename = secure_filename(front_img.filename)
            front_img.save(os.path.join(app.config["UPLOAD_FOLDER"], front_filename))

        if back_img and allowed_file(back_img.filename):
            back_filename = secure_filename(back_img.filename)
            back_img.save(os.path.join(app.config["UPLOAD_FOLDER"], back_filename))

        conn = get_db_connection()
        conn.execute(
            "UPDATE books SET title=?, author=?, year=?, front_image=?, back_image=? WHERE id=?",
            (title, author, year_int, front_filename, back_filename, book_id),
        )
        conn.commit()
        conn.close()
        flash("Book updated successfully.", "success")
        return redirect(url_for("index"))

    return render_template("edit.html", book=book)

@app.route("/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    flash("Book deleted.", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
