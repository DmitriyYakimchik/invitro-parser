# Invitro Parser

Скрипт для парсинга анализов с сайта [invitro.ru](https://www.invitro.ru/).
Работает асинхронно через `aiohttp`, поддерживает выбор города и сохранение результатов.

---

## Возможности
- Асинхронные запросы (`aiohttp`)
- Определение slug для города
- Кэширование slug в `city_slugs_cache.json`
- Очистка текста и безопасные имена листов для Excel
- Настройка количества потоков и таймаута
- Логирование вместо `print()`

---

## Установка и запуск через uv

Клонируем проект и устанавливаем зависимости:

```bash

git clone https://github.com/yourname/invitro-parser.git
cd invitro-parser

uv sync
```

---
Запуск:

```bash

uv run python main.py --cities cities.txt
```

Пример с полным набором аргументов:

```bash

uv run python main.py \
  --cities cities.txt \
  --output results.xlsx \
  --workers 40 \
  --limit 0 \
  --retries 3 \
  --timeout 60 \
  --backoff 1.0
```

## Параметры запуска


- `--cities` — путь к файлу со списком городов (по одному в строке). По умолчанию: `cities.txt`.
- `--output` — имя выходного файла (Excel). По умолчанию: `results.xlsx`.
- `--workers` — максимальное количество одновременных запросов. По умолчанию: `40`.
- `--limit` — максимальное число анализов на город (0 = все). По умолчанию: `0`.
- `--retries` — число попыток при временных ошибках. По умолчанию: `3`.
- `--timeout` — общий таймаут запроса в секундах. По умолчанию: `60`.
- `--backoff` — базовое время ожидания между повторными попытками. По умолчанию: `1.0`.

---

## Описание ключевых файлов

**main.py**
Точка входа: парсит аргументы командной строки, читает файл со списком городов и запускает `AsyncInvitroParser`

**async_invitro_parser.py**
Основной асинхронный контроллер:
- класс `AsyncInvitroParser` (создание сессии, сбор ссылок по городу, параллельный сбор страниц, формирование Excel)
- включает методы: `create_session`, `close_session`, `fetch`, `load_city_slugs_from_site`, `collect_analysis_links`, `fetch_analysis_data`, `process_city`, `run`

**invitro_parser.py**
Парсер одной страницы анализа: функция `parse_analysis_page(html, url)`, возвращает словарь с колонками:
Категория, Подкатегория, Название анализа, Код анализа во внутренней системе Invitro, Код анализа по номенклатуре МЗ РФ (если есть), Срок выполнения анализа, Стоимость анализа

**utils.py**
Вспомогательные функции:
- `load_city_slugs_cache()` — загрузка кэша slug'ов городов из `city_slugs_cache.json`.
- `save_city_slugs_cache(cache)` — сохранение кэша в файл.
- `get_city_slug()` / `build_city_url()` — получение slug и построение URL для города
- `clean_text()` — очистка текста.
- `make_safe_sheet_name()` — формирование безопасного имени листа Excel (<=31 символ)
- `parse_city_slugs()` — извлечение slug'ов городов из HTML.

**constants.py**
Константы проекта: `BASE`, `BASE_HOST`, `CITY_SLUGS_CACHE_FILE`, `CITY_SLUGS` (готовые соответствия названий городов), `COLS` (список колонок для Excel)

**cities.txt**
Файл со списком городов (по одному городу в строке). Пример: `Москва`

**city_slugs_cache.json**
Кэш соответствия названий городов → slug

**results.xlsx**
Файл с итоговыми результатами

---

## Примеры

Запуск для всех городов из `cities.txt`:

```bash

uv run python main.py --cities cities.txt --output results.xlsx
```

Запуск с ограничением (первые 50 анализов на город):

```bash

uv run python main.py --cities cities.txt --limit 50 --workers 20
```
