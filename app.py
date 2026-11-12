import os, sqlite3, secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, abort
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "partnerrent.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL, gender TEXT NOT NULL,
      age INTEGER NOT NULL, city TEXT NOT NULL,
      bio TEXT DEFAULT '', languages TEXT DEFAULT '',
      interests TEXT DEFAULT '', hourly_rate INTEGER DEFAULT 1000,
      photo_url TEXT DEFAULT '', is_companion INTEGER DEFAULT 1,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bookings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_id INTEGER NOT NULL REFERENCES users(id),
      companion_id INTEGER NOT NULL REFERENCES users(id),
      booking_type TEXT NOT NULL, plan TEXT NOT NULL,
      scheduled_at TEXT DEFAULT '', message TEXT DEFAULT '',
      amount INTEGER NOT NULL, status TEXT DEFAULT 'Pending',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS reports (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      reporter_id INTEGER NOT NULL REFERENCES users(id),
      reported_id INTEGER NOT NULL REFERENCES users(id),
      reason TEXT NOT NULL, created_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

@app.before_request
def csrf_token():
    session.setdefault("_csrf", secrets.token_urlsafe(24))

def csrf_check():
    if request.form.get("_csrf") != session.get("_csrf"):
        abort(400, "Invalid form token. Please refresh and try again.")

@app.context_processor
def inject_globals():
    return {"current_user": get_current_user(), "csrf": session.get("_csrf")}

def get_current_user():
    uid = session.get("user_id")
    return db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone() if uid else None

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not get_current_user():
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

@app.route("/")
def index():
    people = db().execute("SELECT * FROM users WHERE is_companion=1 ORDER BY id DESC LIMIT 6").fetchall()
    return render_template("index.html", people=people)

@app.route("/discover")
def discover():
    query = "SELECT * FROM users WHERE is_companion=1"
    params = []
    gender = request.args.get("gender", "")
    city = request.args.get("city", "").strip()
    max_rate = request.args.get("max_rate", "").strip()
    if gender in ("Woman", "Man", "Non-binary"):
        query += " AND gender=?"; params.append(gender)
    if city:
        query += " AND city LIKE ?"; params.append("%" + city + "%")
    if max_rate.isdigit():
        query += " AND hourly_rate<=?"; params.append(int(max_rate))
    query += " ORDER BY id DESC"
    people = db().execute(query, params).fetchall()
    return render_template("discover.html", people=people)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        csrf_check()
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        gender = request.form.get("gender","")
        city = request.form.get("city","").strip()
        age = request.form.get("age","")
        if not all([name,email,password,gender,city,age]) or not age.isdigit() or int(age) < 18:
            flash("Please complete all required fields. You must be at least 18.", "error")
            return render_template("register.html")
        if len(password) < 8:
            flash("Use a password with at least 8 characters.", "error")
            return render_template("register.html")
        try:
            cur = db().execute("""INSERT INTO users
              (name,email,password_hash,gender,age,city,bio,languages,interests,hourly_rate,photo_url,is_companion,created_at)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (name,email,generate_password_hash(password),gender,int(age),city,
               request.form.get("bio","").strip(),request.form.get("languages","").strip(),
               request.form.get("interests","").strip(),
               int(request.form.get("hourly_rate","1000") or 1000),
               request.form.get("photo_url","").strip(),1 if request.form.get("is_companion")=="on" else 0,
               datetime.utcnow().isoformat()))
            db().commit()
            session["user_id"] = cur.lastrowid
            flash("Welcome to PartnerRent. Your account is ready.", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        csrf_check()
        user = db().execute("SELECT * FROM users WHERE email=?", (request.form.get("email","").lower().strip(),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password","")):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/profile/<int:user_id>")
def profile(user_id):
    person = db().execute("SELECT * FROM users WHERE id=? AND is_companion=1", (user_id,)).fetchone()
    if not person: abort(404)
    return render_template("profile.html", person=person)

@app.route("/book/<int:companion_id>", methods=["GET","POST"])
@login_required
def book(companion_id):
    companion = db().execute("SELECT * FROM users WHERE id=? AND is_companion=1", (companion_id,)).fetchone()
    if not companion: abort(404)
    if companion["id"] == session["user_id"]:
        flash("You cannot book your own profile.", "error")
        return redirect(url_for("profile", user_id=companion_id))
    if request.method == "POST":
        csrf_check()
        kind = request.form.get("booking_type","Call")
        if kind not in ("Call","Public meetup"):
            abort(400)
        plan = request.form.get("plan","Intro call")
        allowed = {"Intro call":99, "Starter":499, "Weekly":999, "Monthly":1900, "Hourly meeting":int(companion["hourly_rate"])}
        amount = allowed.get(plan, 99)
        db().execute("""INSERT INTO bookings(customer_id,companion_id,booking_type,plan,scheduled_at,message,amount,created_at)
          VALUES(?,?,?,?,?,?,?,?)""",
          (session["user_id"],companion_id,kind,plan,request.form.get("scheduled_at",""),
           request.form.get("message","").strip(),amount,datetime.utcnow().isoformat()))
        db().commit()
        flash("Your request has been sent. Payment is not collected on this demo website.", "success")
        return redirect(url_for("dashboard"))
    return render_template("book.html", person=companion)

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    received = db().execute("""SELECT b.*, u.name AS other_name FROM bookings b
      JOIN users u ON u.id=b.customer_id WHERE b.companion_id=? ORDER BY b.id DESC""",(user["id"],)).fetchall()
    sent = db().execute("""SELECT b.*, u.name AS other_name FROM bookings b
      JOIN users u ON u.id=b.companion_id WHERE b.customer_id=? ORDER BY b.id DESC""",(user["id"],)).fetchall()
    return render_template("dashboard.html", received=received, sent=sent)

@app.route("/booking/<int:booking_id>/status", methods=["POST"])
@login_required
def booking_status(booking_id):
    csrf_check()
    status = request.form.get("status")
    if status not in ("Accepted","Declined","Completed"): abort(400)
    db().execute("UPDATE bookings SET status=? WHERE id=? AND companion_id=?",
                 (status,booking_id,session["user_id"]))
    db().commit()
    return redirect(url_for("dashboard"))

@app.route("/report/<int:user_id>", methods=["POST"])
@login_required
def report(user_id):
    csrf_check()
    if user_id == session["user_id"]: abort(400)
    db().execute("INSERT INTO reports(reporter_id,reported_id,reason,created_at) VALUES(?,?,?,?)",
                 (session["user_id"],user_id,request.form.get("reason","Safety concern")[:500],datetime.utcnow().isoformat()))
    db().commit()
    flash("Report submitted for review.", "success")
    return redirect(url_for("discover"))

@app.route("/terms")
def terms(): return render_template("terms.html")

@app.route("/sitemap.xml")
def sitemap():
    return app.response_class(render_template("sitemap.xml"), mimetype="application/xml")

@app.route("/robots.txt")
def robots():
    return app.response_class("User-agent: *\\nAllow: /\\nSitemap: /sitemap.xml\\n", mimetype="text/plain")

@app.errorhandler(404)
def not_found(e): return render_template("404.html"),404

init_db()
if __name__ == "__main__":
    app.run(debug=True)
