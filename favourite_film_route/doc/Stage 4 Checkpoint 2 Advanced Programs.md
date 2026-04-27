# Stage 4 Checkpoint 2 Advanced Database Programs

This file documents the Stage 4.2 database programs used by the SceneTrip frontend.
The executable SQL is stored in `sql/05_stage4_advanced.sql`.

## New User Tables

The application adds `app_users` and `app_sessions` for frontend login and session management.
These tables are separate from the Stage 3 synthetic `users` table.

## CRUD Table

The frontend performs CRUD on `saved_trip_plans`, a non-login table.

1. Create: `POST /plans/create` saves a generated itinerary.
2. Read: the Saved Trip Plans panel lists plans for the logged-in user.
3. Update: each saved plan can update its name and budget.
4. Delete: each saved plan can be deleted.

## Transaction

`POST /plans/create` runs a transaction with `READ COMMITTED` isolation.
It inserts a saved trip plan, inserts its stops, and writes an audit row in one MySQL session.
The transaction includes advanced SQL using joins, aggregation, and an `EXISTS` subquery.

## Stored Procedure

`sp_movie_trip_recommendations(keyword, budget, departure_city)` powers the Stored Procedure Recommendations panel.
It uses an `IF` control structure, joins across movies, filming locations, and flights, aggregation with `GROUP BY`, and a subquery over departure-city airports.

## Triggers

`trg_saved_trip_budget_audit` runs after a saved plan is inserted.
If the estimated trip cost exceeds the user budget, it inserts an `OVER_BUDGET_PLAN` event into `stage4_audit_log`.

`trg_saved_trip_delete_audit` runs after a saved plan is deleted.
It records a `PLAN_DELETED` audit event for the deleted saved plan.

## Constraints

The Stage 4.2 tables define primary keys, foreign keys, unique username constraints, cascading deletes, and `CHECK` constraints for positive budget and trip-day values.
