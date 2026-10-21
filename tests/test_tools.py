"""Observable regressions: Unicode damage, misleading metrics and cross-brand reads."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills' / 'hefdah' / 'scripts'
sys.path.insert(0, str(SCRIPTS))


class Tools(unittest.TestCase):
    def setUp(self):
        self.assertTrue((SCRIPTS / 'hefdah_core.py').exists(), 'Persian tools have not been implemented')
        self.core = importlib.import_module('hefdah_core')

    def test_normalization_preserves_meaning_and_protected_spans(self):
        source = 'مي‌خواهم 👩‍💻 https://example.com/علي كد AB12، ۱۲۵٬۰۰۰ تومان نیست.'
        result = self.core.normalize(source)
        self.assertEqual(result['text'], 'می‌خواهم 👩‍💻 https://example.com/علي کد AB12، ۱۲۵٬۰۰۰ تومان نیست.')
        self.assertEqual(self.core.normalize(result['text'])['changes'], [])

    def test_direction_controls_are_reported_without_deletion(self):
        result = self.core.normalize('کد\u202eABC')
        self.assertEqual(result['text'], 'کد\u202eABC')
        self.assertTrue(result['warnings'])

    def test_quantities_handle_real_locale_formats(self):
        for raw, expected in [('۱۲٫۵ هزار', 12500), ('12.5K', 12500), ('١٢٬٥٠٠', 12500), ('۳ میلیون', 3000000), ('۴۵٪', 45)]:
            with self.subTest(raw=raw):
                self.assertEqual(self.core.parse_quantity(raw), expected)

    def test_quantities_do_not_silently_repair_bad_data(self):
        for raw in ['1,2,3', '12,5', '-12', 'NaN', '۱۲ تومان', 'abc12', '', '1e9', '1.2.3']:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    self.core.parse_quantity(raw)

    def test_caption_understands_persian_tags_and_requests(self):
        report = self.core.lint_caption('این تجربه را ذخیره کن.\n#کسب_وکار #آموزش', 125)
        self.assertEqual(report['hashtags'], ['#کسب_وکار', '#آموزش'])
        self.assertEqual(report['asks'], ['save'])
        self.assertTrue(report['preview_is_approximate'])

    def test_caption_does_not_count_negated_request(self):
        self.assertEqual(self.core.lint_caption('این را ذخیره نکن.')['asks'], [])

    def test_style_is_advice_not_automatic_semantic_rewrite(self):
        source = 'در دنیای پرشتاب امروز، می‌خواهم این را بگویم.'
        result = self.core.inspect_style(source)
        self.assertEqual(result['text'], source)
        self.assertTrue(result['suggestions'])
        self.assertNotIn('human_score', result)

    def test_persian_hook_is_not_empty_and_has_no_viral_probability(self):
        result = self.core.review_hook('قبل از خرید لپ‌تاپ، این سه مورد را بررسی کن.')
        self.assertGreater(result['word_count'], 7)
        self.assertNotIn('viral_probability', result)
        self.assertIn('checks', result)

    def test_timing_expands_written_numbers_and_validates_rate(self):
        words = self.core.estimate_beats('۱۲۵۰۰۰ تومان', 120)['spoken_words']
        self.assertGreater(words, self.core.estimate_beats('قیمت مناسب', 120)['spoken_words'])
        with self.assertRaises(ValueError):
            self.core.estimate_beats('متن', 0)

    def test_swipe_keeps_followers_separate_from_baseline(self):
        rows = [{'account': '@a', 'views': '۱۲٫۵ هزار', 'median': '۲۵۰۰'}, {'account': '@b', 'views': '100K', 'followers': '1000'}]
        report = self.core.rank_swipe(rows)
        self.assertEqual(report['ranked'][0]['multiple'], 5)
        self.assertEqual(report['unranked'][0]['account'], '@b')
        self.assertIsNone(report['unranked'][0]['multiple'])

    def test_missing_and_zero_insights_are_distinct(self):
        result = self.core.audit_rows([{'id': '1', 'reach': '0', 'shares': '0'}, {'id': '2', 'reach': '100', 'shares': '0'}, {'id': '3', 'reach': '100'}])
        self.assertIsNone(result['posts'][0]['shares_per_reach'])
        self.assertEqual(result['posts'][1]['shares_per_reach'], 0)
        self.assertIsNone(result['posts'][2]['shares_per_reach'])

    def test_context_is_explicit_and_confined(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            root = Path(folder)
            self.core.create_context(root, 'brand-a')
            self.core.create_context(root, 'brand-b')
            (root / 'brand-a' / 'voice.md').write_text('لحن برند الف', encoding='utf-8')
            self.assertEqual(self.core.load_context(root, 'brand-a')['voice'], 'لحن برند الف')
            self.assertNotIn('لحن برند الف', self.core.load_context(root, 'brand-b')['voice'])
            for bad in ['../outside', '', 'CON', 'a/b', 'A:']:
                with self.subTest(bad=bad):
                    with self.assertRaises(ValueError):
                        self.core.load_context(root, bad)
            with self.assertRaises(FileExistsError):
                self.core.create_context(root, 'brand-a')

    def test_context_does_not_traverse_symlink(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            root = Path(folder)
            outside = root / 'outside'
            outside.mkdir()
            clients = root / 'clients'
            clients.mkdir()
            try:
                (clients / 'escape').symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('OS does not permit creating a test symlink')
            with self.assertRaises(ValueError):
                self.core.load_context(clients, 'escape')

    def test_carousel_escapes_untrusted_text(self):
        html = self.core.render_carousel({'slides': [{'title': '<script>alert(1)</script>', 'body': 'CRM فارسی ۱۲۳', 'alt': 'آزمایش'}]})
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('dir="rtl"', html)
        self.assertIn('۱ از ۱', html)

    def test_cli_accepts_utf8_and_returns_structured_results(self):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPTS / 'hefdah.py'), 'caption', '-', '--json'], input='ذخیره کن\n#آموزش', text=True, capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['hashtags'], ['#آموزش'])

    def test_cli_invalid_input_is_a_clear_error(self):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPTS / 'hefdah.py'), 'beats', '-', '--wpm', '0'], input='متن', text=True, capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Traceback', result.stderr)

    def test_cli_uses_utf8_even_when_windows_pipe_uses_legacy_encoding(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / 'hefdah.py'), 'caption', '-'], input='ذخیره کن\n#آموزش', text=True, capture_output=True, encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONIOENCODING='cp1252'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['hashtags'], ['#آموزش'])


class ContentQualityTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def test_hook_examples_are_usable(self):
        hooks = json.loads((self.ROOT / 'skills/hefdah/resources/hooks.json').read_text(encoding='utf-8'))['hooks']
        self.assertEqual(len(hooks), 26)
        for hook in hooks:
            self.assertGreater(len(hook['example']), 25, hook['id'])
            self.assertNotIn('کامل شود', hook['example'], hook['id'])

    def test_first_output_and_quality_rules_present(self):
        skill = (self.ROOT / 'skills/hefdah/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('## قاعده خروجی اول', skill)
        self.assertIn('## استاندارد کیفیت', skill)
        chat = (self.ROOT / 'HEFDAH-CHAT.md').read_text(encoding='utf-8')
        self.assertIn('## استاندارد کیفیت', chat)


if __name__ == '__main__':
    unittest.main()
