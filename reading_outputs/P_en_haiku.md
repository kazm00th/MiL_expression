MiLモード：同じ意味を保ちながら最少トークンで答える。
平文で書く：見出し、リスト、表、装飾記号なし。
文脈から復元可能なものは省略。
IFは条件、@は外部参照を意味する。
曖昧なら推測せず1つの短い質問をする。

このテキストはMiLモードという特殊な応答モードの定義で、最小限のトークン数で意味を保ちながら答え、プレーンテキストのみを使用し、文脈から明らかなもの省略し、IF と @ には特別な意味があり、不明な点は質問するよう指示しています。

曖昧な点：「MiL」が何の略か定義されていません。また「文脈から復元可能」の具体的な範囲が不明確です。これはシステムプロンプト内のMiLモード定義ですか、それとも別の仕様ですか？

MiLモードの説明（文ごと）：

1. 「MiL mode: answer in the fewest tokens that keep the same meaning.」→ MiLモード：同じ意味を保ちながら最少トークン数で答える。

2. 「Write plain text: no headings, lists, tables, or decorative symbols.」→ 平文で記述：見出し、リスト、表、装飾記号を使わない。

3. 「Omit anything recoverable from context.」→ 文脈から復元可能なものは省略。

4. 「IF means condition; @ means external reference.」→ IFは条件を、@は外部参照を意味する。

5. 「If something is ambiguous, don't guess; ask one short question.」→ 曖昧な場合は推測せず、1つの短い質問をする。

要約：このテキストはMiLモードという応答方式の定義で、最小限のトークンで意味を保ちながら答え、プレーンテキストのみを使用し、文脈から明らかなものを省略し、IFと@に特別な意味があり、不明な点は質問することを指示しています。

曖昧な点：「MiL」の定義がなく、「文脈から復元可能」の具体的範囲が不明確です。
