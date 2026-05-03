# 🎓 Student Result Management System (SRMS)

A full-featured Python Flask web application for managing student academic results.

## 🚀 Quick Start

```bash
pip install flask
python app.py
```

Then visit: **http://localhost:5000**

## 🔐 Default Credentials

- **Username:** admin
- **Password:** admin

## ✨ Features

### Public
- **Home page** with feature overview
- **Student Result lookup** by Roll ID + Class — shows marks, totals, percentage, grade, progress bar, print support

### Admin Panel
- **Dashboard** with stats (students, subjects, classes, results)
- **Classes** — Create, edit, delete classes with sections
- **Subjects** — Create, edit, delete subjects with unique codes
- **Students** — Register, edit, delete students; assign to classes
- **Results** — Enter/update marks per subject per student; live grade calculation
- **Notices** — Post and manage school announcements
- **Analytics** — Top performers leaderboard, subject averages, class-wise performance
- **Change Password**

## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite
- **Frontend:** HTML5, CSS3, Jinja2 Templates

## 📁 Structure

```
srms/
├── app.py              # Flask application (all routes)
├── requirements.txt
├── srms.db             # SQLite database (auto-created)
└── templates/
    ├── base.html           # Public base
    ├── admin_base.html     # Admin sidebar layout
    ├── home.html
    ├── student_result.html
    ├── admin_login.html
    ├── admin_dashboard.html
    ├── manage_classes.html / create_class.html / edit_class.html
    ├── manage_subjects.html / create_subject.html / edit_subject.html
    ├── manage_students.html / create_student.html / edit_student.html
    ├── manage_results.html / add_result.html
    ├── manage_notices.html / create_notice.html
    ├── analytics.html
    └── change_password.html
```

## 🏆 Grade Scale

| Grade | Range     |
|-------|-----------|
| A+    | 90–100%   |
| A     | 80–89%    |
| B     | 70–79%    |
| C     | 60–69%    |
| D     | 50–59%    |
| F     | Below 50% |
