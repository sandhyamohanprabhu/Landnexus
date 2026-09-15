"""
DSS Database Migration Script
Creates dss_scores and dss_decisions tables.
Idempotent — safe to run multiple times.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.core import conn

def migrate():
    c = conn()
    c.executescript('''
CREATE TABLE IF NOT EXISTS dss_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    project_id TEXT,
    district TEXT,
    priority_score REAL DEFAULT 0,
    risk_score REAL DEFAULT 0,
    risk_level TEXT DEFAULT 'LOW',
    data_quality_score REAL DEFAULT 0,
    gis_risk_score REAL DEFAULT 0,
    sla_risk_score REAL DEFAULT 0,
    verification_risk_score REAL DEFAULT 0,
    document_risk_score REAL DEFAULT 0,
    bottleneck_score REAL DEFAULT 0,
    grievance_risk_score REAL DEFAULT 0,
    workflow_delay_score REAL DEFAULT 0,
    master_risk_score REAL DEFAULT 0,
    recommendation TEXT,
    reasons TEXT,
    evidence TEXT,
    confidence TEXT DEFAULT 'MEDIUM',
    engine_version TEXT DEFAULT '1.0.0',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_dss_scores_entity ON dss_scores(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_dss_scores_district ON dss_scores(district);
CREATE INDEX IF NOT EXISTS idx_dss_scores_risk ON dss_scores(risk_level);

CREATE TABLE IF NOT EXISTS dss_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT UNIQUE NOT NULL,
    user_email TEXT NOT NULL,
    user_role TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    project_id TEXT,
    parcel_id INTEGER,
    district TEXT,
    recommendation_id TEXT,
    recommendation TEXT,
    risk_score REAL,
    risk_level TEXT,
    reasons TEXT,
    evidence TEXT,
    human_action TEXT NOT NULL,
    modified_notes TEXT,
    workflow_action TEXT,
    engine_version TEXT DEFAULT '1.0.0',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_dss_decisions_user ON dss_decisions(user_email);
CREATE INDEX IF NOT EXISTS idx_dss_decisions_entity ON dss_decisions(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_dss_decisions_district ON dss_decisions(district);

CREATE TABLE IF NOT EXISTS dss_early_warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warning_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    project_id TEXT,
    district TEXT,
    severity TEXT DEFAULT 'MODERATE',
    message TEXT NOT NULL,
    recommended_action TEXT,
    risk_score REAL DEFAULT 0,
    status TEXT DEFAULT 'Active',
    acknowledged_by TEXT,
    acknowledged_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_dss_warnings_district ON dss_early_warnings(district);
CREATE INDEX IF NOT EXISTS idx_dss_warnings_status ON dss_early_warnings(status);
    ''')
    c.commit()
    c.close()
    print("DSS migration completed successfully.")

if __name__ == '__main__':
    migrate()
