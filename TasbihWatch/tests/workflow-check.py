#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 مدقّق سير عمل GitHub Actions — قبل الدفع إلى المستودع
سبحة

يفحص (بلا إنترنت وبلا Mac):
  ① صحة YAML لكل ملفات سير العمل
  ② أن كل `needs:` يشير إلى مهمة موجودة فعلًا
  ③ أن كل `${{ matrix.X }}` له تعريف في المصفوفة (خطأ شائع يُفشل أول تشغيل)
  ④ أن كل `secrets.X` المطلوبة مذكورة في قائمة الأسرار المطلوبة
     (فتعرف مسبقًا أي أسرار ستحتاج)
  ⑤ أن كل ملف يُستدعى في خطوة run موجود فعلًا (نصوص، اختبارات، مفاتيح)
  ⑥ أن كل `uses:` مثبّت على إصدار (بلا @ فقد يفشل)

الاستخدام:  python3 tests/workflow-check.py
"""

import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WF = ROOT / '.github' / 'workflows'
ok_all = True


def fail(msg):
    global ok_all
    ok_all = False
    print('   ✘ ' + msg)


def ok(msg):
    print('   ✔ ' + msg)


def main():
    try:
        import yaml
    except ImportError:
        print('⚠ PyYAML غير مثبّت — نفّذ: pip install pyyaml')
        return 1

    if not WF.exists():
        print('⚠ لا يوجد مجلد .github/workflows')
        return 1

    for f in sorted(WF.glob('*.yml')) + sorted(WF.glob('*.yaml')):
        print(f'\n▸ {f.name}')
        try:
            doc = yaml.safe_load(f.read_text(encoding='utf-8'))
        except yaml.YAMLError as e:
            fail(f'YAML غير صالح: {e}')
            continue
        ok('YAML صالح')

        jobs = doc.get('jobs') or {}
        if not jobs:
            fail('لا توجد مهام (jobs)')
            continue

        # ② needs
        for name, job in jobs.items():
            for need in ([job['needs']] if isinstance(job.get('needs'), str) else (job.get('needs') or [])):
                if need not in jobs:
                    fail(f'{name}: needs يشير إلى مهمة غير موجودة: {need}')

        # ③ مصفوفات
        for name, job in jobs.items():
            matrix = ((job.get('strategy') or {}).get('matrix') or {})
            text = yaml.safe_dump(job, allow_unicode=True)
            used = set(re.findall(r'\$?\{\{\s*matrix\.(\w+)\s*\}\}', text))
            if used and not matrix:
                fail(f'{name}: يستخدم matrix.{sorted(used)} بلا مصفوفة')
            elif matrix and 'include' in matrix:
                # ⚠️ لكل مدخل على حدة: مفتاح ناقص في مدخل واحد = اسم أثر/سجل فارغ في التشغيل
                problems = []
                for i, item in enumerate(matrix['include'], 1):
                    gap = used - set(item.keys())
                    if gap:
                        problems.append(f'المدخل {i} بلا {sorted(gap)}')
                if problems:
                    for pr in problems:
                        fail(f'{name}: {pr} ← يُنتج اسمًا فارغًا في الأثر/السجل')
                else:
                    ok(f'{name}: مصفوفة سليمة ({len(matrix["include"])} حالة، كل المفاتيح معرَّفة في كل مدخل)')

        # ③-ب أسماء الآثار: يجب أن تكون فريدة (upload-artifact v4 يرفض التكرار)
        for name, job in jobs.items():
            matrix = ((job.get('strategy') or {}).get('matrix') or {})
            entries = matrix.get('include') or ([{}] if matrix else [{}])
            if not entries:
                entries = [{}]
            seen = {}
            for step in (job.get('steps') or []):
                if 'upload-artifact' not in (step.get('uses') or ''):
                    continue
                raw = (step.get('with') or {}).get('name', '')
                for entry in entries:
                    expanded = raw
                    for k, v in entry.items():
                        expanded = expanded.replace('${{ matrix.' + k + ' }}', str(v))
                    seen.setdefault(expanded, 0)
                    seen[expanded] += 1
            dupes = [n for n, c in seen.items() if c > 1]
            if dupes:
                fail(f'{name}: اسم أثر مكرَّر في upload-artifact: {dupes} (v4 يرفض التكرار)')
            elif seen:
                ok(f'{name}: أسماء الآثار فريدة ({len(seen)} أثرًا)')

        # ④ الأسرار + ⑤ الملفات + ⑥ uses
        secrets_needed, missing_files, unpinned = set(), [], []
        for name, job in jobs.items():
            text = yaml.safe_dump(job, allow_unicode=True)
            secrets_needed |= set(re.findall(r'secrets\.([A-Za-z0-9_]+)', text))
            for step in (job.get('steps') or []):
                uses = step.get('uses', '')
                if uses and '@' not in uses:
                    unpinned.append(uses)
                run = step.get('run', '')
                # مجلد التنفيذ: إن حُدِّد في الخطوة تُحسب المسارات نسبيًا له
                wd = step.get('working-directory') or ''
                base = (ROOT / wd) if wd else ROOT
                if wd and not base.exists():
                    missing_files.append(f'{name}: مجلد التنفيذ {wd}')
                for rel in re.findall(r'(?:python3|node)\s+([\w./-]+\.(?:py|mjs|js))', run):
                    if not (base / rel).exists():
                        missing_files.append(f'{name}: {rel}' + (f' (داخل {wd})' if wd else ''))

        if secrets_needed:
            ok('الأسرار المطلوبة: ' + ', '.join(sorted(secrets_needed)))
        if missing_files:
            for m in sorted(set(missing_files)):
                fail('ملف/مجلد مفقود — ' + m)
        else:
            ok('كل الملفات المستدعاة موجودة')
        if unpinned:
            for u in unpinned:
                fail(f'uses بلا إصدار مثبّت: {u}')
        else:
            ok('كل uses مثبّت على إصدار')

    print()
    print('📊 النتيجة:', '✔ كل سير العمل سليم' if ok_all else '❌ توجد مشاكل أعلاه')
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main())
