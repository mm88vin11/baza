#!/usr/bin/env python3
"""
Перекраска сайта БАЗА в тёплую палитру (амбер / золото / коралл / вино / бумага).

Скрипт берёт исходный однофайловый экспорт сайта и выдаёт index.html
в новой палитре. Меняются три слоя:

  1. токены цвета  — глобальная замена двух базовых токенов исходника
                     (#0a0a0a / #f2ebdd) и их rgba-производных;
  2. акценты       — точечные правки: CTA, активная таблетка навигации,
                     бегущая строка, чипы, сердечки, метрики, выделение;
  3. атмосфера     — тёплое свечение фона и цветокоррекция всех кадров
                     секвенций (gradient map по яркости).

Использование:
    python3 tools/recolor.py <исходный экспорт>.html index.html
"""

import base64
import io
import json
import re
import sys

from PIL import Image
import numpy as np

# ─── палитра из референса ────────────────────────────────────────────────────
AMBER = '#d37724'   # 1 — основной тёплый
GOLD = '#eea252'   # 2 — светлый амбер
WINE = '#831a0a'   # 3 — глубокое вино
CORAL = '#f05035'   # 4 — акцент действия
PAPER = '#f7efe4'   # 5 — тёплая бумага (было #f2ebdd)
BASE = '#1a0805'   # подложка (было #0a0a0a)

# ─── 1. токены ───────────────────────────────────────────────────────────────
# Порядок важен: длинные литералы идут раньше коротких.
TOKENS = [
    ('#f2ebdd', PAPER),
    ('#f7f2e8', '#fdf8f0'),          # верхний стоп градиента брифа
    ('#ece3cf', '#efdfc9'),          # нижний стоп градиента брифа
    ('rgba(242,235,221,', 'rgba(247,239,228,'),
    ('#0a0a0a', BASE),
    ('rgba(10,10,10,', 'rgba(26,8,5,'),
    ('#101010', '#2a0e07'),
    ('#111111', '#2c1008'),
    ('#171717', '#361509'),
    ('#191919', '#3a1709'),
    ('#161616', '#331309'),
    ('#151515', '#31120a'),
    ('#0d0d0d', '#210b06'),
    ('#0c0c0c', '#1f0a06'),
    ('#0b0b0b', '#1d0906'),
    ('rgba(14,14,14', 'rgba(30,11,7'),
    ('rgba(13,13,13', 'rgba(28,10,6'),
    ('rgba(22,22,22', 'rgba(44,17,10'),
    ('rgba(16,16,16', 'rgba(34,13,8'),
    ('rgba(6,6,6', 'rgba(18,6,3'),
    ('rgba(0,0,0,', 'rgba(20,5,2,'),          # тени — тёплые
    ('rgba(255,253,247', 'rgba(255,249,240'),
    ('rgba(255,255,255,0.5)', 'rgba(255,250,242,0.62)'),
    ('rgba(255,255,255,0.7)', 'rgba(255,250,242,0.75)'),
    ('#9e3a20', '#8f2a10'),                   # ошибка формы → вино
    ('rgba(158,58,32,', 'rgba(143,42,16,'),
    ('#5ff09a', GOLD),                        # рост в тикере → золото
    ('#ff6a52', CORAL),                       # падение в тикере → коралл
    ('%230a0a0a', '%23' + WINE[1:]),          # фавикон: подложка → вино
    ('%23f2ebdd', '%23' + PAPER[1:]),
]

# «#111» без продолжения (короткая запись) — отдельно, после длинных.
SHORT_HEX = [(r'#111\b', '#2c1008')]

