# FarmConnect Backend

Backend API for **FarmConnect**, built with Django, Django REST Framework, and PostgreSQL.

This repository contains only the backend services and API.

---

## Tech Stack

* Python 3.12+
* Django
* Django REST Framework
* PostgreSQL
* psycopg
* django-cors-headers
* python-dotenv

---

# Project Structure

```text
backend/
│
├── api/
│   ├── migrations/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── .env
├── .gitignore
├── manage.py
├── requirements.txt
└── venv/
```

---

# Requirements

Before starting, make sure you have:

* Python 3.12+
* PostgreSQL
* Git
* pip

Check Python:

```bash
python3 --version
```

Check PostgreSQL:

```bash
psql --version
```

---

# Installation

## 1. Clone the Repository

```bash
git clone <REPOSITORY_URL>
```

Enter the backend:

```bash
cd backend
```

---

# 2. Create a Virtual Environment

Linux/macOS:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

---

# 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If you're setting up the project for the first time and `requirements.txt` isn't available:

```bash
pip install django djangorestframework django-cors-headers python-dotenv "psycopg[binary]"
```

Then:

```bash
pip freeze > requirements.txt
```

---

# PostgreSQL Setup

## 4. Install PostgreSQL

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

Check that PostgreSQL is running:

```bash
sudo systemctl status postgresql
```

Start it if necessary:

```bash
sudo systemctl start postgresql
```

---

# 5. Create the Database

Open PostgreSQL:

```bash
sudo -u postgres psql
```

Create the FarmConnect database:

```sql
CREATE DATABASE farmconnect;
```

Create the database user:

```sql
CREATE USER farmconnect_user WITH PASSWORD 'farmconnect_password';
```

Grant database access:

```sql
GRANT ALL PRIVILEGES ON DATABASE farmconnect TO farmconnect_user;
```

Connect to the database:

```sql
\c farmconnect
```

Grant schema permissions:

```sql
GRANT USAGE, CREATE ON SCHEMA public TO farmconnect_user;
```

Grant permissions on existing tables:

```sql
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO farmconnect_user;
```

Grant sequence permissions:

```sql
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO farmconnect_user;
```

Configure permissions for future tables:

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON TABLES TO farmconnect_user;
```

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL ON SEQUENCES TO farmconnect_user;
```

Exit:

```sql
\q
```

---

# Environment Variables

## 6. Create `.env`

Inside the backend directory:

```bash
touch .env
```

Add:

```env
DEBUG=True

SECRET_KEY=change-this-development-secret-key

DB_NAME=farmconnect
DB_USER=farmconnect_user
DB_PASSWORD=farmconnect_password
DB_HOST=localhost
DB_PORT=5432
```

### Important

**Never commit ****`.env`**** to GitHub.**

Your `.gitignore` should contain:

```gitignore
.env
venv/
__pycache__/
*.pyc
db.sqlite3
```

---

# Django Configuration

Django loads the environment variables from `.env`.

Your database configuration should use PostgreSQL:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}
```

---

# Database Migrations

After setting up PostgreSQL, run:

```bash
python manage.py migrate
```

This creates Django's required tables in PostgreSQL.

When you modify a Django model:

```bash
python manage.py makemigrations
```

Then:

```bash
python manage.py migrate
```

### Important

Migration files should be committed to Git.

---

# Create Admin User

Create a Django administrator:

```bash
python manage.py createsuperuser
```

Follow the prompts.

---

# Run the Development Server

Start Django:

```bash
python manage.py runserver
```

The backend will run at:

```text
http://127.0.0.1:8000/
```

Admin panel:

```text
http://127.0.0.1:8000/admin/
```

---

# API Structure

FarmConnect APIs will be available under:

```text
/api/
```

Planned API structure:

```text
/api/auth/
/api/farmers/
/api/buyers/
/api/products/
/api/orders/
/api/payments/
```

This structure will evolve as development continues.

---

# Development Workflow

Before starting work:

```bash
git pull
```

Activate the virtual environment:

```bash
source venv/bin/activate
```

Run the server:

```bash
python manage.py runserver
```

---

# Creating a New Feature

Create a feature branch:

```bash
git checkout -b feature/farmer-api
```

Examples:

```text
feature/farmer-api
feature/product-api
feature/order-api
feature/payment-api
feature/authentication
```

Make your changes and test them.

Check Django:

```bash
python manage.py check
```

Run tests:

```bash
python manage.py test
```

Commit:

```bash
git add .
git commit -m "feat: add farmer API"
```

Push:

```bash
git push origin feature/farmer-api
```

Then create a Pull Request.

---

# Git Rules

Do not commit:

```text
.env
venv/
__pycache__/
*.pyc
```

Do commit:

```text
models.py
views.py
serializers.py
urls.py
migrations/
requirements.txt
```

---

# Common Commands

### Start server

```bash
python manage.py runserver
```

### Check project

```bash
python manage.py check
```

### Create migrations

```bash
python manage.py makemigrations
```

### Apply migrations

```bash
python manage.py migrate
```

### Create admin user

```bash
python manage.py createsuperuser
```

### Run tests

```bash
python manage.py test
```

### Open Django shell

```bash
python manage.py shell
```

---

# Troubleshooting

## `permission denied for schema public`

Run:

```bash
sudo -u postgres psql
```

Then:

```sql
\c farmconnect

GRANT USAGE, CREATE ON SCHEMA public TO farmconnect_user;
```

Exit:

```sql
\q
```

Then:

```bash
python manage.py migrate
```

---

## PostgreSQL is not running

```bash
sudo systemctl status postgresql
```

Start it:

```bash
sudo systemctl start postgresql
```

---

## Database connection error

Check `.env`:

```env
DB_NAME=farmconnect
DB_USER=farmconnect_user
DB_PASSWORD=farmconnect_password
DB_HOST=localhost
DB_PORT=5432
```

Then:

```bash
python manage.py check
```

---

# Current Backend Status

* [x] Django initialized
* [x] Django REST Framework configured
* [x] PostgreSQL configured
* [x] `.env` configured
* [x] CORS configured
* [x] Database migrations configured
* [ ] Authentication
* [ ] User model
* [ ] Farmer API
* [ ] Buyer API
* [ ] Product API
* [ ] Order API
* [ ] Payment API
* [ ] API documentation
* [ ] Production deployment

---

# Team

When joining the project:

1. Clone the repository.
2. Create your virtual environment.
3. Install dependencies.
4. Create your local PostgreSQL database.
5. Create your `.env`.
6. Run migrations.
7. Create your admin user.
8. Run the server.
9. Create a feature branch before making changes.

```bash
git checkout -b feature/your-feature
```

Keep the backend clean, modular, and API-focused.-----devmorgan
