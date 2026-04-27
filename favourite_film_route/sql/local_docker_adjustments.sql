USE scenetrip;

ALTER TABLE users
  MODIFY home_airport VARCHAR(8) NOT NULL;

ALTER TABLE locations
  MODIFY airport_code VARCHAR(8) NOT NULL;

ALTER TABLE flights
  MODIFY source_airport VARCHAR(8) NOT NULL,
  MODIFY dest_airport VARCHAR(8) NOT NULL;

ALTER TABLE trip_plans
  MODIFY start_airport VARCHAR(8) NOT NULL;
