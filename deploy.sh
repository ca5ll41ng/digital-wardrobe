#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# 电子衣橱 - 云服务器部署脚本
# 使用方法: chmod +x deploy.sh && ./deploy.sh
# ─────────────────────────────────────────────────────────
set -e

APP_DIR="/opt/digital-wardrobe"
SERVICE_NAME="digital-wardrobe"

echo "=== 电子衣橱部署 ==="

# 1. 安装系统依赖
echo "[1/5] 安装系统依赖..."
if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3 python3-pip python3-venv nginx
elif command -v yum &>/dev/null; then
    sudo yum install -y python3 python3-pip nginx
else
    echo "请手动安装: python3, pip, nginx"
fi

# 2. 创建应用目录
echo "[2/5] 创建应用目录..."
sudo mkdir -p "$APP_DIR"
sudo cp -r app.py requirements.txt templates "$APP_DIR/"
sudo mkdir -p "$APP_DIR/uploads" "$APP_DIR/processed"
sudo chown -R $USER:$USER "$APP_DIR"

# 3. 安装 Python 依赖
echo "[3/5] 安装 Python 依赖..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 预下载 rembg 模型（可选，避免首次请求等待）
python3 -c "from rembg import remove; from PIL import Image; import io; remove(Image.new('RGBA', (10,10)))" 2>/dev/null || true

# 4. 配置 systemd 服务
echo "[4/5] 配置 systemd 服务..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Digital Wardrobe Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn app:app -w 2 -b 127.0.0.1:5000 --timeout 60
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl start ${SERVICE_NAME}

# 5. 配置 Nginx 反向代理（可选）
echo "[5/5] 配置 Nginx..."
if command -v nginx &>/dev/null; then
    sudo tee /etc/nginx/sites-available/${SERVICE_NAME} > /dev/null <<'NGINX'
server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
NGINX

    sudo ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl reload nginx
fi

echo ""
echo "=== 部署完成 ==="
echo "服务运行在: http://<你的服务器IP>"
echo "查看状态: sudo systemctl status ${SERVICE_NAME}"
echo "查看日志: sudo journalctl -u ${SERVICE_NAME} -f"
