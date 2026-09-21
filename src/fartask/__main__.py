import argparse

from .web.app import start_web_server


def main() -> None:
    parser = argparse.ArgumentParser(description="启动 fartask NiceGUI 看板")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    start_web_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
