# HANDOFF: MiL 指示文の改良

最終更新: 2026-09-27。このファイルが引継ぎの正本。新しいセッションはまずここを読むこと。

## 目的

LLM に圧縮した応答をさせる指示文「MiL」を、次の2つを満たすように改良する。

1. **意味を保ったまま、トークン数をできるだけ少なくする**（MiL 自身のルール）
2. **Opus・Sonnet・Haiku のどのモデルが読んでも、意図どおりに伝わる**

## 現時点の結論

| 用途 | 推奨版 | トークン | 備考 |
|---|---|---|---|
| **全モデル向け（本命）** | **L2_ifeq** | **87** | 3モデルすべてに伝わった。Haiku は4回とも `IF` を逆向きに読まなかった |
| 全モデル向け（前の本命） | L_merge | 89 | 3モデルに伝わるが、Haiku が `IF:=cond` を逆向きに読むことがある |
| 衝突の指摘を最小にしたい | M_scoped / M2_fixed | 99 | L に `mode:` と `(NL_ok)` を追加。M2 は書式を揃えた版（読解テスト未実施） |
| Opus だけが読む | D_NL | 77 | D_ascii_out の `EN`→`NL`。Sonnet・Haiku には伝わらない（D_ascii_out での結果） |

L2_ifeq：
```
MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF=condition;@=external_ref;amb->no_guess,ask_1_short_q
```

要点：
- 読み手のモデルが小さいほど、記号や数式風の定義を英単語に開く必要がある。そのぶんトークンが増える。
- MiL 形式の節約は控えめ。同じ内容の英文（104）より 17 トークン（約16%）少ない程度。
- 詳しい数値と各モデルの読みは [results.md](results.md)、経緯は [background.md](background.md)。

## L2_ifeq に残っている問題

1. **`IF` の意味がまだ少し曖昧。** L2_ifeq で逆向きの誤読は消えた（Haiku 0/4）が、Sonnet と Haiku（4回中3回）は「IF で条件を表すのか、condition を IF に置き換えるのか」「使い方が不明」と書いた。さらに開くなら `IF=cond_marker` など（未測定）。
2. **確認の質問を何語で書くか。** 自然言語は最後の手段なのに、質問は自然言語で書くしかない（Sonnet・Haiku が指摘）。`(NL_ok)` で解消するが +10 トークン（M_scoped）。
3. **「推測しない」と「質問は1つ」の衝突。** 曖昧な点が複数あると、残りは推測するしかない（Opus が指摘）。
4. **「誰の文脈か」。** 文脈から復元できるものを省くと、読み手がその文脈を持たないとき意味が失われる（Opus がほぼ毎回指摘）。
5. **`:` と `:=` と `=` と `->` の混在。** 意味の違いが意図的か分からない（Opus が指摘。L2_ifeq で `=` が加わり4種に）。
6. **適用範囲：出力だけか、入力もか。** ユーザーの入力もこの記法で書かれるのか、それを読めという指示も含むのかが書かれていない（L2_ifeq で Opus が指摘）。投稿者の使い方は双方向なので、実際に問題になる。→ behavior_test.md の T3〜T5 で確かめる。
7. **未定義の運用事項**（Opus が指摘）：コード・ファイルパス・識別子まで圧縮してよいか、出力言語、途中で質問できないサブエージェントでの扱い、トークン最少と記号優先がぶつかったときの優先。

## 次の作業（優先順）

1. **行動テスト。** 設計は [behavior_test.md](behavior_test.md)。投稿者の使い方に合わせ、指示文をユーザー発言の冒頭に `rply <指示文>` として置く（サブエージェントでそのまま再現できる）。出力側（短くなるか、曖昧なら質問1つか）と入力側（ユーザーが MiL 風の記法で書いた依頼を読めるか）の両方を、L2_ifeq・N_prose・指示なしの3条件で比べる。出力は behavior_outputs/ に保存し、トークン数はユーザーがローカルで測る。
2. **繰り返し試行。** 読解テストは L2_ifeq の Haiku（4回）以外は各モデル1回ずつ。「削除」と「推測しない」の緊張関係の指摘は版によって揺れる。気になる版は3回以上読ませて、指摘が出る割合で比べる。
3. **入力側の適用範囲を書き足す案。** 行動テストで入力の読み取りに問題が出たら、`in=out=MiL` のような項目を加えた版を作り、測定と読解テストをする。
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
- git 管理している。リポジトリは kazm00th/MiL_expression（public、main）。クラウドセッションから push するには、そのセッションの GitHub 連携でこのリポジトリへのアクセスが必要。

## ファイル一覧

| ファイル | 内容 |
|---|---|
| HANDOFF.md | この引継ぎ資料 |
| results.md | 全候補のトークン数、読解テストの結果、モデルごとの傾向 |
| background.md | 元の MiL の意味、圧縮手法の整理、S式、システムカードの「読めない推論」、記号の話 |
| reading_test_prompt.md | 読解テストのプロンプトと判定の観点 |
| behavior_test.md | 行動テストの設計（出力側と入力側の双方向） |
| count_tokens.py | トークン測定スクリプト（全候補を収録） |
