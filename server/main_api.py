from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from matcher import match_hotel, prepare_base
import csv
import io
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


BASE_HOTELS = None


@asynccontextmanager
async def lifespan(app: FastAPI):

    global BASE_HOTELS

    BASE_HOTELS = load_base_hotels(
        "01_hotels_base.csv"
    )

    prepare_base(BASE_HOTELS)

    print(f"Loaded hotels: {len(BASE_HOTELS)}")

    yield


app = FastAPI(lifespan=lifespan)


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Processing-Time-Ms"] = str(elapsed_ms)
        return response


app.add_middleware(TimingMiddleware)


# ======================================================
# ЗАГРУЗКА НАШЕЙ БАЗЫ
# ======================================================

def load_base_hotels(filename):

    with open(filename, encoding="utf-8-sig") as f:
        hotels = list(csv.DictReader(f))

    for hotel in hotels:
        hotel["lat"] = float(hotel["lat"])
        hotel["lon"] = float(hotel["lon"])

    return hotels






# ======================================================
# ПРОВЕРКА API
# ======================================================

@app.get("/")
def home():
    return {
        "message": "Hotel matcher API works"
    }



# ======================================================
# CSV -> CSV
# ======================================================

@app.post("/match")
def match(file: UploadFile = File(...)):

    # читаем загруженный CSV

    content = file.file.read().decode("utf-8-sig")

    reader = csv.DictReader(
        io.StringIO(content)
    )


    results = []


    # обработка каждого внешнего отеля

    for external_hotel in reader:

        try:

            if "hotel_id" not in external_hotel:
                external_hotel["hotel_id"] = external_hotel["id"]

            eid = external_hotel.get("hotel_id")
            if not eid or not eid.strip():
                logger.warning("Skipping row: empty hotel_id")
                results.append({
                    "hotel_id": None,
                    "duplicate_hotel_id": None,
                    "score": 0
                })
                continue

            external_hotel["lat"] = float(
                external_hotel["lat"]
            )

            external_hotel["lon"] = float(
                external_hotel["lon"]
            )

        except (ValueError, TypeError, KeyError) as e:
            logger.warning(
                "Skipping row external_id=%s: %s",
                external_hotel.get("hotel_id"),
                e
            )
            results.append({
                "hotel_id": external_hotel.get("hotel_id"),
                "duplicate_hotel_id": None,
                "score": 0
            })
            continue


        result = match_hotel(
            external_hotel,
            BASE_HOTELS
        )


        results.append(result)



    # создаём CSV ответ

    output = io.StringIO()


    writer = csv.DictWriter(
        output,
        fieldnames=[
            "hotel_id",
            "duplicate_hotel_id",
            "score"
        ]
    )


    writer.writeheader()
    writer.writerows(results)


    output.seek(0)



    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=matches.csv"
        }
    )



# ======================================================
# ЗАПУСК
# ======================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )