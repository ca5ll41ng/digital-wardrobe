#!/usr/bin/env python3
"""电子衣橱 - Flask 后端
功能：图片上传、rembg 自动抠图、衣柜分类管理、搭配方案保存
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, g, jsonify, request, send_file, render_template
from flask_cors import CORS
from PIL import Image
from rembg import remove

# ── 应用初始化 ──────────────────────────────────────────────
app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 最大上传 16MB

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / 'uploads'
PROCESSED_DIR = BASE_DIR / 'processed'
DB_PATH = BASE_DIR / 'wardrobe.db'

UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

MAX_PROCESS_DIM = 500        # 处理后最大尺寸
MAX_UPLOAD_DIM = 800         # 抠图前最大输入尺寸

CATEGORIES = ['top', 'bottom', 'dress', 'skirt', 'hat', 'shoes', 'bag', 'accessory']
CATEGORY_LABELS = {
    'top': '上衣', 'bottom': '裤子', 'dress': '连衣裙',
    'skirt': '半身裙', 'hat': '帽子', 'shoes': '鞋子',
    'bag': '包包', 'accessory': '配饰',
}

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}


# ── 数据库 ──────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def init_db():
    db = sqlite3.connect(str(DB_PATH))
    db.executescript('''
        CREATE TABLE IF NOT EXISTS items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT,
            category    TEXT    NOT NULL,
            original_filename TEXT,
            processed_filename TEXT NOT NULL,
            width       INTEGER DEFAULT 0,
            height      INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS outfits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            items_data  TEXT    NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    db.commit()
    db.close()


init_db()


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ── 辅助函数 ────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_image(input_path: Path):
    """rembg 抠图 → 保存为透明 PNG，返回 (路径, 文件名, 宽, 高)"""
    img = Image.open(input_path).convert('RGBA')
    if max(img.size) > MAX_UPLOAD_DIM:
        img.thumbnail((MAX_UPLOAD_DIM, MAX_UPLOAD_DIM), Image.LANCZOS)

    output = remove(img)

    if max(output.size) > MAX_PROCESS_DIM:
        output.thumbnail((MAX_PROCESS_DIM, MAX_PROCESS_DIM), Image.LANCZOS)

    out_filename = f"{uuid.uuid4().hex}.png"
    out_path = PROCESSED_DIR / out_filename
    output.save(out_path, 'PNG', optimize=True)
    return out_path, out_filename, output.size[0], output.size[1]


# ── 页面 ────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


# ── 图片 API ────────────────────────────────────────────────
@app.route('/api/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({'error': '未选择图片'}), 400

    file = request.files['image']
    category = request.form.get('category', '').strip()
    name = request.form.get('name', '').strip() or file.filename.rsplit('.', 1)[0]

    if not file.filename:
        return jsonify({'error': '文件名为空'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': f'不支持的格式，仅支持: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    if category not in CATEGORIES:
        return jsonify({'error': f'无效分类，可选: {", ".join(CATEGORIES)}'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    orig_filename = f"{uuid.uuid4().hex}.{ext}"
    orig_path = UPLOAD_DIR / orig_filename
    file.save(str(orig_path))

    try:
        out_path, processed_fn, w, h = process_image(orig_path)
    except Exception as e:
        orig_path.unlink(missing_ok=True)
        return jsonify({'error': f'抠图处理失败: {str(e)}'}), 500

    db = get_db()
    cur = db.execute(
        'INSERT INTO items (name, category, original_filename, processed_filename, width, height) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (name, category, orig_filename, processed_fn, w, h)
    )
    item_id = cur.lastrowid
    db.commit()

    return jsonify({
        'id': item_id,
        'name': name,
        'category': category,
        'processed_filename': processed_fn,
        'width': w,
        'height': h,
        'created_at': datetime.now().isoformat(),
    }), 201


@app.route('/api/items', methods=['GET'])
def list_items():
    category = request.args.get('category', '').strip()
    db = get_db()
    if category and category in CATEGORIES:
        rows = db.execute(
            'SELECT * FROM items WHERE category=? ORDER BY created_at DESC', (category,)
        ).fetchall()
    else:
        rows = db.execute('SELECT * FROM items ORDER BY category, created_at DESC').fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    db = get_db()
    row = db.execute('SELECT * FROM items WHERE id=?', (item_id,)).fetchone()
    if not row:
        return jsonify({'error': '物品不存在'}), 404

    orig = UPLOAD_DIR / row['original_filename']
    proc = PROCESSED_DIR / row['processed_filename']
    orig.unlink(missing_ok=True)
    proc.unlink(missing_ok=True)

    db.execute('DELETE FROM items WHERE id=?', (item_id,))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/image/<filename>')
def serve_image(filename):
    path = PROCESSED_DIR / filename
    if not path.exists():
        return jsonify({'error': '图片不存在'}), 404
    return send_file(str(path), mimetype='image/png')


# ── 搭配 API ────────────────────────────────────────────────
@app.route('/api/outfits', methods=['GET'])
def list_outfits():
    db = get_db()
    rows = db.execute('SELECT * FROM outfits ORDER BY created_at DESC').fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d['items_data'] = json.loads(d['items_data'])
        result.append(d)
    return jsonify(result)


@app.route('/api/outfits', methods=['POST'])
def save_outfit():
    data = request.get_json(force=True)
    name = data.get('name', '').strip()
    items_data = data.get('items_data', [])

    if not name:
        return jsonify({'error': '搭配名称不能为空'}), 400
    if not isinstance(items_data, list):
        return jsonify({'error': 'items_data 必须是数组'}), 400

    db = get_db()
    cur = db.execute(
        'INSERT INTO outfits (name, items_data) VALUES (?, ?)',
        (name, json.dumps(items_data, ensure_ascii=False))
    )
    outfit_id = cur.lastrowid
    db.commit()

    return jsonify({
        'id': outfit_id,
        'name': name,
        'items_data': items_data,
        'created_at': datetime.now().isoformat(),
    }), 201


@app.route('/api/outfits/<int:outfit_id>', methods=['DELETE'])
def delete_outfit(outfit_id):
    db = get_db()
    row = db.execute('SELECT id FROM outfits WHERE id=?', (outfit_id,)).fetchone()
    if not row:
        return jsonify({'error': '搭配不存在'}), 404
    db.execute('DELETE FROM outfits WHERE id=?', (outfit_id,))
    db.commit()
    return jsonify({'ok': True})


# ── 启动 ────────────────────────────────────────────────────
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='电子衣橱服务')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)
