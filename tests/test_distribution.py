"""Broken packaging loses workflows; installation must preserve existing skills."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class Distribution(unittest.TestCase):
    def load_builder(self):
        script = ROOT / 'scripts' / 'build_release.py'
        self.assertTrue(script.exists(), 'Distribution builder is not implemented')
        spec = importlib.util.spec_from_file_location('hefdah_builder', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_chat_bundle_has_all_workflows_and_resources(self):
        module = self.load_builder()
        result = module.chat_bundle(ROOT)
        self.assertIn('هفده', result)
        self.assertIn('آمار منبع‌دار', result)
        self.assertIn('shares_per_reach', result)
        for name in ['ریلز', 'دایرکت', 'کاروسل', 'بازاستفاده']:
            self.assertIn(name, result)
        self.assertNotIn('](references/', result)

    def test_release_excludes_private_data_and_contains_self_contained_skill(self):
        module = self.load_builder()
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            target = Path(folder) / 'bundle.zip'
            module.make_zip(ROOT, target, skill_only=True)
            with zipfile.ZipFile(target) as archive:
                names = archive.namelist()
                self.assertIn('hefdah/SKILL.md', names)
                self.assertIn('hefdah/scripts/hefdah_core.py', names)
                self.assertTrue(all('clients/' not in x and '__pycache__' not in x for x in names))

    def test_install_is_additive_and_refuses_overwrite(self):
        script = ROOT / 'scripts' / 'install.py'
        self.assertTrue(script.exists(), 'Safe installer is not implemented')
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            target = Path(folder) / 'my skills'
            args = [sys.executable, str(script), '--target', str(target)]
            first = subprocess.run(args, text=True, capture_output=True, encoding='utf-8')
            self.assertEqual(first.returncode, 0, first.stderr)
            marker = target / 'hefdah' / 'assets' / 'private-note.txt'
            marker.write_text('do not change', encoding='utf-8')
            second = subprocess.run(args, text=True, capture_output=True, encoding='utf-8')
            self.assertEqual(second.returncode, 2)
            self.assertEqual(marker.read_text(encoding='utf-8'), 'do not change')

    def test_full_release_works_after_extraction(self):
        module = self.load_builder()
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            target = Path(folder) / 'full.zip'
            module.make_zip(ROOT, target)
            with zipfile.ZipFile(target) as archive:
                archive.extractall(Path(folder) / 'unpacked')
            checkout = Path(folder) / 'unpacked' / 'hefdah'
            result = subprocess.run([sys.executable, '-X', 'utf8', 'skills/hefdah/scripts/hefdah.py', 'caption', 'examples/caption.fa.txt'], cwd=checkout, capture_output=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
