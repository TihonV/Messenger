from flask import Flask, request, jsonify, render_template, session, send_from_directory
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    
    # Пользователи
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    bio TEXT DEFAULT '',
                    avatar TEXT DEFAULT 'default.png',
                    is_moderator INTEGER DEFAULT 0,
                    is_verified INTEGER DEFAULT 0
                 )''')
    
    # Посты
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    content TEXT,
                    audio_path TEXT,
                    video_path TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    edited_at DATETIME
                 )''')
    
    # Сообщения
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER,
                    username TEXT NOT NULL,
                    message TEXT,
                    sticker TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                 )''')
    
    # Каналы
    c.execute('''CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT CHECK(type IN ('private', 'group', 'channel')) NOT NULL,
                    owner TEXT,
                    members TEXT DEFAULT '[]'
                 )''')
    
    # Стикеры
    c.execute('''CREATE TABLE IF NOT EXISTS stickers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    emoji TEXT NOT NULL
                 )''')
    
    # Создание модератора
    c.execute("SELECT * FROM users WHERE username = 'tihon'")
    if not c.fetchone():
        hashed = generate_password_hash('metla25')
        c.execute("INSERT INTO users (username, password, is_moderator, is_verified) VALUES (?, ?, 1, 1)", 
                  ('tihon', hashed))
    
    # Стикеры
    stickers = [
        ('smile', '😊'), ('heart', '❤️'), ('laugh', '😂'), ('angry', '😠'),
        ('cool', '😎'), ('cry', '😢'), ('surprised', '😲'), ('wink', '😉')
    ]
    for name, emoji in stickers:
        c.execute("INSERT OR IGNORE INTO stickers (name, emoji) VALUES (?, ?)", (name, emoji))
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'success': False, 'message': 'Заполните все поля'})
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    try:
        hashed = generate_password_hash(password)
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'message': 'Пользователь уже существует'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    c.execute("SELECT password, is_moderator, is_verified FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    if result and check_password_hash(result[0], password):
        session['username'] = username
        session['is_moderator'] = bool(result[1])
        session['is_verified'] = bool(result[2])
        conn.close()
        return jsonify({'success': True, 'is_moderator': bool(result[1]), 'is_verified': bool(result[2])})
    else:
        conn.close()
        return jsonify({'success': False, 'message': 'Неверные данные'})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Не авторизован'})
    data = request.get_json()
    content = data.get('content')
    audio_path = data.get('audio_path')
    video_path = data.get('video_path')
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    c.execute("INSERT INTO posts (username, content, audio_path, video_path) VALUES (?, ?, ?, ?)", 
              (session['username'], content, audio_path, video_path))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/get_posts', methods=['GET'])
def get_posts():
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    c.execute("SELECT id, username, content, audio_path, video_path, timestamp, edited_at, is_verified FROM posts JOIN users ON posts.username = users.username ORDER BY timestamp DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    posts = []
    for row in rows:
        post = {
            'id': row[0], 'username': row[1], 'content': row[2],
            'audio_path': row[3], 'video_path': row[4],
            'timestamp': row[5], 'edited_at': row[6], 'is_verified': bool(row[7])
        }
        posts.append(post)
    return jsonify(posts)

@app.route('/edit_post/<int:post_id>', methods=['POST'])
def edit_post(post_id):
    if 'username' not in session or not session.get('is_moderator'):
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    data = request.get_json()
    new_content = data.get('content')
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    c.execute("UPDATE posts SET content = ?, edited_at = CURRENT_TIMESTAMP WHERE id = ?", (new_content, post_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/delete_post/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    if 'username' not in session or not session.get('is_moderator'):
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    c.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/verify_user/<username>', methods=['POST'])
def verify_user(username):
    if 'username' not in session or not session.get('is_moderator'):
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_verified = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Не авторизован'})
    audio_file = request.files.get('audio')
    if not audio_file:
        return jsonify({'success': False, 'message': 'Аудио не загружено'})
    filename = f"{session['username']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    audio_file.save(filepath)
    return jsonify({'success': True, 'path': filename})

@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Не авторизован'})
    video_file = request.files.get('video')
    if not video_file:
        return jsonify({'success': False, 'message': 'Видео не загружено'})
    filename = f"{session['username']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    video_file.save(filepath)
    return jsonify({'success': True, 'path': filename})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/get_channels', methods=['GET'])
def get_channels():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Не авторизован'})
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    c.execute("SELECT id, name, type FROM channels WHERE owner = ? OR (type = 'group' AND members LIKE ?)", 
              (session['username'], f'%{session["username"]}%'))
    channels = c.fetchall()
    result = [{'id': row[0], 'name': row[1], 'type': row[2]} for row in channels]
    conn.close()
    return jsonify(result)

@app.route('/get_stickers', methods=['GET'])
def get_stickers():
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    c.execute("SELECT name, emoji FROM stickers")
    stickers = c.fetchall()
    conn.close()
    return jsonify([{'name': s[0], 'emoji': s[1]} for s in stickers])

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Не авторизован'})
    data = request.get_json()
    channel_id = data.get('channel_id')
    message = data.get('message')
    sticker = data.get('sticker')
    if not message and not sticker:
        return jsonify({'success': False, 'message': 'Сообщение пустое'})
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (channel_id, username, message, sticker) VALUES (?, ?, ?, ?)", 
              (channel_id, session['username'], message, sticker))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/get_messages', methods=['GET'])
def get_messages():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Не авторизован'})
    channel_id = request.args.get('channel_id')
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    c.execute("SELECT username, message, sticker, timestamp FROM messages WHERE channel_id = ? ORDER BY timestamp DESC LIMIT 50", (channel_id,))
    rows = c.fetchall()
    conn.close()
    messages = []
    for row in reversed(rows):
        msg = {'username': row[0], 'timestamp': row[3]}
        if row[1]: msg['message'] = row[1]
        elif row[2]: msg['sticker'] = row[2]
        messages.append(msg)
    return jsonify(messages)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
