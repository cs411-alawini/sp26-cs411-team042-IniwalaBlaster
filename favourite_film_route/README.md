# SceneTrip

SceneTrip is a movie-based trip planner built for the CS 411 project.  
The current repository includes:

1. Stage 3 database schema, dataset loading, advanced queries, and indexing material
2. Stage 4 checkpoint web app that lets a user choose a movie, budget, and departure city and receive a complete itinerary draft

## Repository Layout

- [app.py](/Users/xiaojingxin/Documents/New%20project/app.py): Stage 4 local web app
- [doc/Database Design.md](/Users/xiaojingxin/Documents/New%20project/doc/Database%20Design.md): Stage 3 write-up
- [doc/Stage 4 Checkpoint 1.md](/Users/xiaojingxin/Documents/New%20project/doc/Stage%204%20Checkpoint%201.md): Stage 4 checkpoint notes
- [sql/01_schema.sql](/Users/xiaojingxin/Documents/New%20project/sql/01_schema.sql): MySQL schema
- [sql/02_seed_data.sql](/Users/xiaojingxin/Documents/New%20project/sql/02_seed_data.sql): generated insert statements
- [sql/03_advanced_queries.sql](/Users/xiaojingxin/Documents/New%20project/sql/03_advanced_queries.sql): advanced SQL queries
- [sql/04_indexing.sql](/Users/xiaojingxin/Documents/New%20project/sql/04_indexing.sql): candidate indexes
- [scripts/generate_seed_data.py](/Users/xiaojingxin/Documents/New%20project/scripts/generate_seed_data.py): CSV-to-SQL loader
- [scripts/start_stage4_mysql.sh](/Users/xiaojingxin/Documents/New%20project/scripts/start_stage4_mysql.sh): helper for starting a local MySQL instance
- [scripts/load_stage3_data.sh](/Users/xiaojingxin/Documents/New%20project/scripts/load_stage3_data.sh): helper for loading schema and data

## Local Deployment On Another Computer

These instructions assume you want to run everything locally on another machine.

### 1. Requirements

Install these first:

1. Python 3.11 or newer
2. MySQL 8 client and server tools
3. The three CSV source files used by the project:
   - movie dataset: `final_dataset.csv`
   - airport dataset: `airports (2).csv`
   - route dataset: `routes 2.csv`

The app does not require Node.js.

### 2. Copy the Project

Clone the repository or copy the full project folder to the other computer.

Example:

```bash
git clone <your-repo-url>
cd "<repo-folder>"
```

Or if you are copying manually, make sure the new machine has the full project tree including `app.py`, `scripts/`, `sql/`, and `doc/`.

### 3. Put the CSV Files Somewhere Accessible

The project needs three CSV files to generate the MySQL seed data.  
On another computer, you do not need to keep the exact same absolute paths as on the original machine.

Pick a folder and place the files there, for example:

```bash
/Users/yourname/Downloads/scenetrip-data/final_dataset.csv
/Users/yourname/Downloads/scenetrip-data/airports.csv
/Users/yourname/Downloads/scenetrip-data/routes.csv
```

Then export these environment variables before generating data:

```bash
export SCENETRIP_MOVIE_CSV="/Users/yourname/Downloads/scenetrip-data/final_dataset.csv"
export SCENETRIP_AIRPORT_CSV="/Users/yourname/Downloads/scenetrip-data/airports.csv"
export SCENETRIP_ROUTE_CSV="/Users/yourname/Downloads/scenetrip-data/routes.csv"
```

If you do not set these variables, the script will fall back to the original absolute paths from the development machine.

### 4. Start MySQL 8

You can use your own MySQL 8 instance, or run a local one.

If your computer supports the helper script and `mysqld` is already on your `PATH`, run:

```bash
cd "<repo-folder>"
./scripts/start_stage4_mysql.sh
```

By default, this starts MySQL using:

- socket: `/tmp/scenetrip-mysql-run/mysql.sock`
- port: `3307`

Leave that terminal open.

If you already have your own MySQL 8 server running, that is fine too.  
Just make sure you know the socket or host/port details and use the same values when loading data and starting the web app.

### 5. Generate and Load the Database

In a new terminal:

```bash
cd "<repo-folder>"

export SCENETRIP_MOVIE_CSV="/path/to/final_dataset.csv"
export SCENETRIP_AIRPORT_CSV="/path/to/airports.csv"
export SCENETRIP_ROUTE_CSV="/path/to/routes.csv"

python3 scripts/generate_seed_data.py
mysql -u root --socket=/tmp/scenetrip-mysql-run/mysql.sock --port=3307 < sql/01_schema.sql
mysql -u root --socket=/tmp/scenetrip-mysql-run/mysql.sock --port=3307 < sql/02_seed_data.sql
```

Or use the helper loader:

```bash
cd "<repo-folder>"

export SCENETRIP_MOVIE_CSV="/path/to/final_dataset.csv"
export SCENETRIP_AIRPORT_CSV="/path/to/airports.csv"
export SCENETRIP_ROUTE_CSV="/path/to/routes.csv"

./scripts/load_stage3_data.sh
```

### 6. Verify the Data Loaded

Run:

```bash
mysql -u root --socket=/tmp/scenetrip-mysql-run/mysql.sock --port=3307 -D scenetrip -e "
SELECT COUNT(*) AS movies FROM movies;
SELECT COUNT(*) AS locations FROM locations;
SELECT COUNT(*) AS flights FROM flights;
"
```

If the real CSV-backed load worked, the numbers should be much larger than the original demo dataset. They should be roughly in this range:

- `movies`: around `18221`
- `locations`: around `6373`
- `flights`: around `67171`

### 7. Start the Web App

From the repository root:

```bash
python3 app.py
```

Then open:

[http://127.0.0.1:8000](http://127.0.0.1:8000)

### 8. If Your MySQL Socket or Port Is Different

You can point the app at another local MySQL setup by exporting these variables before running it:

```bash
export SCENETRIP_DB_SOCKET="/path/to/mysql.sock"
export SCENETRIP_DB_PORT="3307"
export SCENETRIP_DB_USER="root"
export SCENETRIP_DB_NAME="scenetrip"
python3 app.py
```

### 9. Demo Flow

Once the page is running:

1. Type a movie title keyword into the movie field
2. Choose a budget
3. Enter a departure city such as `Chicago`, `New York`, or `Los Angeles`
4. Click `Build Itinerary`

The app will return:

1. A route skeleton
2. Recommended filming stops
3. Flight legs where available from the real dataset
4. Transfer-needed legs when a complete route is not available
5. A budget summary

## Troubleshooting

### MySQL says it cannot connect to the socket

This usually means the MySQL server is not running, or the socket path is different from the one the app is using.

Check:

```bash
mysqladmin -u root --socket=/tmp/scenetrip-mysql-run/mysql.sock --port=3307 ping
```

### The app still shows the old 1200-movie demo data

That means the database was not reloaded with the real CSV-backed `sql/02_seed_data.sql`.  
Run `python3 scripts/generate_seed_data.py` again, then reload `sql/01_schema.sql` and `sql/02_seed_data.sql`.

### The itinerary page says no route was found

The current version is designed to still generate an itinerary draft even if some route legs are missing from the real route dataset. If you still see an error, make sure:

1. The real CSV-backed database was loaded
2. The web app was restarted after code changes
3. The departure city exists in the airport dataset

## Notes

This project is intentionally lightweight for checkpoint delivery.  
The Stage 4 app uses Python's standard library plus the local MySQL command-line client, so it can run without adding a larger web framework.
