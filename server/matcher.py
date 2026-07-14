from shared.utils import prepare_name, similarity, haversine, is_within_bbox


# ======================================================
# 1. ПОДГОТОВКА БАЗЫ
# ======================================================

def prepare_base(base_hotels):
    for hotel in base_hotels:
        hotel["search_name"] = prepare_name(
            hotel["name"]
        )


# ======================================================
# 2. ОСНОВНОЙ МАТЧИНГ
# ======================================================

def match_hotel(
        external_hotel,
        base_hotels,
        radius_km=3,
        threshold=0.50
):
    best_score = 0
    best_match = None

    external_name = prepare_name(
        external_hotel["name"]
    )

    for hotel in base_hotels:
        if not is_within_bbox(
                hotel["lat"],
                hotel["lon"],
                external_hotel["lat"],
                external_hotel["lon"],
                radius_km
        ):
            continue

        distance = haversine(
            external_hotel["lat"],
            external_hotel["lon"],
            hotel["lat"],
            hotel["lon"]
        )

        if distance > radius_km:
            continue

        text_score = similarity(
            external_name,
            hotel["search_name"]
        )

        geo_score = max(
            0,
            1 - distance / radius_km
        )

        final_score = (
                0.7 * text_score +
                0.3 * geo_score
        )

        if final_score > best_score:
            best_score = final_score
            best_match = hotel

    if best_match and best_score >= threshold:
        return {
            "hotel_id": external_hotel.get("hotel_id"),
            "duplicate_hotel_id": best_match["hotel_id"],
            "score": round(best_score, 3)
        }

    return {
        "hotel_id": external_hotel.get("hotel_id"),
        "duplicate_hotel_id": None,
        "score": 0
    }
