const API_BASE = "http://127.0.0.1:8000/api";

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }

  return data;
}

export function getSummary() {
  return requestJson(`${API_BASE}/summary`);
}

export function getFeaturedMovies() {
  return requestJson(`${API_BASE}/movies/featured?limit=100`);
}

export function getDemoUsers() {
  return requestJson(`${API_BASE}/users/demo?limit=12`);
}

export function loginUser(identifier) {
  return requestJson(`${API_BASE}/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ identifier }),
  });
}

export function buildItinerary(formData) {
  return requestJson(`${API_BASE}/itinerary`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(formData),
  });
}