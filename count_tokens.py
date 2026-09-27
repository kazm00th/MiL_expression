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
