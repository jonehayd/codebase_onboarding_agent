#!/usr/bin/env bash
# EC2 setup script for Ubuntu 22.04 / 24.04 (t2.micro / t3.micro)
# Run as: sudo bash setup_ec2.sh
set -euo pipefail

APP_DIR="/opt/codebase-onboarding-agent"
APP_USER="appuser"
PYTHON_VERSION="3.12"

echo "==> Updating system packages"
apt-get update -y && apt-get upgrade -y

echo "==> Installing system dependencies"
apt-get install -y \
    python3.12 python3.12-venv python3.12-dev \
    build-essential libpq-dev \
    nginx certbot python3-certbot-nginx \
    redis-server \
    git curl

# --- PostgreSQL 16 + pgvector ---
echo "==> Installing PostgreSQL 16"
apt-get install -y lsb-release gnupg
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
    > /etc/apt/sources.list.d/pgdg.list
apt-get update -y
apt-get install -y postgresql-16 postgresql-client-16

echo "==> Installing pgvector for PostgreSQL 16"
apt-get install -y postgresql-16-pgvector

echo "==> Starting and enabling PostgreSQL and Redis"
systemctl enable --now postgresql
systemctl enable --now redis-server

# --- Application user ---
echo "==> Creating application user: $APP_USER"
id "$APP_USER" &>/dev/null || useradd --system --shell /bin/bash --create-home "$APP_USER"

# --- App directory ---
echo "==> Setting up application directory: $APP_DIR"
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

# --- Python venv ---
echo "==> Creating Python virtual environment"
sudo -u "$APP_USER" python3.12 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip

# --- Install app dependencies ---
# Copy your project to $APP_DIR first, then run:
#   sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/backend/requirements.txt

# --- Environment file ---
# Create $APP_DIR/backend/.env with your production values.
# Required variables (see backend/.env.example for full list):
#
#   DATABASE_URL=postgresql://appuser:PASSWORD@localhost:5432/onboarding
#   REDIS_URL=redis://localhost:6379
#   FRONTEND_URL=https://your-vercel-app.vercel.app
#   JWT_SECRET=$(openssl rand -base64 32)
#   OPEN_AI_KEY=sk-...
#   ANTHROPIC_KEY=sk-ant-...
#   GITHUB_CLIENT_ID=...
#   GITHUB_CLIENT_SECRET=...

# --- PostgreSQL: create DB and user ---
echo "==> Creating PostgreSQL database and user"
sudo -u postgres psql <<'SQL'
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'appuser') THEN
    CREATE USER appuser WITH PASSWORD 'CHANGE_ME';
  END IF;
END $$;
SELECT 'CREATE DATABASE onboarding OWNER appuser'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'onboarding')\gexec
GRANT ALL PRIVILEGES ON DATABASE onboarding TO appuser;
SQL

# --- Run migrations ---
# After deploying your app code and creating .env, run:
#   cd $APP_DIR/backend && sudo -u $APP_USER ../venv/bin/alembic upgrade head

# --- Nginx ---
echo "==> Configuring Nginx"
cp "$(dirname "$0")/nginx.conf" /etc/nginx/sites-available/onboarding-agent
ln -sf /etc/nginx/sites-available/onboarding-agent /etc/nginx/sites-enabled/onboarding-agent
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx

echo ""
echo "==> Nginx configured. Before getting a TLS certificate, point your domain's"
echo "    A record at this server's public IP, then run:"
echo "      sudo certbot --nginx -d YOUR_DOMAIN"

# --- Systemd service ---
echo "==> Creating systemd service"
cat > /etc/systemd/system/onboarding-agent.service <<EOF
[Unit]
Description=Codebase Onboarding Agent (FastAPI)
After=network.target postgresql.service redis.service

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=$APP_DIR/backend/.env
ExecStart=$APP_DIR/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable onboarding-agent

echo ""
echo "==> Setup complete. Next steps:"
echo "  1. Copy your project to $APP_DIR"
echo "  2. Install pip deps:  sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/backend/requirements.txt"
echo "  3. Create $APP_DIR/backend/.env with production values"
echo "  4. Run migrations:    cd $APP_DIR/backend && sudo -u $APP_USER $APP_DIR/venv/bin/alembic upgrade head"
echo "  5. Point DNS A record to this server's IP"
echo "  6. Get TLS cert:      sudo certbot --nginx -d YOUR_DOMAIN"
echo "  7. Start the service: sudo systemctl start onboarding-agent"
echo "  8. Check logs:        sudo journalctl -u onboarding-agent -f"
