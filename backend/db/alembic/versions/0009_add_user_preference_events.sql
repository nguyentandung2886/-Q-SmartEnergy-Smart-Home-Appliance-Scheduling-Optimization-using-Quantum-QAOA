-- Q-SmartEnergy: user_preference_events table for Supabase Postgres.
-- Equivalent of alembic revision d0e1f2a3b4c5 (Revises: b8c9d0e1f2a3) — run this ONCE
-- in the Supabase dashboard -> SQL Editor when alembic can't reach the DB directly.
-- Mirrors backend/db/models.py UserPreferenceEvent. Safe to re-run: uses IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS user_preference_events (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users (id),
    created_at    TIMESTAMP DEFAULT now(),
    w_cost        DOUBLE PRECISION NOT NULL,
    w_comfort     DOUBLE PRECISION NOT NULL,
    w_solar       DOUBLE PRECISION NOT NULL,
    num_variables INTEGER NOT NULL,
    energy        DOUBLE PRECISION NOT NULL,
    accepted      BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX IF NOT EXISTS ix_user_preference_events_id ON user_preference_events (id);

-- Same access model as the other backend-owned tables (users/appliances/schedules in
-- supabase_schema.sql): only the FastAPI backend (DATABASE_URL owner) touches this
-- table and bypasses RLS, so enabling RLS with no policies blocks direct PostgREST
-- access via the anon/authenticated key.
ALTER TABLE user_preference_events ENABLE ROW LEVEL SECURITY;

-- Keep alembic's own bookkeeping table in sync so a FUTURE `alembic upgrade head` run
-- (from a machine that CAN reach this DB) sees 0009 as already applied and doesn't try
-- to CREATE TABLE again. No-op if alembic_version isn't already at b8c9d0e1f2a3.
UPDATE alembic_version SET version_num = 'd0e1f2a3b4c5' WHERE version_num = 'b8c9d0e1f2a3';
