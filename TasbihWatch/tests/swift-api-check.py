#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 فاحص تطابق واجهات Swift ومحتوى الأذكار
سبحة — أداة تُشغَّل قبل كل تسليم (بدون Mac)

يفحص:
  ① أن كل نداء `SharedCounter.xxx()` / `SharedKeys.xxx` موجود فعلًا في Shared.swift
     (مع تجاهل التعليقات — درسٌ من خطأ `SharedCounter.increment()` المحذوفة)
  ② أن كل ملف مصدر مذكور في project.yml / project-container.yml موجود فعليًا
  ③ أن نصوص الأذكار الكاملة متطابقة بين Swift و المحاكي (عدد + المحتوى)

الاستخدام:  python3 tests/swift-api-check.py
"""

import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ok_all = True


def strip_comments(src: str) -> str:
    """يحذف تعليقات // و /* */ حتى لا نُبلّغ عن نداءات موجودة في الشرح فقط."""
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    out = []
    for line in src.splitlines():
        # تجاهل ما بعد // مع مراعاة عدم وجود // داخل نص عادي (تقريب كافٍ هنا)
        idx = line.find('//')
        out.append(line[:idx] if idx >= 0 else line)
    return '\n'.join(out)


def check_apis() -> bool:
    shared = strip_comments((ROOT / 'Shared.swift').read_text(encoding='utf-8'))
    funcs = set(re.findall(r'static func (\w+)', shared))
    keys = set(re.findall(r'static let (\w+)\s*=', shared))

    targets = ['Widget/IncrementIntent.swift', 'Widget/TasbihWidget.swift', 'CounterModel.swift',
               'CounterView.swift', 'ReadingView.swift', 'OptionsPanel.swift', 'MenuView.swift',
               'SetBackgrounds.swift', 'TasbihApp.swift', 'SessionManager.swift', 'Shared.swift']
    bad = []
    for f in targets:
        p = ROOT / f
        if not p.exists():
            continue
        src = strip_comments(p.read_text(encoding='utf-8'))
        for m in re.finditer(r'SharedCounter\.(\w+)\s*\(', src):
            if m.group(1) not in funcs:
                bad.append(f'{f}: SharedCounter.{m.group(1)}() غير موجودة')
        for m in re.finditer(r'SharedKeys\.(\w+)', src):
            if m.group(1) not in keys:
                bad.append(f'{f}: SharedKeys.{m.group(1)} غير موجود')

    print('① نداءات الكود المشترك')
    if bad:
        for b in bad:
            print('   ✘ ' + b)
        return False
    print(f'   ✔ {len(targets)} ملفًا · لا نداء لدالة أو مفتاح محذوف')
    return True


def check_sources() -> bool:
    print('② مصادر ملفات المشروع (yml)')
    try:
        import yaml
    except ImportError:
        print('   ⚠ PyYAML غير مثبّت — تخطّي (pip install pyyaml)')
        return True
    ok = True
    for name in ['project.yml', 'project-container.yml']:
        p = ROOT / name
        if not p.exists():
            continue
        d = yaml.safe_load(p.read_text(encoding='utf-8'))
        miss = []
        for _, t in (d.get('targets') or {}).items():
            for s in (t.get('sources') or []):
                path = s if isinstance(s, str) else s.get('path', '')
                if path and not (ROOT / path.rstrip('/')).exists():
                    miss.append(path)
        if miss:
            ok = False
            print(f'   ✘ {name}: مصادر مفقودة {miss}')
        else:
            print(f'   ✔ {name}: كل المصادر موجودة')
    return ok


def check_dhikr_parity() -> bool:
    print('③ تطابق نصوص الأذكار الكاملة (Swift ↔ المحاكي)')
    sim = (ROOT / 'simulator.html').read_text(encoding='utf-8')
    sw = (ROOT / 'Shared.swift').read_text(encoding='utf-8')

    k = sim.find('const FULL = {')
    sim_full = {}
    if k >= 0:
        for m in re.finditer(r'"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"', sim[k:sim.find('\n};', k)]):
            sim_full[m.group(1)] = m.group(2)

    block = sw[sw.find('adhkarSets'):]
    sw_full = {}
    for m in re.finditer(r'Dhikr\((.*?)\)\s*,?\s*(?=Dhikr\(|\])', block, re.S):
        body = ' '.join(m.group(1).split())
        t = re.search(r'text:\s*"((?:[^"\\]|\\.)*)"', body)
        f = re.search(r'full:\s*"((?:[^"\\]|\\.)*)"', body)
        if t and f:
            sw_full[t.group(1)] = f.group(1)

    only_sw = sorted(set(sw_full) - set(sim_full))
    only_sim = sorted(set(sim_full) - set(sw_full))
    diff = sorted(n for n in set(sim_full) & set(sw_full) if sim_full[n] != sw_full[n])

    print(f'   أسماء بنص كامل — Swift: {len(sw_full)} · المحاكي: {len(sim_full)}')
    for n in only_sw:
        print(f'   ✘ في Swift فقط: {n}')
    for n in only_sim:
        print(f'   ✘ في المحاكي فقط: {n}')
    for n in diff:
        print(f'   ✘ النص مختلف في: {n}')
    if only_sw or only_sim or diff:
        return False
    print('   ✔ الأسماء والنصوص متطابقة تمامًا')
    return True


