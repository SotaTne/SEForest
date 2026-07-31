"""SEForestデスクトップアプリケーションの起動入口。"""

from forest.application import ForestApp


def main() -> None:
    ForestApp().run()


if __name__ == "__main__":
    main()
