# Non-Docker Deployment Instructions

This document provides instructions for running the Shooting Range system without Docker.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Redis server
- PostgreSQL (optional, SQLite for development)

## Backend Setup

### 1. Install Redis

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
```

**Windows:**
Download and run Redis for Windows from https://github.com/tporadowski/redis/releases

### 2. Install PostgreSQL (Production)

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

Create database:
```bash
sudo -u postgres createdb shooting_range
```

### 3. Backend Installation

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgres://postgres:postgres@localhost:5432/shooting_range
export REDIS_URL=redis://localhost:6379/0
export USE_REDIS=true
export DJANGO_SECRET_KEY=your-secret-key
export ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 4. Run Backend

**Development (Daphne):**
```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

**Production (Gunicorn):**
```bash
gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000
```

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Run Development Server

```bash
npm run dev
```

The frontend will be available at http://localhost:3000

### 3. Build for Production

```bash
npm run build
```

Serve the `dist` folder using any static file server (nginx, Apache, etc.)

## Access Points

- **Frontend Client Screen:** http://localhost:3000/client/1
- **Admin Dashboard:** http://localhost:3000/admin
- **Django Admin:** http://localhost:8000/admin
- **WebSocket (Device):** ws://localhost:8000/ws/device/
- **WebSocket (Client):** ws://localhost:8000/ws/client/
- **WebSocket (Admin):** ws://localhost:8000/ws/admin/

## Systemd Service (Linux)

Create `/etc/systemd/system/shooting-range-backend.service`:

```ini
[Unit]
Description=Shooting Range Backend
After=network.target redis.postgresql

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/shooting-range/backend
Environment="PATH=/opt/shooting-range/backend/venv/bin"
Environment="DATABASE_URL=postgres://postgres:postgres@localhost:5432/shooting_range"
Environment="REDIS_URL=redis://localhost:6379/0"
Environment="USE_REDIS=true"
ExecStart=/opt/shooting-range/backend/venv/bin/gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable shooting-range-backend
sudo systemctl start shooting-range-backend
```

## Configuration

All configuration is done via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | SQLite (dev) |
| REDIS_URL | Redis connection string | redis://localhost:6379/0 |
| USE_REDIS | Use Redis for Channels | false (dev) |
| DJANGO_SECRET_KEY | Secret key for Django | auto-generated |
| ALLOWED_HOSTS | Allowed hostnames | localhost |
| DJANGO_DEBUG | Debug mode | True |
