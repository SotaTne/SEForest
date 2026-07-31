---
name: record-test-environment
description: mise testが全件成功した時、またはユーザーが動作確認の成功を明言した時に使用する。実行中マシンの環境情報(OS、CPU、メモリ、Python/uv/mise/flet等のバージョン)を収集し、TestResult/index.htmlに未記載の環境であれば追加案を提示し、承認後に追記する。
---

# Record Test Environment

`mise test` の成功、または動作確認の成功を確認した際に、その時点の実行環境を
`TestResult/index.html` へ記録するかどうかをユーザーに確認し、承認された場合だけ
追記する。

## 基本原則

- `TestResult/index.html` は `AGENTS.md` により明示依頼なしに変更しないと
  定められている。このSkillが起動条件を満たしても、**必ず追加案を提示して
  ユーザーの承認を得てから書き込む**。無断で書き込まない。
- 環境情報はコマンド実行で取得できる事実だけを記載する。推測や一般論を書かない。
- 取得できない項目は空欄にせず、その行ごと省略する。
- macOS以外の環境で取得コマンドが対応していない場合は、対応できない旨を報告し、
  取得できる範囲だけで追加案を作るか、Skipするかをユーザーに確認する。
- `Program/index.html` や `TestSpecification/index.html` など他の文書は対象外。

## 起動条件

次のいずれかを満たした直後に、このSkillの実行を提案する。

- `mise test`(`uv run --all-packages pytest TypistArt Mobile`)を実行し、
  全件成功した時。
- ユーザーが `mise dev` / `mise dev:mobile` などによる動作確認の成功を
  会話の中で明言した時。

いずれの場合も、テスト・動作確認そのものの結果報告を先に行い、その直後に
「この環境をTestResult/index.htmlへ記録しますか？」と一言添える形で提案する。
ユーザーが依頼していないタイミングで先回りして書き込みを始めない。

## ワークフロー

### 1. 環境情報を収集する

現在のOSに応じたコマンドで事実を集める。macOSの場合の例:

```bash
sw_vers -productName
sw_vers -productVersion
sw_vers -buildVersion
uname -m
system_profiler SPHardwareDataType   # Model Name / Model Identifier / Chip または Processor Name / Memory
uv run python3 --version
uv --version
mise --version
uv run --project Mobile python -c "import flet; print(flet.version.version)"
uv run ruff --version
uv run pyrefly --version
```

macOS以外(Windows/Linuxなど)では、同等の情報が取れる標準コマンド
(`systeminfo`、`lsb_release -a`、`uname -a` 等)に読み替える。対応コマンドが
不明な場合は、無理に推測せずユーザーに確認する。

収集する項目:

- 機種名・Model Identifier(重複判定のキーに使う)
- CPUアーキテクチャ/プロセッサ名
- メモリ容量
- OS名・バージョン・ビルド番号
- Python / uv / mise / flet / ruff / pyrefly のバージョン
- 確認したテスト対象(TypistArt(Desktop) / Mobile / 両方)

### 2. 重複を判定する

`TestResult/index.html` を読み、収集した **Model Identifier + OSバージョン**
の組み合わせが既存エントリに含まれていないか確認する(`grep` などで該当する
`<h3>`/`<h4>`/`<pre>` の記載を探す)。

- 完全に一致する組み合わせが既にあれば、新規追加は不要と判断し、その旨を
  報告して終了する(書き込みは行わない)。
- 機種は同じでもOSバージョンが異なる場合は、別エントリとして追加してよい。

### 3. 追加案を提示する

書き込む前に、実際に挿入するHTML断片をそのまま会話に示し、次を明示して
承認を求める。

- 挿入位置(既存エントリの末尾、`<hr>` とフッターの直前)
- 収集した値の一覧
- 初回追加時は、プレースホルダー(`完成させてください` の `div.belt` ブロック)
  を削除する旨

### 4. 承認後に追記する

承認が得られたら、次を行う。

- プレースホルダーブロックが残っている場合は、初回追加時に限り削除する。
- 下記テンプレートに沿った `<div class="belt">` ブロックを、既存エントリの
  末尾・`<hr>` の直前に追記する。
- 既存の `<style>` に定義済みのクラス(`belt`、`content`、`left-small` 等)を
  再利用し、新しいCSSクラスは追加しない。
- フッターの `Updated:` を追記した日付へ更新する。`Created:` は変更しない。

#### エントリテンプレート

```html
<div class="belt">
<h3 id="{ModelIdentifierをケバブケース化したスラッグ}">{機種名}</h3>
</div>
<h4>【正常動作：{YYYY年M月D日}】{確認したテスト対象}のテストが全件成功</h4>
<h4>OS: {OS名} {OSバージョン} (Build {ビルド番号})</h4>
<pre>Python {version}
uv {version}
mise {version}
flet {version}
ruff {version}
pyrefly {version}</pre>
<table class="content" summary="table">
  <tbody>
    <tr>
      <td class="left-small">
      <ul>
        <li>Model Identifier: {Model Identifier}
        </li><li>Processor: {CPU情報}
        </li><li>Memory: {メモリ容量}
        </li><li>Architecture: {uname -mの結果}
      </li></ul>
      </td>
    </tr>
  </tbody>
</table>
```

写真・PDFへのリンクは自動生成できないため含めない。ユーザーが後から手動で
追加したい場合は、その旨だけ伝える。

## 完了条件

次を満たした時に作業完了とする。

- 追加案をユーザーへ提示し、承認を得ている(却下された場合は書き込まずに終了)。
- 承認された内容だけを `TestResult/index.html` へ反映している。
- フッターの `Updated` を更新している。
- 重複と判断して追加しなかった場合は、その理由を報告している。
