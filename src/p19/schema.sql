CREATE TABLE IF NOT EXISTS schema_version(version integer PRIMARY KEY);
INSERT INTO schema_version VALUES (1) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS jobs(
 id text PRIMARY KEY, idempotency_key text UNIQUE NOT NULL, body_hash text NOT NULL,
 state text NOT NULL CHECK(state IN ('queued','preparing','calling','succeeded','failed','cancelled','interrupted','outcome_unknown')),
 failure jsonb NOT NULL, evidence jsonb, result jsonb, trace_context jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(), claimed_at timestamptz,
 worker_instance_id text, cancel_requested boolean NOT NULL DEFAULT false,
 publications integer NOT NULL DEFAULT 0 CHECK(publications BETWEEN 0 AND 3),
 last_publication_at timestamptz, error text, sequence integer NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS attempts(
 id text PRIMARY KEY, job_id text NOT NULL REFERENCES jobs(id), number integer NOT NULL,
 state text NOT NULL, started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 finished_at timestamptz, usage jsonb, duration_seconds double precision,
 UNIQUE(job_id,number)
);
CREATE TABLE IF NOT EXISTS events(
 job_id text NOT NULL REFERENCES jobs(id), sequence integer NOT NULL,
 kind text NOT NULL, at timestamptz NOT NULL DEFAULT clock_timestamp(), data jsonb NOT NULL,
 PRIMARY KEY(job_id,sequence)
);
CREATE TABLE IF NOT EXISTS evidence_records(
 id text PRIMARY KEY, export_id text NOT NULL, sale_id text NOT NULL, fact jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS observations(
 id bigserial PRIMARY KEY, job_id text NOT NULL, kind text NOT NULL,
 at timestamptz NOT NULL DEFAULT clock_timestamp(), data jsonb NOT NULL DEFAULT '{}'
);
