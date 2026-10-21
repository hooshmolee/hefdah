# استفاده و نصب

## استفاده بدون نصب

لینک مخزن را همراه درخواست «START-HERE.md را بخوان و با هفده شروع کن» بده. موفقیت به دسترسی دستیار به فایل‌ها بستگی دارد. اگر دسترسی ندارد، فایل `HEFDAH-CHAT.md` را بارگذاری یا کپی کن. این مسیر برای همان گفت‌وگو است؛ ذخیره ماندگار فرض نمی‌شود.

## بسته مستقل اسکیل

پوشه `skills/hefdah` یک اسکیل خودکفا با همه ۱۳ حالت است. اگر میزبان نصب از ZIP دارد، از `hefdah-skill-0.1.0.zip` خروجی release استفاده کن و رابط همان میزبان را دنبال کن. صرف بارگذاری ZIP در یک چت عادی، نصب اسکیل را اثبات نمی‌کند.

## نصب در پوشه انتخابی

از ریشه پروژه اجرا کن؛ Python 3.10+ لازم است. هیچ پوشه جهانی یا تنظیم حساب خودکار تغییر نمی‌کند:

```sh
python scripts/install.py --target .claude/skills
```

این دستور ورودی اصلی و ۱۳ میان‌بر را در پوشه جدید کپی می‌کند. مسیر مثال مربوط به پروژه فعلی است؛ مسیر موردپشتیبانی میزبان خودت را انتخاب کن. برای فقط ورودی خودکفا:

```sh
python scripts/install.py --target .agents/skills --main-only
```

میان‌برها به پوشه `hefdah` همان بسته نیاز دارند؛ تک‌فایل میان‌بر را جدا نصب نکن. نصب‌کننده اگر هر مقصدی از قبل موجود باشد، قبل از کپی متوقف می‌شود و چیزی را بازنویسی نمی‌کند. برای به‌روزرسانی، فایل‌های شخصی را خارج از اسکیل نگه دار و نسخه‌ها را جدا مقایسه کن. حذف، از رابط میزبان یا با حذف دستی فقط پوشه‌های hefdah انجام شود؛ پوشه داده برند را پاک نکن.

## Claude Code plugin

مخزن manifest و marketplace دارد. پس از دریافت در پوشه `hefdah`، در محیط دارای Claude Code:

```sh
claude plugin validate ./hefdah
claude plugin marketplace add ./hefdah
claude plugin install hefdah@hefdah
```

بعد نصب، از فهرست واقعی مهارت‌ها ورودی هفده را انتخاب کن. نام فرمان ممکن است namespace پلاگین بگیرد؛ شکل نمایش را از میزبان بخوان، حدس نزن. این مسیر از نظر ساختار مستند شده ولی تا وقتی در گزارش سازگاری تست زنده ثبت نشده، نصب موفق همه نسخه‌ها تضمین نمی‌شود.

## بررسی توسعه

```sh
python -m unittest discover -s tests -v
python scripts/build_release.py --check
python scripts/build_release.py --zip
```

خروجی ZIP کامل و ZIP اسکیل مستقل در `dist/` همراه SHA256 ساخته می‌شود. داده `clients/` در آرشیو/مخزن وارد نمی‌شود. فایل مستقل چت و میان‌برها تولیدشده‌اند؛ منابع اصلی را ویرایش و دوباره build کن.

مرجع ساختار: [OpenAI Skills](https://learn.chatgpt.com/docs/build-skills)، [Claude plugin manifest](https://code.claude.com/docs/en/plugins-reference)، [Claude marketplace](https://code.claude.com/docs/en/plugin-marketplaces).