# ─── 2. акценты ──────────────────────────────────────────────────────────────
# (описание, регулярка по исходнику, замена, ожидаемое число совпадений)
ACCENTS = [
    (
        'выделение текста → коралл',
        re.escape('::selection { background: #f2ebdd; color: #0a0a0a; }'),
        '::selection { background: ' + CORAL + '; color: #fff4ea; }',
        1,
    ),
    (
        'главный CTA → градиент коралл/амбер',
        r"(borderRadius: '999px', border: 'none', outline: 'none',\s*\n\s*)backgroundColor: CREAM,\n(\s*)boxShadow: hover \? '0 18px 40px rgba\(0,0,0,0\.5\)' : '0 10px 26px rgba\(0,0,0,0\.34\)',",
        r"\1backgroundColor: '" + CORAL + r"',\n\2backgroundImage: 'linear-gradient(118deg, #f0a24a 0%, " + CORAL + r" 54%, #d3411f 100%)',\n\2boxShadow: hover ? '0 20px 46px rgba(240,80,53,0.42)' : '0 12px 30px rgba(240,80,53,0.28)',",
        1,
    ),
    (
        'таблетка активного пункта меню → золото',
        r"background: '#f2ebdd', opacity: 0, willChange: 'transform, width',\n(\s*)boxShadow: '0 6px 18px rgba\(0,0,0,0\.28\)',",
        r"background: '" + GOLD + r"', opacity: 0, willChange: 'transform, width',\n\1boxShadow: '0 8px 22px rgba(211,119,36,0.42)',",
        1,
    ),
    (
        'бегущая строка → градиент амбер',
        re.escape('overflow: hidden; background: #f2ebdd;'),
        'overflow: hidden; background: linear-gradient(90deg, ' + AMBER + ' 0%, ' + GOLD + ' 38%, ' + CORAL + ' 100%);',
        1,
    ),
    (
        'вкладки правовых документов → золото',
        r"border: '1px solid ' \+ \(on \? '#f2ebdd' : 'rgba\(242,235,221,0\.14\)'\),\n(\s*)background: on \? '#f2ebdd' : 'transparent',",
        r"border: '1px solid ' + (on ? '" + GOLD + r"' : 'rgba(242,235,221,0.14)'),\n\1background: on ? '" + GOLD + r"' : 'transparent',",
        1,
    ),
    (
        'выбранные чипы брифа → золото',
        r"\(on \? '#f2ebdd' : 'rgba\(242,235,221,0\.3\)'\),\n(\s*)background: on \? '#f2ebdd' : 'rgba\(242,235,221,0\.03\)',",
        r"(on ? '" + GOLD + r"' : 'rgba(242,235,221,0.3)'),\n\1background: on ? '" + GOLD + r"' : 'rgba(242,235,221,0.03)',",
        1,
    ),
    (
        'выделенная карточка выгоды → амбер',
        r"background: cream \? '#f2ebdd' : 'linear-gradient\(160deg, #151515, #0d0d0d\)',",
        "background: cream ? 'linear-gradient(150deg, " + GOLD + " 0%, " + AMBER + " 100%)' : 'linear-gradient(160deg, #151515, #0d0d0d)',",
        1,
    ),
    (
        'сердечки отзывов → коралл',
        r"heartFill: lk \? '#f2ebdd' : 'none',",
        "heartFill: lk ? '" + CORAL + "' : 'none',",
        2,
    ),
    (
        'точка активной услуги → золото',
        r"background: on \? CREAM : 'rgba\(242,235,221,0\.24\)',",
        "background: on ? '" + GOLD + "' : 'rgba(242,235,221,0.24)',",
        1,
    ),
    (
        'подсветка курсора → амбер',
        r"background: radial-gradient\(closest-side, rgba\(242,235,221,0\.052\)[^;]*;",
        'background: radial-gradient(closest-side, rgba(238,162,82,0.10) 0%, rgba(238,162,82,0.094) 9%, '
        'rgba(238,162,82,0.082) 18%, rgba(240,80,53,0.068) 27%, rgba(240,80,53,0.053) 36%, '
        'rgba(240,80,53,0.040) 45%, rgba(240,80,53,0.028) 54%, rgba(240,80,53,0.018) 63%, '
        'rgba(240,80,53,0.011) 72%, rgba(240,80,53,0.0055) 81%, rgba(240,80,53,0.002) 90%, '
        'rgba(240,80,53,0) 100%);',
        1,
    ),
    (
        'главная кнопка брифа → градиент коралл/амбер',
        r"border: '1\.4px solid #0a0a0a',\n(\s*)backgroundColor: INK,\n(\s*)fontFamily: 'inherit',\n(\s*)boxShadow: bh\(k\) \? '0 12px 26px rgba\(10,10,10,0\.2\)' : '0 8px 20px rgba\(10,10,10,0\.16\)',",
        r"border: '1.4px solid rgba(131,26,10,0.55)',\n\1backgroundColor: '" + CORAL + r"',\n\1backgroundImage: 'linear-gradient(118deg, #f0a24a 0%, " + CORAL + r" 54%, #d3411f 100%)',\n\2fontFamily: 'inherit',\n\3boxShadow: bh(k) ? '0 14px 30px rgba(240,80,53,0.34)' : '0 8px 22px rgba(240,80,53,0.24)',",
        1,
    ),
    (
        'светлая заливка кнопок при наведении → золото',
        re.escape('[data-sw="light"]::before { background: #f2ebdd; }'),
        '[data-sw="light"]::before { background: linear-gradient(100deg, ' + GOLD + ' 0%, ' + AMBER + ' 100%); }',
        1,
    ),
    (
        'ползунок вилки бюджета → коралл',
        r"borderRadius: '999px', background: CREAM, pointerEvents: 'none',\n(\s*)boxShadow: '0 0 0 6px rgba\(242,235,221,0\.12\), 0 8px 22px rgba\(0,0,0,0\.5\)',",
        r"borderRadius: '999px', background: '" + CORAL + r"', pointerEvents: 'none',\n\1boxShadow: '0 0 0 6px rgba(240,80,53,0.20), 0 8px 22px rgba(20,5,2,0.5)',",
        1,
    ),
    (
        'точка активного шага маршрута → золото',
        r"border: '1px solid ' \+ \(on \? CREAM : 'rgba\(242,235,221,0\.32\)'\),\n(\s*)background: on \? CREAM : '#0a0a0a',\n(\s*)boxShadow: on \? '0 0 0 5px rgba\(242,235,221,0\.09\)' : 'none',",
        r"border: '1px solid ' + (on ? '" + GOLD + r"' : 'rgba(242,235,221,0.32)'),\n\1background: on ? '" + GOLD + r"' : '#0a0a0a',\n\2boxShadow: on ? '0 0 0 5px rgba(238,162,82,0.16)' : 'none',",
        1,
    ),
]

