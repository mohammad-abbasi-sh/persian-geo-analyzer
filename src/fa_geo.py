"""Persian GEO analyzer — AI-citability scoring for Persian (Farsi) content.

Stdlib only, no dependencies, no network calls for scoring. Given Persian
(or bilingual Persian/English) text, :func:`score_text` returns a 0-100
citability score with a per-category breakdown, a grade, and actionable
fix suggestions in Persian.

Research-backed rubric (5 categories, 100 points):
- answer_block_quality  (30): definition patterns, early answer, ؟ headings,
  clear sentences, quotable claims — Persian-first, English also recognized
- self_containment      (25): optimal length, pronoun density, named entities
- structural_readability(20): sentence length, list markers, numbering, breaks
- statistical_density   (15): ٪/%, money (تومان/ریال/دلار/$), numbers+units,
  Shamsi (13xx/14xx) and Gregorian years, named sources
- uniqueness_signals    (10): original research, examples, tool mentions
"""

import re
import unicodedata
from html.parser import HTMLParser
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Persian text normalization (for matching; original text kept for display)
# ---------------------------------------------------------------------------

_AR2FA = str.maketrans({"ي": "ی", "ك": "ک", "ة": "ه", "ؤ": "و", "إ": "ا", "أ": "ا"})
_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_fa(text):
    """Normalize Persian text for keyword/regex matching.

    NFKC, Arabic ي/ك/ة -> Persian ی/ک/ه, Persian/Arabic-Indic digits -> ASCII,
    ZWNJ/ZWJ removed (می‌شود and میشود match the same way), whitespace
    collapsed, stripped. Case is preserved (Persian has none; Latin kept).
    """
    if not isinstance(text, str):
        text = str(text)
    t = unicodedata.normalize("NFKC", text)
    t = t.translate(_AR2FA).translate(_FA_DIGITS)
    t = t.replace("‌", "").replace("‍", "")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


# ---------------------------------------------------------------------------
# Patterns (run against normalized text)
# ---------------------------------------------------------------------------

# Definition patterns: English + Persian mirrors. Persian is SOV with
# «است»/«یعنی» copulas.
DEFINITION_PATTERNS = [
    r"\b\w+\s+is\s+(?:a|an|the)\s",
    r"\b\w+\s+refers?\s+to\s",
    r"\b\w+\s+means?\s",
    r"\b\w+\s+(?:can be |are )?defined\s+as\s",
    r"\bin\s+(?:simple|other)\s+(?:terms|words)\s*,",
    r"\S+\s+یعنی\s",            # «سئو یعنی بهینه‌سازی…»
    r"گفته\s+میشود",            # «به … گفته میشود» (ZWNJ removed by normalize)
    r"عبارت\s+است\s+از",        # «… عبارت است از …»
    r"به\s+معن[یی]\s",          # «به معنای / به معنی …»
    r"\bتعریف\b.{0,40}[:：]",   # «تعریف سئو: …»
]

# Early-answer signals in the first 60 words.
EARLY_PATTERNS = [
    r"\b(?:is|are|was|were|means?|refers?)\b",
    r"\d+%",
    r"\$[\d,]+",
    r"\d+\s+(?:million|billion|thousand)",
    r"\b(?:است|هست|هستند|میباشد|میباشند)\b",
    r"\d+[٪%]",                                        # ٪ U+066A or %
    r"\d+\s+(?:میلیون|میلیارد|هزار|تومان|ریال|دلار|یورو)",
]

# Quotable-claim / evidential markers.
CLAIM_PATTERNS_EN = (
    r"(?:according to|research shows|studies? (?:show|indicate|suggest|found)"
    r"|data (?:shows|indicates|suggests))"
)
CLAIM_PATTERNS_FA = r"(?:طبق|بر\s+اساس|تحقیقات\s+نشان\s+میدهد|پژوهش\s+نشان\s+میدهد|آمار\s+رسمی)"

# Third-person pronouns only (self-containment: fewer = better).
# NOTE: demonstrative determiners (این/آن/چنین/چنان/همان) and reflexives
# (خود/خویش/خودش) are NOT penalized — they anchor nouns and are good Persian.
# Only anaphoric او/وی/ایشان/آنها/اینها risk unresolved reference.
FA_PRONOUNS = r"\b(?:او|وی|ایشان|آنها|اینها)\b"
EN_PRONOUNS = (
    r"\b(?:it|they|them|their|this|that|these|those|he|she|his|her)\b"
)

# List markers.
LIST_MARKERS = (
    r"(?:اول|دوم|سوم|چهارم|نخست|در\s+نهایت|علاوه\s+بر\s+این|همچنین|از\s+سویی|"
    r"first|second|third|finally|additionally|moreover|furthermore)"
)

