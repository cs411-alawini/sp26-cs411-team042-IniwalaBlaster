USE scenetrip;

CREATE TABLE IF NOT EXISTS app_users (
    app_user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash CHAR(64) NOT NULL,
    home_city VARCHAR(80),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_sessions (
    session_token CHAR(64) PRIMARY KEY,
    app_user_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (app_user_id) REFERENCES app_users(app_user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS saved_trip_plans (
    saved_plan_id INT AUTO_INCREMENT PRIMARY KEY,
    app_user_id INT NOT NULL,
    movie_id INT NOT NULL,
    plan_name VARCHAR(100) NOT NULL,
    departure_city VARCHAR(80) NOT NULL,
    departure_airport VARCHAR(8) NOT NULL,
    budget DECIMAL(10,2) NOT NULL,
    total_estimated_budget DECIMAL(10,2) NOT NULL,
    total_days INT NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'draft',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (app_user_id) REFERENCES app_users(app_user_id) ON DELETE CASCADE,
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id),
    CHECK (budget > 0),
    CHECK (total_estimated_budget >= 0),
    CHECK (total_days > 0)
);

CREATE TABLE IF NOT EXISTS saved_trip_stops (
    saved_plan_id INT NOT NULL,
    stop_order INT NOT NULL,
    location_id INT NOT NULL,
    airport_code VARCHAR(8) NOT NULL,
    recommended_days INT NOT NULL,
    PRIMARY KEY (saved_plan_id, stop_order),
    FOREIGN KEY (saved_plan_id) REFERENCES saved_trip_plans(saved_plan_id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(location_id),
    CHECK (recommended_days > 0)
);

CREATE TABLE IF NOT EXISTS stage4_audit_log (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(40) NOT NULL,
    saved_plan_id INT,
    app_user_id INT,
    detail VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DROP TRIGGER IF EXISTS trg_saved_trip_budget_audit;
DROP TRIGGER IF EXISTS trg_saved_trip_delete_audit;

DELIMITER //

CREATE TRIGGER trg_saved_trip_budget_audit
AFTER INSERT ON saved_trip_plans
FOR EACH ROW
BEGIN
    IF NEW.total_estimated_budget > NEW.budget THEN
        INSERT INTO stage4_audit_log (event_type, saved_plan_id, app_user_id, detail)
        VALUES (
            'OVER_BUDGET_PLAN',
            NEW.saved_plan_id,
            NEW.app_user_id,
            CONCAT('Estimated budget exceeds requested budget by ', FORMAT(NEW.total_estimated_budget - NEW.budget, 2))
        );
    END IF;
END//

CREATE TRIGGER trg_saved_trip_delete_audit
AFTER DELETE ON saved_trip_plans
FOR EACH ROW
BEGIN
    IF OLD.saved_plan_id IS NOT NULL THEN
        INSERT INTO stage4_audit_log (event_type, saved_plan_id, app_user_id, detail)
        VALUES ('PLAN_DELETED', OLD.saved_plan_id, OLD.app_user_id, OLD.plan_name);
    END IF;
END//

DROP PROCEDURE IF EXISTS sp_movie_trip_recommendations//

CREATE PROCEDURE sp_movie_trip_recommendations(
    IN p_keyword VARCHAR(120),
    IN p_budget DECIMAL(10,2),
    IN p_departure_city VARCHAR(80)
)
BEGIN
    DECLARE keyword_pattern VARCHAR(130);

    IF p_keyword IS NULL OR TRIM(p_keyword) = '' THEN
        SET keyword_pattern = '%';
    ELSE
        SET keyword_pattern = CONCAT('%', TRIM(p_keyword), '%');
    END IF;

    SELECT
        m.movie_id,
        m.title,
        ROUND(MAX(m.rating), 1) AS rating,
        SUBSTRING_INDEX(GROUP_CONCAT(DISTINCT m.primary_genre ORDER BY m.primary_genre SEPARATOR ', '), ',', 1) AS genre,
        COUNT(DISTINCT ml.location_id) AS stop_count,
        MIN(l.city_name) AS first_city,
        MIN(l.airport_code) AS first_airport,
        COUNT(DISTINCT f.flight_id) AS direct_routes_from_departure,
        ROUND(350 + COUNT(DISTINCT ml.location_id) * 310 + (9.5 - MAX(m.rating)) * 90, 2) AS estimated_floor_budget
    FROM movies AS m
    JOIN movie_locations AS ml
        ON ml.movie_id = m.movie_id
    JOIN locations AS l
        ON l.location_id = ml.location_id
    LEFT JOIN flights AS f
        ON f.dest_airport = l.airport_code
       AND f.source_airport IN (
            SELECT airport_code
            FROM locations
            WHERE city_name LIKE CONCAT('%', p_departure_city, '%')
       )
    WHERE m.title LIKE keyword_pattern
    GROUP BY m.movie_id, m.title
    HAVING estimated_floor_budget <= p_budget
       AND COUNT(DISTINCT ml.location_id) >= 1
    ORDER BY direct_routes_from_departure DESC, rating DESC, stop_count DESC, m.title
    LIMIT 10;
END//

DELIMITER ;

-- Transaction template used by the frontend when a user saves an itinerary.
-- The application binds concrete values and runs the statements in one MySQL session:
--
-- SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
-- START TRANSACTION;
-- INSERT INTO saved_trip_plans (...)
-- SELECT ... FROM movies JOIN movie_locations ... GROUP BY ...
-- INSERT INTO saved_trip_stops (...)
-- SELECT ... FROM movie_locations JOIN locations ... ORDER BY ...
-- COMMIT;
