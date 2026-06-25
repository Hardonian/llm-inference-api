CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    provider TEXT,
    context_length INTEGER,
    max_tokens INTEGER,
    is_active INTEGER DEFAULT 1,
    lane TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS inference_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    prompt TEXT NOT NULL,
    max_tokens INTEGER DEFAULT 512,
    temperature REAL DEFAULT 0.7,
    lane TEXT,
    status TEXT DEFAULT 'queued',
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    latency_ms INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS lane_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lane_name TEXT NOT NULL,
    gpu_type TEXT,
    gpu_index INTEGER,
    status TEXT DEFAULT 'available',
    current_model TEXT,
    queue_depth INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_req_status ON inference_requests(status);
CREATE INDEX IF NOT EXISTS idx_req_model ON inference_requests(model);
