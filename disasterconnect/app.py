"""DisasterConnect - academic prototype. Not a replacement for official emergency services."""
import os, sqlite3, uuid
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, g, send_from_directory, abort)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("DB_PATH", os.path.join(BASE, "disasterconnect.db"))
UPLOAD_DIR = os.path.join(BASE, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
S3_BUCKET = os.environ.get("S3_BUCKET")          # set this on EC2 (Phase 5)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
ALLOWED = {"jpg", "jpeg", "png", "webp"}
TYPES = ["Flood", "Earthquake", "Cyclone", "Landslide", "Fire"]
ICONS = {"Flood": "🌊", "Earthquake": "🌍", "Cyclone": "🌀", "Landslide": "⛰️", "Fire": "🔥"}
STATUSES = ["Pending", "Verified", "In progress", "Resolved", "Rejected"]

GUIDELINES = {
    "Flood": ["Move to higher ground; avoid walking or driving through flood water.",
              "Switch off electricity and gas at the mains if water is entering your home.",
              "Keep drinking water sealed; boil water before use afterwards."],
    "Earthquake": ["Drop, cover and hold on under sturdy furniture.",
                   "Stay away from windows, glass and heavy shelves.",
                   "Outdoors: move to an open area away from buildings and power lines."],
    "Cyclone": ["Stay indoors, away from windows; follow evacuation orders at once.",
                "Secure loose objects and keep a battery radio for official updates.",
                "Do not go out in the calm 'eye'; the storm returns from the other side."],
    "Landslide": ["Move away from the slide path, at right angles to its direction.",
                  "Watch for tilting trees, new cracks and unusual sounds on slopes.",
                  "Avoid river valleys and slopes during heavy rain."],
    "Fire": ["Alert others, leave immediately and call 101; do not use lifts.",
             "Stay low under smoke and feel doors for heat before opening.",
             "Never go back inside for belongings."],
}
CHECKLIST = ["Emergency kit: water, food, torch, first aid, power bank",
             "Copies of ID and key documents in a waterproof bag",
             "Family meeting point and evacuation route agreed",
             "Emergency numbers saved on every phone",
             "Regular medicines for at least 7 days"]
CONTACTS = [("National emergency", "112"), ("Police", "100"), ("Fire", "101"),
            ("Ambulance", "108"), ("Disaster management control room", "1078")]

# ---------- database ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def init_db():
    with sqlite3.connect(DB) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS incidents(
          id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, location TEXT,
          description TEXT, reporter TEXT, photo TEXT,
          status TEXT DEFAULT 'Pending', created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS announcements(
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body TEXT,
          severity TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
        """)

# ---------- photo storage: S3 on EC2, local folder for development ----------
def save_photo(f):
    if not f or not f.filename: return None
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED: return None
    name = f"{uuid.uuid4().hex}.{ext}"
    if S3_BUCKET:
        import boto3  # credentials come from the EC2 IAM role, never hard-coded
        boto3.client("s3").upload_fileobj(f, S3_BUCKET, name,
                                          ExtraArgs={"ContentType": f.mimetype})
    else:
        f.save(os.path.join(UPLOAD_DIR, name))
    return name

@app.template_filter("photo_url")
def photo_url(name):
    if not name: return ""
    if S3_BUCKET:
        import boto3
        return boto3.client("s3").generate_presigned_url(
            "get_object", Params={"Bucket": S3_BUCKET, "Key": name}, ExpiresIn=3600)
    return url_for("uploaded", name=name)

@app.route("/uploads/<name>")
def uploaded(name):
    return send_from_directory(UPLOAD_DIR, name)

# ---------- public + user pages ----------
@app.context_processor
def inject():
    return dict(TYPES=TYPES, CONTACTS=CONTACTS, STATUSES=STATUSES, ICONS=ICONS)

@app.route("/")
def home():
    alerts = db().execute("SELECT * FROM announcements ORDER BY id DESC LIMIT 5").fetchall()
    inc = db().execute("SELECT * FROM incidents WHERE status IN ('Verified','In progress') "
                       "ORDER BY id DESC LIMIT 6").fetchall()
    return render_template("index.html", alerts=alerts, incidents=inc)

@app.route("/guidelines")
def guidelines():
    return render_template("guidelines.html", guides=GUIDELINES, checklist=CHECKLIST)

@app.route("/incidents")
def incidents():
    rows = db().execute("SELECT * FROM incidents WHERE status != 'Pending' AND status != 'Rejected' "
                        "ORDER BY id DESC").fetchall()
    return render_template("incidents.html", rows=rows)

@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        t, loc, desc = (request.form.get(k, "").strip() for k in ("type", "location", "description"))
        if t not in TYPES or not loc or not desc:
            flash("Choose a disaster type and fill in location and description.", "error")
            return render_template("report.html"), 400
        photo = save_photo(request.files.get("photo"))
        db().execute("INSERT INTO incidents(type,location,description,reporter,photo) VALUES(?,?,?,?,?)",
                     (t, loc, desc, request.form.get("reporter", "").strip(), photo))
        db().commit()
        flash("Report sent. An admin will verify it before it appears publicly.", "ok")
        return redirect(url_for("report"))
    return render_template("report.html")

# ---------- admin ----------
def admin_only(fn):
    @wraps(fn)
    def w(*a, **k):
        if not session.get("admin"): return redirect(url_for("login"))
        return fn(*a, **k)
    return w

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        flash("Wrong password.", "error")
    return render_template("login.html")

@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
@admin_only
def admin():
    rows = db().execute("SELECT * FROM incidents ORDER BY id DESC").fetchall()
    counts = {s: 0 for s in STATUSES}
    for r in rows: counts[r["status"]] += 1
    return render_template("admin.html", rows=rows, counts=counts)

@app.route("/admin/status/<int:i>", methods=["POST"])
@admin_only
def set_status(i):
    s = request.form.get("status")
    if s not in STATUSES: abort(400)
    db().execute("UPDATE incidents SET status=? WHERE id=?", (s, i)); db().commit()
    return redirect(url_for("admin"))

@app.route("/admin/delete/<int:i>", methods=["POST"])
@admin_only
def delete(i):
    db().execute("DELETE FROM incidents WHERE id=?", (i,)); db().commit()
    return redirect(url_for("admin"))

@app.route("/admin/announce", methods=["POST"])
@admin_only
def announce():
    db().execute("INSERT INTO announcements(title,body,severity) VALUES(?,?,?)",
                 (request.form["title"], request.form["body"], request.form.get("severity", "Advisory")))
    db().commit()
    flash("Announcement published.", "ok")
    return redirect(url_for("admin"))

init_db()
if __name__ == "__main__":
    import threading, webbrowser
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":   # open the browser once
        threading.Timer(1.5, lambda: webbrowser.open("http://localhost:5000")).start()
    print("DisasterConnect running at http://localhost:5000  (admin password: %s)" % ADMIN_PASSWORD)
    app.run(host="0.0.0.0", port=5000, debug=True)
