# 🧭 Minimal Geospatial App — Preliminary Design & Architecture (Phase 0)

## 🎯 Goal

Build the smallest possible system that allows:

A user opens a map → clicks → saves a point → sees it rendered from the database.

This validates:
- Map rendering
- Map clicking
- Rendering points on map
- Saving geospatial data to PostGIS
- Reading geospatial data from PostGIS
- Rendering persisted data

---

## 🧱 System Overview

Browser (React + OpenLayers)  
→ Backend (FastAPI)  
→ Database (Postgres + PostGIS)

---

## 🧩 Components

### Frontend
- React
- OpenLayers

Responsibilities:
- Render map
- Handle user clicks
- Convert click to lat/lon
- Send coordinates to backend
- Fetch saved points
- Render points on map

---

### Backend
- FastAPI

Responsibilities:
- Accept new point (POST)
- Return all points (GET)
- Execute SQL queries
- Communicate with database

---

### Database
- Postgres + PostGIS

Responsibilities:
- Store points
- Return points

---

## 🗄️ Database Design

### Schema

```sql
CREATE TABLE points (
  id SERIAL PRIMARY KEY,
  geom GEOMETRY(Point, 4326),
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

### Database Access Strategy

We will use SQL directly (via a thin layer), not an ORM.

Why:
- PostGIS is SQL-first
- Keeps system transparent
- Easier to reason about behavior and performance
- Avoids unnecessary abstraction early

Implementation:
- psycopg (v3) or SQLAlchemy Core (NOT ORM)
- Always use parameterized queries

---

## 🔌 API Design

### POST /points

Request:
```json
{
  "lat": 38.9,
  "lon": -77.0
}
```

SQL:
```sql
INSERT INTO points (geom)
VALUES (ST_SetSRID(ST_MakePoint(lon, lat), 4326));
```

---

### GET /points

Response:
```json
[
  {
    "id": 1,
    "lat": 38.9,
    "lon": -77.0
  }
]
```

SQL:
```sql
SELECT 
  id,
  ST_Y(geom) as lat,
  ST_X(geom) as lon
FROM points;
```

---

## 🖱️ Frontend Behavior

### Map Initialization
- Initialize OpenLayers map
- Use OpenStreetMap tiles

### On Map Click
- Capture click event
- Convert to lat/lon
- POST to backend

### On Page Load
- GET /points
- Store in state
- Render points

### Rendering Points
- One feature per point
- Use OpenLayers vector layer

---

## 🔁 Data Flow

### Creating a Point

User clicks map  
→ Frontend gets lat/lon  
→ POST /points  
→ Backend inserts into DB  
→ Frontend refetches  
→ Map updates  

---

### Reading Points

Frontend loads  
→ GET /points  
→ Backend queries DB  
→ Returns lat/lon  
→ Frontend renders markers  

---

## 🧠 Core Design Decisions

### Coordinate System
- WGS84 (EPSG:4326)
- lat/lon in degrees

Important:
- PostGIS Point = (lon, lat)
- NOT (lat, lon)

---

### Projection Strategy
- Frontend uses Web Mercator (EPSG:3857)
- Backend uses WGS84 (EPSG:4326)
- Frontend converts coordinates before sending

---

### Source of Truth
- Backend + DB = source of truth
- Frontend is just a renderer
- Always refetch after write
- No optimistic updates

---

### API Simplicity
Only:
- POST /points
- GET /points

---

### Data Volume Assumption
- < 1000 points

---

### Definition of Done
- Map loads
- Click creates a point
- Refresh persists the point
- Points come from DB

---

## 🧱 Principles

- Start as small as possible
- Keep everything understandable
- No abstraction unless needed
- No optimization before pain
- SQL over ORM

---

## 🚫 Non-Goals

- Realtime updates
- WebSockets
- Caching
- Auth
- Performance optimization
- UI polish

---

## 🐳 Local Setup

- frontend
- backend
- postgres (PostGIS)

---

## 🧭 Summary

Core loop:

UI → API → DB → API → UI

Everything builds on this.
