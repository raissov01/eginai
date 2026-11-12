# Боли пользователей аналогов → что EginAI делает иначе

Основа: 77 отзывов из 5 источников (Plantix — Google Play; Agrio — Google Play и App Store; Farmonaut — App Store и Google Play), собраны 12.11.2026. Цитаты и ссылки — в `reviews.md` (коды P*, A*, F*).
Перекос выборки: в основном 1★ (так и задумано: ищем боли); пользователи — Индия/США/садоводы, а не зерновые хозяйства Казахстана. Reddit прочитать не удалось.
«Тонкая» тема = меньше 3 отзывов или один источник. Такие темы не выдаём за тренд.

## 1. Что ненавидят (ранжировано)

| # | Боль | Отзывов | Источников | Примеры |
| --- | --- | --- | --- | --- |
| 1 | ИИ не узнаёт болезнь, ошибается или отвечает «не знаю, спросите сообщество» | 16 | 3 (Plantix GP, Agrio GP, Agrio AS) | P1: "it either says, “Plantix doesn’t know this disease,” “Unable to detect the disease,” or asks me to consult the community"; P3 (265 «полезно»): "it shows anthracnose, thrips problem even powdery mildew but never once alternaria spot"; A8: "the foto clearly showing its a scale insect, but the diagnosis said it's mite" |
| 2 | Реклама, пейволл, подписка, непонятные списания | 11 | 2 (только Agrio, GP + AS) | A19: "there is no way to use the free version of it, since the ad has no close button"; A7: "spammed with malicious ads attempting to get me to "activate my account" using a Google account phishing page" |
| 3 | Нужной культуры нет в списке | 8 | 2 продукта | P21 (227 «полезно»): "I was a bit disappointed when I saw how limited the crop options were"; A1 (111): "Tomatoes aren't even on the list it offered" |
| 4 | «Спросите эксперта» — а эксперт не отвечает или отвечает только платным | 5 | 3 | A17: "I see once in a while an expert would respond to someone else’s post. I bet that’s because that person paid for the app."; A5: "It has now been a week since I sent the second query and so far no response." |
| 5 | Фото отклоняется как «размытое/далеко», нужен топовый телефон | 3 | 1 (Plantix) — **тонкая по источникам**, но 478 «полезно» у P2 | P2: "the application for each photo says that it is not right, that it does not look good, that you need to focus and similar nonsense"; P6: "the app isn't friendly to phones aren't the absolute newest with the best camera" |
| 6 | Трение на входе: регистрация, контур поля, логин | 3 | 3 | F1: "App doesn’t even allow me to do the first step which is to make “my field”"; P17: "Unable to sign in and send query" |
| 7 | Нельзя оспорить диагноз | 1 | 1 — **тонкая** | A16: "you don’t seem to get an option to disagree with a “diagnosis”" |
| 8 | Совет = торговые марки без действующего вещества | 1 | 1 — **тонкая** | P5: "Currently it only shows product with name of manufacturer which sometimes does not include chemical name clearly" |
| 9 | Долгая обработка фото | 1 | 1 — **тонкая** | A18: "‘processing my image’ for 23 minutes so far" |

