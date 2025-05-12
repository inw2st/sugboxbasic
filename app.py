from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# SQLite 초기화
def init_db():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grade TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )''')
    # 초기 관리자 계정 생성 (username: admin, password: admin123)
    c.execute("INSERT OR IGNORE INTO admin (username, password) VALUES (?, ?)", ('admin', 'admin123'))
    conn.commit()
    conn.close()

# 디바이스 제한 확인 함수
def can_submit(request):
    last_submit = request.cookies.get('last_submit')
    if last_submit:
        last_time = datetime.strptime(last_submit, '%Y-%m-%d')
        if last_time.date() == datetime.now().date():
            return False
    return True

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        grade = request.form.get('grade')
        content = request.form.get('content')

        if not grade or not content:
            return '모든 항목을 입력해주세요.', 400

        if not can_submit(request):
            return '오늘은 이미 건의사항을 제출하셨습니다.', 403

        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        c.execute('INSERT INTO suggestions (grade, content) VALUES (?, ?)', (grade, content))
        suggestion_id = c.lastrowid
        conn.commit()
        conn.close()

        response = make_response(jsonify({'id': suggestion_id}))
        response.set_cookie('last_submit', datetime.now().strftime('%Y-%m-%d'), max_age=86400)
        return response

    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        c.execute('SELECT * FROM admin WHERE username=? AND password=?', (username, password))
        admin = c.fetchone()
        conn.close()

        if admin:
            session['admin'] = username
            return redirect(url_for('admin_panel'))
        else:
            return '로그인 실패', 401

    return render_template('admin_login.html')

@app.route('/admin/panel')
def admin_panel():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('SELECT id, grade, content FROM suggestions ORDER BY timestamp DESC')
    suggestions = c.fetchall()
    conn.close()

    return render_template('admin_panel.html', suggestions=suggestions)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
