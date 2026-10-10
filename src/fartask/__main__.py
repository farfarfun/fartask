"""`python -m fartask` 命令行入口：启动 NiceGUI 网页看板。"""

import typer

from .web.app import start_web_server


def _start(
    host: str = typer.Option("0.0.0.0"),
    port: int = typer.Option(8080),
) -> None:
    """解析 `--host`/`--port` 参数并前台启动网页看板。

    Returns:
        无返回值。副作用是启动 NiceGUI 服务并阻塞当前进程直到服务退出。
    """
    start_web_server(host=host, port=port)


def main() -> None:
    """启动 fartask NiceGUI 看板。"""
    typer.run(_start)


if __name__ == "__main__":
    main()
