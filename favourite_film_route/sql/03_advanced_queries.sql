use scenetrip;

-- Query 1: filming destinations with strong movie quality and outbound connectivity.
select
    l.city_name,
    l.state_name,
    l.airport_code,
    count(distinct ml.movie_id) as movies_filmed,
    round(avg(m.rating), 2) as avg_movie_rating,
    count(distinct concat(f.source_airport, '-', f.dest_airport)) as outbound_routes
from locations as l
join movie_locations as ml
    on l.location_id = ml.location_id
join movies as m
    on ml.movie_id = m.movie_id
join flights as f
    on l.airport_code = f.source_airport
where m.rating >= 7.5
group by l.city_name, l.state_name, l.airport_code
having count(distinct ml.movie_id) >= 3
order by avg_movie_rating desc, outbound_routes desc, l.city_name
limit 15;

-- Query 2: trip plans whose consecutive stops all have available flights and whose
-- filming locations beat the overall average movie rating.
select
    tp.trip_plan_id,
    tp.plan_name,
    u.username,
    count(distinct tps.location_id) as stop_count,
    round(avg(m.rating), 2) as avg_filming_rating
from trip_plans as tp
join users as u
    on tp.user_id = u.user_id
join trip_plan_stops as tps
    on tp.trip_plan_id = tps.trip_plan_id
join movie_locations as ml
    on tps.location_id = ml.location_id
join movies as m
    on ml.movie_id = m.movie_id
where tp.total_budget <= 2500
  and not exists (
      select 1
      from trip_plan_stops as s1
      join trip_plan_stops as s2
          on s1.trip_plan_id = s2.trip_plan_id
         and s2.stop_order = s1.stop_order + 1
      join locations as l1
          on l1.location_id = s1.location_id
      join locations as l2
          on l2.location_id = s2.location_id
      left join flights as f
          on f.source_airport = l1.airport_code
         and f.dest_airport = l2.airport_code
      where s1.trip_plan_id = tp.trip_plan_id
        and f.flight_id is null
  )
group by tp.trip_plan_id, tp.plan_name, u.username
having avg(m.rating) > (
    select avg(rating)
    from movies
)
order by stop_count desc, avg_filming_rating desc, tp.trip_plan_id
limit 15;

-- Query 3: actors whose movies are tied to above-average airport connectivity
-- and appear in at least two trip plans.
select
    a.actor_id,
    a.actor_name,
    count(distinct m.movie_id) as movie_count,
    count(distinct tp.trip_plan_id) as featured_trip_plans,
    round(avg(conn.route_count), 2) as avg_city_connectivity
from actors as a
join movie_actors as ma
    on a.actor_id = ma.actor_id
join movies as m
    on ma.movie_id = m.movie_id
join movie_locations as ml
    on m.movie_id = ml.movie_id
join locations as l
    on ml.location_id = l.location_id
join (
    select source_airport, count(*) as route_count
    from flights
    group by source_airport
) as conn
    on conn.source_airport = l.airport_code
left join trip_plan_stops as tps
    on ml.location_id = tps.location_id
left join trip_plans as tp
    on tps.trip_plan_id = tp.trip_plan_id
where conn.route_count > (
    select avg(route_total)
    from (
        select count(*) as route_total
        from flights
        group by source_airport
    ) as route_stats
)
group by a.actor_id, a.actor_name
having count(distinct tp.trip_plan_id) >= 2
order by avg_city_connectivity desc, movie_count desc, a.actor_name
limit 15;
