from flask import Flask, request, render_template, redirect, flash, session,url_for
from werkzeug.security import generate_password_hash, check_password_hash

import mysql.connector
from markdown_it import MarkdownIt

md = MarkdownIt()

app = Flask(__name__)
app.secret_key = 'Phyforum@123'

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return "<h1>About Us</h1><p>This page is under construction.</p>"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Phyforum@123",
    database="PhyForum"
)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        nickname = request.form['nickname']
        password = request.form['password']
        role = 'user'
        contact_info = request.form['contact_info']

        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("This email is already registered.")
            return redirect('/register')

        hashed_password = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (email, nickname, password_hash, contact_info)
            VALUES (%s, %s, %s, %s, %s)
        """, (email, nickname, hashed_password, contact_info))
        db.commit()
        flash("Registration successful!")
        return redirect('/')

    return render_template('register.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
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

@app.route('/post/new', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        flash('You must be logged in to post.')
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        user_id = session['user_id']

        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO posts (user_id, title, content) VALUES (%s, %s, %s)",
            (user_id, title, content)
        )
        db.commit()
        cursor.close()
        flash('Post created successfully!')
        return redirect('/posts')

    return render_template('new_post.html')

@app.route('/posts')
def show_posts():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT posts.id, posts.title, posts.created_at, users.nickname
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.created_at DESC
    """)
    posts = cursor.fetchall()
    cursor.close()
    return render_template('posts.html', posts=posts)

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    cursor = db.cursor(dictionary=True)
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
    cursor = db.cursor(dictionary=True)
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
    cursor = db.cursor()
    cursor.execute("DELETE FROM posts WHERE id=%s", (post_id,))
    db.commit()
    return redirect('/posts')

@app.route('/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
def edit_comment(comment_id):
    cursor = db.cursor(dictionary=True)
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
    cursor = db.cursor()
    cursor.execute("DELETE FROM comments WHERE id=%s", (comment_id,))
    db.commit()
    return redirect(request.referrer)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')  # current_user.id if you're using flask-login
    cursor = db.cursor(dictionary=True)

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