from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "any_secret_123")

# --- एडमिन ईमेल ---
ADMIN_EMAIL = "naveenahirwar9211@gmail.com"

# --- OAuth सेटअप ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

blueprint = make_google_blueprint(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    scope=["profile", "email"]
)
app.register_blueprint(blueprint, url_prefix="/login")

# --- डेटाबेस सेटअप ---
db_url = os.environ.get("DATABASE_URL", "sqlite:///discussion_portal.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# मॉडल में से image_data हटा दिया गया है
class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    comments = db.relationship('Comment', backref='problem', cascade="all, delete-orphan", lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    user_name = db.Column(db.String(100))
    user_img = db.Column(db.String(500))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))

with app.app_context():
    db.create_all()

# --- HTML (इमेज अपलोड बटन हटा दिए गए हैं) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; background: #3f4094; color: white; text-align: center; margin: 0; padding-bottom: 50px; }
        .top-bar { background: #1a73e8; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
        .card { background: white; color: #333; padding: 15px; border-radius: 10px; max-width: 500px; margin: 20px auto; text-align: left; box-shadow: 0 4px 8px rgba(0,0,0,0.2); position: relative; }
        .user-info { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
        .user-img { width: 30px; height: 30px; border-radius: 50%; border: 1px solid #ccc; }
        .btn-google { background: white; color: #444; padding: 8px 12px; text-decoration: none; border-radius: 5px; font-size: 12px; font-weight: bold; border: 1px solid #ddd; }
        .delete-btn { position: absolute; top: 10px; right: 10px; color: #d93025; text-decoration: none; font-size: 12px; border: 1px solid #d93025; padding: 2px 6px; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="top-bar">
        <strong style="font-size: 18px;">Discussion Portal</strong>
        {% if google.authorized %}
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size: 12px;">Hi, {{ user_name }}</span>
                <a href="/logout" style="color:white; font-size:11px; background:rgba(0,0,0,0.2); padding:4px 8px; border-radius:4px; text-decoration:none;">Logout</a>
            </div>
        {% else %}
            <a href="{{ url_for('google.login') }}" class="btn-google">Login with Google</a>
        {% endif %}
    </div>

    <h2 style="margin-top:20px;">Local Youth Surveyor</h2>

    <div class="card">
        <h3>नया टॉपिक शुरू करें</h3>
        <form action="/post_problem" method="POST">
            <input type="text" name="title" placeholder="विषय का नाम" required style="width:96%; margin-bottom:10px; padding:10px; border-radius:5px; border:1px solid #ccc;">
            <textarea name="content" placeholder="अपनी बात यहाँ लिखें..." style="width:96%; height:80px; padding:10px; border-radius:5px; border:1px solid #ccc;" required></textarea>
            <button type="submit" style="width:100%; background:#ffc107; padding:12px; border:none; border-radius:5px; cursor:pointer; font-weight:bold; font-size:16px;">POST TO SURVEYOR</button>
        </form>
    </div>

    {% for problem in problems %}
    <div class="card">
        {% if is_admin %}
            <a href="/delete_problem/{{ problem.id }}" class="delete-btn" onclick="return confirm('क्या आप इसे डिलीट करना चाहते हैं?')">Delete</a>
        {% endif %}
        
        <strong style="color:#1a73e8; font-size:18px;">{{ problem.title }}</strong>
        <p style="margin: 10px 0;">{{ problem.content }}</p>

        <hr style="border:0; border-top:1px solid #eee;">
        
        <strong style="font-size:14px;">Comments:</strong>
        {% for comment in problem.comments %}
            <div style="background:#f8f9fa; padding:10px; border-radius:8px; margin-top:8px; border-left: 4px solid #1a73e8;">
                <div class="user-info">
                    <img src="{{ comment.user_img }}" class="user-img" onerror="this.src='https://via.placeholder.com/30'">
                    <span style="font-size:12px; font-weight:bold;">{{ comment.user_name }}</span>
                </div>
                <div style="font-size:14px; margin-left:40px; color:#444;">{{ comment.content }}</div>
            </div>
        {% endfor %}

        {% if google.authorized %}
        <form action="/post_comment/{{ problem.id }}" method="POST" style="margin-top:10px; display:flex; gap:8px;">
            <input type="text" name="content" placeholder="अपनी राय दें..." required style="flex:1; padding:10px; border-radius:5px; border:1px solid #ddd;">
            <button type="submit" style="padding:10px 20px; background:#1a73e8; color:white; border:none; border-radius:5px; cursor:pointer;">Reply</button>
        </form>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>
"""

@app.route("/")
def index():
    user_name = ""; is_admin = False
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            user_data = resp.json()
            user_name = user_data.get("name", "User")
            if user_data.get("email") == ADMIN_EMAIL:
                is_admin = True
    
    problems = Problem.query.order_by(Problem.id.desc()).all()
    return render_template_string(HTML_TEMPLATE, problems=problems, user_name=user_name, is_admin=is_admin, google=google)

@app.route("/post_problem", methods=["POST"])
def post_problem():
    title = request.form.get('title')
    content = request.form.get('content')
    if title and content:
        db.session.add(Problem(title=title, content=content))
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/post_comment/<int:problem_id>", methods=["POST"])
def post_comment(problem_id):
    if not google.authorized: return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    if resp.ok:
        user_data = resp.json()
        db.session.add(Comment(
            content=request.form['content'],
            user_name=user_data.get("name"),
            user_img=user_data.get("picture"),
            problem_id=problem_id
        ))
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/delete_problem/<int:problem_id>")
def delete_problem(problem_id):
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok and resp.json().get("email") == ADMIN_EMAIL:
            p = Problem.query.get(problem_id)
            if p:
                db.session.delete(p)
                db.session.commit()
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
