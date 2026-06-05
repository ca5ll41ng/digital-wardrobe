"""
电子衣橱 - 桌面版入口
启动 Flask 后端 + 原生桌面窗口，所有操作在窗口内完成
"""
import sys
import threading
import webview

from app import app

PORT = 5000
WINDOW_TITLE = '电子衣橱'


def start_flask():
    """后台启动 Flask，关闭 reloader 避免双进程"""
    app.run(
        host='127.0.0.1',
        port=PORT,
        debug=False,
        use_reloader=False,
    )


def main():
    # Flask 后台线程
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # 原生桌面窗口
    webview.create_window(
        title=WINDOW_TITLE,
        url=f'http://127.0.0.1:{PORT}',
        width=1150,
        height=780,
        min_size=(900, 600),
        text_select=True,
        confirm_close=True,
    )

    # 阻塞直到窗口关闭
    webview.start()

    # 清理
    sys.exit(0)


if __name__ == '__main__':
    # PyInstaller 打包后禁用 stdout/stderr 缓冲
    if getattr(sys, 'frozen', False):
        import os
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    main()
