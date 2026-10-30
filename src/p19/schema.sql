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
CREATE TABLE IF NOT EXISTS live_studies(
 id text PRIMARY KEY CHECK(id='p19-real-20261030'), manifest jsonb NOT NULL,
 manifest_hash text NOT NULL, state text NOT NULL CHECK(state IN ('active','stopped','completed')),
 reason text, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS live_calls(
 case_id text PRIMARY KEY CHECK(case_id IN ('export_0','export_1','export_2')),
 ordinal integer UNIQUE NOT NULL CHECK(ordinal BETWEEN 0 AND 2),
 study_id text NOT NULL REFERENCES live_studies(id), job_id text UNIQUE NOT NULL,
 attempt_id text UNIQUE NOT NULL, reservation_usd numeric NOT NULL CHECK(reservation_usd=0.50256),
 cost_usd numeric CHECK(cost_usd BETWEEN 0 AND 0.50256), usage jsonb,
 state text NOT NULL CHECK(state IN ('reserved','settled','rejected')),
 assessment text CHECK(assessment IN ('pass','fail')), assessment_notes text,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
