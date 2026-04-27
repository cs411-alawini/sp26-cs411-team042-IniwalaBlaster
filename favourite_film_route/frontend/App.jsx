import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import {
  buildItinerary,
  getDemoUsers,
  getFeaturedMovies,
  getSummary,
  loginUser,
} from "./client.js";

function App() {
  const [summary, setSummary] = useState(null);
  const [movies, setMovies] = useState([]);
  const [demoUsers, setDemoUsers] = useState([]);

  const [currentUser, setCurrentUser] = useState(() => {
    const saved = localStorage.getItem("scenetrip_user");

    if (!saved) {
      return null;
    }

    try {
      return JSON.parse(saved);
    } catch {
      localStorage.removeItem("scenetrip_user");
      return null;
    }
  });

  const [loginInput, setLoginInput] = useState("");
  const [isLoginOpen, setIsLoginOpen] = useState(false);

  const [movieTitle, setMovieTitle] = useState("");
  const [budget, setBudget] = useState(1800);
  const [departureCity, setDepartureCity] = useState("Chicago");

  const [itinerary, setItinerary] = useState(null);
  const [page, setPage] = useState("home");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const suggestedMovies = useMemo(() => movies.slice(0, 8), [movies]);

  useEffect(() => {
    async function loadInitialData() {
      try {
        const summaryData = await getSummary();
        const movieData = await getFeaturedMovies();
        const userData = await getDemoUsers();

        setSummary(summaryData);
        setMovies(movieData.movies || []);
        setDemoUsers(userData.users || []);
      } catch (err) {
        setError(err.message);
      }
    }

    loadInitialData();
  }, []);

  async function handleLogin(event) {
    event.preventDefault();
    setError("");

    try {
      const result = await loginUser(loginInput.trim());
      setCurrentUser(result.user);
      localStorage.setItem("scenetrip_user", JSON.stringify(result.user));
      setIsLoginOpen(false);
    } catch (err) {
      setError(err.message);
    }
  }

  function handleLogout() {
    setCurrentUser(null);
    setItinerary(null);
    setPage("home");
    localStorage.removeItem("scenetrip_user");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setItinerary(null);

    if (!currentUser) {
      setIsLoginOpen(true);
      setError("Please login before building an itinerary.");
      return;
    }

    setLoading(true);

    try {
      const result = await buildItinerary({
        movie_title: movieTitle,
        budget: Number(budget),
        departure_city: departureCity,
      });

      setItinerary(result);
      setPage("results");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function fillMovie(title) {
    setMovieTitle(title);
  }

  function fillDemoUser(username) {
    setLoginInput(username);
  }

  return (
    <main className="site-shell">
      <Navbar
        currentUser={currentUser}
        page={page}
        onHome={() => setPage("home")}
        onOpenLogin={() => setIsLoginOpen(true)}
        onLogout={handleLogout}
      />

      {error && (
        <section className="notice-bar">
          <p>{error}</p>
          <button type="button" onClick={() => setError("")}>
            Dismiss
          </button>
        </section>
      )}

      {page === "home" ? (
        <HomePage
          summary={summary}
          movies={movies}
          suggestedMovies={suggestedMovies}
          movieTitle={movieTitle}
          budget={budget}
          departureCity={departureCity}
          loading={loading}
          currentUser={currentUser}
          onMovieTitleChange={setMovieTitle}
          onBudgetChange={setBudget}
          onDepartureCityChange={setDepartureCity}
          onFillMovie={fillMovie}
          onSubmit={handleSubmit}
          onOpenLogin={() => setIsLoginOpen(true)}
        />
      ) : (
        <ResultsPage
          itinerary={itinerary}
          onBack={() => setPage("home")}
          onNewSearch={() => {
            setItinerary(null);
            setPage("home");
          }}
        />
      )}

      {isLoginOpen && (
        <LoginModal
          loginInput={loginInput}
          demoUsers={demoUsers}
          onClose={() => setIsLoginOpen(false)}
          onInputChange={setLoginInput}
          onSubmit={handleLogin}
          onFillDemoUser={fillDemoUser}
        />
      )}
    </main>
  );
}

function Navbar({ currentUser, page, onHome, onOpenLogin, onLogout }) {
  return (
    <header className="topbar">
      <button className="brand-button" type="button" onClick={onHome}>
        <span className="brand-symbol">SceneTrip</span>
      </button>

      <nav className="nav-links">
        <button
          type="button"
          className={page === "home" ? "active" : ""}
          onClick={onHome}
        >
          Home
        </button>
        <a href="#planner" onClick={onHome}>
          Plan
        </a>
        <a href="#database" onClick={onHome}>
          Data
        </a>
      </nav>

      <div className="nav-actions">
        {currentUser ? (
          <div className="profile-menu">
            <span>{currentUser.username}</span>
            <button type="button" onClick={onLogout}>
              Logout
            </button>
          </div>
        ) : (
          <button className="login-open-button" type="button" onClick={onOpenLogin}>
            Sign in
          </button>
        )}
      </div>
    </header>
  );
}

function HomePage({
  summary,
  movies,
  suggestedMovies,
  movieTitle,
  budget,
  departureCity,
  loading,
  currentUser,
  onMovieTitleChange,
  onBudgetChange,
  onDepartureCityChange,
  onFillMovie,
  onSubmit,
  onOpenLogin,
}) {
  return (
    <>
      <section className="hero-section">
        <div className="hero-copy">
          <span className="eyebrow">Movie-based trip planning</span>
          <h1>Plan where your favorite movie takes you.</h1>
          <p>
            SceneTrip turns film locations, airports, and flight routes into a
            clean travel itinerary with budget estimates.
          </p>

          <div className="hero-actions">
            <a href="#planner" className="primary-button">
              Start planning
            </a>
            {!currentUser && (
              <button type="button" className="secondary-button" onClick={onOpenLogin}>
                Sign in
              </button>
            )}
          </div>
        </div>

        <div className="hero-preview-card">
          <div className="preview-map">
            <div className="map-point point-a" />
            <div className="map-point point-b" />
            <div className="map-point point-c" />
            <div className="map-line line-a" />
            <div className="map-line line-b" />
          </div>

          <div className="preview-card-content">
            <span>Sample route</span>
            <strong>Chicago → Filming stops → Return</strong>
            <p>
              Search a title, choose a budget, and receive a generated route.
            </p>
          </div>
        </div>
      </section>

      <section id="database" className="metrics-section">
        <MetricCard label="Movies" value={summary?.movies} />
        <MetricCard label="Locations" value={summary?.locations} />
        <MetricCard label="Flights" value={summary?.flights} />
        <MetricCard label="Movie links" value={summary?.movie_links} />
      </section>

      <section id="planner" className="planner-section">
        <div className="section-heading">
          <h2>Find your trip</h2>
          <p>
            Enter a movie, budget, and departure city. Your itinerary will open
            on a separate results page.
          </p>
        </div>

        <form className="search-card" onSubmit={onSubmit}>
          <div className="search-main">
            <label>
              Movie title
              <input
                value={movieTitle}
                onChange={(event) => onMovieTitleChange(event.target.value)}
                list="movie-list"
                placeholder="Try Avatar"
                required
              />
            </label>

            <datalist id="movie-list">
              {movies.map((movie) => (
                <option key={movie.movie_id} value={movie.title} />
              ))}
            </datalist>

            <button className="search-button" type="submit" disabled={loading}>
              {loading ? "Searching…" : "Search"}
            </button>
          </div>

          <div className="search-details">
            <label>
              Budget
              <input
                type="number"
                min="200"
                step="50"
                value={budget}
                onChange={(event) => onBudgetChange(event.target.value)}
                required
              />
            </label>

            <label>
              Departure city
              <input
                value={departureCity}
                onChange={(event) => onDepartureCityChange(event.target.value)}
                placeholder="Chicago"
                required
              />
            </label>
          </div>

          {!currentUser && (
            <div className="signin-note">
              <p>Sign in is required before generating an itinerary.</p>
              <button type="button" onClick={onOpenLogin}>
                Sign in
              </button>
            </div>
          )}

          <div className="suggestion-row">
            <span>Popular searches</span>
            <div>
              {suggestedMovies.map((movie) => (
                <button
                  type="button"
                  key={movie.movie_id}
                  onClick={() => onFillMovie(movie.title)}
                >
                  {movie.title}
                </button>
              ))}
            </div>
          </div>
        </form>
      </section>
    </>
  );
}

function ResultsPage({ itinerary, onBack, onNewSearch }) {
  if (!itinerary) {
    return (
      <section className="results-page empty-results">
        <h1>No itinerary yet.</h1>
        <p>Go back and search for a movie first.</p>
        <button type="button" onClick={onBack}>
          Back to search
        </button>
      </section>
    );
  }

  const stops = itinerary.stops || [];
  const legs = itinerary.legs || [];
  const budget = itinerary.budget || {};

  return (
    <section className="results-page">
      <div className="results-toolbar">
        <button type="button" className="quiet-button" onClick={onBack}>
          ← Back
        </button>
        <button type="button" className="primary-small-button" onClick={onNewSearch}>
          New search
        </button>
      </div>

      <section className="result-hero">
        <span>Generated itinerary</span>
        <h1>{itinerary.movie_title}</h1>
        <p>
          Departing from {itinerary.departure_city}{" "}
          <b>({itinerary.departure_airport})</b>
        </p>
      </section>

      <section className="result-summary-grid">
        <div className="summary-card large">
          <span>Route quality</span>
          <p>{itinerary.route_quality}</p>
        </div>

        <div className="summary-card days-card">
          <span>Total days</span>
          <strong>{itinerary.total_days ?? stops.length}</strong>
        </div>
      </section>

      <section className="content-card">
        <div className="content-heading">
          <h2>Filming stops</h2>
          <p>Recommended sequence based on matched movie locations.</p>
        </div>

        <div className="stop-list">
          {stops.map((stop, index) => (
            <article className="stop-item" key={`${stop.location_id}-${index}`}>
              <div className="stop-number">{index + 1}</div>
              <div>
                <strong>
                  {stop.city_name}
                  {stop.state_name ? `, ${stop.state_name}` : ""}
                </strong>
                <p>
                  {stop.airport_code} · Scene count {stop.scene_count ?? "-"} ·{" "}
                  Stay {stop.recommended_days ?? 1} day(s)
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="content-card">
        <div className="content-heading">
          <h2>Flights</h2>
          <p>Flight or transfer legs used to connect the route.</p>
        </div>

        <div className="flight-table-wrap">
          <table>
            <thead>
              <tr>
                <th>From</th>
                <th>To</th>
                <th>Carrier</th>
                <th>Depart</th>
                <th>Arrive</th>
                <th>Distance</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {legs.map((leg, index) => (
                <tr key={index}>
                  <td>{leg.from_airport}</td>
                  <td>{leg.to_airport}</td>
                  <td>{leg.carrier}</td>
                  <td>{leg.depart_time}</td>
                  <td>{leg.arrive_time}</td>
                  <td>{leg.distance_miles || 0} mi</td>
                  <td>${Number(leg.estimated_cost || 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="content-card">
        <div className="content-heading">
          <h2>Budget</h2>
          <p>Projected cost breakdown for this itinerary.</p>
        </div>

        <div className="budget-grid">
          <BudgetCard label="Flights" value={budget.flight_budget} />
          <BudgetCard label="Hotels" value={budget.hotel_budget} />
          <BudgetCard label="Local" value={budget.local_budget} />
          <BudgetCard label="Total" value={budget.total_estimated_budget} highlight />
        </div>

        <div className="budget-message">{budget.budget_status}</div>
      </section>
    </section>
  );
}

function LoginModal({
  loginInput,
  demoUsers,
  onClose,
  onInputChange,
  onSubmit,
  onFillDemoUser,
}) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="login-modal" onMouseDown={(event) => event.stopPropagation()}>
        <button className="modal-close" type="button" onClick={onClose}>
          ×
        </button>

        <div className="modal-heading">
          <h2>Sign in to SceneTrip</h2>
          <p>Use a demo username or email from the database.</p>
        </div>

        <form onSubmit={onSubmit}>
          <label>
            Username or email
            <input
              value={loginInput}
              onChange={(event) => onInputChange(event.target.value)}
              placeholder="user_0001"
              list="demo-user-list"
              autoFocus
              required
            />
          </label>

          <datalist id="demo-user-list">
            {demoUsers.map((user) => (
              <option key={user.user_id} value={user.username} />
            ))}
          </datalist>

          <button className="modal-login-button" type="submit">
            Continue
          </button>
        </form>

        <div className="modal-demo-users">
          <span>Demo users</span>
          <div>
            {demoUsers.slice(0, 6).map((user) => (
              <button
                type="button"
                key={user.user_id}
                onClick={() => onFillDemoUser(user.username)}
              >
                {user.username}
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{formatNumber(value)}</strong>
    </article>
  );
}

function BudgetCard({ label, value, highlight = false }) {
  return (
    <article className={highlight ? "budget-card highlight" : "budget-card"}>
      <span>{label}</span>
      <strong>${Number(value || 0).toFixed(2)}</strong>
    </article>
  );
}

function formatNumber(value) {
  if (value === undefined || value === null) {
    return "—";
  }

  return Number(value).toLocaleString();
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);