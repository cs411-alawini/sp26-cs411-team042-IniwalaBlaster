from db import mysql_query, sql_escape


def find_departure_airports(city: str) -> list[list[str]]:
    city = sql_escape(city)

    return mysql_query(
        f"""
        SELECT location_id, city_name, airport_code, latitude, longitude
        FROM locations
        WHERE city_name LIKE '%{city}%'
        ORDER BY city_name, airport_code
        LIMIT 8;
        """
    )


def get_movie_stops(movie_id: int) -> list[list[str]]:
    return mysql_query(
        f"""
        SELECT
            l.location_id,
            l.city_name,
            COALESCE(l.state_name, ''),
            l.airport_code,
            l.latitude,
            l.longitude,
            ml.scene_count,
            ml.is_primary_location
        FROM movie_locations ml
        JOIN locations l ON l.location_id = ml.location_id
        WHERE ml.movie_id = {movie_id}
        ORDER BY ml.is_primary_location DESC, ml.scene_count DESC, l.city_name
        LIMIT 6;
        """
    )


def get_route_candidates(source_airport: str, dest_airport: str) -> list[list[str]]:
    return mysql_query(
        f"""
        SELECT flight_id, carrier, source_airport, dest_airport, depart_time, arrive_time, distance_miles
        FROM flights
        WHERE source_airport = '{sql_escape(source_airport)}'
          AND dest_airport = '{sql_escape(dest_airport)}'
        ORDER BY distance_miles, flight_id
        LIMIT 3;
        """
    )


def get_outgoing_airports(source_airport: str, limit: int = 60) -> list[str]:
    rows = mysql_query(
        f"""
        SELECT DISTINCT dest_airport
        FROM flights
        WHERE source_airport = '{sql_escape(source_airport)}'
        ORDER BY dest_airport
        LIMIT {limit};
        """
    )

    return [row[0] for row in rows]


def find_best_path(source_airport: str, dest_airport: str, max_legs: int = 3) -> list[list[str]] | None:
    if source_airport == dest_airport:
        return []

    direct = get_route_candidates(source_airport, dest_airport)
    if direct:
        return [direct[0]]

    visited = {source_airport}
    frontier = [(source_airport, [])]

    while frontier:
        airport, path = frontier.pop(0)

        if len(path) >= max_legs:
            continue

        for next_airport in get_outgoing_airports(airport):
            if next_airport in visited:
                continue

            leg = get_route_candidates(airport, next_airport)
            if not leg:
                continue

            next_path = path + [leg[0]]

            if next_airport == dest_airport:
                return next_path

            visited.add(next_airport)
            frontier.append((next_airport, next_path))

    return None