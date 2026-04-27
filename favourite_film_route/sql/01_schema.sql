drop database if exists scenetrip;
create database scenetrip;
use scenetrip;

create table users (
    user_id int primary key,
    username varchar(50) not null unique,
    email varchar(100) not null unique,
    home_airport char(3) not null,
    created_at datetime not null
);

create table movies (
    movie_id int primary key,
    title varchar(120) not null,
    release_year smallint not null,
    rating decimal(3,1) not null,
    runtime_minutes smallint not null,
    primary_genre varchar(40) not null
);

create table actors (
    actor_id int primary key,
    actor_name varchar(100) not null,
    birth_year smallint,
    nationality varchar(60)
);

create table locations (
    location_id int primary key,
    city_name varchar(80) not null,
    state_name varchar(80),
    country_code char(2) not null,
    airport_code char(3) not null,
    latitude decimal(9,6) not null,
    longitude decimal(9,6) not null
);

create table flights (
    flight_id int primary key,
    source_airport char(3) not null,
    dest_airport char(3) not null,
    carrier varchar(50) not null,
    depart_time time not null,
    arrive_time time not null,
    distance_miles int not null,
    daily_frequency tinyint not null,
    constraint chk_distinct_airports check (source_airport <> dest_airport)
);

create table trip_plans (
    trip_plan_id int primary key,
    user_id int not null,
    plan_name varchar(100) not null,
    created_at datetime not null,
    start_airport char(3) not null,
    total_budget decimal(10,2) not null,
    foreign key (user_id) references users(user_id)
);

create table movie_actors (
    movie_id int not null,
    actor_id int not null,
    billing_order tinyint not null,
    primary key (movie_id, actor_id),
    foreign key (movie_id) references movies(movie_id),
    foreign key (actor_id) references actors(actor_id)
);

create table movie_locations (
    movie_id int not null,
    location_id int not null,
    scene_count tinyint not null,
    is_primary_location boolean not null,
    primary key (movie_id, location_id),
    foreign key (movie_id) references movies(movie_id),
    foreign key (location_id) references locations(location_id)
);

create table trip_plan_stops (
    trip_plan_id int not null,
    stop_order tinyint not null,
    location_id int not null,
    planned_days tinyint not null,
    primary key (trip_plan_id, stop_order),
    foreign key (trip_plan_id) references trip_plans(trip_plan_id),
    foreign key (location_id) references locations(location_id)
);

create table booked_flights (
    trip_plan_id int not null,
    leg_order tinyint not null,
    flight_id int not null,
    primary key (trip_plan_id, leg_order),
    foreign key (trip_plan_id) references trip_plans(trip_plan_id),
    foreign key (flight_id) references flights(flight_id)
);
