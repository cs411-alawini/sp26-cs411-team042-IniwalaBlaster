#!/usr/bin/env python3
from __future__ import annotations

import html
import os
import shlex
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
MYSQL_COMMAND = os.environ.get("SCENETRIP_MYSQL_COMMAND", "mysql")


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
    mysql_command = shlex.split(MYSQL_COMMAND)
    proc = subprocess.run(
        [
            *mysql_command,
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
    if max_legs <= 1:
        return None

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
            path = find_best_path(airport_code, stop_airport, max_legs=1)
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

    # Keep local generation responsive by checking direct flights first, then falling back to transfer legs.
    while remaining and len(chosen_stops) < 3:
        picked_index = None
        picked_path = None
        for idx, stop in enumerate(remaining):
            stop_airport = stop[3]
            if stop_airport == current_airport:
                picked_index = idx
                picked_path = []
                break
            path = find_best_path(current_airport, stop_airport, max_legs=1)
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
        return_path = find_best_path(current_airport, origin_airport, max_legs=1)
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
      --bg: #f6f6f6;
      --panel: #ffffff;
      --panel-head: #eeeeee;
      --ink: #222222;
      --muted: #666666;
      --line: #d7d7d7;
      --line-soft: #e9e9e9;
      --link: #1f73cf;
      --blue: #2f86d7;
      --blue-dark: #176fb9;
      --green: #1f7a50;
      --amber: #956511;
      --danger: #a03232;
      --success: #1d6b44;
      --shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--bg);
      font-family: Arial, "Microsoft YaHei", sans-serif;
      font-size: 14px;
      line-height: 1.5;
    }}
    a {{ color: var(--link); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{
      border: 1px solid var(--line-soft);
      border-radius: 3px;
      background: #fafafa;
      padding: 1px 4px;
      color: #333333;
    }}
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      min-height: 48px;
      align-items: stretch;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
      box-shadow: var(--shadow);
    }}
    .brand {{
      display: flex;
      min-width: 164px;
      align-items: center;
      gap: 9px;
      padding: 0 20px;
      color: #202020;
      font-size: 18px;
      font-weight: 700;
    }}
    .brand:hover {{ text-decoration: none; }}
    .brand-mark {{
      display: grid;
      width: 24px;
      height: 24px;
      place-items: center;
      border: 2px solid #222222;
      color: #222222;
      font-size: 13px;
      line-height: 1;
      transform: rotate(-45deg);
    }}
    .brand-mark span {{ transform: rotate(45deg); }}
    .main-nav {{
      display: flex;
      flex: 1;
      min-width: 0;
    }}
    .nav-link {{
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 0 17px;
      color: #222222;
      font-weight: 700;
      white-space: nowrap;
    }}
    .nav-link:hover,
    .nav-link.active {{
      background: #eeeeee;
      text-decoration: none;
    }}
    .auth-actions {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 16px;
    }}
    .top-status {{
      border: 1px solid var(--line);
      border-radius: 4px;
      background: #f7f7f7;
      padding: 7px 10px;
      color: #333333;
      font-weight: 700;
      white-space: nowrap;
    }}
    .shell {{
      width: min(1160px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 326px;
      gap: 26px;
    }}
    .main-column,
    .side-column {{
      display: flex;
      min-width: 0;
      flex-direction: column;
      gap: 14px;
    }}
    .panel {{
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: var(--panel);
      box-shadow: var(--shadow);
    }}
    .panel-header {{
      display: flex;
      min-height: 42px;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--line);
      background: var(--panel-head);
      padding: 0 14px;
    }}
    .panel-header h1,
    .panel-header h2 {{
      margin: 0;
      color: #111111;
      font-size: 15px;
      font-weight: 700;
    }}
    .panel-body {{ padding: 14px; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      border-top: 1px solid #ffffff;
    }}
    .stat-card {{
      min-height: 70px;
      border-right: 1px solid var(--line-soft);
      border-bottom: 1px solid var(--line-soft);
      padding: 12px;
    }}
    .stat-card:nth-child(2n) {{ border-right: 0; }}
    .stat-card span,
    .summary-tile span,
    .budget-card span,
    .stop-card span {{
      display: block;
      margin-bottom: 5px;
      color: var(--muted);
      font-size: 12px;
    }}
    .stat-card strong {{
      display: block;
      color: #111111;
      font-size: 20px;
    }}
    .summary-tile,
    .budget-card,
    .stop-card {{
      border: 1px solid var(--line);
      border-radius: 4px;
      background: #ffffff;
      padding: 12px;
    }}
    .summary-tile strong,
    .budget-card strong {{
      display: block;
      color: #111111;
      font-size: 16px;
    }}
    .form-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) 140px minmax(0, 1fr);
      gap: 10px;
    }}
    form {{
      display: grid;
      gap: 12px;
    }}
    label {{
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
    }}
    .actions-row {{
      display: grid;
      grid-template-columns: auto 1fr;
      align-items: center;
      gap: 12px;
    }}
    select, input, button {{
      font: inherit;
    }}
    select, input {{
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 9px 13px;
      background: #ffffff;
      color: var(--ink);
      outline: 0;
    }}
    select:focus,
    input:focus {{ border-color: #a8c7e6; box-shadow: 0 0 0 2px rgba(47,134,215,0.12); }}
    button {{
      min-height: 36px;
      border: 1px solid transparent;
      border-radius: 4px;
      padding: 7px 15px;
      background: var(--blue);
      color: #ffffff;
      font-weight: 700;
      cursor: pointer;
    }}
    button:hover {{ background: var(--blue-dark); }}
    .btn-muted {{ background: #dddddd; color: #222222; }}
    .btn-muted:hover {{ background: #d2d2d2; }}
    .note,
    .empty {{
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }}
    .empty {{ padding: 14px; }}
    .compact-note {{ color: var(--muted); font-size: 13px; }}
    .route-banner {{
      margin: 14px 0;
      border: 1px solid #cfe1f3;
      border-radius: 4px;
      padding: 12px 14px;
      background: #f4f9ff;
      color: #1f4f7d;
      font-weight: 700;
      line-height: 1.6;
    }}
    .summary-grid, .budget-grid, .stops-grid {{
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }}
    .itinerary-shell h3 {{
      margin: 16px 0 8px;
      font-size: 14px;
    }}
    .stop-card strong {{
      display: block;
      margin-bottom: 5px;
      color: #111111;
      font-size: 14px;
    }}
    .stop-card small {{
      display: block;
      color: var(--muted);
      margin-top: 3px;
    }}
    table {{
      width: calc(100% - 28px);
      margin: 0 14px 14px;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line-soft);
      vertical-align: middle;
    }}
    th {{
      color: #111111;
      font-weight: 700;
      background: #ffffff;
    }}
    td:last-child,
    th:last-child {{ text-align: right; }}
    .rank-table {{
      width: 100%;
      margin: 0;
    }}
    .rank-table th,
    .rank-table td {{ padding: 8px 0; }}
    .rank-table th:last-child,
    .rank-table td:last-child {{ text-align: right; }}
    .status-list {{
      margin: 0;
      padding: 0;
      list-style: none;
    }}
    .status-list li {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid var(--line-soft);
      padding: 8px 0;
    }}
    .status-list li:last-child {{ border-bottom: 0; }}
    .tag {{
      display: inline-flex;
      min-width: 64px;
      justify-content: center;
      border: 1px solid currentColor;
      border-radius: 3px;
      padding: 2px 6px;
      color: var(--green);
      background: #edf8f2;
      font-size: 12px;
      font-weight: 700;
    }}
    .flash {{
      margin-bottom: 14px;
      border: 1px solid currentColor;
      border-radius: 4px;
      padding: 11px 14px;
      font-weight: 700;
    }}
    .flash.error {{ background: rgba(160,50,50,0.12); color: var(--danger); }}
    .flash.success {{ background: rgba(29,107,68,0.12); color: var(--success); }}
    @media (max-width: 920px) {{
      .topbar {{ flex-wrap: wrap; }}
      .brand {{ min-height: 48px; }}
      .main-nav {{
        order: 3;
        width: 100%;
        overflow-x: auto;
        border-top: 1px solid var(--line-soft);
      }}
      .nav-link {{ min-height: 42px; }}
      .auth-actions {{ margin-left: auto; }}
      .shell {{
        width: calc(100vw - 20px);
        padding-top: 16px;
      }}
      .grid {{ grid-template-columns: 1fr; gap: 14px; }}
      .form-grid {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <a class="brand" href="/" aria-label="SceneTrip home">
      <span class="brand-mark"><span>S</span></span>
      <span>SceneTrip</span>
    </a>
    <nav class="main-nav" aria-label="Primary navigation">
      <a class="nav-link active" href="/">Home</a>
      <a class="nav-link" href="#planner">Planner</a>
      <a class="nav-link" href="#itinerary">Itinerary</a>
      <a class="nav-link" href="#database">Database</a>
    </nav>
    <div class="auth-actions" aria-label="Application status">
      <span class="top-status">Stage 4.1</span>
    </div>
  </header>

  <main class="shell">
    {flash_html}
    <section class="grid">
      <div class="main-column">
        <section class="panel" id="planner">
          <header class="panel-header">
            <h1>Trip Planner</h1>
          </header>
          <div class="panel-body">
            <form method="POST" action="/plan">
              <div class="form-grid">
                <label>
                  Favorite movie
                  <input
                    name="movie_title"
                    list="movie-suggestions"
                    value="{html.escape(selected_movie_title)}"
                    placeholder="Movie title"
                    required
                  />
                  <datalist id="movie-suggestions">
                    {''.join(movie_suggestions)}
                  </datalist>
                </label>
                <label>
                  Budget
                  <input name="budget" type="number" min="200" step="50" value="{html.escape(selected_budget)}" required />
                </label>
                <label>
                  Departure city
                  <input name="departure_city" value="{html.escape(departure_city)}" placeholder="City name" required />
                </label>
              </div>
              <div class="actions-row">
                <button type="submit">Build Itinerary</button>
                <span class="compact-note">Uses the live MySQL data loaded for Stage 4.</span>
              </div>
            </form>
          </div>
        </section>

        <section class="panel" id="itinerary">
          <header class="panel-header">
            <h2>Generated Itinerary</h2>
          </header>
          <div class="panel-body">
            {render_itinerary(itinerary)}
          </div>
        </section>
      </div>

      <aside class="side-column">
        <section class="panel" id="database">
          <header class="panel-header">
            <h2>Database Snapshot</h2>
          </header>
          <div class="stats">{summary_html}</div>
        </section>

        <section class="panel">
          <header class="panel-header">
            <h2>Connection</h2>
            <span class="tag">Live</span>
          </header>
          <div class="panel-body">
            <ul class="status-list">
              <li><span>User</span><strong>{html.escape(DB_USER)}</strong></li>
              <li><span>Port</span><strong>{html.escape(DB_PORT)}</strong></li>
              <li><span>Database</span><strong>{html.escape(DB_NAME)}</strong></li>
            </ul>
          </div>
        </section>
      </aside>
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
