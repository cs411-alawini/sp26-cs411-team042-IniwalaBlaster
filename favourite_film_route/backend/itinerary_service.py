from movie_service import get_movie_by_id
from route_service import (
    find_departure_airports,
    get_movie_stops,
    find_best_path,
)


def dedupe_stops(rows: list[list[str]]) -> list[list[str]]:
    seen = set()
    result = []

    for row in rows:
        airport = row[3]
        if airport in seen:
            continue

        seen.add(airport)
        result.append(row)

    return result


def estimate_leg_cost(distance_miles: int) -> float:
    return round(65 + distance_miles * 0.19, 2)


def estimate_transfer_cost(source_airport: str, dest_airport: str) -> float:
    pseudo_distance = 900 + (
        abs(sum(map(ord, source_airport)) - sum(map(ord, dest_airport))) * 4
    )
    return round(120 + pseudo_distance * 0.16, 2)


def append_leg_rows(leg_rows: list[dict], path: list[list[str]]) -> None:
    for leg in path:
        distance = int(leg[6])

        leg_rows.append(
            {
                "from_airport": leg[2],
                "to_airport": leg[3],
                "carrier": leg[1],
                "depart_time": leg[4],
                "arrive_time": leg[5],
                "distance_miles": distance,
                "estimated_cost": estimate_leg_cost(distance),
            }
        )


def choose_best_origin(departure_options: list[list[str]], raw_stops: list[list[str]]) -> list[str]:
    best_option = departure_options[0]
    best_score = -1

    stop_airports = [row[3] for row in raw_stops]

    for option in departure_options:
        airport_code = option[2]
        score = 0

        for stop_airport in stop_airports[:4]:
            path = find_best_path(airport_code, stop_airport, max_legs=2)
            if path is not None:
                score += 5 - len(path)

        if score > best_score:
            best_score = score
            best_option = option

    return best_option


def build_itinerary(movie_id: int, budget: float, departure_city: str) -> dict:
    movie = get_movie_by_id(movie_id)

    departure_options = find_departure_airports(departure_city)
    if not departure_options:
        raise RuntimeError("Departure city was not found in the airport-location dataset.")

    raw_stops = dedupe_stops(get_movie_stops(movie_id))
    if not raw_stops:
        raise RuntimeError("This movie does not currently have matched filming locations.")

    origin = choose_best_origin(departure_options, raw_stops)
    origin_airport = origin[2]
    origin_city = origin[1]

    chosen_stops = []
    leg_rows = []
    current_airport = origin_airport
    remaining = raw_stops.copy()
    fallback_used = False

    while remaining and len(chosen_stops) < 3:
        picked_index = None
        picked_path = None

        for idx, stop in enumerate(remaining):
            stop_airport = stop[3]

            if stop_airport == current_airport:
                picked_index = idx
                picked_path = []
                break

            path = find_best_path(current_airport, stop_airport, max_legs=3)
            if path is not None:
                picked_index = idx
                picked_path = path
                break

        if picked_index is None:
            picked_index = 0
            picked_path = None
            fallback_used = True

        stop = remaining.pop(picked_index)

        chosen_stops.append(
            {
                "location_id": int(stop[0]),
                "city_name": stop[1],
                "state_name": stop[2],
                "airport_code": stop[3],
                "scene_count": int(stop[6]),
                "is_primary": int(stop[7]),
            }
        )

        if picked_path:
            append_leg_rows(leg_rows, picked_path)
        else:
            leg_rows.append(
                {
                    "from_airport": current_airport,
                    "to_airport": stop[3],
                    "carrier": "Transfer required",
                    "depart_time": "TBD",
                    "arrive_time": "TBD",
                    "distance_miles": 0,
                    "estimated_cost": estimate_transfer_cost(current_airport, stop[3]),
                }
            )

        current_airport = stop[3]

    if current_airport != origin_airport:
        return_path = find_best_path(current_airport, origin_airport, max_legs=3)

        if return_path is not None:
            append_leg_rows(leg_rows, return_path)
        else:
            leg_rows.append(
                {
                    "from_airport": current_airport,
                    "to_airport": origin_airport,
                    "carrier": "Manual return transfer",
                    "depart_time": "TBD",
                    "arrive_time": "TBD",
                    "distance_miles": 0,
                    "estimated_cost": estimate_transfer_cost(current_airport, origin_airport),
                }
            )
            fallback_used = True

    stop_count = len(chosen_stops)
    total_days = max(3, min(8, int(budget // 450) + 2))

    base_days = max(1, total_days // stop_count)
    extra_days = total_days - base_days * stop_count

    for idx, stop in enumerate(chosen_stops):
        stop["recommended_days"] = base_days + (1 if idx < extra_days else 0)

    flight_budget = round(sum(float(leg["estimated_cost"]) for leg in leg_rows), 2)
    hotel_budget = round(sum(int(stop["recommended_days"]) * 145 for stop in chosen_stops), 2)
    local_budget = round(total_days * 70, 2)
    total_estimated_budget = round(flight_budget + hotel_budget + local_budget, 2)

    if total_estimated_budget <= budget:
        budget_status = f"Within budget by ${budget - total_estimated_budget:.2f}"
    else:
        budget_status = f"Over budget by ${total_estimated_budget - budget:.2f}"

    route_quality = (
        "Hybrid plan: some legs come from the real route dataset, and some require manual transfer planning."
        if fallback_used
        else "Full route found from the real route dataset."
    )

    return {
        "movie_title": movie["title"],
        "departure_city": origin_city,
        "departure_airport": origin_airport,
        "stops": chosen_stops,
        "legs": leg_rows,
        "total_days": total_days,
        "budget": {
            "flight_budget": flight_budget,
            "hotel_budget": hotel_budget,
            "local_budget": local_budget,
            "total_estimated_budget": total_estimated_budget,
            "budget_status": budget_status,
        },
        "route_quality": route_quality,
    }