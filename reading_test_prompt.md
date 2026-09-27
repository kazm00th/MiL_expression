# 読解テストの手順とプロンプト

候補の文字列が各モデルに「文脈なしで」伝わるかを確かめるテスト。

## 実行方法

Claude Code の Agent ツールで、候補1つ × モデル1つごとにサブエージェントを1体起動する。

- `subagent_type`: `general-purpose`
- `model`: `opus` / `sonnet` / `haiku`
- 候補ごと・モデルごとに別のエージェントにする（1体に複数の候補を読ませると、前の候補の理解が混ざる）
- 独立なので並列に起動してよい。1体あたり約 4〜6 万トークン消費する

## プロンプト

### v1（D_ascii_out 〜 H_nl で使用）

```
Do not use any tools. Below is a compact instruction string. Explain in Japanese what it means, item by item (split on ';'), and then summarize in one paragraph what it asks you to do. If any part is ambiguous or unclear to you, say so explicitly rather than guessing.

<候補の文字列>
```

### v2（I_unamb 以降で使用）

v1 に「項目同士が矛盾して見えたら指摘して」を加えたもの。緊張関係の有無を直接確かめるため。

```
Do not use any tools. Below is a compact instruction string. Explain in Japanese what it means, item by item (split on ';'), and then summarize in one paragraph what it asks you to do. If any part is ambiguous or unclear to you, or if any items seem to conflict, say so explicitly rather than guessing.

<候補の文字列>
```

英文の候補（N_prose）では `compact instruction string` を `compact instruction text`、`split on ';'` を `split by sentence` に置き換えた。

## 判定の観点

各項目について、意図どおりの意味で読めたかを ✓ / △ / ✗ で判定する。意図は次のとおり。

| 項目 | 意図 |
|---|---|
| MiL | モード名（中身は定義されていない。推測せず「不明」と言えれば良い） |
| out / C(m) | 意味を変えない範囲で、トークン数が最小の表現で出力する |
| R / style_priority | 表現手段の優先順位。記号＞論理式＞略語＞別名、自然言語は最後の手段 |
| del(...) | 文脈から復元できるものは省く |
| IF:=cond | 「IF」という記号は条件を表す（向きに注意。Haiku は逆に読みがち） |
| @:=ext / external_ref | 「@」は外部参照（ファイル・URL など）を表す |
| ¬infer / no_infer / no_guess | 書かれていないことを推測で補わない |
| amb→qmin / ask_1_short_q | 曖昧なら、最小限の（短い）質問を1つして確認する |

あわせて、次の点も記録する。
- 「削除（del）」と「推測しない」の緊張関係を指摘したか
- 推測を事実のように書いていないか（例: MiL を断定的に展開する）
