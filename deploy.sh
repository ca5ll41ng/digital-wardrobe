#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# 电子衣橱 - 云服务器部署脚本
# 用法:
#   git clone https://github.com/你的用户名/digital-wardrobe.git
#   cd digital-wardrobe
#   chmod +x deploy.sh
#   sudo ./deploy.sh
# ─────────────────────────────────────────────────────────
set -e

APP_DIR="/opt/digital-wardrobe"
SERVICE_NAME="digital-wardrobe"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== 电子衣橱部署 ==="

# ── 1. 安装系统依赖 ─────────────────────────────────────
echo "[1/5] 安装系统依赖..."

if command -v apt-get &>/dev/null; then
    # Debian / Ubuntu
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3 python3-pip python3-venv nginx
    NGINX_AVAILABLE="/etc/nginx/sites-available"
    NGINX_ENABLED="/etc/nginx/sites-enabled"
elif command -v dnf &>/dev/null; then
    # Fedora / RHEL 8+ / Rocky / Alma / OpenCloudOS
    sudo dnf install -y --disableexcludes=all python3 python3-pip nginx
    NGINX_AVAILABLE="/etc/nginx/conf.d"
    NGINX_ENABLED=""
elif command -v yum &>/dev/null; then
    # RHEL 7 / CentOS 7
    sudo yum install -y python3 python3-pip nginx
    NGINX_AVAILABLE="/etc/nginx/conf.d"
    NGINX_ENABLED=""
else
    echo "⚠ 无法识别包管理器，请手动安装: python3, pip, nginx"
fi

# ── 2. 创建应用目录并复制文件 ───────────────────────────
echo "[2/5] 创建应用目录..."
sudo mkdir -p "$APP_DIR"
sudo cp "$SCRIPT_DIR/app.py" "$APP_DIR/"
sudo cp "$SCRIPT_DIR/requirements.txt" "$APP_DIR/"
sudo cp -r "$SCRIPT_DIR/templates" "$APP_DIR/"
sudo mkdir -p "$APP_DIR/uploads" "$APP_DIR/processed"
sudo chown -R "$USER:$USER" "$APP_DIR"

# ── 3. 安装 Python 依赖 ─────────────────────────────────
echo "[3/5] 安装 Python 依赖..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt

# 预下载 rembg 模型（避免首次上传等待几分钟）
echo "  预下载 rembg 模型（~170MB），请耐心等待..."
python3 -c "
from rembg import remove
from PIL import Image
remove(Image.new('RGBA', (10, 10)))
print('  模型就绪')
" 2>&1 || echo "  模型预下载跳过（首次上传时会自动下载）"

# ── 4. 配置 systemd 服务 ────────────────────────────────
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
sudo systemctl restart ${SERVICE_NAME}

# ── 5. 配置 Nginx 反向代理 ──────────────────────────────
echo "[5/5] 配置 Nginx..."
if command -v nginx &>/dev/null; then
    NGINX_CONF="${NGINX_AVAILABLE}/${SERVICE_NAME}.conf"

    sudo tee "$NGINX_CONF" > /dev/null <<'NGINX'
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

    # Debian/Ubuntu 需要创建软链接
    if [ -n "$NGINX_ENABLED" ]; then
        sudo ln -sf "$NGINX_CONF" "${NGINX_ENABLED}/${SERVICE_NAME}.conf"
    fi

    sudo nginx -t && sudo systemctl reload nginx
fi

# ── 完成 ─────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  部署完成！"
echo "  访问地址: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '<服务器IP>')"
echo "========================================"
echo ""
echo "常用命令："
echo "  查看状态:  sudo systemctl status ${SERVICE_NAME}"
echo "  查看日志:  sudo journalctl -u ${SERVICE_NAME} -f"
echo "  重启服务:  sudo systemctl restart ${SERVICE_NAME}"
echo "  停止服务:  sudo systemctl stop ${SERVICE_NAME}"
