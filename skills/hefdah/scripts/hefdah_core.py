"""Local Persian editing helpers. No network, model calls, or account access."""
import html
import json
import math
from pathlib import Path
import re
import unicodedata
from decimal import Decimal, InvalidOperation

BASE = Path(__file__).resolve().parents[1]
MAX_TEXT = 1_000_000
DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
LETTERS = str.maketrans({'ي': 'ی', 'ك': 'ک'})
PROTECTED = re.compile(r'```[\s\S]*?```|`[^`\n]*`|https?://[^\s<>]+|www\.[^\s<>]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|@[\w.]+|«[^»]*»|“[^”]*”|"[^"\n]*"')
WORD = re.compile(r'[^\W_]+(?:[\u200c\u200d\x27’-][^\W_]+)*', re.UNICODE)


def check_text(text):
    if not isinstance(text, str) or len(text) > MAX_TEXT:
        raise ValueError('متن باید رشته‌ای با حداکثر یک میلیون نویسه باشد.')


def resource(name):
    return json.loads((BASE / 'resources' / name).read_text(encoding='utf-8'))


def normalize(text):
    """Only Arabic yeh/kaf outside protected spans; preserve all meaningful controls."""
    check_text(text)
    changes = []
    parts, end = [], 0
    for match in PROTECTED.finditer(text):
        parts.extend([text[end:match.start()].translate(LETTERS), match.group()])
        end = match.end()
    parts.append(text[end:].translate(LETTERS))
    clean = ''.join(parts)
    if clean.startswith('\ufeff'):
        clean = clean[1:]
        changes.append({'rule': 'leading-bom', 'reason': 'حذف BOM فقط در ابتدای فایل'})
    if clean != text.lstrip('\ufeff'):
        changes.append({'rule': 'persian-letters', 'reason': 'یکسان‌سازی ی/ک خارج از لینک، شناسه و نقل‌قول'})
    controls = sorted({f'U+{ord(c):04X}' for c in clean if unicodedata.category(c) == 'Cf' and c not in '\u200c\u200d'})
    return {'text': clean, 'changes': changes, 'warnings': [{'controls': controls, 'reason': 'کنترل نامرئی/جهت؛ نیاز به بررسی، بدون حذف خودکار'}] if controls else []}


def parse_quantity(raw):
    """Nonnegative numbers, consistent grouping, decimal suffixes; never infer currency."""
    if isinstance(raw, bool) or raw is None:
        raise ValueError('عدد نامعتبر است.')
    text = str(raw).strip().translate(DIGITS).replace('٫', '.').replace('٬', ',')
    match = re.fullmatch(r'([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(هزار|میلیون|میلیارد|[kKmM]|[%٪])?', text)
    if not match:
        raise ValueError(f'قالب عدد مبهم یا نامعتبر: {raw}')
    number, suffix = match.groups()
    integer = number.split('.')[0]
    if ',' in integer and not re.fullmatch(r'[0-9]{1,3}(?:,[0-9]{3})+', integer):
        raise ValueError(f'جداکننده هزارگان نامعتبر: {raw}')
    try:
        value = Decimal(number.replace(',', ''))
    except InvalidOperation as exc:
        raise ValueError('عدد نامعتبر است.') from exc
    multiplier = {'هزار': 1000, 'k': 1000, 'میلیون': 1000000, 'm': 1000000, 'میلیارد': 1000000000}.get((suffix or '').lower(), 1)
    value *= multiplier
    if value > Decimal('1e15'):
        raise ValueError('عدد خارج از محدوده ابزار است.')
    return int(value) if value == value.to_integral_value() else float(value)


def words(text):
    return WORD.findall(text)


