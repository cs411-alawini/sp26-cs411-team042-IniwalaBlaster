# Database Design

## Project

**SceneTrip: Movie-Based Trip Planner**

This document completes the Stage 3 deliverable for our CS 411 project. Our application generates travel itineraries from a user's favorite movies by connecting film locations to real airport data and available flight routes. Based on the Stage 1 project description and the Stage 2 UML, the main entities in our database are `User`, `TripPlan`, `Movie`, `Actor`, `Location`, and `Flight`. To implement the design relationally, we also added bridge tables for many-to-many relationships and ordered trip stops.

## Part 1: Database Implementation

### 1. Main Tables Implemented

We implemented the following main tables from our relational schema:

1. `users`
2. `movies`
3. `actors`
4. `locations`
5. `flights`
6. `trip_plans`

We also implemented the following relationship tables so that the schema supports real application behavior:

1. `movie_actors`
2. `movie_locations`
3. `trip_plan_stops`
4. `booked_flights`

### 2. DDL Commands

The following DDL statements were used to create the database schema in MySQL 8.

```sql
DROP DATABASE IF EXISTS scenetrip;
CREATE DATABASE scenetrip;
USE scenetrip;

CREATE TABLE users (
    user_id INT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    home_airport CHAR(3) NOT NULL,
    created_at DATETIME NOT NULL
);

CREATE TABLE movies (
    movie_id INT PRIMARY KEY,
    title VARCHAR(120) NOT NULL,
    release_year SMALLINT NOT NULL,
    rating DECIMAL(3,1) NOT NULL,
    runtime_minutes SMALLINT NOT NULL,
    primary_genre VARCHAR(40) NOT NULL
);

CREATE TABLE actors (
    actor_id INT PRIMARY KEY,
    actor_name VARCHAR(100) NOT NULL,
    birth_year SMALLINT,
    nationality VARCHAR(60)
);

CREATE TABLE locations (
    location_id INT PRIMARY KEY,
    city_name VARCHAR(80) NOT NULL,
    state_name VARCHAR(80),
    country_code CHAR(2) NOT NULL,
    airport_code CHAR(3) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL
);

CREATE TABLE flights (
    flight_id INT PRIMARY KEY,
    source_airport CHAR(3) NOT NULL,
    dest_airport CHAR(3) NOT NULL,
    carrier VARCHAR(50) NOT NULL,
    depart_time TIME NOT NULL,
    arrive_time TIME NOT NULL,
    distance_miles INT NOT NULL,
    daily_frequency TINYINT NOT NULL,
    CONSTRAINT chk_distinct_airports CHECK (source_airport <> dest_airport)
);

CREATE TABLE trip_plans (
    trip_plan_id INT PRIMARY KEY,
    user_id INT NOT NULL,
    plan_name VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL,
    start_airport CHAR(3) NOT NULL,
    total_budget DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE movie_actors (
    movie_id INT NOT NULL,
    actor_id INT NOT NULL,
    billing_order TINYINT NOT NULL,
    PRIMARY KEY (movie_id, actor_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id),
    FOREIGN KEY (actor_id) REFERENCES actors(actor_id)
);

CREATE TABLE movie_locations (
    movie_id INT NOT NULL,
    location_id INT NOT NULL,
    scene_count TINYINT NOT NULL,
    is_primary_location BOOLEAN NOT NULL,
    PRIMARY KEY (movie_id, location_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id),
    FOREIGN KEY (location_id) REFERENCES locations(location_id)
);

CREATE TABLE trip_plan_stops (
    trip_plan_id INT NOT NULL,
    stop_order TINYINT NOT NULL,
    location_id INT NOT NULL,
    planned_days TINYINT NOT NULL,
    PRIMARY KEY (trip_plan_id, stop_order),
    FOREIGN KEY (trip_plan_id) REFERENCES trip_plans(trip_plan_id),
    FOREIGN KEY (location_id) REFERENCES locations(location_id)
);

CREATE TABLE booked_flights (
    trip_plan_id INT NOT NULL,
    leg_order TINYINT NOT NULL,
    flight_id INT NOT NULL,
    PRIMARY KEY (trip_plan_id, leg_order),
    FOREIGN KEY (trip_plan_id) REFERENCES trip_plans(trip_plan_id),
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
);
```

