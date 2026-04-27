use scenetrip;

alter table users
  modify home_airport varchar(8) not null;

alter table locations
  modify airport_code varchar(8) not null;

alter table flights
  modify source_airport varchar(8) not null,
  modify dest_airport varchar(8) not null;

alter table trip_plans
  modify start_airport varchar(8) not null;
