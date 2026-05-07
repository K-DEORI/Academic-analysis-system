from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'srms_secret_key_2024'
DB = 'srms.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            class_numeric INTEGER NOT NULL,
            section TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            subject_code TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_id TEXT NOT NULL UNIQUE,
            class_id INTEGER NOT NULL,
            email TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(class_id) REFERENCES classes(id)
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            marks INTEGER NOT NULL,
            total_marks INTEGER NOT NULL DEFAULT 100,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        );
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    # Seed admin
    c.execute("INSERT OR IGNORE INTO admin (username, password) VALUES (?, ?)", ('admin', 'admin'))
    conn.commit()
    conn.close()

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ── PUBLIC ROUTES ──────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/public-notices')
def public_notices():
    conn = get_db()
    notices = conn.execute('SELECT * FROM notices ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('public_notices.html', notices=notices)

@app.route('/student-result', methods=['GET', 'POST'])
def student_result():
    conn = get_db()
    classes = conn.execute('SELECT * FROM classes ORDER BY class_numeric').fetchall()
    result = None
    error = None
    if request.method == 'POST':
        roll_id = request.form.get('roll_id', '').strip()
        class_id = request.form.get('class_id', '').strip()
        if not roll_id or not class_id:
            error = 'Please fill in all fields.'
        else:
            student = conn.execute(
                'SELECT s.*, c.class_name, c.section FROM students s JOIN classes c ON s.class_id=c.id WHERE s.roll_id=? AND s.class_id=?',
                (roll_id, class_id)
            ).fetchone()
            if not student:
                error = 'No student found with the given Roll ID and Class.'
            else:
                results = conn.execute(
                    '''SELECT r.marks, r.total_marks, sub.subject_name
                       FROM results r JOIN subjects sub ON r.subject_id=sub.id
                       WHERE r.student_id=?''',
                    (student['id'],)
                ).fetchall()
                total_obtained = sum(r['marks'] for r in results)
                total_max = sum(r['total_marks'] for r in results)
                percentage = round((total_obtained / total_max * 100), 2) if total_max else 0
                grade = get_grade(percentage)
                result = {
                    'student': student,
                    'results': results,
                    'total_obtained': total_obtained,
                    'total_max': total_max,
                    'percentage': percentage,
                    'grade': grade
                }
    conn.close()
    return render_template('student_result.html', classes=classes, result=result, error=error)

def get_grade(pct):
    if pct >= 90: return ('A+', 'Outstanding')
    if pct >= 80: return ('A', 'Excellent')
    if pct >= 70: return ('B', 'Very Good')
    if pct >= 60: return ('C', 'Good')
    if pct >= 50: return ('D', 'Average')
    return ('F', 'Fail')

# ── ADMIN AUTH ─────────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin'):
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db()
        admin = conn.execute('SELECT * FROM admin WHERE username=? AND password=?', (username, password)).fetchone()
        conn.close()
        if admin:
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))
        error = 'Invalid credentials.'
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

# ── ADMIN DASHBOARD ────────────────────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db()
    stats = {
        'students': conn.execute('SELECT COUNT(*) FROM students').fetchone()[0],
        'subjects': conn.execute('SELECT COUNT(*) FROM subjects').fetchone()[0],
        'classes': conn.execute('SELECT COUNT(*) FROM classes').fetchone()[0],
        'results': conn.execute('SELECT COUNT(DISTINCT student_id) FROM results').fetchone()[0],
    }
    notices = conn.execute('SELECT * FROM notices ORDER BY created_at DESC LIMIT 5').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', stats=stats, notices=notices)

# ── ADMIN MANAGEMENT ───────────────────────────────────────────────────────────

@app.route('/admin/admins')
@admin_required
def manage_admins():
    conn = get_db()
    admins = conn.execute('SELECT id, username FROM admin ORDER BY id').fetchall()
    conn.close()
    return render_template('manage_admins.html', admins=admins)