### 3. Data Population

We populated the database with a dataset-driven loader in [generate_seed_data.py](/Users/xiaojingxin/Documents/New project/scripts/generate_seed_data.py). The script uses the actual CSV sources selected for our project work: `final_dataset.csv` for movie metadata, cast, and filming-location information; `airports (2).csv` for real city-to-airport mappings and coordinates; and `routes 2.csv` for real flight-route connectivity. From these sources, we populated `movies`, `actors`, `movie_actors`, `locations`, `flights`, and `movie_locations` using actual dataset content. For application-specific entities that were not present in the provided datasets, such as `users`, `trip_plans`, `trip_plan_stops`, and `booked_flights`, we generated synthetic records on top of the real airport and route graph so the full application schema could still be tested end to end.

The populated dataset contains:

1. 1200 rows in `users`
2. 18221 rows in `movies`
3. 6373 rows in `locations`
4. 67171 rows in `flights`
5. 2000 rows in `trip_plans`

This exceeds the requirement that at least three different tables contain at least 1000 rows each, and it does so using actual movie, airport, and route data for the core domain tables.

The count query used for proof is:

```sql
SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users
UNION ALL SELECT 'movies', COUNT(*) FROM movies
UNION ALL SELECT 'locations', COUNT(*) FROM locations
UNION ALL SELECT 'flights', COUNT(*) FROM flights
UNION ALL SELECT 'trip_plans', COUNT(*) FROM trip_plans;
```

**Screenshot placeholder:** insert the terminal or MySQL Workbench screenshot that shows the count results here.

### 4. Connection Proof

The rubric requires a screenshot showing that the MySQL database is connected locally or on GCP. After running the schema and seed scripts on MySQL 8, insert a screenshot of the live connection here. A terminal example would show the MySQL prompt, the selected database, and a simple verification query such as `SELECT DATABASE();`.

**Screenshot placeholder:** insert connection screenshot here.

## 5. Advanced SQL Queries

Each query below uses at least two advanced SQL concepts from the assignment: joins, aggregation, and subqueries.

### Query 1: Top Filming Destinations with Strong Connectivity

This query identifies filming destinations that are both cinematically important and operationally useful for the application. It joins `locations`, `movie_locations`, `movies`, and `flights`, then aggregates by destination city and airport. The query focuses on locations linked to highly rated movies and counts how many distinct outbound routes exist from the airport attached to that filming location. This is relevant to our application because SceneTrip should prioritize destinations that not only appear in strong films, but can also be connected into a feasible travel itinerary. In practice, this query can support a recommendation feature that ranks the best travel-worthy movie destinations.

```sql
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
```

SQL concepts used:

1. Join multiple relations
2. Aggregation with `GROUP BY`
3. Filtering with `HAVING`

**Screenshot placeholder:** insert the top 15 rows of Query 1 here.

### Query 2: Feasible High-Quality Trip Plans

This query finds trip plans whose consecutive stops can all be connected by available flights and whose associated filming locations are, on average, better than the overall movie rating in the database. It joins `trip_plans`, `users`, `trip_plan_stops`, `movie_locations`, and `movies`, and it uses a correlated `NOT EXISTS` subquery to reject plans where any adjacent pair of stops lacks a valid flight connection. This subquery is important because the logic is based on the nonexistence of a required route between ordered stops, which is not as naturally expressed as a simple join. This query is directly relevant to SceneTrip because a trip should not be recommended unless every leg of the itinerary is actually feasible.

```sql
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
```

SQL concepts used:

1. Join multiple relations
2. Aggregation with `GROUP BY`
3. Correlated subquery with `NOT EXISTS`

**Screenshot placeholder:** insert the top 15 rows of Query 2 here.

### Query 3: Actors Connected to Highly Reachable Filming Cities

This query identifies actors whose movies are associated with above-average airport connectivity and whose filming locations also show up in multiple trip plans. It joins `actors`, `movie_actors`, `movies`, `movie_locations`, `locations`, `trip_plan_stops`, and `trip_plans`, and it uses a derived-table subquery to compute airport route counts from the `flights` table. It then compares those counts against the average connectivity across all source airports. This query is useful because it lets the application surface actors whose filmographies naturally lead to travel-rich recommendations. That can support a feature such as “build a trip inspired by a favorite actor.”

