# Persian GEO Analyzer — Claude Skill

Score Persian (Farsi) content for **AI-search citability (GEO)** and get
actionable fixes in Persian. Stdlib-only Python, no dependencies.

## When to use

The user asks any of:
- «محتوام برای هوش مصنوعی خواناست؟» / "is my content AI-citable?"
- تحلیل سئوی محتوای فارسی، نمره‌ی GEO، بهبود استنادپذیری
- Review Persian content before publishing (blog, landing, FAQ)

## How

**Fastest (no install):** run the analyzer directly —
```bash
python3 src/fa_geo.py --text "متن فارسی…" 
python3 src/fa_geo.py --url "https://example.com/page"
python3 src/fa_geo.py --file page.html --json
```

**As an MCP tool** (Claude Code / Cursor): point the client at
`src/mcp_server.py` (stdio). Tool: `analyze_fa_geo` with `text` or `url`.

## Reading the score (0–100)

| Category | Max | What earns points (Persian-first) |
|---|---|---|
| answer_block_quality | 30 | تعریف با «یعنی/عبارت است از/گفته می‌شود»، جواب زودهنگام، تیتر «؟»، جملات کوتاه، «طبق تحقیقات…» |
| self_containment | 25 | طول ۱۳۰–۱۷۰ کلمه، ضمیر کم، نام‌های خاص |
| structural_readability | 20 | جملات ۱۰–۲۰ کلمه‌ای، لیست (اول/دوم/…)، شماره‌گذاری، پاراگراف‌بندی |
| statistical_density | 15 | ٪، تومان/ریال، میلیون/میلیارد، سال شمسی (۱۴۰۳)، منبع |
| uniqueness_signals | 10 | «بررسی ما نشان داد»، مثال واقعی، مطالعه‌ی موردی |

Grades: A ≥80, B ≥65, C ≥50, D ≥35, F <35. Every weak category
(<60% of its max) comes with a concrete Persian fix suggestion —
**apply the fixes, don't just report the score.**

## Rules

- Score the Persian as-is; never translate it to score it.
- Persian normalization (ي→ی، ك→ک، ارقام فارسی→انگلیسی، حذف نیم‌فاصله)
  is handled inside the tool — pass raw text.
- For a full page, prefer `--url`/`url` so FAQ blocks (`<dl>`) and
  headings are analyzed per-section; then fix the weakest blocks first.
- Bilingual Persian/English content is supported; English patterns
  (is a…, according to…, $…) also count.
