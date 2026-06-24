# Project Guide

## Project

- プロジェクト名は `SEForest`。
- Python 実装は `Forest_Program/` に置く。
- Python 3.13、uv、mise、Bun、VitePress を使用する。
- プロジェクト構成、コマンド、Python ルール、HTML 方針の詳細は `README.md` を参照する。
- 作業に必要な範囲だけを調査し、すべての資料を毎回読み込まない。
- 資料やコードから判断できる軽微な事項は合理的に決定し、仕様、設計、公開API、
  データ損失などに関わる重要な不明点だけをユーザーへ確認する。

## Source Priority

作業対象に応じて、必要な資料だけを次の順で参照する。

1. ユーザーの明示指示
2. `README.md` の Project Map と開発方針
3. `Forest_Document/Requirement/` の要求仕様書
4. `Forest_Program/` の現行実装
5. `Project_Forest_Hints/` の参考実装と JavaDoc

<!--
次の項目は、将来的には使う可能性があるが、現段階では対応する実装、設計、資料が
完成していないため正式な参照元にはしない。

- `Forest_Document/DetailDesign/image/DetailDesign.png` を詳細設計の正本とし、システム全体で必要な
  機能、クラスの責務、属性、メソッド、継承、依存関係、多重度、パッケージ構成の
  判断に使用する。
- 詳細設計図のJava風の型や構文は、責務と公開操作を変えずPythonへ読み替える。
- Viewの実装・変更では、`ui/ui.png` を外観と配置、`ui/index.html` を文言、構造、
  操作イメージの参考資料とする。その後、詳細設計図で必要な全体機能とController
  連携を確認し、使用するGUIライブラリで実現可能な形へ読み替える。
-->

- 軽微な不一致は影響を確認して作業を継続してよい。責務、公開API、依存関係、
  多重度、要求仕様に関わる重要な不一致は、影響範囲と選択肢を報告して判断を求める。
- 新しいクラス、属性、メソッド、依存関係を追加する場合は、詳細設計図の更新要否を
  確認する。
- `Forest_Document/BasicDesign/`、`Forest_Document/DevelopmentPlan/`、
  `Forest_Document/DevelopmentResult/`、`Forest_Document/Manual/`、ルート直下の未整理な画像や文書、
  `下書き/`、`.asta`、`.xlsx` は、作業で明示的に必要な場合を除いて参照・変更しない。

## Testing

- `test-and-report` Skill は、テストが追加・変更された後、ユーザーがテストの追加・実行・
  記録を依頼した場合、または結果を `Forest_Document/TestSpecification/index.html` へ
  反映する場合に使用する。
- Skill の手順に従い、正常系、異常系、境界値、独立性、再現性を確認する。
- `Forest_Document/TestSpecification/index.html` には、実際に実行して確認した対応箇所だけを
  記録する。
- 不明、未確認、間接的に正しいだけの項目を `良好` と記録しない。
- `Forest_Document/TestResult/index.html` は明示依頼なしに変更しない。
- 要求仕様書や設計書と実装の整合性確認は、テスト作業と分離する。

## Change Policy

- 依頼と関係のないファイルを変更しない。
- Git の既存変更を勝手に取り消さず、作業対象と重なる場合は内容を確認して共存させる。
- `.venv/`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`、その他の生成キャッシュを
  成果物へ追加せず、通常の参照・変更対象にしない。
- 破壊的操作、外部サービスへの書き込み、データ損失の可能性がある操作は事前に確認する。