# Original-research markers.
RESEARCH_MARKERS = (
    r"(?:تحقیقات\s+ما|بررسی\s+ما|داده‌های\s+ما|یافته‌های\s+ما|نشان\s+دادیم|"
    r"our (?:research|study|data|analysis|survey|findings)|we (?:found|discovered|analyzed|surveyed|measured))"
)
EXAMPLE_MARKERS = (
    r"(?:برای\s+مثال|به\s+عنوان\s+مثال|مثلا|مطالعه\s+موردی|در\s+عمل|"
    r"case study|for example|for instance|in practice|real-world|hands-on)"
)

# Money and statistics.
MONEY_PATTERNS = [
    r"[\d,]+\s*(?:تومان|ریال|دلار|یورو)",
    r"\d+\s*(?:میلیون|میلیارد|هزار)\s*(?:تومان|ریال|دلار|یورو)",
    r"\$[\d,]+(?:\.\d+)?",
]
NUMBER_UNIT_PATTERN = (
    r"\b\d+(?:,\d{3})*(?:\.\d+)?\s+"
    r"(?:کاربر|مشتری|سایت|شرکت|کسب‌وکار|کسبوکار|نفر|درصد|برابر|بازدید|صفحه"
    r"|users|customers|pages|sites|companies|businesses|people|percent|times|x\b)"
)
YEAR_PATTERN = r"\b(?:1[34]\d{2}|20[12]\d)\b"  # Shamsi 13xx/14xx + Gregorian
SOURCE_PATTERNS = [
    r"(?:طبق|بر\s+اساس|به\s+گفته‌ی?|به\s+نقل\s+از)\s+\S+",
    r"(?:دانشگاه\s+(?:تهران|شریف|امیرکبیر|علم\s+و\s+صنعت)|مرکز\s+آمار|بانک\s+مرکزی)",
    r"(?:Gartner|Forrester|McKinsey|Harvard|Stanford|MIT|Google|Microsoft|OpenAI|Anthropic)",
]

CATEGORY_MAX = {
    "answer_block_quality": 30,
    "self_containment": 25,
    "structural_readability": 20,
    "statistical_density": 15,
    "uniqueness_signals": 10,
}


def _grade(total):
    if total >= 80:
        return "A", "Highly Citable", "بسیار استنادپذیر"
    if total >= 65:
        return "B", "Good Citability", "استنادپذیری خوب"
    if total >= 50:
        return "C", "Moderate Citability", "استنادپذیری متوسط"
    if total >= 35:
        return "D", "Low Citability", "استنادپذیری پایین"
    return "F", "Poor Citability", "استنادپذیری ضعیف"


