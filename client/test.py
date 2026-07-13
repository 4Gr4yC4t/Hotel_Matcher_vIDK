import requests
import os
import time

# адрес нашего API
url = os.environ.get("SERVER_URL", "http://127.0.0.1:8000/match")
health_url = url.replace("/match", "/")

# ждём готовности сервера
for i in range(30):
    try:
        r = requests.get(health_url, timeout=3)
        if r.status_code == 200:
            break
    except requests.ConnectionError:
        pass
    print(f"Ожидание сервера... попытка {i+1}")
    time.sleep(2)

# отправляем CSV
with open("01_hotels_external.csv", "rb") as file:

    response = requests.post(
        url,
        files={
            "file": file
        }
    )

processing_time = response.headers.get("X-Processing-Time-Ms", "N/A")
print(f"Время обработки на сервере: {processing_time} мс")

base_url = url.replace("/match", "")
print(f"Список загрузок: {base_url}/uploads")

path = "output/"
os.makedirs(os.path.dirname(path), exist_ok=True)

# сохраняем ответ в output
with open("output/matches.csv", "wb") as result_file:
    result_file.write(response.content)


print("Готово! Файл сохранён в output/matches.csv")