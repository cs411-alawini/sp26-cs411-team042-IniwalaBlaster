USE scenetrip;

-- Query 1: filming destinations with strong movie quality and outbound connectivity.
SELECT
    l.city_name,
    l.state_name,
    l.airport_code,
    COUNT(DISTINCT ml.movie_id) AS movies_filmed,
    ROUND(AVG(m.rating), 2) AS avg_movie_rating,
    COUNT(DISTINCT CONCAT(f.source_airport, '-', f.dest_airport)) AS outbound_routes
FROM locations AS l
JOIN movie_locations AS ml
    ON l.location_id = ml.location_id
JOIN movies AS m
    ON ml.movie_id = m.movie_id
JOIN flights AS f
    ON l.airport_code = f.source_airport
WHERE m.rating >= 7.5
GROUP BY l.city_name, l.state_name, l.airport_code
HAVING COUNT(DISTINCT ml.movie_id) >= 3
ORDER BY avg_movie_rating DESC, outbound_routes DESC, l.city_name
LIMIT 15;

-- Query 2: trip plans whose consecutive stops all have available flights and whose
-- filming locations beat the overall average movie rating.
SELECT
    tp.trip_plan_id,
    tp.plan_name,
    u.username,
    COUNT(DISTINCT tps.location_id) AS stop_count,
    ROUND(AVG(m.rating), 2) AS avg_filming_rating
FROM trip_plans AS tp
JOIN users AS u
    ON tp.user_id = u.user_id
JOIN trip_plan_stops AS tps
    ON tp.trip_plan_id = tps.trip_plan_id
JOIN movie_locations AS ml
    ON tps.location_id = ml.location_id
JOIN movies AS m
    ON ml.movie_id = m.movie_id
WHERE tp.total_budget <= 2500
  AND NOT EXISTS (
      SELECT 1
      FROM trip_plan_stops AS s1
      JOIN trip_plan_stops AS s2
          ON s1.trip_plan_id = s2.trip_plan_id
         AND s2.stop_order = s1.stop_order + 1
      JOIN locations AS l1
          ON l1.location_id = s1.location_id
      JOIN locations AS l2
          ON l2.location_id = s2.location_id
      LEFT JOIN flights AS f
          ON f.source_airport = l1.airport_code
         AND f.dest_airport = l2.airport_code
      WHERE s1.trip_plan_id = tp.trip_plan_id
        AND f.flight_id IS NULL
  )
GROUP BY tp.trip_plan_id, tp.plan_name, u.username
HAVING AVG(m.rating) > (
    SELECT AVG(rating)
    FROM movies
)
ORDER BY stop_count DESC, avg_filming_rating DESC, tp.trip_plan_id
LIMIT 15;

-- Query 3: actors whose movies are tied to above-average airport connectivity
-- and appear in at least two trip plans.
SELECT
    a.actor_id,
    a.actor_name,
    COUNT(DISTINCT m.movie_id) AS movie_count,
    COUNT(DISTINCT tp.trip_plan_id) AS featured_trip_plans,
    ROUND(AVG(conn.route_count), 2) AS avg_city_connectivity
FROM actors AS a
JOIN movie_actors AS ma
    ON a.actor_id = ma.actor_id
JOIN movies AS m
    ON ma.movie_id = m.movie_id
JOIN movie_locations AS ml
    ON m.movie_id = ml.movie_id
JOIN locations AS l
    ON ml.location_id = l.location_id
JOIN (
    SELECT source_airport, COUNT(*) AS route_count
    FROM flights
    GROUP BY source_airport
) AS conn
    ON conn.source_airport = l.airport_code
LEFT JOIN trip_plan_stops AS tps
    ON ml.location_id = tps.location_id
LEFT JOIN trip_plans AS tp
    ON tps.trip_plan_id = tp.trip_plan_id
WHERE conn.route_count > (
    SELECT AVG(route_total)
    FROM (
        SELECT COUNT(*) AS route_total
        FROM flights
        GROUP BY source_airport
    ) AS route_stats
)
GROUP BY a.actor_id, a.actor_name
HAVING COUNT(DISTINCT tp.trip_plan_id) >= 2
ORDER BY avg_city_connectivity DESC, movie_count DESC, a.actor_name
LIMIT 15;
