# persian-geo-analyzer

**Is your Persian content AI-readable?** A Persian-first GEO
(Generative Engine Optimization) analyzer: scores Persian (Farsi) content
0–100 for AI citability and returns actionable fix suggestions in Persian.
Stdlib-only Python — zero dependencies.

> فارسی: [README-fa.md](README-fa.md)

## Why

Persian businesses are losing traffic to AI answers (ChatGPT, Claude,
Perplexity), and every GEO tool is English-only — even the best
open-source citability scorer cannot score a Persian page (see
[geo-seo-claude#80](https://github.com/zubair-trabzada/geo-seo-claude/issues/80)).
This fills that gap.

## Install

```bash
git clone https://github.com/mohammad-abbasi-sh/persian-geo-analyzer
cd persian-geo-analyzer
# no dependencies — Python 3 only
```

## Usage

```bash
python3 src/fa_geo.py --text "سئو یعنی بهینه‌سازی…"
python3 src/fa_geo.py --url "https://example.com/article"
python3 src/fa_geo.py --file page.html --json
```

## Scoring (100 points, 5 categories)

| Category | Max | What earns points (Persian-first) |
|---|---|---|
| answer_block_quality | 30 | definitions («یعنی/عبارت است از»), ؟ headings, early answers, «طبق تحقیقات» |
| self_containment | 25 | 130–170 words, low pronoun density, named entities |
| structural_readability | 20 | lists (اول/دوم/…), numbered steps, short paragraphs |
| statistical_density | 15 | ٪, تومان/ریال, میلیون/میلیارد, Shamsi years (۱۴۰۳), sources |
| uniqueness_signals | 10 | «بررسی ما نشان داد», real examples, case studies |

Bilingual Persian/English content is supported.

## MCP server & Claude Skill

- MCP (stdio): `python3 src/mcp_server.py` → tool `analyze_fa_geo`
- Claude Skill: [SKILL.md](SKILL.md) · Cursor rules: `.cursor/rules/`

## Tests

```bash
python3 -m unittest discover -s tests   # 18 tests
```

## License

MIT
