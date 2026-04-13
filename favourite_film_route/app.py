#!/usr/bin/env python3
from __future__ import annotations

import html
import os
import subprocess
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from textwrap import dedent
from urllib.parse import parse_qs, quote_plus, urlparse


DB_SOCKET = os.environ.get("SCENETRIP_DB_SOCKET", "/tmp/scenetrip-mysql-run/mysql.sock")
DB_PORT = os.environ.get("SCENETRIP_DB_PORT", "3307")
DB_USER = os.environ.get("SCENETRIP_DB_USER", "root")
DB_NAME = os.environ.get("SCENETRIP_DB_NAME", "scenetrip")
HOST = os.environ.get("SCENETRIP_HOST", "127.0.0.1")
PORT = int(os.environ.get("SCENETRIP_WEB_PORT", "8000"))


@dataclass
class FlashMessage:
    level: str
    text: str


@dataclass
class ItineraryPlan:
    movie_title: str
    departure_city: str
    departure_airport: str
    stop_rows: list[dict[str, str | int | float]]
    leg_rows: list[dict[str, str | int | float]]
    total_days: int
    flight_budget: float
    hotel_budget: float
    local_budget: float
    total_estimated_budget: float
    budget_status: str
    route_quality: str


def mysql_query(sql: str) -> list[list[str]]:
    proc = subprocess.run(
        [
            "mysql",
            "-u",
            DB_USER,
            "--socket",
            DB_SOCKET,
            "--port",
            DB_PORT,
            "-D",
            DB_NAME,
            "--batch",
            "--raw",
            "--skip-column-names",
            "-e",
            sql,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Unknown MySQL error")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return [line.split("\t") for line in lines]


def sql_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "''")


def try_connection() -> str | None:
    try:
        mysql_query("SELECT 1;")
        return None
    except Exception as exc:
        return str(exc)


def get_summary_cards() -> list[tuple[str, str]]:
    queries = {
        "Movies": "SELECT COUNT(*) FROM movies;",
        "Filming Locations": "SELECT COUNT(*) FROM locations;",
        "Routes": "SELECT COUNT(*) FROM flights;",
        "Movie Links": "SELECT COUNT(*) FROM movie_locations;",
    }
    cards = []
    for label, query in queries.items():
        value = mysql_query(query)[0][0]
        cards.append((label, value))
    return cards


def get_featured_movies(limit: int = 250) -> list[list[str]]:
    return mysql_query(
        f"""
        SELECT
            m.title,
            MIN(m.movie_id) AS movie_id,
            ROUND(MAX(m.rating), 1) AS rating,
            SUBSTRING_INDEX(GROUP_CONCAT(DISTINCT m.primary_genre ORDER BY m.primary_genre SEPARATOR ', '), ',', 1) AS primary_genre,
            COUNT(DISTINCT ml.location_id) AS filming_stop_count
        FROM movies m
        JOIN movie_locations ml ON ml.movie_id = m.movie_id
        GROUP BY m.title
        ORDER BY MAX(m.rating) DESC, filming_stop_count DESC, m.title
        LIMIT {limit};
        """
    )


def get_movie_by_id(movie_id: int) -> list[str]:
    rows = mysql_query(
        f"""
        SELECT movie_id, title, ROUND(rating, 1), primary_genre
        FROM movies
        WHERE movie_id = {movie_id}
        LIMIT 1;
        """
    )
    if not rows:
        raise RuntimeError("Selected movie could not be found.")
    return rows[0]


def find_movie_by_title(movie_title: str) -> list[str]:
    title = sql_escape(movie_title.strip())
    rows = mysql_query(
        f"""
        SELECT
            MIN(m.movie_id) AS movie_id,
            m.title,
            ROUND(MAX(m.rating), 1) AS rating,
            SUBSTRING_INDEX(GROUP_CONCAT(DISTINCT m.primary_genre ORDER BY m.primary_genre SEPARATOR ', '), ',', 1) AS primary_genre
        FROM movies m
        JOIN movie_locations ml ON ml.movie_id = m.movie_id
        WHERE m.title = '{title}'
        GROUP BY m.title
        LIMIT 1;
        """
    )
    if rows:
        return rows[0]

    rows = mysql_query(
        f"""
        SELECT
            MIN(m.movie_id) AS movie_id,
            m.title,
            ROUND(MAX(m.rating), 1) AS rating,
            SUBSTRING_INDEX(GROUP_CONCAT(DISTINCT m.primary_genre ORDER BY m.primary_genre SEPARATOR ', '), ',', 1) AS primary_genre
        FROM movies m
        JOIN movie_locations ml ON ml.movie_id = m.movie_id
        WHERE m.title LIKE '%{title}%'
        GROUP BY m.title
        ORDER BY MAX(m.rating) DESC, m.title
        LIMIT 1;
        """
    )
    if not rows:
        raise RuntimeError("No matching movie title was found. Try a different keyword.")
    return rows[0]


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


def get_direct_flight(source_airport: str, dest_airport: str) -> list[str] | None:
    rows = mysql_query(
        f"""
        SELECT flight_id, carrier, source_airport, dest_airport, depart_time, arrive_time, distance_miles
        FROM flights
        WHERE source_airport = '{sql_escape(source_airport)}'
          AND dest_airport = '{sql_escape(dest_airport)}'
        ORDER BY distance_miles, flight_id
        LIMIT 1;
        """
    )
    return rows[0] if rows else None


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
    frontier: list[tuple[str, list[list[str]]]] = [(source_airport, [])]
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
    pseudo_distance = 900 + (abs(sum(map(ord, source_airport)) - sum(map(ord, dest_airport))) * 4)
    return round(120 + pseudo_distance * 0.16, 2)


def append_leg_rows(leg_rows: list[dict[str, str | int | float]], path: list[list[str]]) -> None:
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


def build_itinerary(movie_id: int, budget: float, departure_city: str) -> ItineraryPlan:
    movie = get_movie_by_id(movie_id)
    departure_options = find_departure_airports(departure_city)
    if not departure_options:
        raise RuntimeError("Departure city was not found in the airport-location dataset.")

    raw_stops = dedupe_stops(get_movie_stops(movie_id))
    if not raw_stops:
        raise RuntimeError("This movie does not currently have matched filming locations in the database.")

    origin = choose_best_origin(departure_options, raw_stops)
    origin_airport = origin[2]
    origin_city = origin[1]

    chosen_stops: list[dict[str, str | int | float]] = []
    leg_rows: list[dict[str, str | int | float]] = []
    current_airport = origin_airport
    remaining = raw_stops.copy()
    fallback_used = False

    # Prefer a compact itinerary with up to 3 reachable stops.
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

    if not chosen_stops:
        first_stop = raw_stops[0]
        chosen_stops.append(
            {
                "location_id": int(first_stop[0]),
                "city_name": first_stop[1],
                "state_name": first_stop[2],
                "airport_code": first_stop[3],
                "scene_count": int(first_stop[6]),
                "is_primary": int(first_stop[7]),
            }
        )
        leg_rows.append(
            {
                "from_airport": current_airport,
                "to_airport": first_stop[3],
                "carrier": "Transfer required",
                "depart_time": "TBD",
                "arrive_time": "TBD",
                "distance_miles": 0,
                "estimated_cost": estimate_transfer_cost(current_airport, first_stop[3]),
            }
        )
        current_airport = first_stop[3]
        fallback_used = True

    # Add return leg when possible.
    if current_airport == origin_airport:
        leg_rows.append(
            {
                "from_airport": current_airport,
                "to_airport": origin_airport,
                "carrier": "Local completion",
                "depart_time": "-",
                "arrive_time": "-",
                "distance_miles": 0,
                "estimated_cost": 0.0,
            }
        )
    else:
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
    budget_status = (
        f"Within budget by ${budget - total_estimated_budget:.2f}"
        if total_estimated_budget <= budget
        else f"Over budget by ${total_estimated_budget - budget:.2f}"
    )
    route_quality = (
        "Hybrid plan: some legs come from the real route dataset, and some require manual transfer planning."
        if fallback_used
        else "Full route found from the real route dataset."
    )

    return ItineraryPlan(
        movie_title=movie[1],
        departure_city=origin_city,
        departure_airport=origin_airport,
        stop_rows=chosen_stops,
        leg_rows=leg_rows,
        total_days=total_days,
        flight_budget=flight_budget,
        hotel_budget=hotel_budget,
        local_budget=local_budget,
        total_estimated_budget=total_estimated_budget,
        budget_status=budget_status,
        route_quality=route_quality,
    )


def render_table(headers: list[str], rows: list[list[str]], empty_message: str) -> str:
    if not rows:
        return f"<p class='empty'>{html.escape(empty_message)}</p>"
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(value))}</td>" for value in row)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def render_itinerary(plan: ItineraryPlan | None) -> str:
    if not plan:
        return "<p class='empty'>Choose a movie, budget, and departure city to generate a complete itinerary.</p>"

    route_parts = [f"{html.escape(plan.departure_city)} ({html.escape(plan.departure_airport)})"]
    for stop in plan.stop_rows:
        route_parts.append(f"{html.escape(str(stop['city_name']))} ({html.escape(str(stop['airport_code']))})")
    route_parts.append(f"{html.escape(plan.departure_city)} ({html.escape(plan.departure_airport)})")

    stop_cards = []
    for index, stop in enumerate(plan.stop_rows, start=1):
        state_text = f", {stop['state_name']}" if stop["state_name"] else ""
        stop_cards.append(
            f"""
            <div class="stop-card">
              <span>Stop {index}</span>
              <strong>{html.escape(str(stop['city_name']))}{html.escape(state_text)}</strong>
              <small>Airport {html.escape(str(stop['airport_code']))}</small>
              <small>Recommended stay: {stop['recommended_days']} day(s)</small>
            </div>
            """
        )

    leg_rows = []
    for leg in plan.leg_rows:
        leg_rows.append(
            [
                str(leg["from_airport"]),
                str(leg["to_airport"]),
                str(leg["carrier"]),
                str(leg["depart_time"]),
                str(leg["arrive_time"]),
                str(leg["distance_miles"]),
                f"${float(leg['estimated_cost']):.2f}",
            ]
        )

    summary = f"""
    <div class="summary-grid">
      <div class="summary-tile"><span>Movie</span><strong>{html.escape(plan.movie_title)}</strong></div>
      <div class="summary-tile"><span>Total days</span><strong>{plan.total_days}</strong></div>
      <div class="summary-tile"><span>Estimated total</span><strong>${plan.total_estimated_budget:.2f}</strong></div>
      <div class="summary-tile"><span>Budget check</span><strong>{html.escape(plan.budget_status)}</strong></div>
    </div>
    """

    budget_html = f"""
    <div class="budget-grid">
      <div class="budget-card"><span>Flights</span><strong>${plan.flight_budget:.2f}</strong></div>
      <div class="budget-card"><span>Hotels</span><strong>${plan.hotel_budget:.2f}</strong></div>
      <div class="budget-card"><span>Local spending</span><strong>${plan.local_budget:.2f}</strong></div>
    </div>
    """

    route_text = " &rarr; ".join(route_parts)
    return f"""
    <div class="itinerary-shell">
      {summary}
      <div class="route-banner">{route_text}</div>
      <div class="stops-grid">{''.join(stop_cards)}</div>
      <h3>Flight Legs</h3>
      {render_table(['From', 'To', 'Carrier', 'Depart', 'Arrive', 'Miles', 'Est. Cost'], leg_rows, 'No flight legs were generated.')}
      <h3>Budget Breakdown</h3>
      {budget_html}
    </div>
    """


