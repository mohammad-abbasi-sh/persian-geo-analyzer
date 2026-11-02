"""Real tests for persian-geo-analyzer (stdlib unittest, no deps)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fa_geo import (  # noqa: E402
    analyze_blocks,
    analyze_text,
    extract_blocks,
    normalize_fa,
    score_text,
    suggest_fixes,
)


class TestNormalizeFa(unittest.TestCase):
    def test_arabic_chars(self):
        self.assertEqual(normalize_fa("مي‌خواهم كتاب"), "میخواهم کتاب")

    def test_persian_digits(self):
        self.assertEqual(normalize_fa("۱۴۰۳"), "1403")

    def test_zwnj_removed(self):
        self.assertEqual(normalize_fa("می‌شود"), "میشود")


class TestAnswerBlockQuality(unittest.TestCase):
    def test_persian_definition_yani(self):
        r = score_text("سئو یعنی بهینه‌سازی سایت برای موتورهای جستجو تا رتبه بهتری بگیرند.")
        self.assertGreaterEqual(r["breakdown"]["answer_block_quality"], 15)

    def test_persian_definition_gofteh_mishavad(self):
        r = score_text("به این روش گفته میشود که برندها با محتوا مخاطب جذب می‌کنند.")
        self.assertGreaterEqual(r["breakdown"]["answer_block_quality"], 15)

    def test_persian_definition_ebarate_ast_az(self):
        r = score_text("بازاریابی محتوا عبارت است از تولید محتوای ارزشمند برای جذب مشتری.")
        self.assertGreaterEqual(r["breakdown"]["answer_block_quality"], 15)

    def test_persian_question_heading(self):
        r = score_text("سئو فرایندی زمان‌بر است که نیاز به صبر و استراتژی دقیق دارد.", heading="سئو چیست؟")
        self.assertGreaterEqual(r["breakdown"]["answer_block_quality"], 10)

    def test_persian_early_answer(self):
        r = score_text("طبق آمار رسمی، ۷۳٪ کاربران فقط صفحه اول گوگل را می‌بینند و این عدد مهم است.")
        self.assertGreaterEqual(r["breakdown"]["answer_block_quality"], 25)

    def test_english_still_works(self):
        r = score_text("SEO is the process of optimizing a website. According to research, 73% of users never scroll.")
        self.assertGreaterEqual(r["breakdown"]["answer_block_quality"], 25)


class TestStatisticalDensity(unittest.TestCase):
    def test_persian_percent_and_money(self):
        r = score_text("فروش ۴۵٪ رشد کرد و به ۲ میلیارد تومان رسید در سال ۱۴۰۳ طبق آمار رسمی کشور.")
        self.assertGreaterEqual(r["breakdown"]["statistical_density"], 9)

    def test_shamsi_year(self):
        r = score_text("این روند از سال ۱۴۰۱ آغاز شد و تا ۱۴۰۳ ادامه داشت با رشد پایدار.")
        self.assertGreaterEqual(r["breakdown"]["statistical_density"], 2)


class TestStructure(unittest.TestCase):
    def test_list_markers(self):
        r = score_text("اول محتوا بنویسید. دوم لینک‌سازی کنید. در نهایت نتایج را بسنجید و گزارش دهید.")
        self.assertGreaterEqual(r["breakdown"]["structural_readability"], 4)

    def test_pronoun_density_penalty(self):
        clean = "سئو فرایندی تخصصی است. متخصص سئو استراتژی تدوین می‌کند. استراتژی شامل محتوا و لینک است."
        messy = "او این کار را کرد. او آن را دوست داشت. آنها این را دیدند و او خوشحال شد."
        self.assertGreater(
            score_text(clean)["breakdown"]["self_containment"],
            score_text(messy)["breakdown"]["self_containment"],
        )


class TestBlockExtraction(unittest.TestCase):
    def test_dl_qa_block(self):
        html = """<html><body><h2>سوالات متداول</h2>
        <dl><dt>سئو چیست؟</dt><dd>سئو یعنی بهینه‌سازی وب‌سایت برای موتورهای جستجو تا رتبه بهتری در نتایج کسب کند و ترافیک ارگانیک بیشتری جذب نماید.</dd></dl>
        </body></html>"""
        blocks = extract_blocks(html)
        self.assertEqual(len(blocks), 1)
        self.assertIn("سئو چیست", blocks[0]["content"])
        self.assertEqual(blocks[0]["content"].count("سئو یعنی"), 1)  # no dd double-count

    def test_script_skipped(self):
        html = "<html><body><script>var x = 1;</script><p>این یک پاراگراف واقعی با بیش از پنج کلمه است برای تست.</p></body></html>"
        blocks = extract_blocks(html)
        self.assertTrue(all("var x" not in b["content"] for b in blocks))


class TestFixes(unittest.TestCase):
    def test_weak_text_gets_persian_fixes(self):
        r = analyze_text("این متن خیلی کوتاه است.")
        self.assertTrue(r["fixes"])
        self.assertTrue(all(isinstance(f, str) for f in r["fixes"]))

    def test_strong_text_few_fixes(self):
        text = (
            "سئو یعنی بهینه‌سازی وب‌سایت برای موتورهای جستجو. طبق تحقیقات ما در سال ۱۴۰۳، "
            "۷۳٪ کاربران فقط صفحه اول گوگل را می‌بینند و این آمار رسمی نشان می‌دهد که سئو حیاتی است. "
            "اول: تحقیق کلمه کلیدی انجام دهید. دوم: محتوای ارزشمند تولید کنید. در نهایت نتایج را بسنجید. "
            "برای مثال، فروش یکی از مشتریان ما ۴۵٪ رشد کرد و به ۲ میلیارد تومان رسید."
        )
        r = analyze_text(text, heading="سئو چیست؟")
        self.assertGreaterEqual(r["total_score"], 50)
        self.assertIn(r["grade"], ("A", "B", "C"))


class TestAnalyzeBlocks(unittest.TestCase):
    def test_report_shape(self):
        blocks = [
            {"heading": "سئو چیست؟", "content": "سئو یعنی بهینه‌سازی سایت برای موتورهای جستجو و رتبه گرفتن." * 8},
            {"heading": "مقدمه", "content": "کوتاه."},
        ]
        rep = analyze_blocks(blocks)
        self.assertEqual(rep["total_blocks"], 2)
        self.assertIn("average_score", rep)
        self.assertEqual(len(rep["top_blocks"]), 2)


if __name__ == "__main__":
    unittest.main()
