# SEForest

ソフトウェア工学II「樹状整列」のプロジェクトです。

## Forest ドキュメント

- [ホーム](./Forest_Document/index.html)
- [要求仕様書](./Forest_Document/Requirement/index.html)
- [開発計画書](./Forest_Document/DevelopmentPlan/index.html)
- [基本設計書](./Forest_Document/BasicDesign/index.html)
- [詳細設計書](./Forest_Document/DetailDesign/index.html)
- [テスト仕様書](./Forest_Document/TestSpecification/index.html)
- [テスト結果](./Forest_Document/TestResult/index.html)
- [開発実績](./Forest_Document/DevelopmentResult/index.html)
- [プログラム](./Forest_Document/Program/index.html)
- [マニュアル](./Forest_Document/Manual/index.html)

## Project Forest ヒント

- [Forest JavaDoc](./Project_Forest_Hints/Forest/JavaDoc/index.html)
- [Forest by MVC JavaDoc](./Project_Forest_Hints/Forest_by_MVC/JavaDoc/index.html)

## Project Map

- `Forest_Document/`: 授業で作成する各種ドキュメント。
- `Forest_Document/Requirement/`: 要求仕様書。
- `Forest_Document/DevelopmentPlan/`: 開発計画書。
- `Forest_Document/BasicDesign/`: 基本設計書。
- `Forest_Document/DetailDesign/`: 詳細設計書。
- `Forest_Document/TestSpecification/`: テスト仕様書。
- `Forest_Document/TestResult/`: テスト結果。
- `Forest_Document/DevelopmentResult/`: 開発実績。
- `Forest_Document/Program/`: プログラムに関する資料。
- `Forest_Document/Manual/`: マニュアル。
- `Project_Forest_Hints/`: Forest 実装の参考資料。
- `Project_Forest_Hints/Forest/`: 基本構成の JavaDoc とクラス図。
- `Project_Forest_Hints/Forest_by_MVC/`: MVC 構成の JavaDoc とクラス図。
- `Forest_Program/`: Python 実装、テスト、依存関係を置く場所。
- `docs/`: VitePress の入口。
- `docs/.vitepress/`: VitePress の設定とビルド出力。
- `mise.toml`: プロジェクトルートから使用する統合タスク。
- `.agents/skills/test-and-report/`: テストレビュー、実行、記録を支援する Skill。

<!--
## Future Project Map

次の項目は、将来的には使う可能性があるが、現段階では対応する実装、設計、資料が
完成していないため正式な Project Map には含めない。

- `Forest_Document/DetailDesign/image/DetailDesign.png`: 詳細設計の正本候補。
- `Forest_Program/Model/`: 樹状整列の処理状態と生成処理。
- `Forest_Program/View/`: GUI View。
- `ui/ui.png`: Viewの外観と配置の参考資料候補。
- `ui/index.html`: Viewの文言、構造、操作イメージを共有する参考資料候補。
- `.asta`: Astah などの設計資料候補。
- `.xlsx`: 表計算資料候補。
-->

## はじめにやること

- `mise install` を実行して、プロジェクトルートに仮想環境を構築し、依存関係をインストールします。
- `mise setup` を実行して、プロジェクトの初期セットアップを行います。
- 自分がどういうふうにドキュメントを変更したかを確認したかったら`mise docs:dev` を実行して、VitePress の開発サーバーを起動し、ドキュメントをブラウザで確認します。これはリアルタイムで変更を反映するので、ドキュメントの変更内容を確認したいときに便利です。

## Commands

コマンドはプロジェクトルートで実行します。標準表記には `mise run` を省略した短縮形を
使用します。

- Setup: `mise setup`
- All checks: `mise check`
- Python lint: `mise lint`
- Python format: `mise format`
- Type check: `mise typecheck`
- Test: `mise test`
- HTML lint: `mise check:html`
- HTML lint for selected files: `mise check:html path/to/file.html ...`
- Docs dev server: `mise docs:dev`
- Docs build: `mise docs:build`
- Docs preview: `mise docs:preview`

- 変更内容とリスクに応じて必要なコマンドを選択します。
- 共有コードや広範囲の変更では、関連する lint、format、typecheck、test を広く実行します。
- `lint` と `format` は用途を分け、整形確認や整形が必要な場合は `format` を実行します。
- ツールは検証済みの安定版へ固定します。更新は依頼に関係するものだけを対象とし、
  更新後に関連タスクを実行します。

## Python Rules

- Python標準の命名慣習に従います。
- `name` は公開API、`_name` は内部利用を示す非公開APIとして扱います。
- `__name` は完全なprivate表現ではなく、名前衝突回避が必要な場合だけ使用します。
- インスタンス属性は原則として `__init__` で定義します。dataclassやフレームワークなど
  標準的な実装理由がある場合は例外を許容します。
- クラス、メソッド、変数には、役割が分かる省略のない名前を付けます。
- 既存のパッケージ構成、モジュール構成、命名規則を尊重します。
- 型エラーは原則として原因を修正します。抑制は原因修正が現実的でなく、理由を説明できる
  最小範囲に限ります。
- 新しい依存関係は、目的と影響を説明し、`uv add` または `uv add --dev` で追加します。
- 依存関係の追加後は lockfile を含め、関連する検証まで行います。

## Testing

- Python のテストは `mise test` で実行します。
- テスト仕様と確認済み結果は `Forest_Document/TestSpecification/index.html` に記録します。
- テスト作業の詳細な運用ルールは `AGENTS.md` と `test-and-report` Skill を参照します。

## HTML

- すべてのHTML文書はHTML Living Standardに基づくHTML5、UTF-8として維持します。
- セマンティックな要素構造とアクセシビリティを考慮します。
- CSSは標準プロパティを優先し、必要な場合だけベンダープレフィックスを併記します。
- 既存の文字コード、CSS、ナビゲーション、レイアウト、文書固有の構成を、
  依頼とHTML5対応に必要な範囲を超えて変更しません。
- HTMLを更新した場合は、対応する文書のフッターの `Updated` を更新日へ変更します。
- `Forest_Document/Program/index.html` と `Forest_Document/TestResult/index.html` は、明確な理由や指示がない限り変更はしない
- HTML変更後は、対象範囲に応じて `mise check:html` を実行します。

<!--
- `ui/` はView共有用の参考資料であり、HTML/CSS/JavaScriptのファイル分割方法は固定しない。
  AIによる作成・更新を許容する。
-->

## Change Policy

- 変更方針と AI 作業時の制約は `AGENTS.md` を参照します。

## GitHub Pages

GitHub Pages 用にビルドします。

```sh
mise docs:build
```

ビルド結果は `docs/.vitepress/dist` に出力されます。
