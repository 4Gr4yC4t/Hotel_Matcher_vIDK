import sqlite3
import os
import csv
import io

DB_PATH = os.environ.get("DATABASE_PATH", "data/hotel_matcher.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS base_hotels (
        hotel_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        city_id TEXT,
        lat REAL,
        lon REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        raw_content BLOB NOT NULL,
        row_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS match_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        upload_id INTEGER,
        hotel_id TEXT,
        duplicate_hotel_id TEXT,
        score REAL,
        FOREIGN KEY (upload_id) REFERENCES uploads (id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()


def seed_base_hotels(csv_path):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM base_hotels")
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return False

    if not os.path.exists(csv_path):
        conn.close()
        return False

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cursor.execute(
                    "INSERT OR REPLACE INTO base_hotels (hotel_id, name, city_id, lat, lon) VALUES (?, ?, ?, ?, ?)",
                    (row["hotel_id"], row["name"], row.get("city_id"), float(row["lat"]), float(row["lon"]))
                )
            except (ValueError, KeyError, TypeError):
                continue

    conn.commit()
    conn.close()
    return True


def get_base_hotels():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT hotel_id, name, city_id, lat, lon FROM base_hotels")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_upload(filename, raw_bytes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO uploads (filename, raw_content) VALUES (?, ?)",
        (filename, raw_bytes)
    )
    upload_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return upload_id


def update_upload_row_count(upload_id, row_count):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE uploads SET row_count = ? WHERE id = ?",
        (row_count, upload_id)
    )
    conn.commit()
    conn.close()


def save_results(upload_id, results):
    conn = get_connection()
    cursor = conn.cursor()
    for res in results:
        cursor.execute(
            "INSERT INTO match_results (upload_id, hotel_id, duplicate_hotel_id, score) VALUES (?, ?, ?, ?)",
            (upload_id, res.get("hotel_id"), res.get("duplicate_hotel_id"), res.get("score"))
        )
    conn.commit()
    conn.close()


def list_uploads():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, row_count, created_at FROM uploads ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_upload(upload_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, row_count, created_at FROM uploads WHERE id = ?", (upload_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_upload_content(upload_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT raw_content FROM uploads WHERE id = ?", (upload_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def get_results(upload_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT hotel_id, duplicate_hotel_id, score FROM match_results WHERE upload_id = ?", (upload_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_upload(upload_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM uploads WHERE id = ?", (upload_id,))
    if not cursor.fetchone():
        conn.close()
        return False
    cursor.execute("DELETE FROM match_results WHERE upload_id = ?", (upload_id,))
    cursor.execute("DELETE FROM uploads WHERE id = ?", (upload_id,))
    conn.commit()
    conn.close()
    return True


def replace_base_hotels(raw_csv_bytes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM base_hotels")

    content = raw_csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    count = 0
    for row in reader:
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO base_hotels (hotel_id, name, city_id, lat, lon) VALUES (?, ?, ?, ?, ?)",
                (row["hotel_id"], row["name"], row.get("city_id"), float(row["lat"]), float(row["lon"]))
            )
            count += 1
        except (ValueError, KeyError, TypeError):
            continue

    conn.commit()
    conn.close()
    return count


def delete_base_hotel(hotel_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT hotel_id FROM base_hotels WHERE hotel_id = ?", (hotel_id,))
    if not cursor.fetchone():
        conn.close()
        return False
    cursor.execute("DELETE FROM base_hotels WHERE hotel_id = ?", (hotel_id,))
    conn.commit()
    conn.close()
    return True