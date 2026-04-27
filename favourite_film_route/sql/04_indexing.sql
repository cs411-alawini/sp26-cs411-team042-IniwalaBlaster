use scenetrip;

-- Baseline: run EXPLAIN ANALYZE on each query before creating any extra index.
-- Then try the following configurations one at a time and record the total cost.

-- Query 1 candidates.
create index idx_movies_rating_movie on movies (rating, movie_id);
create index idx_movie_locations_location_movie on movie_locations (location_id, movie_id);
create index idx_flights_source_dest on flights (source_airport, dest_airport);

-- Query 2 candidates.
create index idx_trip_plans_budget_user on trip_plans (total_budget, user_id);
create index idx_trip_plan_stops_trip_stop_loc on trip_plan_stops (trip_plan_id, stop_order, location_id);
create index idx_locations_airport_location on locations (airport_code, location_id);

-- Query 3 candidates.
create index idx_movie_actors_actor_movie on movie_actors (actor_id, movie_id);
create index idx_movie_locations_movie_location on movie_locations (movie_id, location_id);
create index idx_trip_plan_stops_location_trip on trip_plan_stops (location_id, trip_plan_id);

-- Optional cleanup commands if you want to test each design independently.
-- drop index idx_movies_rating_movie on movies;
-- drop index idx_movie_locations_location_movie on movie_locations;
-- drop index idx_flights_source_dest on flights;
-- drop index idx_trip_plans_budget_user on trip_plans;
-- drop index idx_trip_plan_stops_trip_stop_loc on trip_plan_stops;
-- drop index idx_locations_airport_location on locations;
-- drop index idx_movie_actors_actor_movie on movie_actors;
-- drop index idx_movie_locations_movie_location on movie_locations;
-- drop index idx_trip_plan_stops_location_trip on trip_plan_stops;