def lint_caption(text, preview=125):
    check_text(text)
    if not 1 <= preview <= 2200:
        raise ValueError('پیش‌نمایش باید بین ۱ و ۲۲۰۰ باشد.')
    normalized = normalize(text)['text']
    tags = re.findall(r'(?<![\w#])#[^\W_]+(?:_[^\W_]+)*', normalized, re.UNICODE)
    # shortcut: intentional ZWNJ inside hashtags is ambiguous across app versions; flag it.
    ambiguous = bool(re.search(r'#[^\s#]*\u200c', normalized))
    visible = PROTECTED.sub(' ', normalized)
    patterns = {
        'save': r'(?:ذخیره|سیو)\s+(?:کن(?:ید)?|بکن(?:ید)?)\b',
        'share': r'(?:بفرست(?:ید)?|به\s+اشتراک\s+بگذار(?:ید)?)\b',
        'comment': r'(?:کامنت\s+(?:بذار(?:ید)?|بگذار(?:ید)?|کن(?:ید)?)|برام\s+بنویس(?:ید)?)\b',
        'dm': r'(?:دایرکت|پیام)\s+(?:بده(?:ید)?|بفرست(?:ید)?)\b',
        'follow': r'(?:دنبال|فالو)\s+کن(?:ید)?\b',
        'link': r'(?:لینک\s+(?:توی\s+|داخل\s+)?بیو|از\s+لینک\s+بیو)'
    }
    asks = [key for key, pattern in patterns.items() if re.search(pattern, visible)]
    warnings = []
    if len(asks) > 1:
        warnings.append('چند دعوت به اقدام پیدا شد؛ یک هدف اصلی را انتخاب کن.')
    if ambiguous:
        warnings.append('هشتگ دارای نیم‌فاصله است؛ پیوستگی آن را در خود اینستاگرام بررسی کن.')
    if len(text) > 2200:
        warnings.append('بیش از ۲۲۰۰ نویسه؛ طول مجاز را هنگام انتشار در حساب مقصد بررسی کن.')
    if len(tags) > 5:
        warnings.append('بیش از پنج هشتگ؛ پیشنهاد تحریری این بسته، محدودکردن به چند هشتگ مرتبط است؛ این خطا حکم پلتفرم نیست.')
    if re.search(r'https?://|www\.', text):
        warnings.append('قابلیت کلیک لینک را در سطح انتشار مقصد بررسی کن؛ مسیر بیو/دایرکت را در صورت نیاز روشن بنویس.')
    return {'characters': len(text), 'count_unit': 'Unicode code points; not a verified platform counter', 'preview': text[:preview], 'preview_is_approximate': True, 'hashtags': tags, 'asks': asks, 'warnings': warnings}


def inspect_style(text):
    result = normalize(text)
    suggestions = []
    searchable = PROTECTED.sub(' ', result['text'])
    for entry in resource('style.json')['phrases']:
        if entry['phrase'] in searchable:
            suggestions.append(entry)
    result['suggestions'] = suggestions
    result['note'] = 'گزارش ویرایش و وضوح؛ ابزار تشخیص انسان یا هوش مصنوعی نیست. پیشنهادها خودکار اعمال نشده‌اند.'
    return result


def review_hook(text):
    check_text(text)
    normalized = normalize(text)['text']
    tokens = words(normalized)
    checks = []
    if re.match(r'^\s*(سلام|در این ویدیو|توی این ویدیو|امروز می‌خوام|اسکرول نکن)', normalized):
        checks.append({'kind': 'opening', 'advice': 'آغاز را با موضوع یا نتیجه مشخص امتحان کن؛ مقدمه را کوتاه کن.'})
    if len(tokens) > 16:
        checks.append({'kind': 'length', 'advice': 'شروع طولانی است؛ آن را با خوانش واقعی بررسی کن.'})
    if not re.search(r'[0-9۰-۹٠-٩]|\b(دو|سه|چهار|پنج|هزار|میلیون)\b', normalized):
        checks.append({'kind': 'specificity', 'advice': 'اگر جزئیات واقعی داری اضافه کن؛ برای بهترشدن هوک عدد نساز.'})
    return {'text': text, 'word_count': len(tokens), 'checks': checks, 'note': 'چک‌لیست تحریری؛ پیش‌بینی بازدید نیست. مخاطب، وعده و ارتباط متن با تصویر باید توسط انسان/مدل بررسی شوند.'}


