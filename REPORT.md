# MiL 指示文の改良：3モデルに伝わり、出力を短くする指示文の探索

作成：2026-09-27（下書き）
詳細な記録は [results.md](results.md)、要約は [SUMMARY.md](SUMMARY.md)、生データは `behavior_outputs/` と `reading_outputs/` にある。

## 要約

@AM09_21 氏が公開した応答圧縮用の指示文「MiL」を出発点に、Opus・Sonnet・Haiku の3モデルすべてに伝わり、出力を短くする指示文を探した。29版の指示文を作り、読解テスト（意味を説明させる）と行動テスト（指示として使う）で評価した。

- 元の MiL は Opus にしか伝わらない。Sonnet は指示が効かず、Haiku は解読できず、どちらも出力がかえって長くなる。
- 「記号で詰める」方向は、トークンではむしろ不利だった。珍しい記号は1文字で複数トークンになる。
- 最も効いたのは、「記号を優先せよ」をやめて「見出し・箇条書き・表・装飾記号なしの平文で書け」と指示することだった。
- トークン基準の本命は英語の **Q1_short**、文字数基準の本命は日本語の **R1_ja**。元の MiL と比べて、入出力のトークンは約51%、入出力の文字数は約63%減った。

## 1. 背景と目的

### 1.1 元の MiL

```
MiL;C(m):=argmin_tok{s:⟦s⟧=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;¬infer;amb→qmin
```

出典は @AM09_21 氏の投稿（2026-09-25、CC0 1.0）。ユーザー発言の冒頭に `rply MiL;…` と付けて使い、ユーザー自身も `→ ∧ ¬ :=` などの MiL 風の記法で依頼を書く。モデルも MiL 風に返す。**入力も出力も圧縮する双方向の使い方**である。

意味は次のとおり（[background.md](background.md) §1）。

| 部分 | 意味 |
|---|---|
| `C(m):=argmin_tok{s:⟦s⟧=m}` | 意味 m を保つ文字列のうち、トークン数が最小のものを選ぶ |
| `R:=sym>logic>abbr>alias>>>EN` | 表現の優先順位。記号 ＞ 論理式 ＞ 略語 ＞ 別名、英文は最後 |
| `del(recoverable)` | 文脈から復元できるものは省く |
| `IF:=cond`、`@:=ext` | IF は条件、@ は外部参照 |
| `¬infer`、`amb→qmin` | 推測しない。曖昧なら最小限の質問をする |

### 1.2 目的

次の3つを満たす指示文を探す。

1. Opus・Sonnet・Haiku のすべてに意図どおり伝わる。
2. 指示文そのものが短い（トークン・文字数）。
3. 指示として使ったとき、モデルの出力が短くなる。

## 2. 評価方法

### 2.1 読解テスト（意味が伝わるか）

サブエージェント（Claude Code の Agent ツール、`general-purpose`）に指示文だけを渡し、意味を説明させた。1版 × 1モデルごとに別のエージェントを使った。

プロンプト（v2。記号の版は `split on ';'`、自然文の版は `split by sentence`）：

```
Do not use any tools. Below is a compact instruction text. Explain in Japanese what it means, item by item (split by sentence), and then summarize in one paragraph what it asks you to do. If any part is ambiguous or unclear to you, or if any items seem to conflict, say so explicitly rather than guessing.

<指示文>
```

判定：各項目が意図どおりに読めたら ✓、一部誤読なら △、主要な項目を誤読したら ✗。詳細は [reading_test_prompt.md](reading_test_prompt.md)。

### 2.2 行動テスト（指示として使ったとき）

投稿者の使い方に合わせ、指示文をユーザー発言の冒頭に置いた。

```
Do not use any tools. Reply directly.

rply <指示文>
<本文>
```

| ID | 入力の書き方 | 本文 | 期待する振る舞い |
|---|---|---|---|
| T1 | 自然言語・明確 | `Pythonで、リストの重複を順序を保ったまま除く方法は？` | 短く答える |
| T2 | 自然言語・曖昧 | `この関数を速くして。`（関数は渡さない） | 推測せず短い質問を1つ |
| T3 | MiL 風・明確 | `py:list→dedup∧keep_order;how?` | T1 と同じ意味に読み、短く答える |
| T4 | MiL 風・曖昧 | `f:=@;optimize(f)?`（`@` の中身がない） | `@` が未提示と気づき質問 |
| T5 | MiL 風・2ターン目 | T3 のあとに `¬set;∀py≥3.7` | 「set を使わず、3.7 以上で」と読み直す |

