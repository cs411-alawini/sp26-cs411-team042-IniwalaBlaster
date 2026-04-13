# Stage 4 Checkpoint 1

## Goal

For Stage 4 Checkpoint 1, our team needed to present an initial draft of the application with:

1. A functional web page
2. A live connection between the front-end and the database
3. Retrieval or CRUD functionality demonstrated on the page

## What We Implemented

We implemented a lightweight web application for **SceneTrip: Movie-Based Trip Planner** in [app.py](/Users/xiaojingxin/Documents/New project/app.py). The app connects to the MySQL database created in Stage 3 and demonstrates a retrieval-driven itinerary generation workflow in a single functional page.

The page contains the following features:

1. **Database snapshot cards** that confirm the front-end is connected to the database by retrieving live row counts from `movies`, `locations`, `flights`, and `movie_locations`.
2. **Favorite movie selection** from database-backed movie options.
3. **Budget and departure-city input** from the user.
4. **Automatic itinerary generation**, which returns a complete route with filming stops, flight legs, recommended stay lengths, and a budget breakdown.

## Database Connection

The application uses the MySQL command-line client from Python's standard library via subprocess calls. This design keeps the checkpoint implementation lightweight and avoids adding external dependencies, while still demonstrating an actual front-end to database connection. The app reads the database through the same MySQL 8 setup used in Stage 3 and interacts with the `scenetrip` schema.

The default local configuration is:

1. Socket: `/tmp/scenetrip-mysql-run/mysql.sock`
2. Port: `3307`
3. User: `root`
4. Database: `scenetrip`

These values can also be overridden with environment variables when launching the app.

## Retrieval / CRUD Demonstration

The retrieval feature demonstrates that the web page is not static. The user chooses a favorite movie, enters a budget, and chooses a departure city. The app then queries `movies`, `movie_locations`, `locations`, and `flights` to build a full path arrangement. The output includes a route from the departure airport to matched filming locations and back, along with a budget estimate. This is directly connected to the SceneTrip application idea because the product goal is to transform movie preferences into a travel plan.

This satisfies the checkpoint requirement because the page performs live database retrieval and presents the result on the web page as an application-level output rather than a static mockup.

## How To Run

1. Make sure the Stage 3 MySQL instance is running and the `scenetrip` database has already been loaded.
2. From the repository root, run:

```bash
python3 app.py
```

3. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in a browser.

If the database is running on a different socket or port, the app can be started with:

```bash
SCENETRIP_DB_SOCKET=/path/to/mysql.sock SCENETRIP_DB_PORT=3307 python3 app.py
```

## Demo Checklist

For the checkpoint meeting, the demo flow is:

1. Open the web page to show that the application is functional.
2. Point to the database snapshot cards to show that the front-end is connected to the back-end database.
3. Choose a movie from the dropdown.
4. Enter a budget and a departure city such as `Chicago`, `Los Angeles`, or `New York`.
5. Click **Build Itinerary** to show the generated travel path, stop sequence, flight legs, and budget breakdown.

## Submission Reminder

Create the Stage 4 Checkpoint 1 release with the correct tag before submitting on Canvas.
