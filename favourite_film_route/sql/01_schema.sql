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
