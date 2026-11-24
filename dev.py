"""PyCharm 调试专用入口。

用法：在 PyCharm 里直接 Debug 本文件，断点打在 app/main.py 里即可命中。

原理：把 "app.main:app" 以字符串交给 uvicorn，由它用 importlib 把 app.main
作为「包 app 下的模块」加载，所以 main.py 里的 from . import __version__
能正确解析——这正是「脚本方式直接跑 main.py」做不到的。

注意：调试时保持 reload=False。uvicorn 的 --reload 会 fork 出子进程，
debugpy 附加的是父进程，子进程里的断点通常不会命中。改完代码手动重启即可。
需要换端口时设环境变量 FDE_PORT，例如 FDE_PORT=8125。
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=int(os.getenv("FDE_PORT", "8000")),
        reload=False,
        log_level="debug",
    )
