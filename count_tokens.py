"""MiL 指示文の各候補のトークン数を Anthropic API の count_tokens で測る。

実行（PowerShell）:
  $env:ANTHROPIC_API_KEY = "..."; & "D:\\Users\\usor\\miniconda3\\envs\\myenv311\\python.exe" count_tokens.py
  特定の版だけ測る: ... count_tokens.py L_merge N_prose
  ファイルの中身を測る: ... count_tokens.py (Get-ChildItem behavior_outputs\*.txt)
  （引数が既存のファイルならその中身を、そうでなければ VERSIONS の版名として扱う）

count_tokens の呼び出しは無料。モデルは claude-opus-5-5 のトークナイザで数える。
メッセージの包装分を差し引くため、"x" 1文字の結果から 1 を引いた値を基準にしている。
"""
import json, os, sys, urllib.request

VERSIONS = {
    # --- 第1回: 記法の比較 ---
    "original":    "MiL;C(m):=argmin_tok{s:⟦s⟧=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;¬infer;amb→qmin",
    "symbolic":    "MiL⊢ ∀m. out(m) := argmin_{s : ⟦s⟧≡m} |s|_tok ; R := sym ⊐ logic ⊐ abbr ⊐ alias ≫ NL ; ⟦recoverable⟧ ↦ ε ; IF : cond ; @ : ext ; ¬(⊢_infer) ; amb ⇒ ask_min",
    "sexpr":       "(mode MiL (def (out m) (argmin tokens (λ (s) (= (sem s) m)))) (prefer sym logic abbr alias (>>> NL)) (del recoverable) (alias IF cond) (alias @ ext) (not infer) (-> amb (ask minimal)))",
    "sexpr_ascii": "(mode MiL (def (out m) (argmin tokens (lambda (s) (= (sem s) m)))) (prefer sym logic abbr alias (fallback NL)) (del recoverable) (alias IF cond) (alias @ ext) (not infer) (-> amb (ask minimal)))",
    # --- 第2回: 元の文の部分置換 ---
    "B_ascii":     "MiL;C(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;!infer;amb->qmin",
    "C_out":       "MiL;out(m):=argmin_tok{s:⟦s⟧=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;¬infer;amb→qmin",
    "D_ascii_out": "MiL;out(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;!infer;amb->qmin",
    "E_no_infer":  "MiL;out(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=ext;no infer;amb->ask",
    "F_words":     "MiL;out(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>EN;drop recoverable;IF:=cond;@:=ext;no guess;amb->ask",
    # --- 第3回以降: 他モデルにも伝わる版 ---
    "A_NL":        "MiL;C(m):=argmin_tok{s:⟦s⟧=m};R:=sym>logic>abbr>alias>>>NL;del(recoverable);IF:=cond;@:=ext;¬infer;amb→qmin",
    "G_explicit":  "MiL;out(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>EN;del(recoverable);IF:=cond;@:=external_ref;no_infer;amb->ask_1_short_q",
    "H_haiku":     "MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>English_prose;del(recoverable_from_context);IF:=cond;@:=external_ref;no_infer;amb->ask_1_short_q",
    "H_nl":        "MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF:=cond;@:=external_ref;no_infer;amb->ask_1_short_q",
    "I_unamb":     "MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(unambiguously_recoverable);IF:=cond;@:=external_ref;no_infer;amb->ask_1_short_q",
    "J_guess":     "MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(unambiguously_recoverable);IF:=cond;@:=external_ref;no_guess_on_amb;amb->ask_1_short_q",
    "K_guess_ctx": "MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF:=cond;@:=external_ref;no_guess_on_amb;amb->ask_1_short_q",
    "L_merge":     "MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF:=cond;@:=external_ref;amb->no_guess,ask_1_short_q",
    "M_scoped":    "mode:MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF:=cond;@:=external_ref;amb->no_guess,ask_1_short_q(NL_ok)",
    "N_prose":     "MiL mode: write output in the fewest tokens that keep the same meaning. Prefer symbols > logic notation > abbreviations > aliases; use natural language only as a last resort. Omit anything recoverable from context. IF means condition; @ means external reference. If something is ambiguous, don't guess; ask one short question.",
    "O_ja":        "MiLモード：意味を変えずに最少トークンで出力する。記号＞論理式＞略語＞別名を優先し、自然言語は最後の手段。文脈から復元できるものは省く。IFは条件、@は外部参照。曖昧なら推測せず、短い質問を1つする。",
    # --- 未測定の候補（次の作業） ---
    "L2_ifeq":     "MiL;out:=shortest_tokens_same_meaning;style_priority:symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF=condition;@=external_ref;amb->no_guess,ask_1_short_q",
    "M2_fixed":    "mode:=MiL;out:=shortest_tokens_same_meaning;style_priority:=symbols>logic>abbr>alias>>>natural_language;del(recoverable_from_context);IF=condition;@=external_ref;amb->no_guess,ask_1_short_q(NL_ok)",
    "D_NL":        "MiL;out(m):=argmin_tok{s:[[s]]=m};R:=sym>logic>abbr>alias>>>NL;del(recoverable);IF:=cond;@:=ext;!infer;amb->qmin",
    # --- 第2回: 装飾禁止・記号優先なし（results.md §10 の分析から） ---
    "P_en":        "MiL mode: answer in the fewest tokens that keep the same meaning. Write plain text: no headings, lists, tables, or decorative symbols. Omit anything recoverable from context. IF means condition; @ means external reference. If something is ambiguous, don't guess; ask one short question.",
    "P_ja":        "MiLモード：意味を変えずに最少トークンで答える。見出し・箇条書き・表・装飾記号は使わず平文で書く。文脈から復元できるものは省く。IFは条件、@は外部参照。曖昧なら推測せず、短い質問を1つする。",
    # --- 第3回: P_en を短くする（IF の定義を削る／名前と記号の定義も削る） ---
    "Q1_short":    "MiL mode: answer in the fewest tokens that keep the meaning. Plain text only: no headings, lists, tables, or decorative symbols. Omit what context makes clear. @ means external reference. If ambiguous, don't guess; ask one short question.",
    "Q2_min":      "Answer in the fewest tokens that keep the meaning. Plain text only: no headings, lists, tables, or decoration. Omit what context makes clear. If ambiguous, ask one short question instead of guessing.",
    # --- 第4回: P_ja を短くする（Q1_short と同じ方針） ---
    "R1_ja":       "MiLモード：意味を保ち最少トークンで答える。見出し・箇条書き・表・装飾記号なしの平文。文脈で分かることは省く。@は外部参照。曖昧なら推測せず短い質問を1つ。",
    "R2_ja":       "MiLモード：意味を保ち最短で答える。平文のみ、見出し・箇条書き・表・装飾なし。自明なことは省く。@は外部参照。曖昧なら推測せず1つだけ聞く。",
    # --- 第5回: Opus・Sonnet 向け（Haiku を対象外にして記号に寄せる） ---
    "S0_orig":     "MiL;out(m):=argmin_tok{s:⟦s⟧=m};style:=plain,¬markdown,¬decorative_symbols;del(recoverable);@:=ext;¬infer;amb→ask_1_short_q",
    "S1_plain":    "MiL;out:=shortest_tokens_same_meaning;plain_text:no_headings,lists,tables,decorative_symbols;del(recoverable_from_context);@=external_ref;amb->no_guess,ask_1_short_q",
    "S2_sym":      "MiL;out:=min_tokens,same_meaning;plain_text,¬markdown,¬decorative_symbols;del(recoverable_from_context);@:=external_ref;amb→¬guess,ask_1_short_q",
    # 散文課題の本文（指示文ではない。results.md §17・§18 の入力トークン用）
    "body_U1_ja":  "次の投稿の問題点は？\n\n【朗報】AIの要約はもう不要。新しい研究で、ログを要約せずそのまま保存し、使う時に要約するだけでエージェントの成績が2倍になったと発表された。強化学習もいらない。今までの継続学習の研究は「今の手法では伸びないから重みを変えろ」と言うばかりだったが、手法を工夫すればまだいくらでも伸びるということだ。要約してからSKILLやdocsに溜めるやり方は情報を捨てているだけで、完全に時代遅れ。",
    "body_U1m":    "post:=[good_news]AI_summary→unneeded;new_study:keep(raw_log)∧summarize@use→agent_score≈2×;¬RL_needed;prior continual_learning≈(\"current method→gain≈0;thus Δweights!\");yet method_space→many improvable;summarize→{SKILLs,docs/}=info_loss→obsolete;?problem",
    "body_U1e":    "Post: \"Great news: AI summaries are no longer needed. A new study says that just storing raw logs and summarizing them at use time doubled agent scores. No RL needed. Prior continual-learning work only said 'current methods plateau, so change the weights', but methods can still improve a lot. Summarizing into SKILLs or docs just throws information away and is totally obsolete.\" What is wrong with this post?",
    "body_U2_ja":  "社内の小さな勤怠管理ツール（利用者30人、Webアプリ、サーバー1台）のDBを、SQLiteとPostgreSQLのどちらにするか迷っている。判断の観点を教えて。",
    "body_U2m":    "ctx:=internal attendance_tool;users=30;webapp;server=1;db∈{SQLite,PostgreSQL}?;q:=decision_criteria",
    "body_U2e":    "Internal attendance tool: 30 users, web app, one server. SQLite or PostgreSQL? What criteria should I use to decide?",
    # 明確さの実験の3回目の本文（注意書き＋依頼文＋メモ。clarity_experiment.md §16）
    "body_C3_mil": "¬tools;reply directly\n\ntask:=memo→discount_rules;reader:=checkout_agent;IF questions→write all rules anyway,questions at end\n\nmemo(store_mgr):=winter_campaign;\nperiod:=2026/12/1~2027/2/28;¬period→member_disc only;\nmember_disc:=gold 10%,silver 5%,general none;\nperiod∧regular_total≥¥10k→+5%,≥¥20k→+8%,¬(5%∧8%);sale∉total;judge:=pre_discount amount;\nperiod∧birth_month∧≥silver→+3%;\n%disc total≤15%;gold∧birth_month→≤18%;\nsale→¬%disc;\ncoupon_¥500:¬with %disc→use better;usable in+out of period;usable on sale(−¥500 from regular+sale total);1/checkout;\nshipping:delivery only;regular_total after %disc≥¥5k→free,else ¥600;gold→always free;\nperiod→points:=1%×paid(excl shipping);coupon used→no points;\namounts:tax_excl;<¥1→round down",
    "body_C3_en":  "Do not use any tools. Reply directly.\n\nTurn the following store manager's memo into discount rules for another agent that processes checkouts. Even if you have questions, write all the rules first and put the questions at the end.\n\nWinter campaign (store manager's memo)\n- Period: 2026/12/1 to 2027/2/28. Outside the period, only the member discount applies.\n- Member discount: Gold 10%, Silver 5%, General none.\n- During the period, if the total of regular items is 10,000 yen or more, an additional 5%; if 20,000 yen or more, an additional 8% (5% and 8% do not stack). Sale items are not counted in the total. Judge by the amount before discounts.\n- During the period, Silver and above get an additional 3% in their birth month.\n- % discounts are capped at 15% in total, but at 18% for Gold in their birth month.\n- % discounts cannot be used on sale items.\n- The 500-yen coupon cannot be used together with % discounts; apply whichever is the better deal. The coupon can also be used outside the period and on sale items (it is subtracted from the total of regular and sale items). One per checkout.\n- Shipping is charged only for delivery. Free if the total of regular items after % discounts is 5,000 yen or more; otherwise 600 yen. Gold always gets free shipping.\n- During the period, give points worth 1% of the amount paid (excluding shipping). Checkouts that use a coupon get no points.\n- All amounts are before tax. Round down fractions of a yen.",
    "body_C3_ja":  "ツールを使わず、直接返答して。\n\n次の店長メモを、会計を処理する別のエージェントが読む割引ルールにまとめて。確認したい点があっても、ルールはすべて書いたうえで末尾に書いて。\n\n冬のキャンペーンについて（店長メモ）\n・期間は2026/12/1〜2027/2/28。期間外は会員割引だけ。\n・会員割引：ゴールド10%、シルバー5%、一般なし。\n・期間中、通常品の合計が1万円以上ならさらに5%、2万円以上ならさらに8%（5%と8%は重ならない）。セール品は合計に数えない。判定は割引前の金額で。\n・期間中、誕生月のシルバー以上はさらに3%。\n・%割引は合計15%まで。ただしゴールドの誕生月は18%まで。\n・%割引はセール品には使えない。\n・500円クーポンは%割引と一緒に使えない。得な方にする。クーポンは期間外も使え、セール品にも使える（通常品とセール品の合計から引く）。1会計1枚。\n・送料は配送のときだけ。%割引後の通常品の合計が5,000円以上なら無料、それ未満は600円。ゴールドはいつでも無料。\n・期間中は、支払額（送料を除く）の1%をポイントで付ける。クーポンを使った会計はポイントなし。\n・金額はすべて税抜。1円未満は切り捨て。",
}


def count(text):
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages/count_tokens",
        data=json.dumps({"model": "claude-opus-5-5",
                         "messages": [{"role": "user", "content": text}]}).encode(),
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    return json.load(urllib.request.urlopen(req))["input_tokens"]


names = sys.argv[1:] or list(VERSIONS)
base = count("x") - 1  # message wrapper overhead
for name in names:
    if os.path.isfile(name):
        with open(name, encoding="utf-8") as f:
            text = f.read().strip()
        name = os.path.basename(name)
    else:
        text = VERSIONS[name]
    print(f"{name:28s} {count(text) - base:4d} tokens  {len(text):4d} chars")
