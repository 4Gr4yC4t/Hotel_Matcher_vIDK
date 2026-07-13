# Hotel Matcher — объединённый проект

Сопоставление внешних данных об отелях с эталонной базой с помощью нечёткого сравнения названий (транслитерация + SequenceMatcher) и географической близости (формула гаверсинусов). База: 1000 отелей, внешний файл: 1008 записей (1000 валидных + 8 битых для тестирования обработки ошибок).

Все загрузки и результаты сохраняются в SQLite-базу данных и доступны через API.

## Структура

```
hotel-deduplicator2/
├── docker-compose.yml        # Оркестрация server + client
├── server/                   # FastAPI-сервер
│   ├── Dockerfile
│   ├── main_api.py           # Точка входа API + CRUD-эндпоинты
│   ├── matcher.py            # Логика сопоставления (prepare_base, haversine, similarity)
│   ├── database.py           # SQLite: инициализация, CRUD-операции
│   ├── 01_hotels_base.csv    # Эталонная база (1000 отелей, используется для начального заполнения БД)
│   ├── requirements.txt
│   └── README.md
├── client/                   # Тестовый клиент
│   ├── Dockerfile
│   ├── test.py               # Отправляет CSV и сохраняет результат
│   ├── 01_hotels_external.csv
│   ├── requirements.txt
│   └── README.md
└── output/
    └── matches.csv           # Результат сопоставления
```

## Быстрый старт (Docker)

### Предварительные требования

- Установленный Docker

### Сборка и запуск

```bash
docker compose up --abort-on-container-exit
```

Что происходит:
1. Собираются два образа: `server` (FastAPI на порту 8000) и `client` (тестовый скрипт).
2. `server` запускается, инициализирует SQLite-базу (`data/hotel_matcher.db`), заполняет её из `01_hotels_base.csv` и загружает отели в память.
3. `client` отправляет `01_hotels_external.csv` на `/match`.
4. Результаты и загрузка сохраняются в БД.
5. Результат сохраняется также в `output/matches.csv`.

Данные БД сохраняются в Docker-томе `hotel-db-data` и переживают перезапуск контейнера.

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Health check |
| POST | `/match` | Загрузить CSV → получить CSV с совпадениями (сохраняется в БД) |
| GET | `/uploads` | Список всех загрузок |
| GET | `/uploads/{id}` | Метаданные загрузки |
| GET | `/uploads/{id}/download` | Скачать оригинальный CSV загрузки |
| GET | `/uploads/{id}/results` | Результаты сопоставления (JSON) |
| GET | `/uploads/{id}/results/download` | Скачать результаты как CSV |
| DELETE | `/uploads/{id}` | Удалить загрузку и её результаты |
| GET | `/base-hotels` | Список всех отелей базы |
| POST | `/base-hotels` | Заменить базу отелей CSV-файлом |
| DELETE | `/base-hotels/{hotel_id}` | Удалить один отель из базы |

Каждый ответ содержит заголовок `X-Processing-Time-Ms` — время обработки запроса в миллисекундах.

```bash
# Health check
curl http://localhost:8000/

# Отправка файла (результат автоматически сохраняется в БД)
curl -X POST http://localhost:8000/match \
  -F "file=@my_hotels.csv" \
  -o matches.csv

# Список загрузок
curl http://localhost:8000/uploads

# Скачать результаты прошлой загрузки
curl http://localhost:8000/uploads/1/results/download -o results.csv

# Заменить базу отелей
curl -X POST http://localhost:8000/base-hotels \
  -F "file=@new_base.csv"
```
