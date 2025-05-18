from flask import Flask, request, render_template, redirect, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

import pymysql
from markdown_it import MarkdownIt
from config import Config
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

md = MarkdownIt()
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

app.config['MAIL_SERVER'] = Config.MAIL_SERVER
app.config['MAIL_PORT'] = Config.MAIL_PORT
app.config['MAIL_USE_SSL'] = Config.MAIL_USE_SSL
app.config['MAIL_USERNAME'] = Config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = Config.MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = Config.MAIL_DEFAULT_SENDER

mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return "<h1>About Us</h1><p>This page is under construction.</p>"

def get_db_connection():
    print("DB_HOST=", Config.DB_HOST)
    print("DB_PORT=", Config.DB_PORT)
    print("DB_USER=", Config.DB_USER)
    return pymysql.connect(
        charset="utf8mb4",
        connect_timeout=Config.DB_TIMEOUT,
        cursorclass=pymysql.cursors.DictCursor,
        db=Config.DB_NAME,
        host=Config.DB_HOST,
        password=Config.DB_PASSWORD,
        read_timeout=Config.DB_TIMEOUT,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        write_timeout=Config.DB_TIMEOUT,
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        nickname = request.form['nickname']
        password = request.form['password']
        contact_info = request.form['contact_info']

        with get_db_connection() as db:
            with db.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash("This email is already registered.")
                    return redirect('/register')

        password_hash = generate_password_hash(password)
        token = s.dumps({
            'email': email,
            'nickname': nickname,
            'password_hash': password_hash,
            'contact_info': contact_info
        }, salt='email-confirm')

        BASE_URL = Config.BASE_URL
        confirm_url = f"{BASE_URL}/confirm/{token}"

        msg = Message('Confirm your registration', recipients=[email])
        msg.body = f'Hi, please click the link to confirm your registration:\n{confirm_url}'

        mail.send(msg)
        return render_template('check_email.html')

    return render_template('register.html')

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        data = s.loads(token, salt='email-confirm', max_age=3600)
    except:
        return "The confirmation link is invalid or has expired."

    email = data['email']
    nickname = data['nickname']
    password_hash = data['password_hash']
    contact_info = data['contact_info']

    with get_db_connection() as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return "This email has already been confirmed."

            cursor.execute("""
                INSERT INTO users (email, nickname, password_hash, contact_info)
                VALUES (%s, %s, %s, %s)
            """, (email, nickname, password_hash, contact_info))
            db.commit()

    return redirect('/login')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        with get_db_connection() as db:
            with db.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                if user and check_password_hash(user["password_hash"], password):
                    session["user_id"] = user["id"]
                    session["nickname"] = user["nickname"]
                    session["role"] = user["role"]
                    flash("Login successful!")
                    return redirect("/")
                else:
                    flash("Invalid email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect("/")

@app.route('/delete_account', methods=['POST'])
def delete_account():
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to delete your account.")
        return redirect('/login')

    with get_db_connection() as db:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            db.commit()

    session.clear()
    flash("Your account has been deleted.")
    return redirect('/')


@app.route('/post/new', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        flash('You must be logged in to post.')
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        user_id = session['user_id']

        with get_db_connection() as db:
            with db.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO posts (user_id, title, content) VALUES (%s, %s, %s)",
                    (user_id, title, content)
                )
                db.commit()
                flash('Post created successfully!')
                return redirect('/posts')

    return render_template('new_post.html')

@app.route('/posts')
def show_posts():
    with get_db_connection() as db:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT posts.id, posts.title, posts.created_at, users.nickname
                FROM posts
                JOIN users ON posts.user_id = users.id
                ORDER BY posts.created_at DESC
            """)
            posts = cursor.fetchall()
    return render_template('posts.html', posts=posts)

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    with get_db_connection() as db:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT posts.*, users.nickname
                FROM posts
                JOIN users ON posts.user_id = users.id
                WHERE posts.id = %s
            """, (post_id,))
            post = cursor.fetchone()
            if post is None:
                return "Post not found", 404
            if request.method == 'POST':
                content = request.form.get('comment_content')
                user_id = session.get('user_id')
                if user_id and content:
                    cursor.execute(
                        "INSERT INTO comments (post_id, user_id, content) VALUES (%s, %s, %s)",
                        (post_id, user_id, content)
                    )
                    db.commit()
                    flash("Comment added successfully.")
                    return redirect(f'/post/{post_id}')
            post['content_html'] = md.render(post['content'])
            cursor.execute("""
                SELECT comments.*, users.nickname
                FROM comments
                JOIN users ON comments.user_id = users.id
                WHERE comments.post_id = %s
                ORDER BY created_at DESC
            """, (post_id,))
            comments = cursor.fetchall()
    return render_template('post_detail.html', post=post, comments = comments)

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    with get_db_connection() as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM posts WHERE id=%s", (post_id,))
            post = cursor.fetchone()

            if not post:
                return "Post not found", 404

            if post['user_id'] != session.get('user_id') and not session.get('is_admin', False):
                return "Permission denied", 403
            
            if request.method == 'POST':
                title = request.form['title']
                content = request.form['content']
                cursor.execute(
                    "UPDATE posts SET title=%s, content=%s WHERE id=%s",
                    (title, content, post_id)
                )
                db.commit()
                return redirect(f"/post/{post_id}")
            else:
                cursor.execute("SELECT * FROM posts WHERE id=%s", (post_id,))
                post = cursor.fetchone()
                return render_template('edit_post.html', post=post)

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    with get_db_connection() as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM posts WHERE id=%s", (post_id,))
            post = cursor.fetchone()

            if not post:
                return "Post not found", 404

            if post['user_id'] != session.get('user_id') and not session.get('is_admin', False):
                return "Permission denied", 403
            
            cursor.execute("DELETE FROM posts WHERE id=%s", (post_id,))
            db.commit()
    return redirect('/posts')

@app.route('/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
def edit_comment(comment_id):
    with get_db_connection() as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM posts WHERE id=%s", (comment_id,))
            post = cursor.fetchone()

            if not post:
                return "Post not found", 404

            if post['user_id'] != session.get('user_id') and not session.get('is_admin', False):
                return "Permission denied", 403
            
            cursor.execute("SELECT * FROM comments WHERE id=%s", (comment_id,))
            comment = cursor.fetchone()

            if not comment:
                return "Comment not found", 404

            if request.method == 'POST':
                content = request.form['content']
                cursor.execute("UPDATE comments SET content=%s WHERE id=%s", (content, comment_id))
                db.commit()
                return redirect(f"/post/{comment['post_id']}")
            else:
                return render_template('edit_comment.html', comment=comment)

@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    with get_db_connection() as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM posts WHERE id=%s", (comment_id,))
            post = cursor.fetchone()

            if not post:
                return "Post not found", 404

            if post['user_id'] != session.get('user_id') and not session.get('is_admin', False):
                return "Permission denied", 403
            
            cursor.execute("SELECT * FROM comments WHERE id=%s", (comment_id,))
            comment = cursor.fetchone()
            if comment:
                cursor.execute("DELETE FROM comments WHERE id=%s", (comment_id,))
                db.commit()
                return redirect(f"/post/{comment['post_id']}")
    return redirect(request.referrer)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    with get_db_connection() as db:
        with db.cursor() as cursor:
            if request.method == 'POST':
                nickname = request.form['nickname']
                contact = request.form['contact']

                cursor.execute("""
                    UPDATE users
                    SET nickname=%s, contact_info=%s
                    WHERE id=%s
                """, (nickname, contact, user_id))
                db.commit()
                flash('Profile updated successfully.', 'success')
                return redirect('/')

            cursor.execute("SELECT id, email, nickname, contact_info, role, created_at FROM users WHERE id=%s", (user_id,))
            user = cursor.fetchone()

    return render_template('profile.html', user=user)

if __name__ == "__main__":
    app.run(debug=True)