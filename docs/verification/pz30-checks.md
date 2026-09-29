# Протокол ПЗ30 — 29.09.2026

Це резюме фактично виконаних перевірок за інструментальними результатами поточної сесії, не сирий stdout.

- Django test suite:32 tests,OK.
- Node test suite:22 tests,22pass,0fail.
- tools/check_integration.py з окремим шляхом артефакту:26успішних операцій,10очікуваних помилок; ізольована тестова БД.
- IAB/admin + Safari/mechanic:ST-0005 від приймання до видачі,всі7статусів,1500грн,діагностика/коментарі/історія/reload.
- IAB390×844:коментар/фільтр/вихід; document.scrollWidth=390.
- Неправильний пароль:форма входу + alert,без входу.
- BUG006:latency1500мс→відкрити з історії→закрити→після завершення loadingfalse,openDialogs0.
- BUG007:offline→відкрити з історії→alert в dialog. Повернуто online/latency0.
- BUG005:backup старої демобази;dry-run4;apply4. Два тести перевіряють scope,idempotence,collision rollback.
- Тільки вигадані дані. Браузерна база окрема від звичайного локального демо.
- Знімки:docs/images/pz30-{delivered,safari,mobile,network-error}.png.
- UAT добровольців і незалежне review не виконувалися.