# ─── 3. атмосфера ────────────────────────────────────────────────────────────
SCRIM_SRC = ('<div style="position: absolute; inset: 0; background: radial-gradient'
             '(78% 62% at 50% 34%, rgba(26,8,5,0.22) 0%, rgba(26,8,5,0.62) 62%, '
             'rgba(26,8,5,0.86) 100%);"></div>')

WARM_LAYER = (
    '\n    <div aria-hidden="true" style="position: absolute; inset: 0; background: '
    'radial-gradient(118% 88% at 6% -16%, rgba(240,80,53,0.26) 0%, rgba(211,119,36,0.13) 32%, rgba(26,8,5,0) 66%), '
    'radial-gradient(92% 68% at 106% 4%, rgba(238,162,82,0.15) 0%, rgba(26,8,5,0) 58%), '
    'radial-gradient(130% 96% at 50% 120%, rgba(131,26,10,0.40) 0%, rgba(26,8,5,0) 64%);"></div>'
)

# gradient map по яркости: тени садятся ровно в цвет подложки
GRADE_STOPS = [
    (0.00, BASE),
    (0.18, '#3e1208'),
    (0.42, '#873a18'),
    (0.66, '#cd7f3d'),
    (0.85, '#f0be86'),
    (1.00, '#fbf4ea'),
]
GRADE_PREFIXES = ('seqd/', 'seqm5/', 'seqdc/', 'closem5/', 'haze/')


def _rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def build_lut(stops):
    xs = [p for p, _ in stops]
    lut = []
    for ch in range(3):
        ys = [_rgb(c)[ch] for _, c in stops]
        lut += list(np.interp(np.arange(256) / 255.0, xs, ys).astype(np.uint8))
    return lut


def grade_sequences(html):
    """Тёплая цветокоррекция всех кадров секвенций внутри window.__resources."""
    lut = build_lut(GRADE_STOPS)
    head = 'window.__resources = '
    i = html.index(head) + len(head)
    j = html.index('};', i) + 1
    res = json.loads(html[i:j])

    done = 0
    for key, uri in res.items():
        if not key.startswith(GRADE_PREFIXES):
            continue
        raw = base64.b64decode(uri.split(',', 1)[1])
        src = Image.open(io.BytesIO(raw)).convert('RGB')
        lum = src.convert('L')
        out = Image.merge('RGB', (lum, lum, lum)).point(lut)
        buf = io.BytesIO()
        out.save(buf, 'WEBP', quality=80, method=5)
        res[key] = 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()
        done += 1

    print('  кадров перекрашено: %d' % done)
    return html[:i] + json.dumps(res, ensure_ascii=False) + html[j:]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    html = open(src, encoding='utf-8').read()

    print('акценты:')
    for name, pat, rep, want in ACCENTS:
        html, n = re.subn(pat, rep, html)
        assert n == want, 'акцент «%s»: %d совпадений вместо %d' % (name, n, want)
        print('  %-46s %d' % (name, n))

    print('токены:')
    for old, new in TOKENS:
        html = html.replace(old, new)
    for pat, new in SHORT_HEX:
        html = re.sub(pat, new, html)
    print('  заменено %d правил' % (len(TOKENS) + len(SHORT_HEX)))

    print('атмосфера:')
    assert html.count(SCRIM_SRC) == 1, 'не найден фоновый скрим'
    html = html.replace(SCRIM_SRC, SCRIM_SRC + WARM_LAYER)
    print('  тёплый слой свечения добавлен')
    html = grade_sequences(html)

    open(dst, 'w', encoding='utf-8').write(html)
    print('готово: %s (%.1f МБ)' % (dst, len(html.encode()) / 1e6))


if __name__ == '__main__':
    main()
