"""
SQLite DDL Schema & Index Definitions [REQ-KERNEL-004].
Job + Phase tables [REQ-ORCH-031, REQ-ORCH-032].
Follow-up proposals [REQ-ORCH-043].
"""

JOBS_PHASES_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    budget_max_phases INTEGER NOT NULL DEFAULT 16,
    budget_max_handoffs INTEGER NOT NULL DEFAULT 4,
    budget_max_ollama_slots INTEGER NOT NULL DEFAULT 1,
    current_phase_id TEXT,
    template_id TEXT,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_session ON jobs(session_id);

CREATE TABLE IF NOT EXISTS phases (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    "index" INTEGER NOT NULL,
    assigned_agent_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    success_rule TEXT NOT NULL DEFAULT '',
    verify_checker TEXT,
    input_packet_json TEXT,
    output_packet_json TEXT,
    parent_phase_id TEXT,
    max_turns INTEGER NOT NULL DEFAULT 10,
    react_state TEXT,
    UNIQUE(job_id, "index")
);

CREATE INDEX IF NOT EXISTS idx_phases_job ON phases(job_id);
"""

PROPOSALS_SQL = """
CREATE TABLE IF NOT EXISTS proposals (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    requested_by_job_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_proposals_parent ON proposals(requested_by_job_id);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);
"""

TONES_SQL = """
CREATE TABLE IF NOT EXISTS tones (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    directive TEXT NOT NULL,
    is_builtin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

EPISODIC_FACTS_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS episodic_facts_fts USING fts5(
    entity,
    key,
    value,
    content='episodic_facts',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS episodic_facts_ai AFTER INSERT ON episodic_facts BEGIN
  INSERT INTO episodic_facts_fts(rowid, entity, key, value) VALUES (new.rowid, new.entity, new.key, new.value);
END;
CREATE TRIGGER IF NOT EXISTS episodic_facts_ad AFTER DELETE ON episodic_facts BEGIN
  INSERT INTO episodic_facts_fts(episodic_facts_fts, rowid, entity, key, value) VALUES('delete', old.rowid, old.entity, old.key, old.value);
END;
CREATE TRIGGER IF NOT EXISTS episodic_facts_au AFTER UPDATE ON episodic_facts BEGIN
  INSERT INTO episodic_facts_fts(episodic_facts_fts, rowid, entity, key, value) VALUES('delete', old.rowid, old.entity, old.key, old.value);
  INSERT INTO episodic_facts_fts(rowid, entity, key, value) VALUES (new.rowid, new.entity, new.key, new.value);
END;
"""


INIT_SCHEMA_SQL = (
    """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_calls_json TEXT,
    tool_call_id TEXT,
    name TEXT,
    sequence_num INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, sequence_num);

CREATE TABLE IF NOT EXISTS telemetry_spans (
    id TEXT PRIMARY KEY,
    trace_id TEXT,
    parent_span_id TEXT,
    session_id TEXT,
    agent_id TEXT,
    span_type TEXT NOT NULL,
    name TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    duration_ms REAL NOT NULL,
    ttft_ms REAL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    success BOOLEAN NOT NULL DEFAULT 1,
    status TEXT DEFAULT 'ok',
    error_message TEXT,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_telemetry_agent ON telemetry_spans(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_telemetry_span_type ON telemetry_spans(span_type, created_at);
CREATE INDEX IF NOT EXISTS idx_telemetry_trace ON telemetry_spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_parent_span ON telemetry_spans(parent_span_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_provider_model ON telemetry_spans(provider, model);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    priority TEXT NOT NULL DEFAULT 'medium',
    due_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

CREATE TABLE IF NOT EXISTS routines (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    agent_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    schedule_type TEXT NOT NULL DEFAULT 'interval',
    interval_seconds INTEGER DEFAULT 3600,
    cron_expression TEXT,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    last_status TEXT NOT NULL DEFAULT 'idle',
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS routine_runs (
    id TEXT PRIMARY KEY,
    routine_id TEXT NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    output TEXT DEFAULT '',
    error_message TEXT,
    duration_ms REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_routine_runs_routine ON routine_runs(routine_id, created_at);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_overrides (
    agent_id TEXT PRIMARY KEY,
    provider TEXT DEFAULT 'default',
    api_base_url TEXT,
    api_key TEXT,
    context_window INTEGER,
    tone TEXT,
    system_prompt TEXT,
    model TEXT,
    purpose TEXT,
    allowed_tools_json TEXT,
    allowed_skills_json TEXT,
    pack_tools_json TEXT,
    show_in_chat INTEGER DEFAULT 1,
    max_turns INTEGER,
    history_retention_days INTEGER DEFAULT 30,
    storage_enabled INTEGER DEFAULT 0,
    storage_type TEXT DEFAULT 'sqlite',
    memory_enabled INTEGER DEFAULT 1,
    memory_retention_days INTEGER DEFAULT 30,
    pinned_memory TEXT DEFAULT '',
    allow_autonomous_training INTEGER DEFAULT 0,
    max_training_retries INTEGER DEFAULT 2,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS custom_agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'default',
    api_base_url TEXT,
    api_key TEXT,
    context_window INTEGER,
    purpose TEXT NOT NULL DEFAULT 'general',
    tone TEXT DEFAULT 'default',
    avatar_icon TEXT DEFAULT 'bot',
    model TEXT DEFAULT 'default',
    allowed_tools_json TEXT,
    allowed_skills_json TEXT,
    pack_tools_json TEXT,
    show_in_chat INTEGER DEFAULT 1,
    max_turns INTEGER DEFAULT 10,
    history_retention_days INTEGER DEFAULT 30,
    is_builtin BOOLEAN DEFAULT 0,
    storage_enabled INTEGER DEFAULT 0,
    storage_type TEXT DEFAULT 'sqlite',
    memory_enabled INTEGER DEFAULT 1,
    memory_retention_days INTEGER DEFAULT 30,
    pinned_memory TEXT DEFAULT '',
    allow_autonomous_training INTEGER DEFAULT 0,
    max_training_retries INTEGER DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_capability_gaps (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    session_id TEXT,
    turn_text TEXT NOT NULL,
    identified_capability TEXT NOT NULL,
    suggested_tool_name TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gaps_agent_status ON agent_capability_gaps(agent_id, status);

CREATE TABLE IF NOT EXISTS episodic_facts (
    id TEXT PRIMARY KEY,
    entity TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source_session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity, key)
);

CREATE TABLE IF NOT EXISTS pending_approvals (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    routine_id TEXT,
    tool_name TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    decision_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session_artifacts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'text/markdown',
    content TEXT NOT NULL,
    summary TEXT NOT NULL,
    item_count INTEGER DEFAULT 0,
    is_pinned BOOLEAN DEFAULT 0,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_approvals_session ON pending_approvals(session_id, status);
CREATE INDEX IF NOT EXISTS idx_approvals_agent ON pending_approvals(agent_id, status);
CREATE INDEX IF NOT EXISTS idx_facts_entity ON episodic_facts(entity);
CREATE INDEX IF NOT EXISTS idx_telemetry_spans_query ON telemetry_spans(agent_id, span_type, created_at);
CREATE INDEX IF NOT EXISTS idx_telemetry_spans_error ON telemetry_spans(success, span_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_session ON session_artifacts(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_artifacts_expires ON session_artifacts(expires_at, is_pinned);
"""
    + JOBS_PHASES_SQL
    + PROPOSALS_SQL
    + TONES_SQL
    + EPISODIC_FACTS_FTS_SQL
    + """
CREATE TABLE IF NOT EXISTS prompt_catalog (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT DEFAULT 'general',
    template_text TEXT NOT NULL,
    tags TEXT,
    is_builtin INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prompt_category ON prompt_catalog(category);
"""
)

FACTORY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS factory_jobs (
    id TEXT PRIMARY KEY,
    target_agent_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    seed_intent TEXT NOT NULL,
    target_host TEXT,
    environment_manifest_json TEXT,
    active_graph_id TEXT NOT NULL DEFAULT 'graph_standard_factory_v1',
    current_node_id TEXT NOT NULL DEFAULT 'socratic_handshake',
    budget_max_cycles INTEGER DEFAULT 25,
    cycles_consumed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_factory_jobs_status ON factory_jobs(status);
CREATE INDEX IF NOT EXISTS idx_factory_jobs_agent ON factory_jobs(target_agent_id);

CREATE TABLE IF NOT EXISTS factory_graphs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    nodes_json TEXT NOT NULL,
    edges_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS factory_packets (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES factory_jobs(id) ON DELETE CASCADE,
    packet_type TEXT NOT NULL,
    sender_role TEXT NOT NULL,
    recipient_role TEXT NOT NULL,
    node_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_factory_packets_job ON factory_packets(job_id, created_at);

CREATE TABLE IF NOT EXISTS factory_eval_runs (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES factory_jobs(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    stage_1_functional BOOLEAN NOT NULL DEFAULT 0,
    stage_2_safety BOOLEAN NOT NULL DEFAULT 0,
    stage_3_idempotency BOOLEAN NOT NULL DEFAULT 0,
    stage_4_critic BOOLEAN NOT NULL DEFAULT 0,
    stdout_log TEXT,
    stderr_log TEXT,
    critic_notes TEXT,
    duration_ms REAL NOT NULL,
    overall_passed BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_factory_eval_job ON factory_eval_runs(job_id, tool_name);
"""

INIT_SCHEMA_SQL = INIT_SCHEMA_SQL + FACTORY_SCHEMA_SQL
