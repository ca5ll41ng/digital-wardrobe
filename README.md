# 👗 电子衣橱 (Digital Wardrobe)

一个自带智能抠图的个人电子衣橱应用。上传衣物照片 → 自动去除背景 → 归类存储 → 在画布上自由搭配。

## ✨ 功能

- **📤 智能抠图** — 上传图片后，后端自动调用 rembg 去除背景，输出透明 PNG
- **🗂 分类衣柜** — 支持上衣、裤子、连衣裙、半身裙、帽子、鞋子、包包、配饰 8 个分类
- **🎨 自由搭配画布** — 拖拽衣物到画布上，自由调整位置、大小、前后层级
- **💾 搭配方案保存** — 保存多个搭配方案，随时加载切换
- **📱 移动端适配** — 响应式布局，手机/平板也能用

## 🖼 截图

```
┌──────────────────────────────────────────────────┐
│  👗 电子衣橱          [添加衣物] [搭配] [保存]   │
├──────────────┬───────────────────────────────────┤
│ 🏠 我的衣柜  │       ✨ 搭配画布                 │
│ [全部][上衣] │                                   │
│ [裤子][裙子] │        ┌─────────────┐            │
│              │        │  👤 人体轮廓  │            │
│  ┌──┐ ┌──┐  │        │   🧥 外套    │            │
│  │👔│ │👖│  │        │   👖 裤子    │            │
│  └──┘ └──┘  │        │   👠 鞋子    │            │
│  ┌──┐ ┌──┐  │        └─────────────┘            │
│  │🧢│ │👜│  │        滚轮缩放 · 拖动调整        │
│  └──┘ └──┘  │                                   │
└──────────────┴───────────────────────────────────┘
```

## 🚀 快速开始

### 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务（首次运行 rembg 会自动下载 ~170MB 模型）
python app.py --host 0.0.0.0 --port 5000

# 3. 浏览器打开
# http://localhost:5000
```

### 部署到云服务器

```bash
# 上传项目
scp -r digital-wardrobe/ user@你的服务器IP:/tmp/

# SSH 登录
ssh user@你的服务器IP

# 一键部署（自动配置 systemd + nginx）
cd /tmp/digital-wardrobe
chmod +x deploy.sh
sudo ./deploy.sh
```

部署完成后访问 `http://服务器IP` 即可使用。

## 🛠 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python + Flask |
| 抠图 | rembg (U²-Net) |
| 图片处理 | Pillow |
| 数据库 | SQLite |
| 前端 | 原生 HTML/CSS/JS（零框架依赖） |
| 部署 | systemd + nginx + gunicorn |

## 📁 项目结构

```
digital-wardrobe/
├── app.py              # Flask 后端
├── requirements.txt    # Python 依赖
├── deploy.sh           # 一键部署脚本
├── .gitignore
├── README.md
├── templates/
│   └── index.html      # 前端单页面（含全部 CSS/JS）
├── uploads/            # 原始上传图片（自动创建，已 gitignore）
├── processed/          # 抠图后透明 PNG（自动创建，已 gitignore）
└── wardrobe.db         # SQLite 数据库（自动创建，已 gitignore）
```

## 📝 待办

- [ ] 人体姿态检测，衣物自动适配位置
- [ ] 多套搭配对比模式
- [ ] 导出搭配图为图片
- [ ] Docker 一键部署

## 📄 License

MIT
