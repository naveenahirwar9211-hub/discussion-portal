from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
import os
import base64

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "any_secret_123")

ADMIN_EMAIL = "naveenahirwar9211@gmail.com"

# --- सुरक्षित OAuth सेटअप ---
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
# 2MB Limit for Python (Server Side)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 

db = SQLAlchemy(app)

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    image_data = db.Column(db.Text)
    comments = db.relationship('Comment', backref='problem', cascade="all, delete-orphan", lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    user_name = db.Column(db.String(100))
    user_img = db.Column(db.String(500))
    image_data = db.Column(db.Text)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))

with app.app_context():
    db.create_all()

# --- HTML डिजाइन (Image Limit Logic के साथ) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; background: #3f4094; color: white; text-align: center; margin: 0; padding-bottom: 50px; }
        .top-bar { background: #1a73e8; padding: 15px; display: flex; justify-content: space-between; align-items: center; }
        .card { background: white; color: #333; padding: 15px; border-radius: 10px; max-width: 500px; margin: 20px auto; text-align: left; box-shadow: 0 4px 8px rgba(0,0,0,0.2); position: relative; }
        .post-img { width: 100%; border-radius: 8px; margin-top: 10px; border: 1px solid #eee; }
        .user-info { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
        .user-img { width: 30px; height: 30px; border-radius: 50%; border: 1px solid #ccc; }
        .btn-google { background: white; color: #444; padding: 8px 12px; text-decoration: none; border-radius: 5px; font-size: 12px; font-weight: bold; border: 1px solid #ddd; }
        .delete-btn { position: absolute; top: 10px; right: 10px; color: #d93025; text-decoration: none; font-size: 12px; border: 1px solid #d93025; padding: 2px 6px; border-radius: 4px; }
        .error-msg { color: #d93025; font-size: 12px; margin-top: 5px; display: none; }
    </style>
    <script>
        function checkFileSize(input) {
            const file = input.files[0];
            const limit = 2 * 1024 * 1024; // 2MB
            if (file && file.size > limit) {
                alert("सावधान! फोटो 2MB से बड़ी है। कृपया छोटी फोटो चुनें।");
                input.value = ""; // Clear the input
            }
        }
    </script>
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
        <form action="/post_problem" method="POST" enctype="multipart/form-data">
            <input type="text" name="title" placeholder="विषय का नाम" required style="width:96%; margin-bottom:10px; padding:10px; border-radius:5px; border:1px solid #ccc;">
            <textarea name="content" placeholder="अपनी बात यहाँ लिखें..." style="width:96%; height:80px; padding:10px; border-radius:5px; border:1px solid #ccc;" required></textarea>
            <label style="font-size:12px; color:#666; margin-top:10px; display:block;">फोटो जोड़ें (Max 2MB):</label>
            <input type="file" name="image" accept="image/*" onchange="checkFileSize(this)" style="margin-bottom:10px; font-size:12px;">
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
        
        {% if problem.image_data %}
            <img src="data:image/jpeg;base64,{{ problem.image_data }}" class="post-img">
        {% endif %}

        <hr style="border:0; border-top:1px solid #eee; margin:15px 0;">
        
        <strong style="font-size:14px;">Comments:</strong>
        {% for comment in problem.comments %}
            <div style="background:#f8f9fa; padding:10px; border-radius:8px; margin-top:8px; border-left: 4px solid #1a73e8;">
                <div class="user-info">
                    <img src="{{ comment.user_img }}" class="user-img">
                    <span style="font-size:12px; font-weight:bold;">{{ comment.user_name }}</span>
                </div>
                <div style="font-size:14px; margin-left:40px; color:#444;">{{ comment.content }}</div>
                {% if comment.image_data %}
                    <img src="data:image/jpeg;base64,{{ comment.image_data }}" style="width:60%; border-radius:5px; margin:5px 0 0 40px;">
                {% endif %}
            </div>
        {% endfor %}

        {% if google.authorized %}
        <form action="/post_comment/{{ problem.id }}" method="POST" enctype="multipart/form-data" style="margin-top:15px;">
            <input type="text" name="content" placeholder="अपनी राय दें..." required style="width:94%; padding:10px; border-radius:5px; border:1px solid #ddd; margin-bottom:5px;">
            <div style="display:flex; align-items:center; gap:10px;">
                <input type="file" name="image" accept="image/*" onchange="checkFileSize(this)" style="width:150px; font-size:11px;">
                <button type="submit" style="flex:1; padding:10px; background:#1a73e8; color:white; border:none; border-radius:5px; cursor:pointer; font-size:13px;">Reply with Photo</button>
            </div>
        </form>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>
"""

def image_to_base64(file):
    if file and file.filename != '':
        # डबल चेक सर्वर साइड
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > 2 * 1024 * 1024:
            return None
        return base64.b64encode(file.read()).decode('utf-8')
    return None

@app.errorhandler(413)
def request_entity_too_large(error):
    return "फाइल बहुत बड़ी है! कृपया 2MB से कम की इमेज अपलोड करें। <a href='/'>वापस जाएँ</a>", 413

@app.route("/")
def index():
    user_name = ""; is_admin = False
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            user_data = resp.json()
            user_name = user_data.get("name", "User")
            if user_data.get("email") == ADMIN_EMAIL: is_admin = True
    
    problems = Problem.query.order_by(Problem.id.desc()).all()
    return render_template_string(HTML_TEMPLATE, problems=problems, user_name=user_name, is_admin=is_admin, google=google)

@app.route("/post_problem", methods=["POST"])
def post_problem():
    title = request.form.get('title')
    content = request.form.get('content')
    img_file = request.files.get('image')
    img_base64 = image_to_base64(img_file)
    
    if title and content:
        db.session.add(Problem(title=title, content=content, image_data=img_base64))
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/post_comment/<int:problem_id>", methods=["POST"])
def post_comment(problem_id):
    if not google.authorized: return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    if resp.ok:
        user_data = resp.json()
        img_file = request.files.get('image')
        img_base64 = image_to_base64(img_file)
        
        db.session.add(Comment(
            content=request.form['content'],
            user_name=user_data.get("name"),
            user_img=user_data.get("picture"),
            image_data=img_base64,
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
            if p: db.session.delete(p); db.session.commit()
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

