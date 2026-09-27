# HANDOFF: MiL 指示文の改良

最終更新: 2026-09-27。このファイルが引継ぎの正本。新しいセッションはまずここを読むこと。

## 目的

LLM に圧縮した応答をさせる指示文「MiL」を、次の2つを満たすように改良する。

1. **意味を保ったまま、トークン数をできるだけ少なくする**（MiL 自身のルール）
2. **Opus・Sonnet・Haiku のどのモデルが読んでも、意図どおりに伝わる**

## 現時点の結論

| 用途 | 推奨版 | トークン | 備考 |
|---|---|---|---|
| **全モデル向け（本命）** | **L_merge** | **89** | 3モデルすべてに伝わった |
| 全モデル向け（次の本命候補） | L2_ifeq | 87 | L の `IF`・`@` の定義を `=` と開いた語にした版。**読解テスト未実施** |
| 衝突の指摘を最小にしたい | M_scoped / M2_fixed | 99 | L に `mode:` と `(NL_ok)` を追加。M2 は書式を揃えた版（読解テスト未実施） |
| Opus だけが読む | D_NL | 77 | D_ascii_out の `EN`→`NL`。Sonnet・Haiku には伝わらない（D_ascii_out での結果） |

L_merge：
```
MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF:=cond;@:=external_ref;amb->no_guess,ask_1_short_q
```

要点：
- 読み手のモデルが小さいほど、記号や数式風の定義を英単語に開く必要がある。そのぶんトークンが増える。
- MiL 形式の節約は控えめ。同じ内容の英文（104）より 15 トークン（約14%）少ない程度。
- 詳しい数値と各モデルの読みは [results.md](results.md)、経緯は [background.md](background.md)。

## L_merge に残っている問題

1. **`IF:=cond` の向きが曖昧。** Haiku が「IF の代わりに cond を使う」と逆に読むことがあり、Opus も曖昧だと指摘した。→ `IF=condition` にする案（L2_ifeq、未検証）。
2. **確認の質問を何語で書くか。** 自然言語は最後の手段なのに、質問は自然言語で書くしかない（Sonnet・Haiku が指摘）。`(NL_ok)` で解消するが +10 トークン（M_scoped）。
3. **「推測しない」と「質問は1つ」の衝突。** 曖昧な点が複数あると、残りは推測するしかない（Opus が指摘）。
4. **「誰の文脈か」。** 文脈から復元できるものを省くと、読み手がその文脈を持たないとき意味が失われる（Opus がほぼ毎回指摘）。
5. **`:` と `:=` の混在。** `style_priority:` だけ `:` になっている（Opus が指摘）。
6. **未定義の運用事項**（Opus が指摘）：コード・ファイルパス・識別子まで圧縮してよいか、出力言語、途中で質問できないサブエージェントでの扱い、トークン最少と記号優先がぶつかったときの優先。

## 次の作業（優先順）

1. **L2_ifeq の読解テスト。** `IF=condition`、`@=external_ref` に変えた版で、測定済み（87、L より −2）。3モデルに読ませ、Haiku が `IF` を逆向きに読まなくなるかを確かめる。全員に伝われば本命を L2_ifeq に切り替える。
2. **行動テスト。** これまでは「意味を説明させる」テストだけだった。L_merge（比較用に N_prose も）を指示として渡し、普通の質問と曖昧な質問を投げて次を確かめる。
   - 出力が実際に短くなるか（出力テキストを count_tokens で測れる）
   - 曖昧なときに、短い質問を1つだけ返すか
   - サブエージェントでやる場合は、プロンプト冒頭に「Follow these rules for your reply: <L_merge>」と置き、続けて質問を書く。システムプロンプトとして渡す厳密なテストには API 直接呼び出しが必要（こちらは有料）。
3. **繰り返し試行。** 読解テストはすべて各モデル1回ずつ。特に「削除」と「推測しない」の緊張関係は、Opus が K で指摘し J・L・M・N で指摘しないなど揺れている。気になる版は3回以上読ませて、指摘が出る割合で比べる。
4. **M2_fixed の読解テスト（任意）。** 測定済み（99、M と同じ）。`:` と `:=` の混在の指摘が消えるかを確かめる。

## 作業環境と手順

### トークン測定

- `count_tokens.py` に全候補の文字列が入っている。引数で版名を渡すと、その版だけ測れる。
- **API キーはユーザーが自分で設定して実行する。** Claude はキーを扱わない。Claude のシェルでは `ANTHROPIC_API_KEY` は未設定。
- count_tokens の呼び出しは無料。数えるのは claude-opus-5-5 のトークナイザ。Sonnet・Haiku で同じ値になるかは確かめていない。

```powershell
cd D:\claude_code\MiL_expression
$env:ANTHROPIC_API_KEY = "ここにキー"; & "D:\Users\usor\miniconda3\envs\myenv311\python.exe" count_tokens.py L2_ifeq M2_fixed D_NL
```

### 読解テスト

[reading_test_prompt.md](reading_test_prompt.md) にプロンプトと判定の観点がある。Agent ツールで `model` を opus / sonnet / haiku にして、候補1つ × モデル1つずつ起動する。

### その他

- Python は `D:\Users\usor\miniconda3\envs\myenv311\python.exe` をフルパスで実行する（activate 不要）。
- このフォルダは git 管理していない。

## ファイル一覧

| ファイル | 内容 |
|---|---|
| HANDOFF.md | この引継ぎ資料 |
| results.md | 全候補のトークン数、読解テストの結果、モデルごとの傾向 |
| background.md | 元の MiL の意味、圧縮手法の整理、S式、システムカードの「読めない推論」、記号の話 |
| reading_test_prompt.md | 読解テストのプロンプトと判定の観点 |
| count_tokens.py | トークン測定スクリプト（全候補を収録） |