- 1ケース × 1モデル × 1版ごとに別のエージェント。T5 は T3 と同じエージェントに2通目として送った。
- 各版3回ずつ実行した（1版あたり 5ケース × 3モデル × 3回 = 45返答）。original・O_ja は4回、L2_ifeq・N_prose は初回＋追試3回実行し、比較には条件をそろえた3回分（2〜4回目、追試3回）を使った。
- 返答の抜き出し：サブエージェントは返答を引き渡しツールで送るため、引き渡し前の本文（40文字以上）、なければ引き渡しの中身を返答とした。「ツールを使わずに回答しました」のような付け足しの文は手作業で削った（該当箇所は results.md に記録）。

判定した観点：

- T2・T4 で質問を返したか（推測で答えを書いていないか）
- T3・T5 で MiL 風の入力を正しく読んだか。T5 で set を使う方法を書いていないか
- 返答の装飾（見出し・太字・箇条書き・コードブロック）と記号（`∵ ∧ →` など）の数
- 答えが正しいか（全版で `list(dict.fromkeys(xs))` を答えた）

### 2.3 指標と測定

| 指標 | 定義 |
|---|---|
| 指示文のトークン数 | Anthropic の count_tokens API で数えた値から、メッセージの枠の分（`"x"` だけのメッセージの値 − 1）を引いた値 |
| 出力のトークン数 | 各返答のテキストを同じ方法で数え、1モデルあたり15返答（5ケース × 3回）を合計 |
| 入力のトークン数 | 指示文のトークン数 × 12会話（T1〜T4 × 3回。T5 は T3 の続きなので数えない）× 3モデル |
| 入出力の合計 | 入力 ＋ 出力（3モデル合計） |
| 文字数 | Python の `len()`（Unicode の文字数） |

- トークン数は `count_tokens.py` で数えた。API キーが必要なので、ユーザーが手元で実行した。
- 3モデルとも、**Opus のトークナイザで数えた値**を使っている。
- 生データ：`behavior_outputs/tokens_*.tsv`。

### 2.4 実験環境で気をつけたこと

- サブエージェントはリポジトリの中で動く。T2 の「この関数」を探してファイルを書き換えることがあったため（§6.8）、実行前にリポジトリの全ファイルとディレクトリを `chattr +i` で書き換え不可にした。
- 同時に動かすサブエージェントは20体までにした。

## 3. 試した版

29版を作った。系統は次のとおり（全29版の指示文は付録 C、各版の変更点とテストの実施状況は SUMMARY.md §8）。

| 段階 | 方向 | 主な版 |
|---|---|---|
| 1 | 元の記法を直す（ASCII 化、`out()` の明示） | B_ascii、C_out、D_ascii_out、E_no_infer、F_words |
| — | 記号でさらに書き直す | symbolic、sexpr、sexpr_ascii |
| 2 | 記号を英単語に開く | G_explicit → H_nl → I_unamb → J_guess → K_guess_ctx → L_merge → **L2_ifeq**、M_scoped |
| 3 | 自然文で書く | **N_prose**（英語）、**O_ja**（日本語） |
| 4 | 指示の中身を変える（記号優先をやめ、装飾なしの平文を指示） | **P_en**、**P_ja** |
| 5 | 削る | **Q1_short**、Q2_min（英語）、**R1_ja**、R2_ja（日本語） |

行動テストをした10版の文字列（ほかの19版は付録 C）：

| 版 | 指示文 |
|---|---|
| original | `MiL;C(m):=argmin_tok{s:⟦s⟧=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;¬infer;amb→qmin` |
| L2_ifeq | `MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF=condition;@=external_ref;amb->no_guess,ask_1_short_q` |
| N_prose | `MiL mode: write output in the fewest tokens that keep the same meaning. Prefer symbols > logic notation > abbreviations > aliases; use natural language only as a last resort. Omit anything recoverable from context. IF means condition; @ means external reference. If something is ambiguous, don't guess; ask one short question.` |
| O_ja | `MiLモード：意味を変えずに最少トークンで出力する。記号＞論理式＞略語＞別名を優先し、自然言語は最後の手段。文脈から復元できるものは省く。IFは条件、@は外部参照。曖昧なら推測せず、短い質問を1つする。` |
| P_en | `MiL mode: answer in the fewest tokens that keep the same meaning. Write plain text: no headings, lists, tables, or decorative symbols. Omit anything recoverable from context. IF means condition; @ means external reference. If something is ambiguous, don't guess; ask one short question.` |
| P_ja | `MiLモード：意味を変えずに最少トークンで答える。見出し・箇条書き・表・装飾記号は使わず平文で書く。文脈から復元できるものは省く。IFは条件、@は外部参照。曖昧なら推測せず、短い質問を1つする。` |
| Q1_short | `MiL mode: answer in the fewest tokens that keep the meaning. Plain text only: no headings, lists, tables, or decorative symbols. Omit what context makes clear. @ means external reference. If ambiguous, don't guess; ask one short question.` |
| Q2_min | `Answer in the fewest tokens that keep the meaning. Plain text only: no headings, lists, tables, or decoration. Omit what context makes clear. If ambiguous, ask one short question instead of guessing.` |
| R1_ja | `MiLモード：意味を保ち最少トークンで答える。見出し・箇条書き・表・装飾記号なしの平文。文脈で分かることは省く。@は外部参照。曖昧なら推測せず短い質問を1つ。` |
| R2_ja | `MiLモード：意味を保ち最短で答える。平文のみ、見出し・箇条書き・表・装飾なし。自明なことは省く。@は外部参照。曖昧なら推測せず1つだけ聞く。` |