def render_page(
    *,
    flash: FlashMessage | None = None,
    db_error: str | None = None,
    itinerary: ItineraryPlan | None = None,
    departure_city: str = "",
    selected_movie_title: str = "",
    selected_budget: str = "1800",
) -> str:
    summary = []
    featured_movies = []
    if not db_error:
        summary = get_summary_cards()
        featured_movies = get_featured_movies()

    summary_html = "".join(
        f"<div class='stat-card'><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>"
        for label, value in summary
    )

    flash_html = ""
    if flash:
        flash_html = f"<div class='flash {html.escape(flash.level)}'>{html.escape(flash.text)}</div>"
    if db_error:
        flash_html += f"<div class='flash error'>Database connection failed: {html.escape(db_error)}</div>"

    movie_suggestions = []
    for title, movie_id, rating, genre, filming_stop_count in featured_movies:
        movie_suggestions.append(
            f"<option value='{html.escape(title)}'>{html.escape(title)} | rating {rating} | {genre} | {filming_stop_count} stop(s)</option>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SceneTrip Planner</title>
  <style>
    :root {{
      --bg: #f5efe5;
      --panel: rgba(255,255,255,0.86);
      --ink: #21303b;
      --muted: #63727d;
      --accent: #b54d26;
      --accent-2: #2f6f62;
      --line: #d7c9b7;
      --shadow: 0 22px 60px rgba(71, 54, 38, 0.12);
      --danger: #a03232;
      --success: #1d6b44;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top left, rgba(181,77,38,0.17), transparent 32%),
        radial-gradient(circle at bottom right, rgba(47,111,98,0.15), transparent 28%),
        linear-gradient(180deg, #faf6f1 0%, var(--bg) 100%);
    }}
    .shell {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 30px 20px 60px;
    }}
    .hero {{
      border-radius: 28px;
      padding: 30px;
      background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(246,235,223,0.95));
      border: 1px solid rgba(181,77,38,0.16);
      box-shadow: var(--shadow);
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: clamp(2.4rem, 6vw, 4.7rem);
      letter-spacing: -0.05em;
      line-height: 0.95;
    }}
    .subtitle {{
      margin: 0;
      max-width: 780px;
      color: var(--muted);
      font-size: 1.08rem;
      line-height: 1.7;
    }}
    .grid {{
      display: grid;
      gap: 20px;
      grid-template-columns: repeat(12, 1fr);
    }}
    .card {{
      grid-column: span 12;
      background: var(--panel);
      border-radius: 22px;
      border: 1px solid rgba(33,48,59,0.08);
      box-shadow: var(--shadow);
      padding: 22px;
    }}
    .half {{ grid-column: span 6; }}
    .wide {{ grid-column: span 12; }}
    .stats {{
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    }}
    .stat-card, .summary-tile, .budget-card, .stop-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.74);
      padding: 16px;
    }}
    .stat-card span, .summary-tile span, .budget-card span, .stop-card span {{
      display: block;
      color: var(--muted);
      font-size: 0.9rem;
      margin-bottom: 8px;
    }}
    .stat-card strong, .summary-tile strong, .budget-card strong {{
      font-size: 1.7rem;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 1.4rem;
    }}
    h3 {{
      margin: 22px 0 12px;
      font-size: 1.12rem;
    }}
    .form-grid {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    }}
    form {{
      display: grid;
      gap: 12px;
    }}
    label {{
      display: grid;
      gap: 7px;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    select, input, button {{
      font: inherit;
      border-radius: 12px;
    }}
    select, input {{
      border: 1px solid var(--line);
      padding: 12px 13px;
      background: rgba(255,255,255,0.95);
      color: var(--ink);
    }}
    button {{
      border: 0;
      padding: 13px 18px;
      background: var(--accent);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }}
    .route-banner {{
      margin-top: 18px;
      border-radius: 16px;
      padding: 16px 18px;
      background: linear-gradient(135deg, rgba(47,111,98,0.12), rgba(181,77,38,0.12));
      border: 1px solid rgba(47,111,98,0.14);
      font-weight: 700;
      line-height: 1.6;
    }}
    .summary-grid, .budget-grid, .stops-grid {{
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }}
    .stop-card strong {{
      display: block;
      margin-bottom: 6px;
      font-size: 1.05rem;
    }}
    .stop-card small {{
      display: block;
      color: var(--muted);
      margin-top: 4px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      border-radius: 14px;
      overflow: hidden;
      font-size: 0.96rem;
    }}
    th, td {{
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1px solid #eadfd3;
    }}
    th {{
      text-transform: uppercase;
      letter-spacing: 0.03em;
      font-size: 0.81rem;
      background: #f2e4d5;
    }}
    .note, .empty {{
      color: var(--muted);
      line-height: 1.6;
    }}
    .flash {{
      margin-bottom: 18px;
      padding: 14px 16px;
      border-radius: 14px;
      font-weight: 700;
    }}
    .flash.error {{ background: rgba(160,50,50,0.12); color: var(--danger); }}
    .flash.success {{ background: rgba(29,107,68,0.12); color: var(--success); }}
    @media (max-width: 920px) {{
      .half {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <h1>SceneTrip Planner</h1>
    </section>

    {flash_html}

    <section class="card">
      <h2>Database Snapshot</h2>
      <div class="stats">{summary_html}</div>
      <p class="note">Connection target: <code>{html.escape(DB_USER)}</code> on <code>{html.escape(DB_SOCKET)}</code>, database <code>{html.escape(DB_NAME)}</code>.</p>
    </section>

    <section class="grid">
      <article class="card half">
        <h2>Generate Your Itinerary</h2>
        <form method="POST" action="/plan">
          <div class="form-grid">
            <label>
              Favorite movie
              <input
                name="movie_title"
                list="movie-suggestions"
                value="{html.escape(selected_movie_title)}"
                placeholder="Type a movie title keyword"
                required
              />
              <datalist id="movie-suggestions">
                {''.join(movie_suggestions)}
              </datalist>
            </label>
            <label>
              Budget (USD)
              <input name="budget" type="number" min="200" step="50" value="{html.escape(selected_budget)}" required />
            </label>
            <label>
              Departure city
              <input name="departure_city" value="{html.escape(departure_city)}" placeholder="Chicago, New York, Los Angeles" required />
            </label>
          </div>
          <button type="submit">Build Itinerary</button>
        </form>
      </article>

      <article class="card half">
        <h2>Ready To Plan</h2>
      </article>

      <article class="card wide">
        <h2>Generated Itinerary</h2>
        {render_itinerary(itinerary)}
      </article>
    </section>
  </main>
</body>
</html>"""


class SceneTripHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        flash = None
        if "message" in params:
            flash = FlashMessage(params.get("level", ["success"])[0], params["message"][0])
        db_error = try_connection()
        body = render_page(flash=flash, db_error=db_error)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length).decode("utf-8")
        form = {key: values[0] for key, values in parse_qs(payload).items()}
        try:
            if parsed.path == "/plan":
                movie_title = form.get("movie_title", "").strip()
                movie_row = find_movie_by_title(movie_title)
                movie_id = int(movie_row[0])
                budget = float(form.get("budget", "").strip())
                departure_city = form.get("departure_city", "").strip()
                itinerary = build_itinerary(movie_id, budget, departure_city)
                body = render_page(
                    flash=FlashMessage("success", "Itinerary generated from live database content."),
                    db_error=try_connection(),
                    itinerary=itinerary,
                    departure_city=departure_city,
                    selected_movie_title=movie_row[1],
                    selected_budget=form.get("budget", "1800").strip(),
                )
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))
                return
            self.redirect("/?message=Unknown+action&level=error")
        except Exception as exc:
            self.redirect(f"/?message={quote_plus(str(exc))}&level=error")

    def log_message(self, format: str, *args) -> None:
        return

    def redirect(self, target: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", target)
        self.end_headers()


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), SceneTripHandler)
    print(
        dedent(
            f"""
            SceneTrip web app running.
            Open http://{HOST}:{PORT}
            MySQL socket: {DB_SOCKET}
            Database: {DB_NAME}
            """
        ).strip()
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
