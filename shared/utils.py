import re
from difflib import SequenceMatcher
from math import radians, sin, cos, sqrt, atan2


TRANSLIT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
    'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
    'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
    'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
    'э': 'e', 'ю': 'yu', 'я': 'ya',

    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
    'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
    'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
    'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
    'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch',
    'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
    'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
}

STOP_WORDS = {
    # Английские стоп-слова
    "hotel", "resort", "spa", "club", "and", "lounge", "suites",
    "palace", "beach", "retreat", "garden", "villas", "oasis",
    "wellness", "exclusive", "premium", "luxury", "deluxe",
    "classic", "grand", "royal", "elite", "superior", "prime", "star", "stars",

    # Транслитерированные русские аналоги стоп-слов
    "otel", "rezort", "klub", "end", "launzh", "laundzh", "syut", "syuts",
    "palas", "bich", "ritrit", "velnes", "velness", "eksklyuziv", "lyuks",
    "delyuks", "klassik", "elit", "praym", "khotel"
}


def transliterate(text):
    return ''.join(TRANSLIT_MAP.get(char, char) for char in text)


def clean_name(text):
    if not text:
        return ""
    text = transliterate(text)
    text = text.lower()
    text = text.replace("5*", " ")
    text = re.sub(r'[^a-z0-9\s]', ' ', text)

    words = text.split()
    cleaned_words = [w for w in words if w not in STOP_WORDS]

    if not cleaned_words:
        cleaned_words = words

    return " ".join(cleaned_words)


def prepare_name(text):
    return clean_name(text)


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def haversine(lat1, lon1, lat2, lon2):
    R = 6371

    lat1, lon1, lat2, lon2 = map(
        radians,
        [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
            sin(dlat / 2) ** 2 +
            cos(lat1) *
            cos(lat2) *
            sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return R * c


def is_within_bbox(
        lat,
        lon,
        center_lat,
        center_lon,
        radius_km
):
    lat_delta = radius_km / 111

    cos_lat = cos(radians(center_lat))
    if abs(cos_lat) < 1e-6:
        cos_lat = 1e-6
    lon_delta = radius_km / (111 * cos_lat)

    return (
            center_lat - lat_delta <= lat <= center_lat + lat_delta
            and
            center_lon - lon_delta <= lon <= center_lon + lon_delta
    )