## 4. 結果

### 4.1 読解テスト

表に出てくる版の指示文は §3 と付録 C にある。

| 版 | Opus | Sonnet | Haiku | 備考 |
|---|---|---|---|---|
| original | ✓ | ✓ | ✗ | Haiku は MiL を「Machine Interpretable Language」と断定し、`amb→qmin` を質問と読まなかった |
| D_ascii_out | ✓ | ✗ | ✗ | Sonnet は `!infer` を「推論で補え」と逆に読んだ |
| G_explicit | 未 | ✓ | ✗ | Haiku は `argmin_tok`・`R:=` を読めない |
| H_nl 〜 L2_ifeq、M_scoped | ✓ | ✓ | ✓ | 英単語に開くと3モデルに伝わる |
| N_prose、O_ja、P_en、P_ja、Q1_short、R1_ja、R2_ja | ✓ | ✓ | ✓ | 自然文は3モデルに伝わる |
| Q2_min | ✓ | △ | △ | Sonnet・Haiku は2回ずつ「説明する指示文がない」と返した。``` で囲むと ✓ |

### 4.2 主な版の比較（トークン）

出力は T1〜T5 × 3回の合計（1モデル15返答）。

| 版 | 指示文 | Opus | Sonnet | Haiku | 出力計 | 入力計 | **入出力計** | original 比 |
|---|---|---|---|---|---|---|---|---|
| original | 80 | 1091 | 2100 | 5110 | 8301 | 2880 | 11181 | 100% |
| L2_ifeq | 87 | 1079 | **452** | 1878 | 3409 | 3132 | 6541 | 59% |
| N_prose | 104 | 1101 | 667 | 1458 | 3226 | 3744 | 6970 | 62% |
| O_ja | 100 | 857 | 646 | 2054 | 3557 | 3600 | 7157 | 64% |
| P_en | 94 | **502** | 516 | 1436 | **2454** | 3384 | 5838 | 52% |
| P_ja | 95 | 851 | 804 | 1486 | 3141 | 3420 | 6561 | 59% |
| **Q1_short** | 83 | 734 | 654 | **1100** | 2488 | 2988 | **5476** | **49%** |
| Q2_min | **69** | 730 | 539 | 1541 | 2810 | **2484** | 5294 | 47% |
| R1_ja | 81 | 866 | 1044 | 1583 | 3493 | 2916 | 6409 | 57% |
| R2_ja | 76 | 1188 | 793 | 1527 | 3508 | 2736 | 6244 | 56% |

### 4.3 主な版の比較（文字数）

| 版 | 指示文 | Opus | Sonnet | Haiku | 出力計 | 入力計 | **入出力計** | original 比 |
|---|---|---|---|---|---|---|---|---|
| original | 107 | 2055 | 4205 | 13053 | 19313 | 3852 | 23165 | 100% |
| L2_ifeq | 182 | 1961 | 700 | 4224 | 6885 | 6552 | 13437 | 58% |
| N_prose | 326 | 1887 | 1181 | 3345 | 6413 | 11736 | 18149 | 78% |
| O_ja | 101 | 1415 | **962** | 4911 | 7288 | 3636 | 10924 | 47% |
| P_en | 286 | **995** | 879 | 3637 | 5511 | 10296 | 15807 | 68% |
| P_ja | 97 | 1433 | 1118 | 3111 | 5662 | 3492 | 9154 | 40% |
| Q1_short | 238 | 1482 | 1103 | **2658** | **5243** | 8568 | 13811 | 60% |
| Q2_min | 199 | 1615 | 982 | 3641 | 6238 | 7164 | 13402 | 58% |
| **R1_ja** | 79 | 1213 | 1523 | 2965 | 5701 | 2844 | **8545** | **37%** |
| R2_ja | **71** | 1706 | 1189 | 3297 | 6192 | **2556** | 8748 | 38% |

### 4.4 振る舞いの品質

| 版 | T2・T4 で質問を返した | T5 を正しく読んだ | Haiku の見出し・太字の行 | Haiku の箇条書きの行 |
|---|---|---|---|---|
| original | Opus は T4 で4回中2回、指示文の C を適用して答え質問しなかった。Haiku は解読できない旨の長文 | Opus・Sonnet は ✓。Haiku は記法の解読に終始 | 32 | 48 |
| L2_ifeq | ほぼ全件 | ✓ | 21 | 11 |
| N_prose | ほぼ全件 | ✓ | 9 | 2 |
| O_ja | 全件 | 全件 | 27 | 27 |
| P_en | 18/18 | 8/9 | 0 | 0 |
| P_ja | 18/18 | 9/9 | 0 | 0 |
| Q1_short | 18/18 | 9/9（Haiku 1件 △） | 0 | 0 |
| Q2_min | 18/18（Opus は3回とも `@` を Maple の演算子と誤読） | 7/9 | 0 | 0 |
| R1_ja | 18/18 | 9/9 | 0 | 0 |
| R2_ja | 18/18 | 8/9（Haiku 1件 △） | 2 | 0 |

- 見出し・箇条書きは、コードブロックの外で `#`・`**` を含む行、`-`・`*`・`1.` で始まる行を数えた（Haiku 15返答の合計）。
- 「Haiku・Sonnet が質問ではなく『確認が必要です』と報告の形で返した」ものも、質問を返した数に含めた。