@app.route('/admin/admins/create', methods=['GET', 'POST'])
@admin_required
def create_admin():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if username and password:
            conn = get_db()
            try:
                conn.execute('INSERT INTO admin (username, password) VALUES (?,?)', (username, password))
                conn.commit()
                flash('Admin created successfully!', 'success')
                conn.close()
                return redirect(url_for('manage_admins'))
            except sqlite3.IntegrityError:
                flash('Username already exists.', 'danger')
                conn.close()
        else:
            flash('Please fill in all fields.', 'danger')
    return render_template('create_admin.html')

@app.route('/admin/admins/delete/<int:id>')
@admin_required
def delete_admin(id):
    conn = get_db()
    admin_to_delete = conn.execute('SELECT username FROM admin WHERE id=?', (id,)).fetchone()
    if admin_to_delete:
        if admin_to_delete['username'] == session['admin']:
            flash('You cannot delete your own account.', 'danger')
        else:
            conn.execute('DELETE FROM admin WHERE id=?', (id,))
            conn.commit()
            flash('Admin deleted.', 'info')
    conn.close()
    return redirect(url_for('manage_admins'))

# ── CLASSES ────────────────────────────────────────────────────────────────────

@app.route('/admin/classes')
@admin_required
def manage_classes():
    conn = get_db()
    classes = conn.execute('SELECT * FROM classes ORDER BY class_numeric').fetchall()
    conn.close()
    return render_template('manage_classes.html', classes=classes)

@app.route('/admin/classes/create', methods=['GET', 'POST'])
@admin_required
def create_class():
    if request.method == 'POST':
        name = request.form['class_name'].strip()
        numeric = request.form['class_numeric'].strip()
        section = request.form['section'].strip()
        if name and numeric and section:
            conn = get_db()
            conn.execute('INSERT INTO classes (class_name, class_numeric, section) VALUES (?,?,?)', (name, numeric, section))
            conn.commit()
            conn.close()
            flash('Class created successfully!', 'success')
            return redirect(url_for('manage_classes'))
    return render_template('create_class.html')