ONES = ['صفر', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه', 'ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده']
TENS = ['', '', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود']
HUNDREDS = ['', 'صد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد']


def spoken_integer(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + (' و ' + spoken_integer(n % 10) if n % 10 else '')
    if n < 1000:
        return HUNDREDS[n // 100] + (' و ' + spoken_integer(n % 100) if n % 100 else '')
    for scale, name in [(10**12, 'تریلیون'), (10**9, 'میلیارد'), (10**6, 'میلیون'), (1000, 'هزار')]:
        if n >= scale:
            return spoken_integer(n // scale) + ' ' + name + (' و ' + spoken_integer(n % scale) if n % scale else '')


def spoken_text(text):
    def replace(match):
        raw = match.group().translate(DIGITS).replace('٫', '.').replace('٬', ',')
        try:
            value = parse_quantity(raw)
        except ValueError:
            return raw
        # shortcut: decimal fractions read digit by digit; speaker calibration remains necessary.
        integer, _, fraction = raw.replace(',', '').partition('.')
        if fraction:
            return spoken_integer(int(integer)) + ' ممیز ' + ' '.join(ONES[int(c)] for c in fraction)
        return spoken_integer(int(value))
    return re.sub(r'[0-9۰-۹٠-٩]+(?:[٬,][0-9۰-۹٠-٩]{3})*(?:[٫.][0-9۰-۹٠-٩]+)?', replace, text)


def estimate_beats(text, wpm=150):
    check_text(text)
    if not math.isfinite(wpm) or not 40 <= wpm <= 400:
        raise ValueError('سرعت خوانش باید بین ۴۰ و ۴۰۰ واژه در دقیقه باشد.')
    rows, start, total_words = [], 0.0, 0
    for line in text.splitlines():
        if not line.strip():
            continue
        n = len(words(spoken_text(line)))
        pause = len(re.findall(r'[،؛.!؟?]', line)) * 0.25
        duration = n * 60 / wpm + pause
        rows.append({'text': line, 'start': round(start, 2), 'seconds': round(duration, 2), 'spoken_words': n})
        start += duration
        total_words += n
    return {'beats': rows, 'spoken_words': total_words, 'estimated_seconds': round(start, 2), 'range_seconds': [round(start * .75, 2), round(start * 1.3, 2)], 'wpm': wpm, 'calibrated': False, 'note': 'برآورد برنامه‌ریزی، نه زمان‌سنجی صدا؛ نرخ پیش‌فرض روی گویندگان فارسی اعتبارسنجی نشده است.'}


def optional_number(row, key):
    value = row.get(key)
    if value is None or str(value).strip() == '':
        return None
    return parse_quantity(value)


def rank_swipe(rows):
    ranked, unranked = [], []
    for row in rows:
        views, median = optional_number(row, 'views'), optional_number(row, 'median')
        result = dict(row)
        result['multiple'] = round(views / median, 3) if views is not None and median is not None and median > 0 else None
        result['baseline_type'] = 'account_median' if result['multiple'] is not None else 'missing_or_zero_median'
        (ranked if result['multiple'] is not None else unranked).append(result)
    ranked.sort(key=lambda r: r['multiple'], reverse=True)
    return {'ranked': ranked, 'unranked': unranked, 'note': 'مقایسه فقط با میانه همان حساب؛ سن محتوا، فرمت و تبلیغ باید هم‌سنخ باشند. تعداد فالوئر جایگزین میانه نشده است.'}


def audit_rows(rows):
    posts, warnings = [], []
    for row in rows:
        result = dict(row)
        reach = optional_number(row, 'reach')
        for metric in ['shares', 'saves', 'follows']:
            value = optional_number(row, metric)
            result[metric + '_per_reach'] = round(value / reach, 6) if reach is not None and reach > 0 and value is not None else None
        posts.append(result)
    if len(rows) < 10:
        warnings.append('نمونه محدود است؛ نتیجه اکتشافی است و علت موفقیت/شکست را ثابت نمی‌کند.')
    if any(not row.get('window') for row in rows):
        warnings.append('پنجره اندازه‌گیری برخی ردیف‌ها مشخص نیست؛ رتبه‌بندی نهایی انجام نشد.')
    return {'posts': posts, 'warnings': warnings, 'note': 'ناموجود با صفر فرق دارد؛ نرخ‌ها نسبت اعشاری‌اند، نه درصد. shares الزاماً همان sends خصوصی نیست.'}


def client_path(root, client_id):
    if not isinstance(client_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', client_id):
        raise ValueError('شناسه مشتری باید ۱ تا ۴۸ حرف کوچک لاتین، عدد یا خط تیره باشد.')
    if client_id in {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(1, 10)), *(f'lpt{i}' for i in range(1, 10))}:
        raise ValueError('شناسه رزروشده مجاز نیست.')
    root = Path(root).resolve()
    path = root / client_id
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError('مسیر مشتری باید داخل پوشه انتخابی و بدون پیوند نمادین باشد.')
    return path


def create_context(root, client_id):
    path = client_path(root, client_id)
    path.mkdir(parents=True, exist_ok=False)
    (path / 'voice.md').write_text('# صدای این برند\nلحن: هنوز مشخص نشده\nنمونه متن: هنوز ارائه نشده\n', encoding='utf-8')
    (path / 'facts.json').write_text('{"approved_facts": [], "forbidden_claims": []}\n', encoding='utf-8')
    return {'client_id': client_id, 'path': str(path)}


def load_context(root, client_id):
    path = client_path(root, client_id)
    values = {}
    for filename in ['voice.md', 'facts.json']:
        file = path / filename
        if file.is_symlink() or not file.resolve().is_relative_to(path.resolve()):
            raise ValueError('فایل context نباید از پوشه مشتری خارج شود.')
        if file.stat().st_size > MAX_TEXT:
            raise ValueError('فایل context بیش از حد بزرگ است.')
        values[filename] = file.read_text(encoding='utf-8')
    facts = json.loads(values['facts.json'])
    if not isinstance(facts, dict) or not isinstance(facts.get('approved_facts'), list):
        raise ValueError('facts.json باید approved_facts به شکل فهرست داشته باشد.')
    return {'client_id': client_id, 'voice': values['voice.md'], 'facts': facts}


def render_carousel(data):
    slides = data.get('slides') if isinstance(data, dict) else None
    if not isinstance(slides, list) or not 1 <= len(slides) <= 20:
        raise ValueError('slides باید فهرستی با یک تا بیست اسلاید باشد.')
    cards = []
    for index, slide in enumerate(slides, 1):
        if not isinstance(slide, dict) or not isinstance(slide.get('title'), str) or not isinstance(slide.get('body', ''), str):
            raise ValueError('هر اسلاید به title متنی و body متنی نیاز دارد.')
        title, body = slide['title'], slide.get('body', '')
        if len(title) > 120 or len(body) > 500:
            raise ValueError('متن اسلاید بلند است؛ آن را به اسلایدهای کوتاه‌تر تقسیم کن.')
        alt = slide.get('alt', title)
        if not isinstance(alt, str):
            raise ValueError('alt باید متن باشد.')
        label = f'{index} از {len(slides)}'.translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))
        cards.append(f'<section class="slide" aria-label="{html.escape(alt, quote=True)}"><small>{label}</small><h1>{html.escape(title)}</h1><p>{html.escape(body)}</p></section>')
    return '''<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>کاروسل</title><style>
*{box-sizing:border-box}body{margin:0;background:#e4e5e7;color:#171d27;font-family:Tahoma,Arial,sans-serif}.slide{width:1080px;height:1350px;background:#faf9f6;padding:120px;overflow:hidden;break-after:page;position:relative;margin:24px auto;border-top:20px solid #136b5d}h1{font-size:70px;line-height:1.6;margin:80px 0 48px;overflow-wrap:anywhere}p{font-size:44px;line-height:1.9;white-space:pre-wrap;unicode-bidi:plaintext;overflow-wrap:anywhere}small{font-size:28px;color:#49645f}h1{unicode-bidi:plaintext}@page{size:1080px 1350px;margin:0}@media print{body{background:white}.slide{margin:0}}@media screen and (max-width:1100px){body{width:1080px}}
</style><body>''' + ''.join(cards) + '</body></html>'