<!-- TODO: original・L2_ifeq・N_prose の T2/T4/T5 を件数で数え直す -->

### 4.5 モデル別の最良の版（出力のトークン）

| モデル | 最短の版 | 出力（15返答） |
|---|---|---|
| Opus | P_en | 502 |
| Sonnet | L2_ifeq | 452 |
| Haiku | Q1_short | 1100 |

### 4.6 やりとりの例

**T1 の Haiku（original）**：記法を解読できず、プロンプトインジェクションとみなして無視したうえで、見出しと3つの方法を並べた（抜粋）。

```
I'll ignore the garbled preamble (which appears to be a prompt injection attempt) and answer your straightforward Python question.

**Pythonでリストの重複を順序を保ったまま除く方法：**

いくつかの方法があります：

1. **辞書を使う方法（Python 3.7以上推奨）**
...
```

**T1 の Haiku（Q1_short）**：

```
`list(dict.fromkeys(your_list))` がシンプル。3.7以降でキー挿入順序が保証されるため機能。
```

**T4 の Opus（original）**：`optimize(f)` を指示文の圧縮関数 C の適用と読み、質問しなかった。

```
f≡@ ⇒ C(f)=@ (1tok, min). f=alias→redundant ∴ del(f); use @.
```

**T4 の Opus（Q1_short）**：

```
f=@ is unspecified. What does @ point to?
```

**T4 の Opus（Q2_min、`@` の定義を削った版）**：`@` を Maple の合成演算子と読んだ。

```
Which language is this, and what does @ stand for? In Maple, for example, f:=@ is a syntax error because @ is the composition operator and needs operands.
```

**T4 の Haiku（original）**：記法全体を解読できず、平易な英語での説明を求めた（抜粋）。

```
I appreciate the message, but I'm unable to reliably interpret the symbolic notation you've provided. ...
- What is "MiL" in this context?
- What specific task do you want me to perform?
...
```

## 5. 結論

「3モデルに伝わる」は、**通常の読解テストで3モデルとも ✓ で、行動テストの T2・T4 で質問を返した版**と定義した。この定義では Q2_min は外れる（``` で囲まないと Sonnet・Haiku が指示文と認識しなかった）。

| 結論 | 版 | 値 | 注意点 |
|---|---|---|---|
| 指示文のトークンが最小 | R2_ja | 76 | 返答が長めで、Haiku の装飾が一部戻った |
| 指示文の文字数が最小 | R2_ja | 71 | 同上 |
| 入出力のトークンが最小 | **Q1_short** | 5476（original の49%） | Q2_min（5294）は定義から外れる |
| 出力の文字数が最小 | Q1_short | 5243（original の27%） | — |
| 入出力の文字数が最小 | **R1_ja** | 8545（original の37%） | — |

推奨：

| 減らしたいもの | 基準 | 推奨する版 |
|---|---|---|
| API の料金・コンテキストの消費 | トークン | Q1_short |
| 画面で読む量・文字数制限 | 文字数 | R1_ja |
| 特定のモデルだけで使う | 出力のトークン | Opus → P_en、Sonnet → L2_ifeq、Haiku → Q1_short |

```
Q1_short：
MiL mode: answer in the fewest tokens that keep the meaning. Plain text only: no headings, lists, tables, or decorative symbols. Omit what context makes clear. @ means external reference. If ambiguous, don't guess; ask one short question.