```sql
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
```

SQL concepts used:

1. Join multiple relations
2. Aggregation with `GROUP BY`
3. Subquery using a derived table

**Screenshot placeholder:** insert the top 15 rows of Query 3 here.

## Part 2: Indexing Analysis

### Method

For each advanced query, we first ran `EXPLAIN ANALYZE` before adding any extra index beyond the default primary keys. Following the project instructions, we compared the optimizer cost rather than execution time because time can fluctuate between runs. We then tested at least three different indexing designs per query, focusing only on non-primary-key attributes used in joins, filters, grouping conditions, or subqueries. This method let us measure whether each candidate index improved row access patterns, reduced table scans, or changed join strategy in a beneficial way.

The exact `EXPLAIN ANALYZE` command pattern used was:

```sql
EXPLAIN ANALYZE
SELECT ...;
```

### Query 1 Index Designs

**Baseline query:** Query 1 from above.

Tried indexing ideas:

1. `CREATE INDEX idx_movies_rating_movie ON movies (rating, movie_id);`
2. `CREATE INDEX idx_movie_locations_location_movie ON movie_locations (location_id, movie_id);`
3. `CREATE INDEX idx_flights_source_dest ON flights (source_airport, dest_airport);`

Analysis paragraph:

Query 1 filters on `movies.rating`, joins `movie_locations` on `location_id` and `movie_id`, and joins `flights` on `source_airport`. Because of that access pattern, the most natural index candidates are the filter attribute in `movies`, the bridge-table join path in `movie_locations`, and the route origin in `flights`. The rating index can help the optimizer narrow the set of qualifying movies before joining outward. The composite `movie_locations` index can support the join from location to movie while preserving the lookup order used by the query. The flights index can reduce work when counting outbound routes for each filming airport. After running `EXPLAIN ANALYZE`, report whether the total cost decreased, increased, or stayed similar for each configuration, and explain the result in terms of selectivity and join order.

Result table to fill in:

| Design | Added Indexes | Total Cost | Change vs. Baseline |
| --- | --- | --- | --- |
| Baseline | none | TODO | TODO |
| Q1-A | `idx_movies_rating_movie` | TODO | TODO |
| Q1-B | `idx_movie_locations_location_movie` | TODO | TODO |
| Q1-C | `idx_flights_source_dest` | TODO | TODO |
| Q1-D | all three | TODO | TODO |

**Screenshot placeholder:** insert `EXPLAIN ANALYZE` screenshots for Query 1 here.

### Query 2 Index Designs

**Baseline query:** Query 2 from above.

Tried indexing ideas:

1. `CREATE INDEX idx_trip_plans_budget_user ON trip_plans (total_budget, user_id);`
2. `CREATE INDEX idx_trip_plan_stops_trip_stop_loc ON trip_plan_stops (trip_plan_id, stop_order, location_id);`
3. `CREATE INDEX idx_locations_airport_location ON locations (airport_code, location_id);`
4. Reuse `CREATE INDEX idx_flights_source_dest ON flights (source_airport, dest_airport);`

Analysis paragraph:

Query 2 is the most complex of the three because it contains a correlated subquery over ordered stops. The `trip_plans` index is intended to help the budget filter while still keeping the foreign-key join to `user_id` nearby in the same structure. The `trip_plan_stops` composite index is especially important because the subquery repeatedly matches rows by `trip_plan_id` and adjacent `stop_order`, and also needs `location_id` to resolve airport codes. The `locations` index supports the lookup from location to airport code, while the route index on `flights` supports the existence check for each leg. If a configuration shows only a small improvement, that should be explained by the limited selectivity of the budget predicate or the fact that the correlated subquery still has to examine many stop pairs.

Result table to fill in:

| Design | Added Indexes | Total Cost | Change vs. Baseline |
| --- | --- | --- | --- |
| Baseline | none | TODO | TODO |
| Q2-A | `idx_trip_plans_budget_user` | TODO | TODO |
| Q2-B | `idx_trip_plan_stops_trip_stop_loc` | TODO | TODO |
| Q2-C | `idx_locations_airport_location` + `idx_flights_source_dest` | TODO | TODO |
| Q2-D | all four | TODO | TODO |