Контекст, не из отзывов: собственный тест Plantix с CABI — верный диагноз в ~51% из 900 фото (https://blog.plantwise.org/2020/06/19/teaching-an-app-to-help-farmers/).

## 2. Чего не хватает (запросы своими словами)

| Запрос | Отзывов | Цитата |
| --- | --- | --- |
| Больше культур / ввод своей культуры | 8 | A15: "let the user manually key in the plant species itself, as not every plant type is listed" |
| Офлайн-доступ | 1 (**тонкая**, но 532 «полезно» — максимум в выборке) | P4: "There should be an option to use it's contents offline,like bookmarking or else." |
| Действующее вещество в совете | 1 | P5: "If possible, please include chemical" |
| Местные единицы измерения | 1 | P14: "Please add scale measurement as per local or statewise" |
| Оповещения о грибных болезнях с мерами защиты | 1 | A22: "if you start sending advance intelligence inputs regarding pest attack and fungal attack with counter measures,it will be great useful." |
| Несколько полей бесплатно | 1 (единственный RU-отзыв) | A21: "можно добавлять только одно поле а не несколько а за это надо покупать подписку" |

Позитив, который надо сохранить: скорость и простота (P22, F5), родной язык (P23, F4: "multi-language support is game changer").

## 3. Что не решено никем (позиционирование)

1. **Казахский язык.** Plantix — 19 языков, казахского не найдено; Agrio — только EN (App Store); DoctorP — EN/RU; PlantVillage+ — EN/FR/HI/SW/TW. Ни одного продукта с kk.
2. **Зерновые Северного Казахстана.** Глобальные приложения сделаны под Индию/Африку/огород. У Plantix полная библиотека болезней пшеницы, но нет страницы ячменя (404). DoctorP: пшеница есть, ячмень «в планах на 2023». В Казахстане — только исследования (Павлодар, гиперспектр) и спутник/дроны (Agroscope); фото-диагностики листа нет.
3. **Публичная карта очагов по районам.** Plantix и Agrio шлют push «в вашем районе», xarvio имел «радар» соседей — приложение снято из App Store. Открытой карты очагов, которую видят фермер, агроном района и акимат, не нашли ни у кого.
4. **Telegram без установки.** Ни один аналог не работает в Telegram (у Plantix был WhatsApp-бот — P8 ругает его ответы «I am sorry, but I am not sure»). Telegram-боты по болезням пшеницы в РФ — исследовательские прототипы.

## 4. План исправлений для EginAI (доказательность × дешевизна)

| # | Что делаем | Против какой боли | Размер | Доказательства |
| --- | --- | --- | --- | --- |
| 1 | Узкий фокус: только пшеница (ячмень — этап 2), только болезни, важные для СКО/Акмолы/Костаная/Павлодара; явный ответ «это не пшеница / не листовая болезнь» вместо выдуманного диагноза | #1 (16 отз., 3 ист.) | M | P1, P3, A8, A9 |
| 2 | Честная неопределённость: топ-3 с уверенностью, порог отказа, тепловая карта CAM «где признаки», кнопка «не согласен» → пометка для дообучения | #1, #7 | S | A16, P8 |
| 3 | Бесплатно, без рекламы, без регистрации: Telegram ID вместо аккаунта, без контура поля | #2 (11/2), #6 (3/3) | S | A19, A7, F1, P17 |
| 4 | Нет «спросите сообщество»: при низкой уверенности — чек-лист признаков kk/ru + контакт районной фитосанитарной службы, а не платный эксперт | #4 (5/3) | S | A5, A17 |
| 5 | Мягкая проверка фото: подсказка, как переснять, но фото всё равно анализируется; сжатие на клиенте, CPU-инференс ≤ 5 с | #5, #9 | S | P2, P6, A18 |
| 6 | Совет с действующим веществом и нормой, ссылка на казахстанский список разрешённых пестицидов; без продажи брендов | #8 | S | P5 |
| 7 | Карта очагов по районам: с согласия, координаты округлены до ~1 км, фото не хранятся; агрегирование по району и неделе | раздел 3.3; запрос A22 | M | A22; отсутствие у аналогов |
| 8 | Интерфейс kk по умолчанию + ru; гектары | раздел 3.1; P14, P23, F4 | S | P23, F4 |

Не берём (вне ядра): спутниковый NDVI (Farmonaut, Agrio), калькуляторы прибыли (P19), сообщество экспертов.

## 5. Угол позиционирования

**A (рекомендуем).** Для фермера Северного Казахстана, которому глобальные «доктора растений» отвечают «не знаю, спросите сообщество» и показывают рекламу, EginAI за 5 секунд в Telegram называет болезнь пшеницы на казахском или русском, показывает, где на листе признаки, и честно говорит, когда не уверен.
Доказательства: тема #1 — 16 отзывов, 3 источника; тема #2 — 11 отзывов, 2 источника; казахского языка нет ни у одного аналога.

**B.** Для района и акимата, которые узнают о вспышке ржавчины слишком поздно, EginAI собирает анонимные сигналы фермеров в публичную карту очагов по районам.
Доказательства: запрос A22 (тонкий), push-оповещения у Plantix/Agrio без публичной карты, xarvio «радар» снят.

**C.** Для агронома, которому нужны действующее вещество и норма, а не реклама бренда, EginAI даёт совет по казахстанскому списку разрешённых пестицидов.
Доказательства: P5 (тонкая), дилерские модели Cropwise/xarvio.

Рекомендация: A как главный, B как второй слайд («что получает регион»). Названия аналогов в названии и рекламе EginAI не использовать; сравнительную таблицу в отчёте давать фактами со ссылками.