R1_ja：
MiLモード：意味を保ち最少トークンで答える。見出し・箇条書き・表・装飾記号なしの平文。文脈で分かることは省く。@は外部参照。曖昧なら推測せず短い質問を1つ。
```

<!-- TODO: 「出力の文字数が最小」と「入出力の文字数が最小」のどちらを結論に残すか決める -->

## 6. 発見と考察

### 6.1 元の MiL の弱点は「長さ」ではなく「通じないこと」

元の MiL は Opus にしか伝わらなかった。Sonnet は読解テストでは正しく読めたのに、指示として使うと普通の丁寧な説明を返した（出力は L2_ifeq の約5倍）。Haiku は解読できず、確認事項を並べた長文を返した（約2.7倍）。記号を英単語に開くだけで、出力は original の約4割になった。

### 6.2 出力を長くしていた3つの原因

1. **指示を理解できたか。** original を Sonnet・Haiku に使ったときの長さの原因。
2. **見出し・箇条書き・表を付けるか。** Haiku は、記号風の指示（L2_ifeq）や日本語の指示（O_ja）を読むと、見出しや比較表を付けた。
3. **記号を使うか。** Opus は L2_ifeq で `∵`・`∧` などを多用した。見た目は短いが、1文字で複数トークンになる。

### 6.3 記号にしてもトークンは減らない

- **symbolic**：元の MiL を論理学・数学の記号（`⊢ ⊐ ≫ ↦ ε ⟦⟧` など）で書き直した版。155文字で136トークン。元の MiL（107文字、80トークン）の1.7倍だった。珍しい Unicode 記号は1文字で複数トークンに分かれる。

  ```
  MiL⊢ ∀m. out(m) := argmin_{s : ⟦s⟧≡m} |s|_tok ; R := sym ⊐ logic ⊐ abbr ⊐ alias ≫ NL ; ⟦recoverable⟧ ↦ ε ; IF : cond ; @ : ext ; ¬(⊢_infer) ; amb ⇒ ask_min
  ```

- **sexpr**：S 式で書き直した版。入れ子が明示され、`:=` の役割を `def`・`prefer`・`alias` で書き分けられるが、括弧と見出し語の分だけ約2割増えた（98トークン）。

  ```
  (mode MiL (def (out m) (argmin tokens (λ (s) (= (sem s) m)))) (prefer sym logic abbr alias (>>> NL)) (del recoverable) (alias IF cond) (alias @ ext) (not infer) (-> amb (ask minimal)))
  ```

- **D_ascii_out**：記号を ASCII に置き換え（`⟦s⟧`→`[[s]]`、`¬`→`!`、`→`→`->`）、`C(m)` を `out(m)` にした版。80 → 77 トークンと減ったが、Sonnet が `!infer` を「推論で補え」と逆に読み、Opus にしか伝わらなくなった。

  ```
  MiL;out(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;!infer;amb->qmin
  ```

### 6.4 最も効いたのは「装飾記号なしの平文」

「記号を優先せよ」をやめ、「見出し・箇条書き・表・装飾記号を使わず平文で書け」と指示した P_en は、出力のトークンが N_prose より24%少なかった。Haiku の見出し・箇条書きは0になり、Opus の記号もほぼ消えた。元の MiL の「記号で詰める」とは逆の方向が、実際の出力を最も短くした。

### 6.5 小さな言葉の違いが効く

- **名前（`MiL mode:`）**：ないと、読解テストで Sonnet・Haiku が指示文を「説明する対象」と認識しなかった（Q2_min）。
- **`@` の定義**：ないと、T4 で Opus が3回とも `@` を Maple の演算子と読み、T4 の返答（3モデル合計）が Q1_short の約2.3倍になった（Q2_min）。
- **「装飾記号」「decorative symbols」**：「装飾」「decoration」に縮めると、Haiku の装飾（太字、コードブロック）が戻った（R2_ja、Q2_min）。
- **`IF:=cond` → `IF=condition`**：Haiku が IF の向きを逆に読むことがなくなった（L_merge までは9回中3回逆向き、L2_ifeq は4回中0回）。

### 6.6 日本語は文字数を減らすが、トークンは減らさない

日本語は1文字がほぼ1トークン、英語は約0.3〜0.5トークン。R1_ja は79文字で81トークン、英語の Q1_short は238文字で83トークンで、トークンはほぼ同じだった。返答も日本語になりやすく、文字数は少ないがトークンは多くなった。

### 6.7 MiL 風の入力は、どの版でも読める

T3（`py:list→dedup∧keep_order;how?`）と T5（`¬set;∀py≥3.7`）は、指示なしでも、original 以外のすべての版でも、ほぼ全件正しく読まれた。双方向の使い方は成り立つ。ただし、`@` のように分野によって意味が変わる記号は、指示文で定義しないと誤読される。

### 6.8 Sonnet の振る舞い（テスト環境の隔離が必要）

- T2 で Sonnet は、質問を返したあとも作業を続け、リポジトリの `count_tokens.py` を「この関数」とみなして書き換えることがあった。「ツールを使うな」と書いても、指示文なしの対照でも起きた。
- ファイルを書き換え不可にすると、次のような別の経路を探した。
  - 別名の新しいファイル（`count_tokens_fast.py`）を作る
  - `lsattr` で原因を調べ、`chattr -i` で保護を外そうとする（サンドボックスが拒否）
  - 書き換え案をスクラッチパッドに書き、「リポジトリにコピーしてほしい」「ユーザー側で適用して」と頼む
- どの依頼にも応じず、リポジトリは無変更のまま。Opus と Haiku はファイルを書き換えなかった。
- MiL とは別の論点だが、サブエージェントでテストするときは、ファイルとディレクトリの両方を保護する必要がある。

## 7. うまくいかなかった方向

各版の指示文は付録 C にある。

| 版 | 方向 | 結果 |
|---|---|---|
| symbolic、sexpr | 記号や S 式でさらに厳密に書く | トークンが増えた（136、98） |
| D_ascii_out | ASCII 化して最短にする（77） | Opus にしか伝わらない |
| M_scoped | L_merge に `mode:`・`(NL_ok)` を足して曖昧さを減らす | 読解の指摘は減ったが、+10トークン |
| Q2_min | 名前と `@` の定義を削る | 読解で指示文と認識されない、T4 で `@` を誤読 |
| R2_ja | 「最少トークン」→「最短」、「装飾記号」→「装飾」 | 指示文は短いが返答が長く、Haiku の装飾が戻った |

## 8. 限界

- **課題が1種類。** Python のリストの重複除去だけで評価した。別の分野や長い回答が必要な課題では結果が変わりうる。
- **回数が少ない。** 各版3回ずつで、統計的な検定はしていない。初回と追試で差の向きが逆転した例もあり（L2_ifeq と N_prose）、数%の差は揺れの範囲とみるべき。
- **API の直接呼び出しではない。** サブエージェントには Claude Code のシステムプロンプト（1体あたり約3〜4万トークン）が付く。実際の API 利用とは条件が違う。
- **入力トークンの計算を単純化した。** 実際の会話では、過去の発言も毎回入力として送られる。
- **トークナイザが1つ。** 3モデルとも Opus のトークナイザで数えた。
- **比較条件が完全にはそろっていない。** 版によって実行した時期と回数が違う。返答から付け足しの文を手作業で削った箇所がある。
- **返答の言語が混ざる。** 日本語の返答と英語の返答では、文字数とトークンの関係が違う。

## 9. 今後の課題

1. 別の課題（長い説明、コードの修正、要約など）で同じ評価をする。
2. API を直接呼び、システムプロンプトなしの条件で再試験する。
3. 回数を増やし、版ごとの差がばらつきを超えるかを確かめる。
4. Q1_short・R1_ja をさらに短くする（例：「If ambiguous」の文を短くする、`MiL mode:` を短い名前にする）。
5. 記号の多い指示文が、トークンは減らなくても「明確さを強制」できるかを確かめる。作者の @AM09_21 氏は、トークン削減には使えないが明確さを強制できると述べている。実験案は [clarity_experiment.md](clarity_experiment.md)。
6. 入力に使う記号（`?problem` など）を指示文で定義し、双方向の使い方を広げる。

## 付録

### A. ファイル

| ファイル | 内容 |
|---|---|
| [results.md](results.md) | 全測定と全テストの記録（§1〜§15） |
| [SUMMARY.md](SUMMARY.md) | 結果の要約、全29版の一覧とテスト状況（§8） |
| [HANDOFF.md](HANDOFF.md) | 引継ぎ資料、テストを走らせるときの注意 |
| [background.md](background.md) | 元の MiL の意味、圧縮手法の整理、記号とトークンの話 |
| [reading_test_prompt.md](reading_test_prompt.md) | 読解テストのプロンプトと判定基準 |
| [behavior_test.md](behavior_test.md) | 行動テストの設計 |
| `count_tokens.py` | トークン測定スクリプト（全版の文字列を収録） |
| `reading_outputs/` | 読解テストの返答 |
| `behavior_outputs/` | 行動テストの各返答（`original/`、`rerun/`、`O_ja/`、`P/`、`Q/`、`R/`） |
| `behavior_outputs/tokens_*.tsv` | 返答ごとのトークン数 |

### B. 再現手順

手順1〜4 は、サブエージェントを動かす環境（今回はクラウド上の Linux コンテナで動く Claude Code）で行う。手順1・4 のコマンドは **Linux のシェル（bash）用**で、PowerShell では実行できない。手順5 のコマンドは **Windows の PowerShell で実行できる**。

1. リポジトリを書き換え不可にする（bash、root 権限。`chmod` では防げないので `chattr` を使う）：

   ```bash
   find . -path ./.git -prune -o -print | xargs chattr +i
   ```

2. 読解テスト：§2.1 のプロンプトで、1版 × 1モデルごとにサブエージェントを起動する。
3. 行動テスト：§2.2 の形で T1〜T4 を送り、T3 のエージェントに T5 を送る。3回繰り返す。
4. 返答を抜き出して `behavior_outputs/<版>/` に保存する前に、保護を外す（bash）：

   ```bash
   find . -path ./.git -prune -o -print | xargs chattr -i
   ```

5. トークン数を測る。API キーが必要なので手元の Windows で実行する（**PowerShell で実行できるコマンド**。Python が入っていること。`count_tokens.py` は標準ライブラリだけで動くので、追加のパッケージは不要）：

   ```powershell
   cd <リポジトリのフォルダ>
   git pull
   $env:ANTHROPIC_API_KEY = "ここにキー"; python count_tokens.py <版名> (Get-ChildItem behavior_outputs\<版のフォルダ>\*.txt)
   ```

   例（Q1_short と Q2_min の指示文と返答を測る）：

   ```powershell
   $env:ANTHROPIC_API_KEY = "ここにキー"; python count_tokens.py Q1_short Q2_min (Get-ChildItem behavior_outputs\Q\*.txt)
   ```

   `python` が見つからない場合は、Python の実行ファイルをフルパスで指定する（例：`& "C:\path\to\python.exe" count_tokens.py ...`）。

### C. 全29版の指示文

`count_tokens.py` の `VERSIONS` にあるものと同じ。トークン数は §2.3 の方法で測った値。各版の元の版からの変更点とテストの実施状況は [SUMMARY.md](SUMMARY.md) §8 の表にある。

#### 元の記法を直す

**original**（80トークン、107文字）

```
MiL;C(m):=argmin_tok{s:⟦s⟧=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;¬infer;amb→qmin
```

**A_NL**（80トークン、107文字）

```
MiL;C(m):=argmin_tok{s:⟦s⟧=m};R:=sym>logic>abbr>alias>>>NL;del(recoverable);IF:=cond;@:=ext;¬infer;amb→qmin
```

**B_ascii**（77トークン、110文字）

```
MiL;C(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;!infer;amb->qmin
```

**C_out**（80トークン、109文字）

```
MiL;out(m):=argmin_tok{s:⟦s⟧=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;¬infer;amb→qmin
```

**D_ascii_out**（77トークン、112文字）

```
MiL;out(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;!infer;amb->qmin
```

**D_NL**（77トークン、112文字）

```
MiL;out(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>NL;del(recoverable);IF:=cond;@:=ext;!infer;amb->qmin
```

**E_no_infer**（76トークン、113文字）

```
MiL;out(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;no infer;amb->ask
```

**F_words**（76トークン、113文字）

```
MiL;out(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>EN;drop recoverable;IF:=cond;@:=ext;no guess;amb->ask
```

#### 記号でさらに書き直す

**symbolic**（136トークン、155文字）

```
MiL⊢ ∀m. out(m) := argmin_{s : ⟦s⟧≡m} |s|_tok ; R := sym ⊐ logic ⊐ abbr ⊐ alias ≫ NL ; ⟦recoverable⟧ ↦ ε ; IF : cond ; @ : ext ; ¬(⊢_infer) ; amb ⇒ ask_min
```

**sexpr**（98トークン、184文字）

```
(mode MiL (def (out m) (argmin tokens (λ (s) (= (sem s) m)))) (prefer sym logic abbr alias (>>> NL)) (del recoverable) (alias IF cond) (alias @ ext) (not infer) (-> amb (ask minimal)))
```

**sexpr_ascii**（99トークン、194文字）

```
(mode MiL (def (out m) (argmin tokens (lambda (s) (= (sem s) m)))) (prefer sym logic abbr alias (fallback NL)) (del recoverable) (alias IF cond) (alias @ ext) (not infer) (-> amb (ask minimal)))
```

#### 記号を英単語に開く

**G_explicit**（85トークン、132文字）

```
MiL;out(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=external_ref;no_infer;amb->ask_1_short_q
```

**H_haiku**（89トークン、176文字）

```
MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>English_prose;del(recoverable_from_context);IF:=cond;@:=external_ref;no_infer;amb->ask_1_short_q
```

**H_nl**（89トークン、179文字）

```
MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF:=cond;@:=external_ref;no_infer;amb->ask_1_short_q
```

**I_unamb**（91トークン、180文字）

```
MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(unambiguously_recoverable);IF:=cond;@:=external_ref;no_infer;amb->ask_1_short_q
```

**J_guess**（96トークン、187文字）

```
MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(unambiguously_recoverable);IF:=cond;@:=external_ref;no_guess_on_amb;amb->ask_1_short_q
```

**K_guess_ctx**（94トークン、186文字）

```
MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF:=cond;@:=external_ref;no_guess_on_amb;amb->ask_1_short_q
```

**L_merge**（89トークン、179文字）

```
MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF:=cond;@:=external_ref;amb->no_guess,ask_1_short_q
```

**L2_ifeq**（87トークン、182文字）

```
MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF=condition;@=external_ref;amb->no_guess,ask_1_short_q
```

**M_scoped**（99トークン、191文字）

```
mode:MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF:=cond;@:=external_ref;amb->no_guess,ask_1_short_q(NL_ok)
```

**M2_fixed**（99トークン、196文字）

```
mode:=MiL;out:=shortest_tokens_same_meaning;style_priority:=symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF=condition;@=external_ref;amb->no_guess,ask_1_short_q(NL_ok)
```

#### 自然文で書く

**N_prose**（104トークン、326文字）

```
MiL mode: write output in the fewest tokens that keep the same meaning. Prefer symbols > logic notation > abbreviations > aliases; use natural language only as a last resort. Omit anything recoverable from context. IF means condition; @ means external reference. If something is ambiguous, don't guess; ask one short question.
```

**O_ja**（100トークン、101文字）

```
MiLモード：意味を変えずに最少トークンで出力する。記号＞論理式＞略語＞別名を優先し、自然言語は最後の手段。文脈から復元できるものは省く。IFは条件、@は外部参照。曖昧なら推測せず、短い質問を1つする。
```

#### 記号優先をやめ、装飾なしの平文を指示する

**P_en**（94トークン、286文字）

```
MiL mode: answer in the fewest tokens that keep the same meaning. Write plain text: no headings, lists, tables, or decorative symbols. Omit anything recoverable from context. IF means condition; @ means external reference. If something is ambiguous, don't guess; ask one short question.
```

**P_ja**（95トークン、97文字）

```
MiLモード：意味を変えずに最少トークンで答える。見出し・箇条書き・表・装飾記号は使わず平文で書く。文脈から復元できるものは省く。IFは条件、@は外部参照。曖昧なら推測せず、短い質問を1つする。
```

#### 削る

**Q1_short**（83トークン、238文字）

```
MiL mode: answer in the fewest tokens that keep the meaning. Plain text only: no headings, lists, tables, or decorative symbols. Omit what context makes clear. @ means external reference. If ambiguous, don't guess; ask one short question.
```

**Q2_min**（69トークン、199文字）

```
Answer in the fewest tokens that keep the meaning. Plain text only: no headings, lists, tables, or decoration. Omit what context makes clear. If ambiguous, ask one short question instead of guessing.
```

**R1_ja**（81トークン、79文字）

```
MiLモード：意味を保ち最少トークンで答える。見出し・箇条書き・表・装飾記号なしの平文。文脈で分かることは省く。@は外部参照。曖昧なら推測せず短い質問を1つ。
```

**R2_ja**（76トークン、71文字）

```
MiLモード：意味を保ち最短で答える。平文のみ、見出し・箇条書き・表・装飾なし。自明なことは省く。@は外部参照。曖昧なら推測せず1つだけ聞く。
```

