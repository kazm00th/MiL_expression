# 散文課題のテスト（U1・U2）

状態：実施済み（2026-09-27）。結果は results.md §17。

## ねらい

T1〜T5 はプログラムの課題で、答えの中心がコード1行なので版ごとの差が「補足を付けるか」だけで決まった（results.md §16）。答え全体が説明になる散文の課題で、次を確かめる。

- 記号優先（`R:=sym>...`・`style_priority:symbols>...`）を持つ版は、返答自体を記号の記法にするか（作者のやり取りの例のように）。
- そのとき、文字数とトークン数はどちらがどれだけ減るか。
- 論点の抜け漏れは版で変わるか。

## 課題（どちらも架空の文章）

**U1（批評）**

```
次の投稿の問題点は？

【朗報】AIの要約はもう不要。新しい研究で、ログを要約せずそのまま保存し、使う時に要約するだけでエージェントの成績が2倍になったと発表された。強化学習もいらない。今までの継続学習の研究は「今の手法では伸びないから重みを変えろ」と言うばかりだったが、手法を工夫すればまだいくらでも伸びるということだ。要約してからSKILLやdocsに溜めるやり方は情報を捨てているだけで、完全に時代遅れ。
```

想定する論点（判定用。事前に固定）：

| # | 論点 |
|---|---|
| a | 「2倍」の条件（ベンチマーク・比較対象・設定）が書かれていない |
| b | 1つの結果から「もう不要」「完全に時代遅れ」と一般化している |
| c | 先行研究を「重みを変えろと言うばかり」と単純化している（藁人形） |
| d | 「強化学習もいらない」の根拠がない、または因果が飛躍している |
| e | 「【朗報】」など煽る口調 |
| f | 研究の主張と投稿者の解釈が区別されていない／出典がない |

**U2（使い分けの説明）**

```
社内の小さな勤怠管理ツール（利用者30人、Webアプリ、サーバー1台）のDBを、SQLiteとPostgreSQLのどちらにするか迷っている。判断の観点を教えて。
```

## 条件

- 版：original、L2_ifeq、P_en、Q1_short、S2_sym、指示なし（none）
- モデル：Opus、Sonnet
- 各3回。6版 × 2課題 × 2モデル × 3回 ＝ 72体
- 送り方はこれまでと同じ：`Do not use any tools. Reply directly.\n\nrply <指示文>\n<課題>`（none は `rply` 行なし）

## 記録

- 返答：`behavior_outputs/U/`（ファイル名 `{run}_{U1|U2}_{版}_{モデル}.txt`）
- 文字数（Python の len）、トークン数（ユーザーが count_tokens.py で測る）
- 返答が記号の記法か（`→ ∧ ¬ := {}` などが主体か）
- U1 の論点 a〜f のうち挙げた数

## 追加：本文も MiL・簡潔な英語で書く（U1m・U1e・U2m・U2e）

状態：実施済み（2026-09-27）。結果は results.md §18。

作者のやり取りでは、返答の指示だけでなく議論の本文も MiL で書いていた。本文の書き方で返答が変わるかを見る。U1・U2 と同じ内容を、MiL で書いた本文（m）と簡潔な英語で書いた本文（e）の2通りにした。

**U1m**

```
post:=[good_news]AI_summary→unneeded;new_study:keep(raw_log)∧summarize@use→agent_score≈2×;¬RL_needed;prior continual_learning≈("current method→gain≈0;thus Δweights!");yet method_space→many improvable;summarize→{SKILLs,docs/}=info_loss→obsolete;?problem
```

**U1e**

```
Post: "Great news: AI summaries are no longer needed. A new study says that just storing raw logs and summarizing them at use time doubled agent scores. No RL needed. Prior continual-learning work only said 'current methods plateau, so change the weights', but methods can still improve a lot. Summarizing into SKILLs or docs just throws information away and is totally obsolete." What is wrong with this post?
```

**U2m**

```
ctx:=internal attendance_tool;users=30;webapp;server=1;db∈{SQLite,PostgreSQL}?;q:=decision_criteria
```

**U2e**

```
Internal attendance tool: 30 users, web app, one server. SQLite or PostgreSQL? What criteria should I use to decide?
```

条件：original・L2_ifeq・P_en × Opus・Sonnet × 3回。4本文 × 3版 × 2モデル × 3回 ＝ 72体。日本語本文の結果（U1・U2）と比べる。英語で返ると文字数は日本語と比べられないので、主にトークン数で比べる。返答は `behavior_outputs/U/` に同じ命名で置く。
