#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from config import HOST, PORT
from db import mysql_query, sql_escape
from movie_service import get_summary_cards, get_featured_movies, find_movie_by_title
from itinerary_service import build_itinerary


def normalize_summary(raw):
    if isinstance(raw, dict):
        return raw

    result = {}
    for label, value in raw:
        key = (
            str(label)
            .lower()
            .replace(" ", "_")
            .replace("filming_locations", "locations")
            .replace("routes", "flights")
        )
        result[key] = int(value)
    return result


def normalize_movies(raw):
    movies = []

    for item in raw:
        if isinstance(item, dict):
            movies.append(item)
        else:
            title, movie_id, rating, genre, filming_stop_count = item
            movies.append(
                {
                    "title": title,
                    "movie_id": int(movie_id),
                    "rating": float(rating),
                    "primary_genre": genre,
                    "filming_stop_count": int(filming_stop_count),
                }
            )

    return movies


def normalize_itinerary(plan):
    if is_dataclass(plan):
        data = asdict(plan)
    elif isinstance(plan, dict):
        data = plan
    else:
        raise RuntimeError("Unsupported itinerary response format.")

    if "stop_rows" in data and "stops" not in data:
        data["stops"] = data.pop("stop_rows")

    if "leg_rows" in data and "legs" not in data:
        data["legs"] = data.pop("leg_rows")

    if "budget" not in data:
        data["budget"] = {
            "flight_budget": data.get("flight_budget", 0),
            "hotel_budget": data.get("hotel_budget", 0),
            "local_budget": data.get("local_budget", 0),
            "total_estimated_budget": data.get("total_estimated_budget", 0),
            "budget_status": data.get("budget_status", ""),
        }

    return data

def find_user(identifier: str):
    identifier = sql_escape(identifier.strip())

    rows = mysql_query(
        f"""
        SELECT user_id, username, email, home_airport, created_at
        FROM users
        WHERE username = '{identifier}'
           OR email = '{identifier}'
        LIMIT 1;
        """
    )

    if not rows:
        return None

    row = rows[0]

    return {
        "user_id": int(row[0]),
        "username": row[1],
        "email": row[2],
        "home_airport": row[3],
        "created_at": row[4],
    }


def get_demo_users(limit: int = 12):
    rows = mysql_query(
        f"""
        SELECT user_id, username, email, home_airport, created_at
        FROM users
        ORDER BY user_id
        LIMIT {limit};
        """
    )

    users = []

    for row in rows:
        users.append(
            {
                "user_id": int(row[0]),
                "username": row[1],
                "email": row[2],
                "home_airport": row[3],
                "created_at": row[4],
            }
        )

    return users

def send_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


class SceneTripAPIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_json(self, HTTPStatus.OK, {"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        try:
            if parsed.path == "/api/health":
                mysql_query("SELECT 1;")
                send_json(self, HTTPStatus.OK, {"status": "ok"})
                return

            if parsed.path == "/api/summary":
                summary = normalize_summary(get_summary_cards())
                send_json(self, HTTPStatus.OK, summary)
                return

            if parsed.path == "/api/movies/featured":
                limit = int(params.get("limit", ["80"])[0])
                movies = normalize_movies(get_featured_movies(limit))
                send_json(self, HTTPStatus.OK, {"movies": movies})
                return
            if parsed.path == "/api/users/demo":
                limit = int(params.get("limit", ["12"])[0])
                users = get_demo_users(limit)
                send_json(self, HTTPStatus.OK, {"users": users})
                return

            send_json(self, HTTPStatus.NOT_FOUND, {"error": "Unknown API endpoint"})

        except Exception as exc:
            send_json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def do_POST(self):
        parsed = urlparse(self.path)

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(raw_body or "{}")
            if parsed.path == "/api/login":
                identifier = data.get("identifier", "").strip()

                if not identifier:
                    raise RuntimeError("Username or email is required.")

                user = find_user(identifier)

                if user is None:
                    raise RuntimeError("No matching user was found.")

                send_json(
                    self,
                    HTTPStatus.OK,
                    {
                        "message": "Login successful.",
                        "user": user,
                    },
                )
                return

            if parsed.path == "/api/itinerary":
                movie_title = data.get("movie_title", "").strip()
                departure_city = data.get("departure_city", "").strip()
                budget = float(data.get("budget", 1800))

                if not movie_title:
                    raise RuntimeError("Movie title is required.")

                if not departure_city:
                    raise RuntimeError("Departure city is required.")

                movie_row = find_movie_by_title(movie_title)

                if isinstance(movie_row, dict):
                    movie_id = int(movie_row["movie_id"])
                else:
                    movie_id = int(movie_row[0])

                itinerary = build_itinerary(movie_id, budget, departure_city)
                send_json(self, HTTPStatus.OK, normalize_itinerary(itinerary))
                return

            send_json(self, HTTPStatus.NOT_FOUND, {"error": "Unknown API endpoint"})

        except Exception as exc:
            send_json(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def log_message(self, format, *args):
        return


def main():
    server = ThreadingHTTPServer((HOST, PORT), SceneTripAPIHandler)

    print(f"SceneTrip API running at http://{HOST}:{PORT}")
    print("Available endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/summary")
    print("  GET  /api/movies/featured")
    print("  POST /api/itinerary")

    server.serve_forever()


if __name__ == "__main__":
    main()