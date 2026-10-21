#!/usr/bin/env python3
"""Hefdah's offline CLI; Python 3.10+, standard library only."""
import argparse
import csv
import io
import json
from pathlib import Path
import sys
import hefdah_core as core


def main():
    parser = argparse.ArgumentParser(description='هفده — ابزارهای محلی متن فارسی؛ بدون اتصال به حساب')
    parser.add_argument('command', choices=['normalize', 'human', 'caption', 'hook', 'beats', 'swipe', 'audit', 'carousel', 'context-init', 'context-show'])
    parser.add_argument('input', help='مسیر UTF-8 یا - برای ورودی استاندارد؛ در context مسیر پوشه مشتری‌ها')
    parser.add_argument('--json', action='store_true', help='خروجی JSON؛ خروجی پیش‌فرض هم ساختاریافته است')
    parser.add_argument('--preview', type=int, default=125)
    parser.add_argument('--wpm', type=float, default=150)
    parser.add_argument('--client', help='شناسه صریح مشتری؛ فقط برای context')
    parser.add_argument('-o', '--output', help='فایل خروجی جدید؛ فایل موجود بازنویسی نمی‌شود')
    args = parser.parse_args()
    try:
        if args.command.startswith('context-'):
            fn = core.create_context if args.command == 'context-init' else core.load_context
            result = fn(args.input, args.client)
        else:
            if args.input == '-':
                text = sys.stdin.read(core.MAX_TEXT + 1)
            else:
                source = Path(args.input)
                if source.stat().st_size > core.MAX_TEXT * 4:
                    raise ValueError('فایل بیش از حد بزرگ است.')
                text = source.read_text(encoding='utf-8-sig')
            core.check_text(text)
            if args.command in ['swipe', 'audit']:
                rows = list(csv.DictReader(io.StringIO(text), delimiter='\t' if '\t' in text.split('\n')[0] else ','))
                if not rows:
                    raise ValueError('جدول خالی است یا سرستون ندارد.')
                required = {'views'} if args.command == 'swipe' else {'reach'}
                if not required.issubset(rows[0]):
                    raise ValueError('ستون لازم موجود نیست: ' + ', '.join(sorted(required)))
                result = (core.rank_swipe if args.command == 'swipe' else core.audit_rows)(rows)
            elif args.command == 'carousel':
                result = core.render_carousel(json.loads(text))
            elif args.command == 'caption':
                result = core.lint_caption(text, args.preview)
            elif args.command == 'beats':
                result = core.estimate_beats(text, args.wpm)
            else:
                result = {'normalize': core.normalize, 'human': core.inspect_style, 'hook': core.review_hook}[args.command](text)
        output = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            with Path(args.output).open('x', encoding='utf-8', newline='\n') as target:
                target.write(output + '\n')
        else:
            print(output)
        return 0
    except (ValueError, OSError, TypeError, csv.Error) as error:
        print('خطا: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
