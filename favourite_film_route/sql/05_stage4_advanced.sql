use scenetrip;

create table if not exists app_users (
    app_user_id int auto_increment primary key,
    username varchar(50) not null unique,
    password_hash char(64) not null,
    home_city varchar(80),
    created_at datetime not null default current_timestamp
);

create table if not exists app_sessions (
    session_token char(64) primary key,
    app_user_id int not null,
    created_at datetime not null default current_timestamp,
    expires_at datetime not null,
    foreign key (app_user_id) references app_users(app_user_id) on delete cascade
);

create table if not exists saved_trip_plans (
    saved_plan_id int auto_increment primary key,
    app_user_id int not null,
    movie_id int not null,
    plan_name varchar(100) not null,
    departure_city varchar(80) not null,
    departure_airport varchar(8) not null,
    budget decimal(10,2) not null,
    total_estimated_budget decimal(10,2) not null,
    total_days int not null,
    status varchar(24) not null default 'draft',
    created_at datetime not null default current_timestamp,
    updated_at datetime not null default current_timestamp on update current_timestamp,
    foreign key (app_user_id) references app_users(app_user_id) on delete cascade,
    foreign key (movie_id) references movies(movie_id),
    check (budget > 0),
    check (total_estimated_budget >= 0),
    check (total_days > 0)
);

create table if not exists saved_trip_stops (
    saved_plan_id int not null,
    stop_order int not null,
    location_id int not null,
    airport_code varchar(8) not null,
    recommended_days int not null,
    primary key (saved_plan_id, stop_order),
    foreign key (saved_plan_id) references saved_trip_plans(saved_plan_id) on delete cascade,
    foreign key (location_id) references locations(location_id),
    check (recommended_days > 0)
);

create table if not exists stage4_audit_log (
    audit_id int auto_increment primary key,
    event_type varchar(40) not null,
    saved_plan_id int,
    app_user_id int,
    detail varchar(255) not null,
    created_at datetime not null default current_timestamp
);

drop trigger if exists trg_saved_trip_budget_audit;
drop trigger if exists trg_saved_trip_delete_audit;

delimiter //

create trigger trg_saved_trip_budget_audit
after insert on saved_trip_plans
for each row
begin
    if new.total_estimated_budget > new.budget then
        insert into stage4_audit_log (event_type, saved_plan_id, app_user_id, detail)
        values (
            'OVER_BUDGET_PLAN',
            new.saved_plan_id,
            new.app_user_id,
            concat('Estimated budget exceeds requested budget by ', format(new.total_estimated_budget - new.budget, 2))
        );
    end if;
end//

create trigger trg_saved_trip_delete_audit
after delete on saved_trip_plans
for each row
begin
    if old.saved_plan_id is not null then
        insert into stage4_audit_log (event_type, saved_plan_id, app_user_id, detail)
        values ('PLAN_DELETED', old.saved_plan_id, old.app_user_id, old.plan_name);
    end if;
end//

drop procedure if exists sp_movie_trip_recommendations//

create procedure sp_movie_trip_recommendations(
    in p_keyword varchar(120),
    in p_budget decimal(10,2),
    in p_departure_city varchar(80)
)
begin
    declare keyword_pattern varchar(130);

    if p_keyword is null or trim(p_keyword) = '' then
        set keyword_pattern = '%';
    else
        set keyword_pattern = concat('%', trim(p_keyword), '%');
    end if;

    select
        m.movie_id,
        m.title,
        round(max(m.rating), 1) as rating,
        substring_index(group_concat(distinct m.primary_genre order by m.primary_genre separator ', '), ',', 1) as genre,
        count(distinct ml.location_id) as stop_count,
        min(l.city_name) as first_city,
        min(l.airport_code) as first_airport,
        count(distinct f.flight_id) as direct_routes_from_departure,
        round(350 + count(distinct ml.location_id) * 310 + (9.5 - max(m.rating)) * 90, 2) as estimated_floor_budget
    from movies as m
    join movie_locations as ml
        on ml.movie_id = m.movie_id
    join locations as l
        on l.location_id = ml.location_id
    left join flights as f
        on f.dest_airport = l.airport_code
       and f.source_airport in (
            select airport_code
            from locations
            where city_name like concat('%', p_departure_city, '%')
       )
    where m.title like keyword_pattern
    group by m.movie_id, m.title
    having estimated_floor_budget <= p_budget
       and count(distinct ml.location_id) >= 1
    order by direct_routes_from_departure desc, rating desc, stop_count desc, m.title
    limit 10;
end//

delimiter ;

-- Transaction template used by the frontend when a user saves an itinerary.
-- The application binds concrete values and runs the statements in one MySQL session:
--
-- set transaction ISOLATION LEVEL read committed;
-- start transaction;
-- insert into saved_trip_plans (...)
-- select ... from movies join movie_locations ... group by ...
-- insert into saved_trip_stops (...)
-- select ... from movie_locations join locations ... order by ...
-- commit;
