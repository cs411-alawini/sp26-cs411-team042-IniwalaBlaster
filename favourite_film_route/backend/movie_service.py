from db import mysql_query, sql_escape


def get_summary_cards() -> dict:
    queries = {
        "movies": "SELECT COUNT(*) FROM movies;",
        "locations": "SELECT COUNT(*) FROM locations;",
        "flights": "SELECT COUNT(*) FROM flights;",
        "movie_links": "SELECT COUNT(*) FROM movie_locations;",
    }

    result = {}
    for label, query in queries.items():
        result[label] = int(mysql_query(query)[0][0])

    return result


def get_featured_movies(limit: int = 50) -> list[dict]:
    rows = mysql_query(
        f"""
        SELECT
            m.title,
            MIN(m.movie_id) AS movie_id,
            ROUND(MAX(m.rating), 1) AS rating,
            SUBSTRING_INDEX(
                GROUP_CONCAT(DISTINCT m.primary_genre ORDER BY m.primary_genre SEPARATOR ', '),
                ',',
                1
            ) AS primary_genre,
            COUNT(DISTINCT ml.location_id) AS filming_stop_count
        FROM movies m
        JOIN movie_locations ml ON ml.movie_id = m.movie_id
        GROUP BY m.title
        ORDER BY MAX(m.rating) DESC, filming_stop_count DESC, m.title
        LIMIT {limit};
        """
    )

    movies = []
    for row in rows:
        movies.append(
            {
                "title": row[0],
                "movie_id": int(row[1]),
                "rating": float(row[2]),
                "primary_genre": row[3],
                "filming_stop_count": int(row[4]),
            }
        )

    return movies


def find_movie_by_title(movie_title: str) -> dict:
    title = sql_escape(movie_title.strip())

    rows = mysql_query(
        f"""
        SELECT
            MIN(m.movie_id) AS movie_id,
            m.title,
            ROUND(MAX(m.rating), 1) AS rating,
            SUBSTRING_INDEX(
                GROUP_CONCAT(DISTINCT m.primary_genre ORDER BY m.primary_genre SEPARATOR ', '),
                ',',
                1
            ) AS primary_genre
        FROM movies m
        JOIN movie_locations ml ON ml.movie_id = m.movie_id
        WHERE m.title = '{title}'
        GROUP BY m.title
        LIMIT 1;
        """
    )

    if not rows:
        rows = mysql_query(
            f"""
            SELECT
                MIN(m.movie_id) AS movie_id,
                m.title,
                ROUND(MAX(m.rating), 1) AS rating,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(DISTINCT m.primary_genre ORDER BY m.primary_genre SEPARATOR ', '),
                    ',',
                    1
                ) AS primary_genre
            FROM movies m
            JOIN movie_locations ml ON ml.movie_id = m.movie_id
            WHERE m.title LIKE '%{title}%'
            GROUP BY m.title
            ORDER BY MAX(m.rating) DESC, m.title
            LIMIT 1;
            """
        )

    if not rows:
        raise RuntimeError("No matching movie title was found.")

    row = rows[0]
    return {
        "movie_id": int(row[0]),
        "title": row[1],
        "rating": float(row[2]),
        "primary_genre": row[3],
    }


def get_movie_by_id(movie_id: int) -> dict:
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

    row = rows[0]
    return {
        "movie_id": int(row[0]),
        "title": row[1],
        "rating": float(row[2]),
        "primary_genre": row[3],
    }