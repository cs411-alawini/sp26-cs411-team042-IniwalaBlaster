## 1. Project Pivot Overview

The primary change in this revision is a shift from a content-retrieval system to an algorithmic optimization system. While the original proposal focused on using an AI API to identify filming locations , the revised version implements a TSP approach to design an efficient travel itinerary based on those locations.


## 2. Technical and Logical Revisions

### Creative Component and Algorithm

**Original**: The "Creative Component" was an AI-powered feature to find real-world places from movie scenes.

**Revised**: The new "Creative Component" is a graph-based itinerary optimization that uses a TSP-style planning pipeline to create a feasible travel route.

**Impact**: This increases the project's technical complexity by moving from a simple API call to a non-trivial algorithmic planning task.


### Dataset Changes

**Removed**: We removed the Book dataset.

**Added**: We added **City-to-Airport dataset** and a **Flight Route dataset**.

**Expanded**: The movie dataset was upgraded from a regional San Francisco set to a global IMDB dataset with over 60,000 entries.



### Functionality Updates

**Standardization**: The system now normalizes filming locations into city-level destinations and matches them to real IATA airport codes.

**Connectivity**: We now use flight data to determine connectivity between airports, ensuring the generated trip is grounded in actual transportation links.

**Itinerary Generation**: The output has changed from a list of locations to an ordered itinerary of cities and recommended flight legs.
