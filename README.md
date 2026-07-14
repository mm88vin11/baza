# БАЗА — lllbaza.ru

Одностраничный лендинг digital-студии **БАЗА** (сайты, приложения, Telegram-боты).
Single self-contained landing page for the **БАЗА** studio. Russian + English.

## Что внутри / What's inside

- **`index.html`** — весь сайт в одном файле: инлайн-CSS + JS, библиотеки с CDN (`defer`).
  Everything in one file: inlined critical CSS + JS, libraries loaded from CDN.
- **`og.png`** — превью для соцсетей 1200×630 (Open Graph / Twitter).

## Возможности / Features

- 🌍 **RU / EN** — переключатель языка в шапке (кнопки RU·EN), контент через `data-ru` / `data-en`.
- ⏳ **Реальный прелоадер** — считает загрузку картинок и шрифтов (`Promise.all`), логотип `///`
  «улетает» в навигацию через GSAP Flip, без FOUC.
- ✨ **Анимации** — GSAP 3.13 (ScrollTrigger, Flip, SplitText) + Lenis (плавный скролл),
  магнитные кнопки, кастомный курсор, WebGL-подобное поле частиц в hero.
- 📈 **Мультишаговая форма-бриф** — тип → бюджет → сроки → контакты, отправка через `mailto:`.
- 🔎 **SEO** — title/description, Open Graph, Twitter Card, JSON-LD (`Organization`/`WebSite`/`Service`),
  canonical, favicon (инлайн SVG).
- ♿ **Доступность** — уважает `prefers-reduced-motion`, курсор/магнит отключены на touch,
  плавный скролл выключается на мобильных.
- 🛟 **Отказоустойчивость** — если CDN/скрипты не загрузились, контент всё равно показывается
  (fallback + таймаут-предохранитель).

## Что заменить перед запуском / Before going live

- Контакты: `hello@lllbaza.ru`, `t.me/lllbaza`, `vk.com/lllbaza` (в шапке, форме, футере, JSON-LD).
- Кейсы в блоке «Работы» — на реальные проекты и метрики.
- Отзыв в блоке «Отзыв».
- При желании — подключить реальный бэкенд/PHP-обработчик формы вместо `mailto:`.

## Деплой на reg.ru / Deploy

1. Загрузите `index.html` и `og.png` в корень сайта (`public_html`) через файловый
   менеджер панели (ispmanager / cPanel / Plesk) или по FTP.
2. Удалите файлы «парковочной» страницы.
3. Статический HTML отдаётся как есть — PHP/БД не нужны.

> Версии библиотек (GSAP 3.13.0, Lenis 1.3.11) закреплены в CDN-ссылках.
> Для продакшена можно добавить SRI-хэши (`integrity`) к `<script>`.
