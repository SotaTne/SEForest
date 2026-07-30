# Third-party notices

SEForestはGPL-3.0-or-laterで提供されます。第三者コンポーネントには、それぞれの
ライセンスが適用されます。

## 現在使用しているランタイム依存関係

| コンポーネント | 用途 | ライセンス | 同梱ファイル |
|---|---|---|---|
| Pillow 12.3.0 | 画像処理・画像出力 | MIT-CMUおよび同梱第三者ライセンス | `Pillow-MIT-CMU.txt` |
| Noto Serif JP | 画面・画像出力用フォント | SIL Open Font License 1.1 | `Noto-Serif-JP-OFL-1.1.txt` |
| PySide6 6.11.1 / Qt 6.11.1 | GUI、Graphics View、DnD、ジェスチャー | LGPL-3.0/GPL | `LGPL-3.0.txt`、`GPL-3.0.txt` |

## Qt/PySide6

Qt for Python Community Edition（PySide6）とQt Widgetsには、LGPL-3.0またはGPLの
条件が適用されます。本ディレクトリには次の公式ライセンス本文を配置しています。

- `LGPL-3.0.txt`
- `GPL-3.0.txt`

使用するQtモジュールはQt Core、Qt GUI、Qt WidgetsおよびQt Testです。配布物を作成する
場合は、PySide6 6.11.1に含まれる第三者コンポーネントのライセンスも同梱します。

## 開発ツール

PyInstaller、pytest、Ruff、tyなどの開発ツールは、それぞれのオープンソース
ライセンスに基づいて使用しています。これらはSEForestのランタイムライブラリとして
リンクするものではありません。
