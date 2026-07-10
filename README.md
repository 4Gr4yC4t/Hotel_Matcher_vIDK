# Hotel Matcher — объединённый проект

Сопоставление внешних данных об отелях с эталонной базой с помощью нечёткого сравнения названий (транслитерация + SequenceMatcher) и географической близости (формула гаверсинусов). База: 1000 отелей, внешний файл: 1008 записей (1000 валидных + 8 битых для тестирования обработки ошибок).

## Структура

```
hotel-deduplicator-main/
├── docker-compose.yml        # Оркестрация server + client
├── server/                   # FastAPI-сервер
│   ├── Dockerfile
│   ├── main_api.py           # Точка входа API
│   ├── matcher.py            # Логика сопоставления (prepare_base, haversine, similarity)
│   ├── 01_hotels_base.csv    # Эталонная база (1000 отелей)
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
2. `server` запускается первым, проходит health check, загружает 1000 отелей и предобрабатывает их имена.
3. `client` отправляет `01_hotels_external.csv` на `/match`.
4. Выводит время обработки сервером.
5. Результат сохраняется в `output/matches.csv`.

### Результат

```csv
external_id,hotel_id,score
E1001,5001,0.865
E1002,5002,0.977
E1003,5003,0.969
...
E_BAD1,,0
```

## API (сервер)

| Метод | Путь      | Описание                        |
|-------|-----------|---------------------------------|
| GET   | `/`       | Health check                    |
| POST  | `/match`  | Загрузить CSV → получить CSV с совпадениями |

Каждый ответ содержит заголовок `X-Processing-Time-Ms` — время обработки запроса в миллисекундах.

```bash
# Health check
curl http://localhost:8000/

# Отправка своего файла
curl -X POST http://localhost:8000/match \
  -F "file=@my_hotels.csv" \
  -o matches.csv
```