def score_text(text, heading=None):
    """Score a single Persian passage for AI citability (0-100).

    Returns dict with total_score, grade, English + Persian labels,
    per-category breakdown, word_count and a 30-word preview.
    """
    nq = normalize_fa(text)
    words = nq.split()
    word_count = len(words)

    scores = {k: 0 for k in CATEGORY_MAX}

    # === 1. Answer Block Quality (30) ===
    abq = 0
    for pattern in DEFINITION_PATTERNS:  # definition patterns (+15, once)
        if re.search(pattern, nq, re.IGNORECASE):
            abq += 15
            break
    first_60 = " ".join(words[:60])  # answer appears early (+15)
    if any(re.search(p, first_60, re.IGNORECASE) for p in EARLY_PATTERNS):
        abq += 15
    if heading and (heading.endswith("?") or heading.endswith("؟")):  # ؟ U+06F7
        abq += 10
    sentences = re.split(r"[.!?؟؛]+", nq)  # short, clear sentences (+10)
    clear = sum(1 for s in sentences if 5 <= len(s.split()) <= 25)
    if sentences:
        abq += int(clear / len(sentences) * 10)
    if re.search(CLAIM_PATTERNS_EN, nq, re.IGNORECASE) or re.search(
        CLAIM_PATTERNS_FA, nq
    ):
        abq += 10
    scores["answer_block_quality"] = min(abq, 30)

    # === 2. Self-Containment (25) ===
    sc = 0
    if 134 <= word_count <= 167:
        sc += 10
    elif 100 <= word_count <= 200:
        sc += 7
    elif 80 <= word_count <= 250:
        sc += 4
    elif word_count < 30 or word_count > 400:
        sc += 0
    else:
        sc += 2
    pronouns = len(re.findall(FA_PRONOUNS, nq)) + len(
        re.findall(EN_PRONOUNS, nq, re.IGNORECASE)
    )
    if word_count > 0:
        ratio = pronouns / word_count
        if ratio < 0.02:
            sc += 8
        elif ratio < 0.04:
            sc += 5
        elif ratio < 0.06:
            sc += 3
    # specificity signals: «quoted» terms + Latin proper nouns + figures
    quoted = len(re.findall(r"[«»\"]([^«»\"]{2,60})[«»\"]", text))
    latin_proper = len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text))
    if quoted + latin_proper >= 3:
        sc += 7
    elif quoted + latin_proper >= 1:
        sc += 4
    scores["self_containment"] = min(sc, 25)
    diagnostics = {
        "pronoun_ratio": (pronouns / word_count) if word_count else 0.0,
        "specificity_signals": quoted + latin_proper,
    }

    # === 3. Structural Readability (20) ===
    sr = 0
    if sentences:
        avg_len = word_count / len(sentences)
        if 10 <= avg_len <= 20:
            sr += 8
        elif 8 <= avg_len <= 25:
            sr += 5
        else:
            sr += 2
    if re.search(LIST_MARKERS, nq, re.IGNORECASE):
        sr += 4
    if re.search(r"(?:\d+[\.\)]\s|\b(?:قدم|مرحله|نکته|گام|step|tip)\s*\d+)", nq, re.IGNORECASE):
        sr += 4
    if "\n" in text:
        sr += 4
    scores["structural_readability"] = min(sr, 20)

    # === 4. Statistical Density (15) ===
    sd = 0
    sd += min(len(re.findall(r"\d+(?:\.\d+)?[٪%]", nq)) * 3, 6)
    money = sum(len(re.findall(p, nq)) for p in MONEY_PATTERNS)
    sd += min(money * 3, 5)
    sd += min(len(re.findall(NUMBER_UNIT_PATTERN, nq, re.IGNORECASE)) * 2, 4)
    if re.search(YEAR_PATTERN, nq):
        sd += 2
    for pattern in SOURCE_PATTERNS:
        if re.search(pattern, nq):
            sd += 2
    scores["statistical_density"] = min(sd, 15)

    # === 5. Uniqueness Signals (10) ===
    us = 0
    if re.search(RESEARCH_MARKERS, nq, re.IGNORECASE):
        us += 5
    if re.search(EXAMPLE_MARKERS, nq, re.IGNORECASE):
        us += 3
    if re.search(r"(?:با\s+استفاده\s+از|using|with|via)\s+[A-Z][a-z]+", text):
        us += 2
    scores["uniqueness_signals"] = min(us, 10)

    total = sum(scores.values())
    grade, label_en, label_fa = _grade(total)
    return {
        "heading": heading,
        "word_count": word_count,
        "total_score": total,
        "grade": grade,
        "label_en": label_en,
        "label_fa": label_fa,
        "breakdown": scores,
        "diagnostics": diagnostics,
        "preview": " ".join(text.split()[:30]) + ("..." if word_count > 30 else ""),
    }

# ---------------------------------------------------------------------------
# HTML block extraction (stdlib html.parser — no bs4 needed)
# ---------------------------------------------------------------------------

SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form"}
BLOCK_TAGS = {"h1", "h2", "h3", "h4", "p", "ul", "ol", "table", "dl", "dd"}


