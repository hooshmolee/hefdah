#!/usr/bin/env python3
"""Copy the skill pack into an explicitly selected directory; never overwrite."""
import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description='Install hefdah into a directory you choose; no global settings are changed')
    parser.add_argument('--target', required=True, type=Path, help='Skill directory for your host, e.g. a project .claude/skills')
    parser.add_argument('--main-only', action='store_true', help='Only install the self-contained hefdah entrypoint')
    args = parser.parse_args()
    try:
        if args.target.is_symlink():
            raise ValueError('پوشه مقصد نباید پیوند نمادین باشد.')
        target = args.target.resolve()
        sources = [ROOT / 'skills' / 'hefdah'] if args.main_only else sorted(p for p in (ROOT / 'skills').iterdir() if p.is_dir() and (p / 'SKILL.md').is_file())
        for source in sources:
            destination = target / source.name
            if destination.exists() or destination.is_symlink():
                raise FileExistsError(f'قبلاً وجود دارد؛ هیچ فایلی بازنویسی نشد: {destination}')
        target.mkdir(parents=True, exist_ok=True)
        for source in sources:
            shutil.copytree(source, target / source.name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        print(f'{len(sources)} پوشه در {target} کپی شد. شناسایی در میزبان را جدا بررسی کن.')
        return 0
    except (ValueError, OSError) as error:
        print('خطا: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
