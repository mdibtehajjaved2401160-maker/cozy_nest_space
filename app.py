from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from functools import wraps
import cloudinary
import cloudinary.uploader
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_jugaad_key_decor')

# --- ADMIN ACCOUNTS WITH PERSONALIZATION ---
ADMIN_ACCOUNTS = {
    'mdibtehaj.javed24011602@gmail.com': {'name': 'Ibtehaj', 'greeting': 'Hi, admin Ibtehaj Sahab', 'password': 'admin123'},
    'ibtehajiqbal07@gmail.com': {'name': 'Ibtehaj', 'greeting': 'Hi, admin Ibtehaj Sahab', 'password': 'admin123'},
    'ansariibtehaj576@gmail.com': {'name': 'Ibtehaj', 'greeting': 'Hi, admin Ibtehaj Sahab', 'password': 'admin123'},
    'sf4093943@gmail.com': {'name': 'Sana Fatima', 'greeting': 'Hi, Admin Sana Fatima Sahiba', 'password': 'sana123'},
    '2025n15494@gmail.com': {'name': 'Sana Fatima', 'greeting': 'Hi, Admin Sana Fatima Sahiba', 'password': 'sana123'},
    'ibtehajandsana2903@gmail.com': {'name': 'CuteCouple Admins', 'greeting': 'Hi, CuteCouple Admins!!', 'password': 'couple123'}
}

# Emails excluded from view counts and subscriber counts
EXCLUDED_EMAILS = set(ADMIN_ACCOUNTS.keys())

# --- GOOGLE SHEET URLS ---
NEWSLETTER_URL = "https://script.google.com/macros/s/AKfycbxFWpVix2EVm-aOz3RlSLGeo1SEcQzXcRWNAiJZI1UHMK_pCLwSvr0Xz-dGcR9mklgn/exec"
COMMENT_URL = "https://script.google.com/macros/s/AKfycbyih5FdUL3Q-W_rGa-nujOXk1lIF0cHjM4BLzjdW2BmuWb7y4pN6XvLrYRtETE4917zpg/exec"
USER_SHEET_URL = "https://script.google.com/macros/s/AKfycbyOK5Jq4rVjx1sU1g9RRU9kHQ4J9J_U7QD5V9S1YaFP6Y1GrtZnEIu9igbJUBYR1c6t_g/exec"

def get_db_connection():
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row  
    return conn

cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', 'dsi6p2jl5'),
    api_key = os.environ.get('CLOUDINARY_API_KEY', '632899118883272'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET', 'FZrOtMmnKocMVUCM-PS1v5h3Ozk'),
    secure = True
)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, content TEXT, image_url TEXT, date_posted TIMESTAMP DEFAULT CURRENT_TIMESTAMP, views INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS subscribers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, name TEXT, comment TEXT, date_posted TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- DUAL LOGIN ROUTES ---

@app.route('/login', defaults={'login_type': 'user'}, methods=['GET', 'POST'])
@app.route('/login/<login_type>', methods=['GET', 'POST'])
def login(login_type):
    login_type = login_type if login_type in ['admin', 'user'] else 'user'
    if request.method == 'POST':
        posted_type = request.form.get('login_type', login_type)
        login_type = posted_type if posted_type in ['admin', 'user'] else login_type
        
        if login_type == 'admin':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            # Check credentials
            if username == os.environ.get('ADMIN_USERNAME', 'admin') and password == os.environ.get('ADMIN_PASSWORD', 'admin123'):
                session['logged_in'] = True
                session['admin_name'] = 'Admin'
                session['admin_greeting'] = 'Welcome, Admin'
                return redirect(url_for('admin'))
            flash('Invalid admin credentials!')
        elif login_type == 'user':
            name = request.form.get('name')
            email = request.form.get('email')
            interests = request.form.getlist('interests')
            try:
                requests.post(USER_SHEET_URL, json={
                    'name': name,
                    'email': email,
                    'age': request.form.get('age'),
                    'interests': ', '.join(interests)
                })
            except:
                pass
            session['user_logged_in'] = True
            session['user_name'] = name
            session['user_email'] = email
            return redirect(url_for('index'))
    return render_template('login.html', active_login=login_type)

