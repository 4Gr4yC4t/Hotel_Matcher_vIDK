import requests
import os
import time
import csv
import io
from difflib import SequenceMatcher
from shared.utils import clean_name, haversine


url = os.environ.get("SERVER_URL", "http://127.0.0.1:8000/match")
health_url = url.replace("/match", "/")
base_url = url.replace("/match", "")

url = os.environ.get("SERVER_URL", "http://127.0.0.1:8000/match")
health_url = url.replace("/match", "/")
base_url = url.replace("/match", "")

for i in range(30):
    try:
        r = requests.get(health_url, timeout=3)
        if r.status_code == 200:
            break
    except requests.ConnectionError:
        pass
    print(f"Ожидание сервера... попытка {i + 1}")
    time.sleep(2)

print("\n--- Отправка основного файла отелей ---")
with open("datainput/01_hotels_external.csv", "rb") as file:
    response = requests.post(url, files={"file": file})

processing_time = response.headers.get("X-Processing-Time-Ms", "N/A")
print(f"Время обработки основного файла на сервере: {processing_time} мс")

path = "output/"
os.makedirs(path, exist_ok=True)

with open("output/matches.csv", "wb") as result_file:
    result_file.write(response.content)
print("Основной файл matches.csv сохранён в output/matches.csv")

# ======================================================
# ЗАПУСК ТЕСТОВ (PRECISION / RECALL)
# ======================================================

test_base_path = "datainput/01_hotels_base_10.csv"
test_ext_path = "datainput/01_hotels_external_10.csv"
expected_path = "datainput/01_expected_matches.csv"

if os.path.exists(test_base_path) and os.path.exists(test_ext_path) and os.path.exists(expected_path):
    print("\n--- Запуск тестов качества сопоставления ---")

    # 1. Резервное копирование текущей базы данных отелей
    original_base = []
    try:
        backup_res = requests.get(f"{base_url}/base-hotels")
        if backup_res.status_code == 200:
            original_base = backup_res.json()
            print(f"Бэкап текущей базы сохранён ({len(original_base)} отелей)")
    except Exception as e:
        print(f"Ошибка бэкапа базы: {e}")

    # 2. Переопределение тестовой базы (10 отелей)
    try:
        with open(test_base_path, "rb") as bf:
            requests.post(f"{base_url}/base-hotels", files={"file": bf})
        print("База данных временно переопределена тестовым набором.")
    except Exception as e:
        print(f"Не удалось загрузить тестовую базу: {e}")

    # 3. Отправка тестовых отелей на сопоставление
    actual_results = {}
    try:
        with open(test_ext_path, "rb") as ef:
            res = requests.post(url, files={"file": ef})
            if res.status_code == 200:
                reader = csv.DictReader(io.StringIO(res.text))
                for row in reader:
                    actual_results[row["hotel_id"]] = row.get("duplicate_hotel_id") or None
    except Exception as e:
        print(f"Ошибка сопоставления тестовых отелей: {e}")

    # 4. Подгрузка метаданных для формирования отчёта
    base_hotels = {}
    with open(test_base_path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            base_hotels[row["hotel_id"]] = {
                "name": row["name"], "lat": float(row["lat"]), "lon": float(row["lon"])
            }

    external_hotels = {}
    with open(test_ext_path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            external_hotels[row["external_id"]] = {
                "name": row["name"], "lat": float(row["lat"]), "lon": float(row["lon"])
            }

    expected_matches = {}
    with open(expected_path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            expected_matches[row["external_id"]] = {
                "expected_id": row["expected_hotel_id"], "comment": row["comment"]
            }

    # Сравнение результатов
    tp, fp, fn = 0, 0, 0
    report = []
    report.append("=" * 80)
    report.append("ОТЧЁТ ПО ТЕСТИРОВАНИЮ КАЧЕСТВА МАТЧИНГА")
    report.append("=" * 80)

    for ext_id, expected_data in expected_matches.items():
        expected_id = expected_data["expected_id"]
        comment = expected_data["comment"]
        actual_id = actual_results.get(ext_id)

        ext_hotel = external_hotels.get(ext_id, {})
        ext_name = ext_hotel.get("name", "N/A")

        expected_name = base_hotels.get(expected_id, {}).get("name", "N/A") if expected_id else "N/A"
        actual_name = base_hotels.get(actual_id, {}).get("name", "N/A") if actual_id else "N/A"

        name_sim = 0.0
        geo_dist = 0.0
        if actual_id and ext_hotel:
            act_hotel = base_hotels.get(actual_id)
            if act_hotel:
                name_sim = SequenceMatcher(None, clean_name(ext_name), clean_name(act_hotel["name"])).ratio()
                geo_dist = haversine(ext_hotel["lat"], ext_hotel["lon"], act_hotel["lat"], act_hotel["lon"])

        # Классификация
        status = "FAIL"
        if expected_id:
            if actual_id == expected_id:
                tp += 1
                status = "SUCCESS (True Positive - совпали корректно)"
            else:
                fn += 1
                status = "FAIL (False Negative - не сопоставили или сопоставили неверно)"
        else:
            if actual_id:
                fp += 1
                status = "FAIL (False Positive - сопоставлено неверно)"
            else:
                status = "SUCCESS (True Negative - корректно не совпали)"

        report.append(f"\nВнешний отель ID: {ext_id} '{ext_name}'")
        report.append(f"  Ожидаемый ID:   {expected_id} '{expected_name}' ({comment})")
        report.append(f"  Фактический ID: {actual_id} '{actual_name}'")
        report.append(f"  Параметры связи:")
        report.append(f"    - Сходство очищенных имен: {name_sim:.3f}")
        report.append(f"    - Дистанция:               {geo_dist:.3f} км")
        report.append(f"  Статус:         {status}")

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    summary = f"""
{"=" * 80}
ИТОГОВЫЕ МЕТРИКИ:
  Precision (Точность): {precision:.2%}
  Recall (Полнота):     {recall:.2%}
  F1-Score:             {f1:.2%}
  True Positives (TP):  {tp}
  False Positives (FP): {fp}
  False Negatives (FN): {fn}
{"=" * 80}
"""
    report.append(summary)

    # Печать отчета в консоль и запись в файл
    final_report = "\n".join(report)
    print(final_report)

    with open("output/matching_report.txt", "w", encoding="utf-8") as rf:
        rf.write(final_report)
    print("Детальный отчет сохранён в output/matching_report.txt")

    # 5. Восстановление исходной базы отелей
    if original_base:
        print("\nВосстановление исходной базы отелей...")
        out_csv = io.StringIO()
        writer = csv.DictWriter(out_csv, fieldnames=["hotel_id", "name", "city_id", "lat", "lon"],
                                extrasaction='ignore')
        writer.writeheader()
        writer.writerows(original_base)

        requests.post(
            f"{base_url}/base-hotels",
            files={"file": ("restore.csv", out_csv.getvalue().encode("utf-8-sig"))}
        )
        print("Исходная база успешно восстановлена.")
else:
    print("Тестовые файлы не обнаружены. Валидация пропущена.")