class _BlockExtractor(HTMLParser):
    """Collect content blocks: headings split sections; dl/dd kept as Q&A."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self._heading = "مقدمه"
        self._paras = []
        self._buf = []
        self._tag = None
        self._skip_depth = 0
        self._in_dl = 0  # inside <dl>: dt+dd accumulate into ONE Q&A block

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "dl":
            self._flush_buf()
            self._in_dl += 1
            self._tag = "dl"
            self._buf = []
            return
        if self._in_dl and tag in ("dt", "dd"):
            self._buf.append(" ")  # keep accumulating into the dl block
            return
        if tag in BLOCK_TAGS:
            self._flush_buf()
            self._tag = tag
            self._buf = []

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "dl" and self._in_dl:
            self._in_dl -= 1
            self._flush_buf()  # whole Q&A as one block
            self._tag = None
            return
        if self._in_dl and tag in ("dt", "dd"):
            return  # don't flush pieces separately
        if tag in BLOCK_TAGS and self._tag == tag:
            self._flush_buf()
            self._tag = None

    def handle_data(self, data):
        if self._skip_depth or not self._tag:
            return
        self._buf.append(data)

    def _flush_buf(self):
        text = " ".join("".join(self._buf).split())
        self._buf = []
        if not text or len(text.split()) < 5:
            return
        if self._tag and self._tag.startswith("h"):
            self._close_section()
            self._heading = text
        else:
            self._paras.append(text)

    def _close_section(self):
        combined = " ".join(self._paras)
        if len(combined.split()) >= 20:
            self.blocks.append({"heading": self._heading, "content": combined})
        self._paras = []

    def result(self):
        self._flush_buf()
        self._close_section()
        return self.blocks


def extract_blocks(html):
    """Split an HTML document into scored content blocks (heading + content)."""
    ex = _BlockExtractor()
    ex.feed(html)
    return ex.result()


def fetch_html(url, timeout=30):
    req = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; persian-geo-analyzer/1.0)"},
    )
    with urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


# ---------------------------------------------------------------------------
# Fix suggestions (Persian, actionable)
# ---------------------------------------------------------------------------

def suggest_fixes(result):
    """Persian fix suggestions for weak categories (<60% of max)."""
    b = result["breakdown"]
    fixes = []
    if b["answer_block_quality"] < 18:
        fixes.append(
            "یک جمله‌ی تعریفی در ابتدای پاراگراف اضافه کنید "
            "(«… یعنی …»، «… عبارت است از …»). تیتر را سؤالی کنید (؟)."
        )
    if b["self_containment"] < 15:
        d = result.get("diagnostics", {})
        wc = result.get("word_count", 0)
        if wc and not 80 <= wc <= 250:
            wc_fa = str(wc).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            fixes.append(
                f"طول بلوک را به ۱۳۰ تا ۱۷۰ کلمه برسانید (الان {wc_fa} کلمه است)."
            )
        if d.get("pronoun_ratio", 0) >= 0.02:
            fixes.append(
                "ضمیرهای سوم‌شخص (او/وی/ایشان) را کم کنید و به‌جای آن‌ها نام کامل را تکرار کنید."
            )
        if not d.get("specificity_signals"):
            fixes.append("نام خاص، نقل‌قول یا عدد دقیق اضافه کنید تا متن خاص‌تر شود.")
    if b["structural_readability"] < 12:
        fixes.append(
            "از لیست (اول، دوم، …)، قدم‌های شماره‌دار و پاراگراف‌های کوتاه استفاده کنید."
        )
    if b["statistical_density"] < 9:
        fixes.append(
            "آمار اضافه کنید: درصد (٪)، مبلغ (تومان)، سال (۱۴۰۳) و منبع («طبق …»)."
        )
    if b["uniqueness_signals"] < 6:
        fixes.append(
            "یک مثال واقعی، مطالعه‌ی موردی یا یافته‌ی اختصاصی («بررسی ما نشان داد …») اضافه کنید."
        )
    return fixes


def analyze_text(text, heading=None):
    result = score_text(text, heading)
    result["fixes"] = suggest_fixes(result)
    return result


def analyze_blocks(blocks, top_k=5):
    scored = []
    for bl in blocks:
        r = score_text(bl["content"], bl.get("heading"))
        r["fixes"] = suggest_fixes(r)
        scored.append(r)
    scored.sort(key=lambda r: r["total_score"], reverse=True)
    avg = sum(r["total_score"] for r in scored) / len(scored) if scored else 0
    grades = {}
    for r in scored:
        grades[r["grade"]] = grades.get(r["grade"], 0) + 1
    return {
        "total_blocks": len(scored),
        "average_score": round(avg, 1),
        "grade_distribution": grades,
        "top_blocks": scored[:top_k],
        "all_blocks": scored,
    }


def analyze_url(url):
    html = fetch_html(url)
    blocks = extract_blocks(html)
    report = analyze_blocks(blocks)
    report["url"] = url
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_report(result, show_fixes=True):
    print(f"نمره: {result['total_score']}/100  —  درجه {result['grade']} ({result['label_fa']})")
    print(f"تعداد کلمات: {result['word_count']}")
    for key, val in result["breakdown"].items():
        pct = int(100 * val / CATEGORY_MAX[key])
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        print(f"  {key:24s} {val:3d}/{CATEGORY_MAX[key]:3d}  {bar}")
    if show_fixes and result.get("fixes"):
        print("\nپیشنهادهای بهبود:")
        for f in result["fixes"]:
            print(f"  • {f}")


def main(argv=None):
    import argparse
    import json as _json

    ap = argparse.ArgumentParser(description="Persian GEO analyzer — AI-citability scoring for Persian content")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="page URL to fetch and analyze")
    src.add_argument("--text", help="raw Persian text to analyze")
    src.add_argument("--file", help="HTML or text file to analyze")
    ap.add_argument("--json", action="store_true", help="output JSON")
    ap.add_argument("--top", type=int, default=5, help="top blocks to show")
    args = ap.parse_args(argv)

    if args.url:
        report = analyze_url(args.url)
    else:
        raw = args.text if args.text else open(args.file, encoding="utf-8").read()
        if "<" in raw and ">" in raw:
            report = analyze_blocks(extract_blocks(raw), top_k=args.top)
        else:
            report = analyze_text(raw)

    if args.json:
        print(_json.dumps(report, ensure_ascii=False, indent=2, default=str))
    elif "total_blocks" in report:
        print(f"بلوک‌ها: {report['total_blocks']}  —  میانگین نمره: {report['average_score']}")
        for r in report["top_blocks"]:
            print("\n" + "=" * 60)
            print(f"تیتر: {r['heading']}")
            _print_report(r)
    else:
        _print_report(report)


if __name__ == "__main__":
    main()
