# Сторонние компоненты и данные

Весь код в этом репозитории написан командой EginAI (лицензия MIT, см. `LICENSE`).
Ниже — всё, что использовано со стороны, с лицензиями.

## Данные и модели

| Компонент | Для чего | Лицензия / условия |
|---|---|---|
| [Project-AgML/wheat_disease_detection](https://huggingface.co/datasets/Project-AgML/wheat_disease_detection) — 4156 полевых фото пшеницы, Henan Agricultural University, 2023 | обучение и тест классификатора | CC-BY-4.0. Цитирование: Qian J., Dai C., Ji Z., Liu J. GDFC-YOLO… *Agriculture* 2025, 15(14):1526 |
| Предобученные веса `efficientnet_b0.ra_in1k` (библиотека timm, обучены на ImageNet-1k) | стартовая точка для transfer learning | веса timm — Apache-2.0; данные ImageNet — условия ImageNet (некоммерческие исследования) |
| Тексты базы знаний `kb/diseases.yaml` | рекомендации | написаны командой по открытым справочникам FAO, CIMMYT, «Агроэкологический атлас» ВИЗР (ссылки в самом файле) |

## Библиотеки

| Библиотека | Лицензия |
|---|---|
| PyTorch, torchvision (только обучение) | BSD-3-Clause |
| timm (только обучение) | Apache-2.0 |
| scikit-learn, matplotlib (метрики, графики) | BSD-3-Clause, PSF-based |
| ONNX, ONNX Runtime | Apache-2.0, MIT |
| NumPy | BSD-3-Clause |
| Pillow | MIT-CMU (HPND) |
| FastAPI, Starlette, Uvicorn, Pydantic | MIT, BSD-3-Clause |
| SQLAlchemy | MIT |
| psycopg 3 | LGPL-3.0 (используется как библиотека без изменений) |
| PyYAML | MIT |
| rank-bm25 | Apache-2.0 |
| anthropic (Python SDK, опционально) | MIT |
| aiogram, httpx | MIT, BSD-3-Clause |
| React, Vite | MIT |
| Leaflet | BSD-2-Clause |
| react-leaflet | Hippocratic License 2.1 |
| PostgreSQL (Docker-образ) | PostgreSQL License |

## Шрифты и карты

| Компонент | Лицензия |
|---|---|
| Шрифт Onest (через @fontsource/onest; проверено наличие всех казахских букв) | SIL Open Font License 1.1 |
| Тайлы карты © участники OpenStreetMap | ODbL, атрибуция выводится на карте |

## Внешние сервисы

| Сервис | Когда используется |
|---|---|
| Claude API (Anthropic) | только если задан `ANTHROPIC_API_KEY`: формулирует ответ на вопрос фермера **по найденным фрагментам базы знаний**. Без ключа система полностью работает на базе знаний |
| Telegram Bot API | только если задан `BOT_TOKEN` |
| OpenStreetMap tile servers | подложка карты в браузере |