def check_model_members() -> bool:
    """يتأكد أن كل مرجع `model.x` و`session.x` في الواجهات موجود فعلًا في النموذجين.
       هذا يلتقط خطأ الإملاء في اسم خاصية — وهو أكثر خطأ يوقف الترجمة."""
    print('④ مراجع النماذج (model.x / session.x)')

    def members(path):
        src = re.sub(r'/\*.*?\*/', '', path.read_text(encoding='utf-8'), flags=re.S)
        src = '\n'.join(l[:l.find('//')] if '//' in l else l for l in src.splitlines())
        names = set(re.findall(r'(?:var|let)\s+(\w+)', src))
        names |= set(re.findall(r'func\s+(\w+)', src))
        names |= set(re.findall(r'case\s+(\w+)', src))
        return names

    cm = members(ROOT / 'CounterModel.swift')
    sm = members(ROOT / 'SessionManager.swift')
    bad = []
    for f in ['CounterView.swift', 'ReadingView.swift', 'OptionsPanel.swift',
              'MenuView.swift', 'TasbihApp.swift', 'SetBackgrounds.swift']:
        p = ROOT / f
        if not p.exists():
            continue
        src = p.read_text(encoding='utf-8')
        for m in re.finditer(r'\bmodel\.(\w+)', src):
            if m.group(1) not in cm:
                bad.append(f'{f}: model.{m.group(1)}')
        for m in re.finditer(r'\bsession\.(\w+)', src):
            if m.group(1) not in sm:
                bad.append(f'{f}: session.{m.group(1)}')
    if bad:
        for b in sorted(set(bad)):
            print('   ✘ ' + b)
        return False
    print(f'   ✔ لا مراجع مفقودة (CounterModel: {len(cm)} عضوًا · SessionManager: {len(sm)})')
    return True


def check_app_group() -> bool:
    print('⑤ صلاحية مجموعة التطبيق (App Group)')
    try:
        import yaml
    except ImportError:
        print('   ⚠ PyYAML غير مثبّت — تخطّي')
        return True
    shared = (ROOT / 'Shared.swift').read_text(encoding='utf-8')
    m = re.search(r'appGroupID\s*=\s*"([^"]+)"', shared)
    want = m.group(1) if m else None
    print(f'   المعرّف في Shared.swift: {want}')
    ok = True
    for name in ['project.yml', 'project-container.yml']:
        p = ROOT / name
        if not p.exists():
            continue
        d = yaml.safe_load(p.read_text(encoding='utf-8'))
        for tname, t in (d.get('targets') or {}).items():
            srcs = [x if isinstance(x, str) else x.get('path', '') for x in (t.get('sources') or [])]
            if not any('Shared.swift' in str(x) for x in srcs):
                continue                      # لا يستخدم الكود المشترك ⇒ لا يحتاج الصلاحية
            groups = (((t.get('entitlements') or {}).get('properties') or {})
                      .get('com.apple.security.application-groups')) or []
            if want in groups:
                print(f'   ✔ {name} · {tname}')
            else:
                ok = False
                print(f'   ✘ {name} · {tname}: صلاحية مجموعة التطبيق مفقودة أو مختلفة')
    if ok:
        print('   ✔ كل هدف يقرأ الكود المشترك يملك الصلاحية نفسها')
    return ok


if __name__ == '__main__':
    ok_all = (check_apis() and check_sources() and check_dhikr_parity()
              and check_model_members() and check_app_group())
    print()
    print('📊 النتيجة:', '✔ كل الفحوصات سليمة' if ok_all else '❌ توجد مشاكل أعلاه')
    sys.exit(0 if ok_all else 1)
