# Hotel Matcher API

Сервис на FastAPI для сопоставления внешних данных об отелях с эталонной базой отелей. Использует **нечёткое сравнение названий** (с транслитерацией кириллицы) и **географическую близость** (формула гаверсинусов). Все загрузки и результаты сохраняются в **SQLite**-базу данных.

## Как это работает

1. При запуске инициализируется SQLite-база (`data/hotel_matcher.db`).
2. Если база пуста, эталонные отели загружаются из `01_hotels_base.csv` (1000 отелей).
3. Имена всех базовых отелей предобрабатываются один раз при старте (транслитерация + lowercase).
4. Пользователь отправляет POST-запрос на `/match` с CSV-файлом внешних отелей.
5. Для каждого внешнего отеля:
   - Быстрый фильтр по bounding box.
   - Расчёт расстояния через формулу гаверсинусов (радиус — 3 км).
   - Сравнение имён через `SequenceMatcher`.
   - Итоговая оценка: **0.7 × текстовое сходство + 0.3 × географическое сходство**.
6. Загрузка и результаты сохраняются в БД, CSV возвращается клиенту.

## Быстрый старт

### Установка и запуск

```bash
pip install -r requirements.txt
uvicorn main_api:app --host 0.0.0.0 --port 8000
```

Или:

```bash
python main_api.py
```

### Docker

```bash
docker build -t hotel-matcher .
docker run -p 8000:8000 hotel-matcher
```

### Проверка

```bash
curl http://localhost:8000/
# {"message": "Hotel matcher API works"}
```

### Пример использования

```bash
# Отправка CSV на сопоставление
curl -X POST http://localhost:8000/match \
  -F "file=@external_hotels.csv" \
  -o matches.csv

# Список загрузок
curl http://localhost:8000/uploads

# Результаты конкретной загрузки
curl http://localhost:8000/uploads/1/results

# Скачать результаты
curl http://localhost:8000/uploads/1/results/download -o results.csv

# Скачать оригинальный файл
curl http://localhost:8000/uploads/1/download

# Заменить базу отелей
curl -X POST http://localhost:8000/base-hotels \
  -F "file=@new_base.csv"

# Удалить отель из базы
curl -X DELETE http://localhost:8000/base-hotels/5501
```

## Структура проекта

```
├── main_api.py            # Точка входа FastAPI + CRUD-эндпоинты
├── matcher.py             # Логика сопоставления (транслитерация, similarity, haversine, prepare_base)
├── database.py            # SQLite: init, seed, CRUD-операции
├── 01_hotels_base.csv     # Эталонная база отелей (1000 шт.)
├── requirements.txt       # Зависимости
├── Dockerfile             # Docker-образ
└── README.md              # Документация
```

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Health check |
| POST | `/match` | Загрузить CSV → получить CSV с совпадениями (сохраняется в БД) |
| GET | `/uploads` | Список всех загрузок |
| GET | `/uploads/{id}` | Метаданные загрузки |
| GET | `/uploads/{id}/download` | Скачать оригинальный CSV |
| GET | `/uploads/{id}/results` | Результаты сопоставления (JSON) |
| GET | `/uploads/{id}/results/download` | Скачать результаты как CSV |
| DELETE | `/uploads/{id}` | Удалить загрузку и результаты |
| GET | `/base-hotels` | Список всех отелей базы |
| POST | `/base-hotels` | Заменить базу CSV-файлом |
| DELETE | `/base-hotels/{hotel_id}` | Удалить один отель |

### Время обработки

Каждый ответ сервера содержит заголовок `X-Processing-Time-Ms` — время обработки запроса в миллисекундах.

```bash
curl -v -X POST http://localhost:8000/match \
  -F "file=@external_hotels.csv" \
  -o matches.csv
# В заголовках ответа: < X-Processing-Time-Ms: 13.53
```

## Технологии

- **Python 3.14**
- **FastAPI** — веб-фреймворк
- **Uvicorn** — ASGI-сервер
- **SQLite** — файловая база данных (встроенная в Python)
- **difflib.SequenceMatcher** — нечёткое сравнение строк
- **Docker** — контейнеризация

### Оптимизация

При запуске сервера имена всех базовых отелей предобрабатываются один раз через `prepare_base()` (транслитерация + lowercase). В каждом запросе внешнее имя тоже обрабатывается один раз. Это исключает повторную транслитерацию на каждой итерации цикла.

### База данных

SQLite-база хранится в `data/hotel_matcher.db` (создаётся автоматически при первом запуске). В Docker-окружении данные сохраняются в томе `hotel-db-data`. База содержит три таблицы:

- `base_hotels` — эталонные отели (из CSV или загруженные через API)
- `uploads` — загруженные CSV-файлы (хранится оригинальное содержимое)
- `match_results` — результаты сопоставления, привязанные к загрузке
