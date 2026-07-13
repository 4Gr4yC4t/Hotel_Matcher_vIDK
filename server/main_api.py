from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from matcher import match_hotel, prepare_base
import database as db
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

    db.init_db()
    seeded = db.seed_base_hotels("01_hotels_base.csv")
    if seeded:
        logger.info("Seeded base_hotels from CSV")

    BASE_HOTELS = db.get_base_hotels()
    prepare_base(BASE_HOTELS)

    logger.info("Loaded hotels from DB: %d", len(BASE_HOTELS))

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
# ПРОВЕРКА API
# ======================================================

@app.get("/")
def home():
    return {
        "message": "Hotel matcher API works"
    }


# ======================================================
# CSV -> CSV (с сохранением в БД)
# ======================================================

@app.post("/match")
def match(file: UploadFile = File(...)):

    raw = file.file.read()
    content = raw.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(content))

    results = []

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

    upload_id = db.save_upload(file.filename, raw)
    db.update_upload_row_count(upload_id, len(results))
    db.save_results(upload_id, results)
    logger.info("Saved upload #%d (%d results) to DB", upload_id, len(results))

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
# CRUD: UPLOADS
# ======================================================

@app.get("/uploads")
def list_uploads():
    return db.list_uploads()


@app.get("/uploads/{upload_id}")
def get_upload(upload_id: int):
    upload = db.get_upload(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


@app.get("/uploads/{upload_id}/download")
def download_upload(upload_id: int):
    content = db.get_upload_content(upload_id)
    if not content:
        raise HTTPException(status_code=404, detail="Upload not found")
    upload = db.get_upload(upload_id)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename={upload["filename"]}'
        },
    )


@app.get("/uploads/{upload_id}/results")
def get_results(upload_id: int):
    upload = db.get_upload(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return db.get_results(upload_id)


@app.get("/uploads/{upload_id}/results/download")
def download_results(upload_id: int):
    upload = db.get_upload(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    results = db.get_results(upload_id)
    if not results:
        raise HTTPException(status_code=404, detail="No results for this upload")

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["hotel_id", "duplicate_hotel_id", "score"],
    )
    writer.writeheader()
    writer.writerows(results)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename=matches.csv'
        },
    )


@app.delete("/uploads/{upload_id}")
def delete_upload(upload_id: int):
    deleted = db.delete_upload(upload_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Upload not found")
    return {"detail": f"Upload {upload_id} deleted"}


# ======================================================
# CRUD: BASE HOTELS
# ======================================================

@app.get("/base-hotels")
def list_base_hotels():
    return db.get_base_hotels()


@app.post("/base-hotels")
def upload_base_hotels(file: UploadFile = File(...)):
    global BASE_HOTELS
    raw = file.file.read()
    count = db.replace_base_hotels(raw)
    BASE_HOTELS = db.get_base_hotels()
    prepare_base(BASE_HOTELS)
    logger.info("Replaced base hotels: %d loaded", count)
    return {"detail": f"Base hotels replaced: {count} records loaded"}


@app.delete("/base-hotels/{hotel_id}")
def delete_base_hotel(hotel_id: str):
    global BASE_HOTELS
    deleted = db.delete_base_hotel(hotel_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Hotel not found")
    BASE_HOTELS = db.get_base_hotels()
    prepare_base(BASE_HOTELS)
    return {"detail": f"Hotel {hotel_id} deleted"}


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