@app.route('/admin/classes/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_class(id):
    conn = get_db()
    cls = conn.execute('SELECT * FROM classes WHERE id=?', (id,)).fetchone()
    if request.method == 'POST':
        name = request.form['class_name'].strip()
        numeric = request.form['class_numeric'].strip()
        section = request.form['section'].strip()
        conn.execute('UPDATE classes SET class_name=?, class_numeric=?, section=?, updated_at=? WHERE id=?',
                     (name, numeric, section, datetime.now().strftime('%Y-%m-%d %H:%M'), id))
        conn.commit()
        conn.close()
        flash('Class updated!', 'success')
        return redirect(url_for('manage_classes'))
    conn.close()
    return render_template('edit_class.html', cls=cls)

@app.route('/admin/classes/delete/<int:id>')
@admin_required
def delete_class(id):
    conn = get_db()
    conn.execute('DELETE FROM classes WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Class deleted.', 'info')
    return redirect(url_for('manage_classes'))

# ── SUBJECTS ───────────────────────────────────────────────────────────────────

@app.route('/admin/subjects')
@admin_required
def manage_subjects():
    conn = get_db()
    subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_name').fetchall()
    conn.close()
    return render_template('manage_subjects.html', subjects=subjects)

@app.route('/admin/subjects/create', methods=['GET', 'POST'])
@admin_required
def create_subject():
    if request.method == 'POST':
        name = request.form['subject_name'].strip()
        code = request.form['subject_code'].strip()
        if name and code:
            conn = get_db()
            try:
                conn.execute('INSERT INTO subjects (subject_name, subject_code) VALUES (?,?)', (name, code))
                conn.commit()
                flash('Subject created!', 'success')
            except:
                flash('Subject code already exists.', 'danger')
            conn.close()
            return redirect(url_for('manage_subjects'))
    return render_template('create_subject.html')

@app.route('/admin/subjects/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_subject(id):
    conn = get_db()
    sub = conn.execute('SELECT * FROM subjects WHERE id=?', (id,)).fetchone()
    if request.method == 'POST':
        name = request.form['subject_name'].strip()
        code = request.form['subject_code'].strip()
        conn.execute('UPDATE subjects SET subject_name=?, subject_code=?, updated_at=? WHERE id=?',
                     (name, code, datetime.now().strftime('%Y-%m-%d %H:%M'), id))
        conn.commit()
        conn.close()
        flash('Subject updated!', 'success')
        return redirect(url_for('manage_subjects'))
    conn.close()
    return render_template('edit_subject.html', sub=sub)

@app.route('/admin/subjects/delete/<int:id>')
@admin_required
def delete_subject(id):
    conn = get_db()
    conn.execute('DELETE FROM subjects WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Subject deleted.', 'info')
    return redirect(url_for('manage_subjects'))

# ── STUDENTS ───────────────────────────────────────────────────────────────────

@app.route('/admin/students')
@admin_required
def manage_students():
    conn = get_db()
    students = conn.execute(
        'SELECT s.*, c.class_name, c.section FROM students s JOIN classes c ON s.class_id=c.id ORDER BY s.name'
    ).fetchall()
    conn.close()
    return render_template('manage_students.html', students=students)

@app.route('/admin/students/create', methods=['GET', 'POST'])
@admin_required
def create_student():
    conn = get_db()
    classes = conn.execute('SELECT * FROM classes ORDER BY class_numeric').fetchall()
    if request.method == 'POST':
        name = request.form['name'].strip()
        roll_id = request.form['roll_id'].strip()
        class_id = request.form['class_id']
        email = request.form.get('email', '').strip()
        try:
            conn.execute('INSERT INTO students (name, roll_id, class_id, email) VALUES (?,?,?,?)',
                         (name, roll_id, class_id, email))
            conn.commit()
            flash('Student registered!', 'success')
            return redirect(url_for('manage_students'))
        except:
            flash('Roll ID already exists.', 'danger')
    conn.close()
    return render_template('create_student.html', classes=classes)

@app.route('/admin/students/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_student(id):
    conn = get_db()
    student = conn.execute('SELECT * FROM students WHERE id=?', (id,)).fetchone()
    classes = conn.execute('SELECT * FROM classes ORDER BY class_numeric').fetchall()
    if request.method == 'POST':
        name = request.form['name'].strip()
        roll_id = request.form['roll_id'].strip()
        class_id = request.form['class_id']
        email = request.form.get('email', '').strip()
        conn.execute('UPDATE students SET name=?, roll_id=?, class_id=?, email=? WHERE id=?',
                     (name, roll_id, class_id, email, id))
        conn.commit()
        conn.close()
        flash('Student updated!', 'success')
        return redirect(url_for('manage_students'))
    conn.close()
    return render_template('edit_student.html', student=student, classes=classes)

@app.route('/admin/students/delete/<int:id>')
@admin_required
def delete_student(id):
    conn = get_db()
    conn.execute('DELETE FROM results WHERE student_id=?', (id,))
    conn.execute('DELETE FROM students WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Student deleted.', 'info')
    return redirect(url_for('manage_students'))

# ── RESULTS ────────────────────────────────────────────────────────────────────

@app.route('/admin/results')
@admin_required
def manage_results():
    conn = get_db()
    students = conn.execute(
        'SELECT s.*, c.class_name, c.section FROM students s JOIN classes c ON s.class_id=c.id ORDER BY s.name'
    ).fetchall()
    conn.close()
    return render_template('manage_results.html', students=students)

@app.route('/admin/results/add/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def add_result(student_id):
    conn = get_db()
    student = conn.execute(
        'SELECT s.*, c.class_name, c.section FROM students s JOIN classes c ON s.class_id=c.id WHERE s.id=?', (student_id,)
    ).fetchone()
    subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_name').fetchall()
    existing = conn.execute(
        'SELECT r.*, sub.subject_name FROM results r JOIN subjects sub ON r.subject_id=sub.id WHERE r.student_id=?',
        (student_id,)
    ).fetchall()
    existing_ids = {r['subject_id'] for r in existing}

    if request.method == 'POST':
        subject_id = request.form['subject_id']
        marks = request.form['marks']
        total_marks = request.form.get('total_marks', 100)
        if int(subject_id) in existing_ids:
            conn.execute('UPDATE results SET marks=?, total_marks=? WHERE student_id=? AND subject_id=?',
                         (marks, total_marks, student_id, subject_id))
        else:
            conn.execute('INSERT INTO results (student_id, subject_id, marks, total_marks) VALUES (?,?,?,?)',
                         (student_id, subject_id, marks, total_marks))
        conn.commit()
        flash('Result saved!', 'success')
        return redirect(url_for('add_result', student_id=student_id))
    conn.close()
    return render_template('add_result.html', student=student, subjects=subjects, existing=existing, existing_ids=existing_ids)

@app.route('/admin/results/delete/<int:id>')
@admin_required
def delete_result(id):
    conn = get_db()
    r = conn.execute('SELECT student_id FROM results WHERE id=?', (id,)).fetchone()
    student_id = r['student_id'] if r else None
    conn.execute('DELETE FROM results WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Result entry deleted.', 'info')
    return redirect(url_for('add_result', student_id=student_id) if student_id else url_for('manage_results'))

# ── NOTICES ────────────────────────────────────────────────────────────────────

@app.route('/admin/notices')
@admin_required
def manage_notices():
    conn = get_db()
    notices = conn.execute('SELECT * FROM notices ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('manage_notices.html', notices=notices)

@app.route('/admin/notices/create', methods=['GET', 'POST'])
@admin_required
def create_notice():
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        conn = get_db()
        conn.execute('INSERT INTO notices (title, content) VALUES (?,?)', (title, content))
        conn.commit()
        conn.close()
        flash('Notice posted!', 'success')
        return redirect(url_for('manage_notices'))
    return render_template('create_notice.html')

@app.route('/admin/notices/delete/<int:id>')
@admin_required
def delete_notice(id):
    conn = get_db()
    conn.execute('DELETE FROM notices WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Notice deleted.', 'info')
    return redirect(url_for('manage_notices'))

# ── CHANGE PASSWORD ────────────────────────────────────────────────────────────

@app.route('/admin/change-password', methods=['GET', 'POST'])
@admin_required
def change_password():
    error = None
    if request.method == 'POST':
        current = request.form['current_password']
        new = request.form['new_password']
        confirm = request.form['confirm_password']
        conn = get_db()
        admin = conn.execute('SELECT * FROM admin WHERE username=? AND password=?', (session['admin'], current)).fetchone()
        if not admin:
            error = 'Current password is incorrect.'
        elif new != confirm:
            error = 'New passwords do not match.'
        else:
            conn.execute('UPDATE admin SET password=? WHERE username=?', (new, session['admin']))
            conn.commit()
            flash('Password changed successfully!', 'success')
            conn.close()
            return redirect(url_for('admin_dashboard'))
        conn.close()
    return render_template('change_password.html', error=error)

# ── ANALYTICS API ──────────────────────────────────────────────────────────────

@app.route('/admin/analytics')
@admin_required
def analytics():
    conn = get_db()
    # Top performers
    top = conn.execute('''
        SELECT s.name, s.roll_id, c.class_name, c.section,
               SUM(r.marks) as total, SUM(r.total_marks) as max_marks,
               ROUND(SUM(r.marks)*100.0/SUM(r.total_marks),2) as pct
        FROM students s
        JOIN results r ON s.id=r.student_id
        JOIN classes c ON s.class_id=c.id
        GROUP BY s.id ORDER BY pct DESC LIMIT 10
    ''').fetchall()
    # Subject averages
    subj_avg = conn.execute('''
        SELECT sub.subject_name, ROUND(AVG(r.marks),1) as avg_marks
        FROM results r JOIN subjects sub ON r.subject_id=sub.id
        GROUP BY sub.id ORDER BY avg_marks DESC
    ''').fetchall()
    # Class performance
    class_perf = conn.execute('''
        SELECT c.class_name, c.section, COUNT(DISTINCT s.id) as student_count,
               ROUND(AVG(r.marks*100.0/r.total_marks),2) as avg_pct
        FROM classes c
        LEFT JOIN students s ON s.class_id=c.id
        LEFT JOIN results r ON r.student_id=s.id
        GROUP BY c.id
    ''').fetchall()
    conn.close()
    return render_template('analytics.html', top=top, subj_avg=subj_avg, class_perf=class_perf)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
