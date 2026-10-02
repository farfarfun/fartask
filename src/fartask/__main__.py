"""`python -m fartask` 命令行入口：启动 NiceGUI 网页看板。"""

import argparse

from .web.app import start_web_server


def main() -> None:
    """解析 `--host`/`--port` 参数并前台启动网页看板。

    Returns:
        无返回值。副作用是启动 NiceGUI 服务并阻塞当前进程直到服务退出。
    """
    parser = argparse.ArgumentParser(description="启动 fartask NiceGUI 看板")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    start_web_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
