-- Q-SmartEnergy schema for Supabase Postgres.
-- Run this once in the Supabase dashboard → SQL Editor (equivalent to `alembic upgrade head`).
-- Mirrors backend/db/models.py: users, appliances, schedules.
-- Safe to re-run: uses IF NOT EXISTS.

-- ── users ─────────────────────────────────────────────────
-- One row per Supabase Auth user, created on first authenticated request.
CREATE TABLE IF NOT EXISTS users (
    id           SERIAL PRIMARY KEY,
    supabase_uid VARCHAR(36) NOT NULL,
    email        VARCHAR(255),
    username     VARCHAR(50),
    created_at   TIMESTAMP DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_supabase_uid ON users (supabase_uid);

-- ── appliances ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS appliances (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users (id),
    name            VARCHAR(100) NOT NULL,
    power_w         DOUBLE PRECISION NOT NULL,
    duration_hours  DOUBLE PRECISION NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 1,
    candidate_hours JSON NOT NULL DEFAULT '[]',
    is_flexible     BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMP DEFAULT now()
);

-- ── schedules ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schedules (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER NOT NULL REFERENCES users (id),
    created_at        TIMESTAMP DEFAULT now(),
    day_of_month      INTEGER NOT NULL,
    weather_condition VARCHAR(20) NOT NULL,
    solver_used       VARCHAR(30) NOT NULL,
    used_fallback     BOOLEAN NOT NULL,
    energy            DOUBLE PRECISION NOT NULL,
    schedule_json     TEXT NOT NULL,
    monthly_kwh       DOUBLE PRECISION NOT NULL,
    bill_before_vnd   DOUBLE PRECISION NOT NULL,
    bill_after_vnd    DOUBLE PRECISION NOT NULL,
    savings_percent   DOUBLE PRECISION
);

-- ── Row Level Security ────────────────────────────────────
-- All data access goes through the FastAPI backend, which connects as the table
-- owner (DATABASE_URL) and therefore BYPASSES RLS. Enabling RLS with NO policies
-- blocks direct PostgREST access via the public anon key (anon/authenticated
-- roles) — locking these tables to the backend only. The frontend uses Supabase
-- for Auth only and never queries these tables directly, so no policies are needed.
ALTER TABLE users      ENABLE ROW LEVEL SECURITY;
ALTER TABLE appliances ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules  ENABLE ROW LEVEL SECURITY;