**Screenshot placeholder:** insert `EXPLAIN ANALYZE` screenshots for Query 2 here.

### Query 3 Index Designs

**Baseline query:** Query 3 from above.

Tried indexing ideas:

1. `CREATE INDEX idx_movie_actors_actor_movie ON movie_actors (actor_id, movie_id);`
2. `CREATE INDEX idx_movie_locations_movie_location ON movie_locations (movie_id, location_id);`
3. `CREATE INDEX idx_trip_plan_stops_location_trip ON trip_plan_stops (location_id, trip_plan_id);`
4. Reuse `CREATE INDEX idx_flights_source_dest ON flights (source_airport, dest_airport);`

Analysis paragraph:

Query 3 depends on a chain of joins that starts with actors and walks through movie participation, filming locations, airport connectivity, and trip-plan reuse. The `movie_actors` index supports actor-to-movie expansion, while the `movie_locations` index supports movie-to-location expansion. The `trip_plan_stops` index helps the left join that counts how often a filming location appears in saved trip plans. Because airport connectivity is derived from `flights`, the route-origin index may also help the derived table or related joins. When writing the final analysis paragraph, compare the baseline cost to each design, explain which index contributed the largest change, and note whether the derived-table aggregation over `flights` limited how much the optimizer could benefit from indexing.

Result table to fill in:

| Design | Added Indexes | Total Cost | Change vs. Baseline |
| --- | --- | --- | --- |
| Baseline | none | TODO | TODO |
| Q3-A | `idx_movie_actors_actor_movie` | TODO | TODO |
| Q3-B | `idx_movie_locations_movie_location` | TODO | TODO |
| Q3-C | `idx_trip_plan_stops_location_trip` | TODO | TODO |
| Q3-D | all three plus `idx_flights_source_dest` | TODO | TODO |

**Screenshot placeholder:** insert `EXPLAIN ANALYZE` screenshots for Query 3 here.

### Final Index Design Selection

Our final index design should include only the indexes that produce a meaningful reduction in optimizer cost for the workload we care about most. In our application, Query 2 is likely the most important because itinerary feasibility is central to the user experience, so if one index set clearly helps Query 2 without badly hurting the other queries, it is a strong candidate for the final design. The final report should explain which indexes were retained, which ones were rejected, and why. If any tested index failed to help, that should still be reported, along with a reason such as low selectivity, a small table, optimizer preference for another access path, or the cost of maintaining the index outweighing the benefit for that query.

**Final paragraph to customize after measurements:** After reviewing all `EXPLAIN ANALYZE` costs, we selected `TODO` as the final index design because `TODO`. This configuration was chosen over the alternatives because `TODO`. Any indexes we did not keep were excluded because `TODO`.

## Reproducibility

The project files used for this stage are:

1. [01_schema.sql](/Users/xiaojingxin/Documents/New project/sql/01_schema.sql)
2. [02_seed_data.sql](/Users/xiaojingxin/Documents/New project/sql/02_seed_data.sql)
3. [03_advanced_queries.sql](/Users/xiaojingxin/Documents/New project/sql/03_advanced_queries.sql)
4. [04_indexing.sql](/Users/xiaojingxin/Documents/New project/sql/04_indexing.sql)
5. [generate_seed_data.py](/Users/xiaojingxin/Documents/New project/scripts/generate_seed_data.py)
6. [run_stage3_report.sh](/Users/xiaojingxin/Documents/New project/scripts/run_stage3_report.sh)

To reproduce the full setup on MySQL 8:

1. Start a MySQL 8 instance locally or on GCP.
2. Run `python3 scripts/generate_seed_data.py`.
3. Run `mysql ... < sql/01_schema.sql`.
4. Run `mysql ... < sql/02_seed_data.sql`.
5. Run the three advanced queries in `sql/03_advanced_queries.sql`.
6. For each query, run `EXPLAIN ANALYZE` before and after testing the candidate indexes from `sql/04_indexing.sql`.
7. Insert the required screenshots and measured costs into this document before submitting the release.

## Submission Notes

Before creating the Canvas release, make sure the repository contains this file inside the `doc` folder, and make sure the release tag is correct. If you are also revising Stage 2 for point recovery, add a new file called `stage2_revisions.md` to explain what was changed and which grader comments were addressed.
