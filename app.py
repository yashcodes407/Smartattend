from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import sqlite3, os, io, csv
from datetime import datetime, date
import qrcode

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import DictCursor
    DB_ERRORS = (sqlite3.IntegrityError, psycopg2.IntegrityError)
else:
    DB_ERRORS = (sqlite3.IntegrityError,)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smartattend-demo-change-this")
DB_PATH = os.path.join(os.path.dirname(__file__), "smartattend.db")
DEMO_USER = "teacher"
DEMO_PASSWORD = "1234"


class PostgresDB:
    def __init__(self, url):
        self.conn = psycopg2.connect(url, cursor_factory=DictCursor)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
        finally:
            self.conn.close()

    def execute(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query.replace("?", "%s"), params)
        return cur


def db():
    if USE_POSTGRES:
        return PostgresDB(DATABASE_URL)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as con:
        if USE_POSTGRES:
            con.execute("""CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                roll TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES students(id),
                marked_at TEXT NOT NULL,
                attendance_date TEXT NOT NULL,
                UNIQUE(student_id, attendance_date)
            )""")
        else:
            con.execute("""CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                marked_at TEXT NOT NULL,
                attendance_date TEXT NOT NULL,
                UNIQUE(student_id, attendance_date),
                FOREIGN KEY(student_id) REFERENCES students(id)
            )""")


@app.route("/")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    with db() as con:
        total = con.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        today = con.execute(
            "SELECT COUNT(*) FROM attendance WHERE attendance_date=?",
            (date.today().isoformat(),)
        ).fetchone()[0]
        recent = con.execute("""SELECT s.roll, s.name, s.class_name, a.marked_at
            FROM attendance a JOIN students s ON s.id=a.student_id
            WHERE a.attendance_date=? ORDER BY a.marked_at DESC LIMIT 8""",
            (date.today().isoformat(),)).fetchall()
    return render_template("dashboard.html", total=total, today=today,
        recent=recent, today_date=date.today().strftime("%d %b %Y"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == DEMO_USER and password == DEMO_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("home"))
        flash("Username ya password galat hai.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def require_login():
    return session.get("logged_in", False)


@app.route("/students", methods=["GET", "POST"])
def students():
    if not require_login():
        return redirect(url_for("login"))
    if request.method == "POST":
        roll = request.form.get("roll", "").strip()
        name = request.form.get("name", "").strip()
        class_name = request.form.get("class_name", "").strip()
        if not all([roll, name, class_name]):
            flash("Saari details bharna zaroori hai.")
        else:
            try:
                with db() as con:
                    query = """INSERT INTO students
                        (roll,name,class_name,created_at) VALUES(?,?,?,?)"""
                    params = (roll, name, class_name,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    if USE_POSTGRES:
                        cur = con.execute(query + " RETURNING id", params)
                        student_id = cur.fetchone()["id"]
                    else:
                        cur = con.execute(query, params)
                        student_id = cur.lastrowid
                flash(f"{name} add ho gaya. Ab QR code generate kar sakte ho.")
                return redirect(url_for("student_qr", student_id=student_id))
            except DB_ERRORS:
                flash("Ye roll number pehle se registered hai.")
    with db() as con:
        rows = con.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    return render_template("students.html", students=rows)


@app.route("/student/<int:student_id>/qr")
def student_qr(student_id):
    if not require_login():
        return redirect(url_for("login"))
    with db() as con:
        student = con.execute("SELECT * FROM students WHERE id=?",
            (student_id,)).fetchone()
    if not student:
        flash("Student nahi mila.")
        return redirect(url_for("students"))
    return render_template("qr.html", student=student)


@app.route("/student/<int:student_id>/qr.png")
def qr_png(student_id):
    if not require_login():
        return redirect(url_for("login"))
    with db() as con:
        student = con.execute("SELECT * FROM students WHERE id=?",
            (student_id,)).fetchone()
    if not student:
        return "Not found", 404
    img = qrcode.make(f"SMARTATTEND:{student['roll']}")
    out = io.BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return send_file(out, mimetype="image/png",
        download_name=f"{student['roll']}_QR.png")


@app.route("/scan")
def scan():
    if not require_login():
        return redirect(url_for("login"))
    return render_template("scan.html")


@app.route("/api/mark", methods=["POST"])
def api_mark():
    if not require_login():
        return jsonify(ok=False,
            message="Session expire ho gaya. Dobara login karein."), 401
    data = request.get_json(silent=True) or {}
    raw = (data.get("code") or "").strip()
    if not raw.startswith("SMARTATTEND:"):
        return jsonify(ok=False, message="Ye SmartAttend ka valid QR code nahi hai.")
    roll = raw.split(":", 1)[1].strip()
    with db() as con:
        student = con.execute("SELECT * FROM students WHERE roll=?",
            (roll,)).fetchone()
        if not student:
            return jsonify(ok=False,
                message="Is roll number ka student registered nahi hai.")
        now = datetime.now()
        try:
            con.execute("""INSERT INTO attendance
                (student_id, marked_at, attendance_date) VALUES(?,?,?)""",
                (student["id"], now.strftime("%Y-%m-%d %H:%M:%S"),
                 date.today().isoformat()))
        except DB_ERRORS:
            return jsonify(ok=False,
                message=f"{student['name']} ki attendance aaj pehle hi lag chuki hai.")
    return jsonify(ok=True,
        message=f"Attendance marked: {student['name']} ({student['roll']})")


@app.route("/attendance")
def attendance():
    if not require_login():
        return redirect(url_for("login"))
    selected = request.args.get("date", date.today().isoformat())
    with db() as con:
        rows = con.execute("""SELECT s.roll, s.name, s.class_name, a.marked_at
            FROM attendance a JOIN students s ON s.id=a.student_id
            WHERE a.attendance_date=? ORDER BY a.marked_at DESC""",
            (selected,)).fetchall()
    return render_template("attendance.html", rows=rows, selected=selected)


@app.route("/export")
def export():
    if not require_login():
        return redirect(url_for("login"))
    selected = request.args.get("date", date.today().isoformat())
    with db() as con:
        rows = con.execute("""SELECT s.roll, s.name, s.class_name, a.marked_at
            FROM attendance a JOIN students s ON s.id=a.student_id
            WHERE a.attendance_date=? ORDER BY a.marked_at DESC""",
            (selected,)).fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Roll Number", "Student Name", "Class", "Marked At", "Date"])
    for r in rows:
        writer.writerow([r["roll"], r["name"], r["class_name"], r["marked_at"], selected])
    mem = io.BytesIO(out.getvalue().encode("utf-8-sig"))
    return send_file(mem, mimetype="text/csv", as_attachment=True,
        download_name=f"SmartAttend_{selected}.csv")


# Gunicorn/Render ke liye startup par database tables banao.
init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
