#!/usr/bin/env python3
"""Generate MySQL seed data using the user's actual CSV datasets."""

from __future__ import annotations

import ast
import csv
import math
import os
import random
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, time
from pathlib import Path


SEED = 411
random.seed(SEED)

REPO_ROOT = Path(__file__).resolve().parents[1]
MOVIE_DATASET = Path(
    os.environ.get(
        "SCENETRIP_MOVIE_CSV",
        "/Users/xiaojingxin/Downloads/archive (2)/Dataset/final_dataset.csv",
    )
)
AIRPORT_DATASET = Path(
    os.environ.get(
        "SCENETRIP_AIRPORT_CSV",
        "/Users/xiaojingxin/Downloads/airports (2).csv",
    )
)
ROUTE_DATASET = Path(
    os.environ.get(
        "SCENETRIP_ROUTE_CSV",
        "/Users/xiaojingxin/Downloads/routes 2.csv",
    )
)
OUTPUT_SQL = REPO_ROOT / "sql" / "02_seed_data.sql"


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required dataset not found: {path}")


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def parse_list_cell(value: str) -> list[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    try:
        parsed = ast.literal_eval(raw)
    except Exception:
        return []
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return []


def parse_duration_minutes(value: str) -> int:
    raw = (value or "").strip().lower()
    if not raw:
        return 100
    hours = re.search(r"(\d+)\s*h", raw)
    minutes = re.search(r"(\d+)\s*m", raw)
    total = 0
    if hours:
        total += int(hours.group(1)) * 60
    if minutes:
        total += int(minutes.group(1))
    return total or 100


def parse_release_year(value: str) -> int:
    raw = (value or "").strip()
    if len(raw) >= 4 and raw[:4].isdigit():
        return int(raw[:4])
    return 2000


def parse_rating(value: str) -> float:
    raw = (value or "").strip()
    try:
        return round(float(raw), 1)
    except Exception:
        return 0.0


def canonical_country_key(row: dict[str, str]) -> str:
    code_a2 = normalize_text(row.get("Country_CodeA2", ""))
    code_a3 = normalize_text(row.get("Country_CodeA3", ""))
    name = normalize_text(row.get("Country_Name", ""))
    return name or code_a3 or code_a2


def build_country_aliases(rows: list[dict[str, str]]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for row in rows:
        canonical = canonical_country_key(row)
        for key in (
            row.get("Country_Name", ""),
            row.get("Country_CodeA2", ""),
            row.get("Country_CodeA3", ""),
        ):
            normalized = normalize_text(key)
            if normalized:
                aliases[normalized] = canonical
    manual_aliases = {
        "usa": "united states of america",
        "us": "united states of america",
        "u s a": "united states of america",
        "uk": "united kingdom",
        "u k": "united kingdom",
    }
    aliases.update(manual_aliases)
    return aliases


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    radius_miles = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return max(1, int(radius_miles * c))


def sql_quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def write_insert(handle, table: str, columns: list[str], rows: list[tuple]) -> None:
    if not rows:
        return
    handle.write(f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n")
    values = []
    for row in rows:
        pieces = []
        for item in row:
            if item is None:
                pieces.append("NULL")
            elif isinstance(item, bool):
                pieces.append("1" if item else "0")
            elif isinstance(item, (int, float)):
                pieces.append(str(item))
            else:
                pieces.append(sql_quote(str(item)))
        values.append("(" + ", ".join(pieces) + ")")
    handle.write(",\n".join(values))
    handle.write(";\n\n")


def load_airports() -> tuple[list[tuple], dict[str, int], dict[str, list[int]], dict[tuple[str, str], list[int]], dict[str, str], dict[int, tuple[float, float]]]:
    with AIRPORT_DATASET.open("r", encoding="utf-8-sig", newline="") as handle:
        airport_rows = list(csv.DictReader(handle))

    country_aliases = build_country_aliases(airport_rows)
    locations: list[tuple] = []
    airport_to_location: dict[str, int] = {}
    city_to_locations: dict[str, list[int]] = defaultdict(list)
    city_country_to_locations: dict[tuple[str, str], list[int]] = defaultdict(list)
    location_coords: dict[int, tuple[float, float]] = {}

    location_id = 1
    seen_airports: set[str] = set()
    for row in airport_rows:
        airport_code = (row.get("IATA") or "").strip().upper()
        if not airport_code or airport_code == "\\N" or airport_code in seen_airports:
            continue
        seen_airports.add(airport_code)
        city_name = (row.get("City_Name") or "").strip()
        if not city_name:
            continue
        country_key = canonical_country_key(row)
        latitude = float(row.get("GeoPointLat") or 0.0)
        longitude = float(row.get("GeoPointLong") or 0.0)
        state_name = None
        city_parts = [part.strip() for part in city_name.split(",") if part.strip()]
        if len(city_parts) > 1:
            state_name = city_parts[-1]
        locations.append(
            (
                location_id,
                city_name,
                state_name,
                (row.get("Country_CodeA2") or "XX").strip().upper()[:2] or "XX",
                airport_code,
                round(latitude, 6),
                round(longitude, 6),
            )
        )
        airport_to_location[airport_code] = location_id
        city_key = normalize_text(city_name)
        city_to_locations[city_key].append(location_id)
        city_country_to_locations[(city_key, country_key)].append(location_id)
        location_coords[location_id] = (latitude, longitude)
        location_id += 1

    return (
        locations,
        airport_to_location,
        city_to_locations,
        city_country_to_locations,
        country_aliases,
        location_coords,
    )


def load_flights(
    airport_to_location: dict[str, int],
    location_coords: dict[int, tuple[float, float]],
) -> tuple[list[tuple], dict[tuple[str, str], list[int]], dict[str, list[str]]]:
    flights: list[tuple] = []
    flight_map: dict[tuple[str, str], list[int]] = defaultdict(list)
    outgoing: dict[str, list[str]] = defaultdict(list)

    with ROUTE_DATASET.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        flight_id = 1
        for row in reader:
            source = (row.get("Source airport") or "").strip().upper()
            dest = (row.get("Destination airport") or "").strip().upper()
            if source not in airport_to_location or dest not in airport_to_location or source == dest:
                continue
            src_coords = location_coords[airport_to_location[source]]
            dst_coords = location_coords[airport_to_location[dest]]
            distance = haversine_miles(src_coords[0], src_coords[1], dst_coords[0], dst_coords[1])
            depart_hour = (flight_id * 3) % 24
            depart_minute = (flight_id * 7) % 60
            duration_minutes = max(45, int(distance / 8))
            arrival_total = depart_hour * 60 + depart_minute + duration_minutes
            arrive_hour = (arrival_total // 60) % 24
            arrive_minute = arrival_total % 60
            carrier = (row.get("Airline") or "").strip() or "UNK"
            stops = int((row.get("Stops") or "0").strip() or 0)
            flights.append(
                (
                    flight_id,
                    source,
                    dest,
                    carrier,
                    time(depart_hour, depart_minute).strftime("%H:%M:%S"),
                    time(arrive_hour, arrive_minute).strftime("%H:%M:%S"),
                    distance,
                    max(1, 7 - min(stops, 6)),
                )
            )
            flight_map[(source, dest)].append(flight_id)
            outgoing[source].append(dest)
            flight_id += 1

    for airport_code, dests in outgoing.items():
        outgoing[airport_code] = sorted(set(dests))

    return flights, flight_map, outgoing


def match_filming_location(
    location_text: str,
    city_to_locations: dict[str, list[int]],
    city_country_to_locations: dict[tuple[str, str], list[int]],
    country_aliases: dict[str, str],
) -> int | None:
    parts = [part.strip() for part in str(location_text).split(",") if part.strip()]
    if not parts:
        return None

    country_key = None
    if parts:
        last_key = normalize_text(parts[-1])
        country_key = country_aliases.get(last_key, last_key)

    candidate_cities: list[str] = []
    if len(parts) >= 2:
        candidate_cities.append(parts[1])
    if len(parts) >= 1:
        candidate_cities.append(parts[0])
    if len(parts) >= 3:
        candidate_cities.append(parts[-2])
    if len(parts) >= 4:
        candidate_cities.append(parts[-3])

    seen_candidates: set[str] = set()
    for city in candidate_cities:
        city_key = normalize_text(city)
        if not city_key or city_key in seen_candidates:
            continue
        seen_candidates.add(city_key)
        if country_key and (city_key, country_key) in city_country_to_locations:
            return city_country_to_locations[(city_key, country_key)][0]
        if city_key in city_to_locations:
            return city_to_locations[city_key][0]
    return None


def load_movies_and_relationships(
    city_to_locations: dict[str, list[int]],
    city_country_to_locations: dict[tuple[str, str], list[int]],
    country_aliases: dict[str, str],
) -> tuple[list[tuple], list[tuple], list[tuple], list[tuple], list[int]]:
    movies: list[tuple] = []
    movie_actors: list[tuple] = []
    movie_locations: list[tuple] = []
    chosen_movie_ids: list[int] = []

    actor_ids: dict[str, int] = {}
    actors: list[tuple] = []

    with MOVIE_DATASET.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        movie_id = 1
        actor_id = 1
        for row in reader:
            title = (row.get("title") or "").strip()
            if not title:
                continue
            filming_locations_raw = parse_list_cell(row.get("filming_locations", ""))
            matched_locations: list[int] = []
            seen_locations: set[int] = set()
            for location_text in filming_locations_raw:
                matched = match_filming_location(
                    location_text,
                    city_to_locations,
                    city_country_to_locations,
                    country_aliases,
                )
                if matched is not None and matched not in seen_locations:
                    seen_locations.add(matched)
                    matched_locations.append(matched)
            if not matched_locations:
                continue

            genres = parse_list_cell(row.get("genres", ""))
            release_date = (row.get("release_date") or "").strip()
            movies.append(
                (
                    movie_id,
                    title[:120],
                    parse_release_year(release_date),
                    parse_rating(row.get("rating", "")),
                    parse_duration_minutes(row.get("duration", "")),
                    (genres[0] if genres else "Unknown")[:40],
                )
            )

            stars = parse_list_cell(row.get("stars", ""))
            seen_actors_for_movie: set[int] = set()
            for billing_order, actor_name in enumerate(stars[:10], start=1):
                if actor_name not in actor_ids:
                    actor_ids[actor_name] = actor_id
                    actors.append(
                        (
                            actor_id,
                            actor_name[:100],
                            None,
                            None,
                        )
                    )
                    actor_id += 1
                current_actor_id = actor_ids[actor_name]
                if current_actor_id in seen_actors_for_movie:
                    continue
                seen_actors_for_movie.add(current_actor_id)
                movie_actors.append((movie_id, current_actor_id, billing_order))

            for offset, location_id in enumerate(matched_locations[:5], start=1):
                movie_locations.append((movie_id, location_id, max(1, 6 - offset), offset == 1))

            chosen_movie_ids.append(movie_id)
            movie_id += 1

    return movies, actors, movie_actors, movie_locations, chosen_movie_ids


def build_users(eligible_airports: list[str]) -> list[tuple]:
    users: list[tuple] = []
    base = datetime(2024, 1, 1, 9, 0, 0)
    for user_id in range(1, 1201):
        airport = eligible_airports[(user_id - 1) % len(eligible_airports)]
        created_at = base + timedelta(hours=user_id * 3)
        users.append(
            (
                user_id,
                f"user_{user_id:04d}",
                f"user_{user_id:04d}@scenetrip.app",
                airport,
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
    return users


def build_trip_data(
    eligible_airports: list[str],
    airport_to_location: dict[str, int],
    outgoing: dict[str, list[str]],
    flight_map: dict[tuple[str, str], list[int]],
) -> tuple[list[tuple], list[tuple], list[tuple]]:
    trip_plans: list[tuple] = []
    trip_plan_stops: list[tuple] = []
    booked_flights: list[tuple] = []

    base = datetime(2025, 1, 1, 8, 0, 0)
    for trip_plan_id in range(1, 2001):
        start_airport = eligible_airports[(trip_plan_id * 5) % len(eligible_airports)]
        stop_airports = [start_airport]
        current = start_airport
        desired_stops = 3 + (trip_plan_id % 3)

        for step in range(1, desired_stops):
            candidates = outgoing.get(current, [])
            if not candidates:
                current = eligible_airports[(trip_plan_id + step) % len(eligible_airports)]
            else:
                current = candidates[(trip_plan_id + step) % len(candidates)]
            stop_airports.append(current)

        created_at = base + timedelta(hours=trip_plan_id * 2)
        trip_plans.append(
            (
                trip_plan_id,
                1 + ((trip_plan_id * 7) % 1200),
                f"SceneTrip Plan {trip_plan_id:04d}",
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
                start_airport,
                round(900 + (trip_plan_id % 14) * 160 + (trip_plan_id % 5) * 35, 2),
            )
        )

        for stop_order, airport_code in enumerate(stop_airports, start=1):
            trip_plan_stops.append(
                (
                    trip_plan_id,
                    stop_order,
                    airport_to_location[airport_code],
                    1 + ((trip_plan_id + stop_order) % 4),
                )
            )

        for leg_order in range(1, len(stop_airports)):
            source = stop_airports[leg_order - 1]
            dest = stop_airports[leg_order]
            candidates = flight_map.get((source, dest))
            if not candidates:
                continue
            booked_flights.append(
                (
                    trip_plan_id,
                    leg_order,
                    candidates[(trip_plan_id + leg_order) % len(candidates)],
                )
            )

    return trip_plans, trip_plan_stops, booked_flights


def main() -> None:
    require_file(MOVIE_DATASET)
    require_file(AIRPORT_DATASET)
    require_file(ROUTE_DATASET)

    (
        locations,
        airport_to_location,
        city_to_locations,
        city_country_to_locations,
        country_aliases,
        location_coords,
    ) = load_airports()
    flights, flight_map, outgoing = load_flights(airport_to_location, location_coords)
    movies, actors, movie_actors, movie_locations, _chosen_movie_ids = load_movies_and_relationships(
        city_to_locations,
        city_country_to_locations,
        country_aliases,
    )

    eligible_airports = sorted(
        airport
        for airport in outgoing
        if airport in airport_to_location and outgoing[airport]
    )
    users = build_users(eligible_airports)
    trip_plans, trip_plan_stops, booked_flights = build_trip_data(
        eligible_airports,
        airport_to_location,
        outgoing,
        flight_map,
    )

    with OUTPUT_SQL.open("w", encoding="utf-8") as handle:
        handle.write("USE scenetrip;\n\n")
        handle.write("SET FOREIGN_KEY_CHECKS = 0;\n")
        for table in [
            "booked_flights",
            "trip_plan_stops",
            "movie_locations",
            "movie_actors",
            "trip_plans",
            "flights",
            "locations",
            "actors",
            "movies",
            "users",
        ]:
            handle.write(f"TRUNCATE TABLE {table};\n")
        handle.write("SET FOREIGN_KEY_CHECKS = 1;\n\n")

        write_insert(handle, "users", ["user_id", "username", "email", "home_airport", "created_at"], users)
        write_insert(handle, "movies", ["movie_id", "title", "release_year", "rating", "runtime_minutes", "primary_genre"], movies)
        write_insert(handle, "actors", ["actor_id", "actor_name", "birth_year", "nationality"], actors)
        write_insert(handle, "locations", ["location_id", "city_name", "state_name", "country_code", "airport_code", "latitude", "longitude"], locations)
        write_insert(handle, "flights", ["flight_id", "source_airport", "dest_airport", "carrier", "depart_time", "arrive_time", "distance_miles", "daily_frequency"], flights)
        write_insert(handle, "trip_plans", ["trip_plan_id", "user_id", "plan_name", "created_at", "start_airport", "total_budget"], trip_plans)
        write_insert(handle, "movie_actors", ["movie_id", "actor_id", "billing_order"], movie_actors)
        write_insert(handle, "movie_locations", ["movie_id", "location_id", "scene_count", "is_primary_location"], movie_locations)
        write_insert(handle, "trip_plan_stops", ["trip_plan_id", "stop_order", "location_id", "planned_days"], trip_plan_stops)
        write_insert(handle, "booked_flights", ["trip_plan_id", "leg_order", "flight_id"], booked_flights)

        handle.write("-- Row-count checks required by the rubric.\n")
        handle.write("SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users\n")
        handle.write("UNION ALL SELECT 'movies', COUNT(*) FROM movies\n")
        handle.write("UNION ALL SELECT 'locations', COUNT(*) FROM locations\n")
        handle.write("UNION ALL SELECT 'flights', COUNT(*) FROM flights\n")
        handle.write("UNION ALL SELECT 'trip_plans', COUNT(*) FROM trip_plans;\n")

    print(f"Wrote seed data to {OUTPUT_SQL}")
    print("Dataset-backed row counts:")
    print(f"  users: {len(users)}")
    print(f"  movies: {len(movies)}")
    print(f"  actors: {len(actors)}")
    print(f"  locations: {len(locations)}")
    print(f"  flights: {len(flights)}")
    print(f"  trip_plans: {len(trip_plans)}")
    print(f"  movie_actors: {len(movie_actors)}")
    print(f"  movie_locations: {len(movie_locations)}")
    print(f"  trip_plan_stops: {len(trip_plan_stops)}")
    print(f"  booked_flights: {len(booked_flights)}")


if __name__ == "__main__":
    main()
