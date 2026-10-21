#!/usr/bin/env python3
"""Generate chat/shortcut files and deterministic, allowlisted release archives."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.1'
MODES = {
    'reel': ('ریلز', 'Write Persian Reels, hooks and spoken video scripts.'),
    'viral': ('تحقیق الگوها', 'Research supplied Instagram examples and compare account-relative performance.'),
    'caption': ('کپشن', 'Write and review Persian Instagram captions, hashtags and calls to action.'),
    'carousel': ('کاروسل', 'Create Persian carousel copy and optional local RTL HTML.'),
    'story': ('استوری', 'Draft Persian Instagram Story sequences and interaction ideas.'),
    'profile': ('پروفایل', 'Review personal or business Instagram profiles using visible evidence.'),
    'plan': ('برنامه هفته', 'Plan feasible Persian Instagram content for the week.'),
    'human': ('ویرایش طبیعی', 'Edit Persian content in the creator voice while preserving meaning.'),
    'comment': ('کامنت', 'Draft relevant Persian comments on supplied posts without posting.'),
    'reply': ('پاسخ', 'Triage and draft Persian replies to supplied comments.'),
    'dm': ('دایرکت', 'Draft Persian Instagram DMs and collaboration proposals without sending.'),
    'repurpose': ('بازاستفاده', 'Turn supplied long-form Persian content into source-grounded posts.'),
    'audit': ('گزارش عملکرد', 'Analyze supplied Instagram insights without inferring unsupported causes.')
}


def chat_bundle(root):
    skill = root / 'skills' / 'hefdah'
    text = (skill / 'SKILL.md').read_text(encoding='utf-8')
    text = re.sub(r'\A---\n.*?\n---\n', '', text, count=1, flags=re.S)
    parts = ['# HEFDAH CHAT — نسخه گفت‌وگویی ۰٫۱٫۱\n\nاین فایل را در گفت‌وگو بارگذاری/کپی کن و بگو «با هفده شروع کن». این فایل راهنماست؛ خودبه‌خود نصب ماندگار یا ابزار اجرایی ایجاد نمی‌کند. منابع لازم پایین همین فایل آمده‌اند. در نبود اجرای محلی، کار نوشتاری انجام بده و بررسی ابزار را انجام‌شده اعلام نکن.\n', text]
    for mode, (title, _) in MODES.items():
        parts.append(f'\n---\n## حالت {title}\n\n' + (skill / 'references' / f'{mode}.md').read_text(encoding='utf-8'))
    for filename in ['hooks.json', 'profile-rubrics.json', 'style.json', 'platform-rules.json']:
        data = json.loads((skill / 'resources' / filename).read_text(encoding='utf-8'))
        parts.append('\n---\n## منبع داخلی: ' + filename + '\n\n```json\n' + json.dumps(data, ensure_ascii=False, indent=2) + '\n```\n')
    parts.append('\n---\n' + (skill / 'references' / 'about.md').read_text(encoding='utf-8'))
    parts.append('\n---\n' + (skill / 'assets' / 'voice.fa.md').read_text(encoding='utf-8'))
    # All local referenced files are embedded; don't send chat-only users to missing paths.
    result = '\n'.join(parts)
    return re.sub(r'\[([^\]]+)\]\((?:references|assets)/[^)]+\)', r'\1 (در همین فایل)', result)


def generated_files(root):
    files = {root / 'HEFDAH-CHAT.md': chat_bundle(root)}
    for mode, (title, description) in MODES.items():
        files[root / 'skills' / f'hefdah-{mode}' / 'SKILL.md'] = f'''---
name: hefdah-{mode}
description: {description} Use when the user requests {mode} through hefdah or هفده.
---
# هفده — {title}

ابتدا اصول مشترک، لحن و مرزهای کار را از [هفده](../hefdah/SKILL.md) بخوان؛ سپس [راهنمای {title}](../hefdah/references/{mode}.md) را اجرا کن. فقط منابع مرتبط با درخواست را بارگیری کن.

این میان‌بر بخشی از بسته hefdah است؛ همراه پوشه اصلی نصب شود. اگر فایل اصلی در دسترس نیست، نبود دسترسی را بگو و نسخه مستقل HEFDAH-CHAT.md را پیشنهاد بده. نصب/انتشار/ارسال انجام‌شده فرض نکن. دستور کاربر و محدودیت محیط بر راهنما مقدم‌اند.
'''
    for name in ['LICENSE', 'NOTICE']:
        files[root / 'skills' / 'hefdah' / name] = (root / name).read_text(encoding='utf-8')
    return files


def release_files(root, skill_only=False):
    if skill_only:
        base = root / 'skills' / 'hefdah'
        candidates = sorted(base.rglob('*'))
    else:
        base = root
        candidates = [root / name for name in ['README.md', 'START-HERE.md', 'HEFDAH-CHAT.md', 'LICENSE', 'NOTICE', 'CHANGELOG.md', 'pyproject.toml', '.gitignore']]
        for directory in ['skills', 'scripts', 'docs', 'examples', 'tests', '.claude-plugin', '.github']:
            candidates.extend(sorted((root / directory).rglob('*')))
    for file in candidates:
        if not file.is_file() or file.is_symlink():
            continue
        rel = file.relative_to(base)
        if any(p in {'__pycache__', 'clients', '.git', 'dist'} for p in rel.parts):
            continue
        if file.suffix not in {'.md', '.json', '.py', '.html', '.csv', '.tsv', '.txt', '.yml', '.yaml', '.toml', ''} and file.name != '.gitignore':
            continue
        yield file, Path('hefdah') / rel


def make_zip(root, target, skill_only=False):
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for file, rel in release_files(root, skill_only):
            info = zipfile.ZipInfo(rel.as_posix(), (2026, 10, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, file.read_bytes())


def main():
    parser = argparse.ArgumentParser(description='Build hefdah chat file and release archives')
    parser.add_argument('--check', action='store_true', help='Check generated-file freshness without writing')
    parser.add_argument('--zip', action='store_true', help='Build full and standalone-skill archives')
    args = parser.parse_args()
    for file, content in generated_files(ROOT).items():
        if args.check:
            if not file.exists() or file.read_text(encoding='utf-8') != content:
                parser.exit(1, f'Generated file is stale: {file.relative_to(ROOT)}\n')
        else:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content, encoding='utf-8', newline='\n')
    if args.zip and not args.check:
        out = ROOT / 'dist'
        out.mkdir(exist_ok=True)
        sums = []
        for suffix, standalone in [('', False), ('-skill', True)]:
            target = out / f'hefdah{suffix}-{VERSION}.zip'
            make_zip(ROOT, target, standalone)
            sums.append(hashlib.sha256(target.read_bytes()).hexdigest() + '  ' + target.name)
            print(target.name)
        (out / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n', encoding='utf-8')
    print('Generated files are current.' if args.check else 'Generated hefdah chat file and 13 shortcuts.')


if __name__ == '__main__':
    main()