@app.route('/user_logout')
def user_logout():
    session.pop('user_logged_in', None)
    session.pop('user_name', None)
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- EXISTING ROUTES ---

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 16 
    offset = (page - 1) * per_page
    conn = get_db_connection()
    total_posts = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    posts = conn.execute('SELECT * FROM posts ORDER BY id DESC LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
    conn.close()
    total_pages = (total_posts // per_page) + (1 if total_posts % per_page > 0 else 0)
    return render_template('index.html', posts=posts, page=page, total_pages=total_pages)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        title, category, content = request.form['title'], request.form['category'], request.form['content']
        image_url = ""
        image_file = request.files.get('image_file')
        if image_file and image_file.filename != '':
            upload_result = cloudinary.uploader.upload(image_file)
            image_url = upload_result['secure_url']
        conn = get_db_connection()
        conn.execute('INSERT INTO posts (title, category, content, image_url) VALUES (?, ?, ?, ?)', (title, category, content, image_url))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    conn = get_db_connection()
    all_posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin.html', all_posts=all_posts)

@app.route('/stats')
@login_required
def stats():
    conn = get_db_connection()
    total_posts = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    total_views = conn.execute('SELECT SUM(views) FROM posts').fetchone()[0] or 0
    total_subs = conn.execute('SELECT COUNT(*) FROM subscribers').fetchone()[0]
    top_posts = conn.execute('SELECT title, views, category FROM posts WHERE views > 0 ORDER BY views DESC LIMIT 5').fetchall()
    conn.close()
    return render_template('stats.html', total_posts=total_posts, total_views=total_views, total_subs=total_subs, top_posts=top_posts)

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    conn = get_db_connection()
    if request.method == 'POST':
        title, category, content = request.form['title'], request.form['category'], request.form['content']
        image_file = request.files.get('image_file')
        if image_file and image_file.filename != '':
            upload_result = cloudinary.uploader.upload(image_file)
            conn.execute('UPDATE posts SET title=?, category=?, content=?, image_url=? WHERE id=?', (title, category, content, upload_result['secure_url'], post_id))
        else:
            conn.execute('UPDATE posts SET title=?, category=?, content=? WHERE id=?', (title, category, content, post_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()
    return render_template('edit.html', post=post)

@app.route('/delete/<int:post_id>')
@login_required
def delete_post(post_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/search')
def search():
    query = request.args.get('query', '')
    conn = get_db_connection()
    posts = conn.execute("SELECT * FROM posts WHERE LOWER(title) LIKE LOWER(?) OR LOWER(category) LIKE LOWER(?) OR LOWER(content) LIKE LOWER(?)", ('%'+query+'%', '%'+query+'%', '%'+query+'%')).fetchall()
    conn.close()
    return render_template('index.html', posts=posts, search_query=query)

@app.route('/category/<category_name>')
def category(category_name):
    category_value = category_name.replace('-', ' ')
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts WHERE LOWER(category) = LOWER(?) ORDER BY id DESC', (category_value,)).fetchall()
    conn.close()
    return render_template('index.html', posts=posts, search_query=category_value)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    name = request.form.get('name')
    email = request.form.get('email', '').strip().lower()
    if name and email:
        # Only store in DB if email is not in excluded list
        if email not in EXCLUDED_EMAILS:
            conn = get_db_connection()
            conn.execute('INSERT INTO subscribers (name, email) VALUES (?, ?)', (name, email))
            conn.commit()
            conn.close()
        try:
            requests.post(NEWSLETTER_URL, json={'name': name, 'email': email}, timeout=5)
        except Exception:
            try:
                requests.post(NEWSLETTER_URL, data={'name': name, 'email': email}, timeout=5)
            except Exception:
                pass
    return redirect(url_for('index'))

@app.route('/reset_stats', methods=['POST'])
@login_required
def reset_stats():
    conn = get_db_connection()
    conn.execute('UPDATE posts SET views = 0')
    conn.execute('DELETE FROM subscribers')
    conn.commit()
    conn.close()
    flash('Views and subscriber statistics have been reset.')
    return redirect(url_for('stats'))


@app.route('/wishlist')
def wishlist():
    wishlist_ids = session.get('wishlist', [])
    posts = []
    if wishlist_ids:
        conn = get_db_connection()
        placeholders = ','.join(['?'] * len(wishlist_ids))
        posts = conn.execute(f'SELECT * FROM posts WHERE id IN ({placeholders})', wishlist_ids).fetchall()
        conn.close()
    return render_template('wishlist.html', posts=posts)

@app.route('/wishlist/add/<int:post_id>')
def add_to_wishlist(post_id):
    if 'wishlist' not in session: session['wishlist'] = []
    if post_id not in session['wishlist']:
        session['wishlist'].append(post_id)
        session.modified = True
    return jsonify({'status': 'added'})

@app.route('/wishlist/remove/<int:post_id>')
def remove_from_wishlist(post_id):
    if 'wishlist' in session and post_id in session['wishlist']:
        session['wishlist'].remove(post_id)
        session.modified = True
    return jsonify({'status': 'removed'})

@app.route('/post/<int:post_id>')
def post(post_id):
    conn = get_db_connection()
    # Only count views if not logged in as admin and not a user in excluded list
    user_email = session.get('user_email', '').strip().lower()
    if not session.get('logged_in') and user_email not in EXCLUDED_EMAILS:
        conn.execute('UPDATE posts SET views = views + 1 WHERE id = ?', (post_id,))
        conn.commit()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    related = conn.execute('SELECT id, title, image_url, category FROM posts WHERE category = ? AND id != ? ORDER BY id DESC LIMIT 3', (post['category'], post_id)).fetchall() if post else []
    comments = conn.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY id DESC', (post_id,)).fetchall()
    conn.close()
    return render_template('post.html', post=post, related_posts=related, comments=comments)

@app.route('/add_comment', methods=['POST'])
def add_comment():
    post_id = int(request.form.get('post_id', 0))
    name, comment_text = request.form.get('name', 'Anonymous'), request.form.get('comment')
    conn = get_db_connection()
    conn.execute('INSERT INTO comments (post_id, name, comment) VALUES (?, ?, ?)', (post_id, name, comment_text))
    conn.commit()
    conn.close()
    try: requests.post(COMMENT_URL, json={'post_id': post_id, 'name': name, 'comment': comment_text})
    except: pass
    return redirect(url_for('post', post_id=post_id)) if post_id else redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)