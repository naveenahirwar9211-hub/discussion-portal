from flask import Flask, render_template_string, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
import os
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "any_secret_123")

ADMIN_EMAIL = "naveenahirwar9211@gmail.com"
POSTS_PER_PAGE = 10
IST = pytz.timezone('Asia/Kolkata')

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

likes = db.Table('likes',
    db.Column('user_email', db.String(100), db.ForeignKey('user_stat.email')),
    db.Column('problem_id', db.Integer, db.ForeignKey('problem.id'))
)

class UserStat(db.Model):
    email = db.Column(db.String(100), primary_key=True)

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    author_name = db.Column(db.String(100))
    author_img = db.Column(db.String(500))
    is_pinned = db.Column(db.Boolean, default=False)
    # यहाँ बदलाव किया गया है ताकि डिफ़ॉल्ट IST समय मिले
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(IST))
    liked_by = db.relationship('UserStat', secondary=likes, backref=db.backref('liked_posts', lazy='dynamic'))
    comments = db.relationship('Comment', backref='problem', cascade="all, delete-orphan", lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    user_name = db.Column(db.String(100))
    user_img = db.Column(db.String(500))
    # यहाँ बदलाव किया गया है
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(IST))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))

with app.app_context():
    db.create_all()

# --- HTML डिजाइन (कोई बदलाव नहीं) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; background: #3f4094; color: white; text-align: center; margin: 0; padding-bottom: 50px; }
        .top-bar { background: #1a73e8; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
        .card { background: white; color: #333; padding: 15px; border-radius: 10px; max-width: 500px; margin: 20px auto; text-align: left; box-shadow: 0 4px 8px rgba(0,0,0,0.2); position: relative; }
        .pinned { border: 3px solid #ffc107; }
        .pin-tag { background: #ffc107; color: black; font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: bold; margin-bottom: 5px; display: inline-block; }
        .user-info { display: flex; align-items: center; gap: 10px; }
        .user-img { width: 35px; height: 35px; border-radius: 50%; border: 1px solid #ddd; }
        .time-text { font-size: 10px; color: #888; }
        .btn-google { background: white; color: #444; padding: 8px 12px; text-decoration: none; border-radius: 5px; font-size: 12px; font-weight: bold; border: 1px solid #ddd; }
        .admin-action { color: #d93025; text-decoration: none; font-size: 10px; border: 1px solid #d93025; padding: 1px 4px; border-radius: 3px; margin-left: 5px; }
        .like-section { display: flex; align-items: center; gap: 5px; margin-top: 10px; font-size: 14px; color: #444; }
        .like-btn { text-decoration: none; color: #e91e63; font-weight: bold; border: 1px solid #e91e63; padding: 3px 8px; border-radius: 15px; transition: 0.3s; }
        .like-btn:hover { background: #e91e63; color: white; }
    </style>
</head>
<body>
    <div class="top-bar">
        <strong style="font-size: 18px;">Help Desk</strong>
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
        {% if google.authorized %}
        <form action="/post_problem" method="POST">
            <input type="text" name="title" placeholder="विषय का नाम" required style="width:96%; margin-bottom:10px; padding:10px; border-radius:5px; border:1px solid #ccc;">
            <textarea name="content" placeholder="अपनी बात यहाँ लिखें..." style="width:96%; height:80px; padding:10px; border-radius:5px; border:1px solid #ccc;" required></textarea>
            <button type="submit" style="width:100%; background:#ffc107; padding:12px; border:none; border-radius:5px; cursor:pointer; font-weight:bold; font-size:16px;">POST TO SURVEYOR</button>
        </form>
        {% else %}
        <p style="color:#d93025; font-size:14px; text-align:center;">टॉपिक पोस्ट करने के लिए कृपया लॉगिन करें।</p>
        {% endif %}
    </div>

    {% for problem in problems.items %}
    <div class="card {{ 'pinned' if problem.is_pinned else '' }}">
        {% if problem.is_pinned %}<span class="pin-tag">PINNED</span>{% endif %}
        
        <div style="float:right;">
            {% if is_admin %}
                <a href="/pin_problem/{{ problem.id }}" class="admin-action" style="color:#1a73e8; border-color:#1a73e8;">Pin</a>
                <a href="/delete_problem/{{ problem.id }}" class="admin-action" onclick="return confirm('डिलीट करें?')">Delete</a>
            {% endif %}
        </div>
        
        <div class="user-info">
            <img src="{{ problem.author_img if problem.author_img else 'https://via.placeholder.com/35' }}" class="user-img">
            <div>
                <div style="font-size:13px; font-weight:bold; color:#1a73e8;">{{ problem.author_name }}</div>
                <div class="time-text">{{ problem.timestamp.strftime('%d %b, %I:%M %p') }}</div>
            </div>
        </div>

        <strong style="font-size:18px; display:block; margin-top:8px;">{{ problem.title }}</strong>
        <p style="margin: 8px 0; font-size:15px;">{{ problem.content }}</p>

        <div class="like-section">
            <a href="/like_problem/{{ problem.id }}" class="like-btn">❤️ Like</a>
            <span>{{ problem.liked_by|length }} Likes</span>
        </div>

        <hr style="border:0; border-top:1px solid #eee; margin:15px 0;">
        
        <strong style="font-size:12px;">Comments:</strong>
        {% for comment in problem.comments %}
            <div style="background:#f8f9fa; padding:8px; border-radius:8px; margin-top:5px; border-left: 3px solid #1a73e8;">
                <div class="user-info">
                    <img src="{{ comment.user_img }}" class="user-img" style="width:20px; height:20px;">
                    <span style="font-size:11px; font-weight:bold;">{{ comment.user_name }}</span>
                    {% if is_admin %}
                        <a href="/delete_comment/{{ comment.id }}" class="admin-action" style="font-size:8px;">Del</a>
                    {% endif %}
                </div>
                <div style="font-size:12px; margin-left:30px;">{{ comment.content }}</div>
            </div>
        {% endfor %}

        {% if google.authorized %}
        <form action="/post_comment/{{ problem.id }}" method="POST" style="margin-top:10px; display:flex; gap:5px;">
            <input type="text" name="content" placeholder="Reply..." required style="flex:1; padding:8px; border-radius:5px; border:1px solid #ddd; font-size:12px;">
            <button type="submit" style="padding:8px 12px; background:#1a73e8; color:white; border:none; border-radius:5px; cursor:pointer; font-size:12px;">Send</button>
        </form>
        {% endif %}
    </div>
    {% endfor %}

    <div class="pagination">
        {% if problems.has_prev %}<a href="{{ url_for('index', page=problems.prev_num) }}" style="color:white; margin-right:10px;">← Back</a>{% endif %}
        {% if problems.has_next %}<a href="{{ url_for('index', page=problems.next_num) }}" style="color:white;">Next →</a>{% endif %}
    </div>
</body>
</html>
"""

# --- Routes ---

@app.route("/")
def index():
    page = request.args.get('page', 1, type=int)
    user_name = ""; is_admin = False
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            user_data = resp.json()
            user_name = user_data.get("name", "User")
            if user_data.get("email") == ADMIN_EMAIL: is_admin = True
    
    problems = Problem.query.order_by(Problem.is_pinned.desc(), Problem.id.desc()).paginate(page=page, per_page=POSTS_PER_PAGE)
    return render_template_string(HTML_TEMPLATE, problems=problems, user_name=user_name, is_admin=is_admin, google=google)

@app.route("/like_problem/<int:problem_id>")
def like_problem(problem_id):
    if not google.authorized: return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    if resp.ok:
        user_email = resp.json().get("email")
        user = UserStat.query.get(user_email)
        if not user:
            user = UserStat(email=user_email)
            db.session.add(user)
        
        problem = Problem.query.get(problem_id)
        if problem and user not in problem.liked_by:
            problem.liked_by.append(user)
            db.session.commit()
    return redirect(url_for("index"))

@app.route("/post_problem", methods=["POST"])
def post_problem():
    if not google.authorized: return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    if resp.ok:
        ud = resp.json()
        # यहाँ समय को IST में फिक्स किया गया है
        new_prob = Problem(
            title=request.form['title'], 
            content=request.form['content'], 
            author_name=ud.get("name"), 
            author_img=ud.get("picture"),
            timestamp=datetime.now(IST)
        )
        db.session.add(new_prob)
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/post_comment/<int:problem_id>", methods=["POST"])
def post_comment(problem_id):
    if not google.authorized: return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    if resp.ok:
        ud = resp.json()
        # यहाँ समय को IST में फिक्स किया गया है
        new_comm = Comment(
            content=request.form['content'], 
            user_name=ud.get("name"), 
            user_img=ud.get("picture"), 
            problem_id=problem_id,
            timestamp=datetime.now(IST)
        )
        db.session.add(new_comm)
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/pin_problem/<int:problem_id>")
def pin_problem(problem_id):
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok and resp.json().get("email") == ADMIN_EMAIL:
            p = Problem.query.get(problem_id)
            if p:
                p.is_pinned = not p.is_pinned
                db.session.commit()
    return redirect(url_for("index"))

@app.route("/delete_comment/<int:comment_id>")
def delete_comment(comment_id):
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok and resp.json().get("email") == ADMIN_EMAIL:
            c = Comment.query.get(comment_id)
            if c: db.session.delete(c); db.session.commit()
    return redirect(url_for("index"))

@app.route("/delete_problem/<int:problem_id>")
def delete_problem(problem_id):
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok and resp.json().get("email") == ADMIN_EMAIL:
            p = Problem.query.get(problem_id)
            if p: db.session.delete(p); db.session.commit()
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
