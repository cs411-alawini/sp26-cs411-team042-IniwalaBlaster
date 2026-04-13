USE scenetrip;

-- Baseline: run EXPLAIN ANALYZE on each query before creating any extra index.
-- Then try the following configurations one at a time and record the total cost.

-- Query 1 candidates.
CREATE INDEX idx_movies_rating_movie ON movies (rating, movie_id);
CREATE INDEX idx_movie_locations_location_movie ON movie_locations (location_id, movie_id);
CREATE INDEX idx_flights_source_dest ON flights (source_airport, dest_airport);

-- Query 2 candidates.
CREATE INDEX idx_trip_plans_budget_user ON trip_plans (total_budget, user_id);
CREATE INDEX idx_trip_plan_stops_trip_stop_loc ON trip_plan_stops (trip_plan_id, stop_order, location_id);
CREATE INDEX idx_locations_airport_location ON locations (airport_code, location_id);

-- Query 3 candidates.
CREATE INDEX idx_movie_actors_actor_movie ON movie_actors (actor_id, movie_id);
CREATE INDEX idx_movie_locations_movie_location ON movie_locations (movie_id, location_id);
CREATE INDEX idx_trip_plan_stops_location_trip ON trip_plan_stops (location_id, trip_plan_id);

-- Optional cleanup commands if you want to test each design independently.
-- DROP INDEX idx_movies_rating_movie ON movies;
-- DROP INDEX idx_movie_locations_location_movie ON movie_locations;
-- DROP INDEX idx_flights_source_dest ON flights;
-- DROP INDEX idx_trip_plans_budget_user ON trip_plans;
-- DROP INDEX idx_trip_plan_stops_trip_stop_loc ON trip_plan_stops;
-- DROP INDEX idx_locations_airport_location ON locations;
-- DROP INDEX idx_movie_actors_actor_movie ON movie_actors;
-- DROP INDEX idx_movie_locations_movie_location ON movie_locations;
-- DROP INDEX idx_trip_plan_stops_location_trip ON trip_plan_stops;
