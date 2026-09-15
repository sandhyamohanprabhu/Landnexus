# LANDNEXUS — AI Role-Based Decision Support System (RB-DSS)

## Architecture Overview

The LandNexus Decision Support System (RB-DSS) is an intelligent layer operating above existing LandNexus operational entities (Projects, Parcels, GIS geometries, Field Verifications, SLA Milestones, Grievances, and Statutory Workflows).

### Core Principle
**DSS calculates → Rules recommend → LLM explains → Human decides → System records**

The system guarantees that AI never makes unilateral legal or acquisition decisions. All statutory transitions, approvals, and possession authorizations remain exclusively under authorized human officers.

---

## Multi-Criteria Scoring Formulations

### 1. Parcel Priority Score (0–100)
```text
Parcel Priority = 
  0.25 × Data Quality Risk +
  0.20 × GIS / Boundary Risk +
  0.20 × Verification Delay +
  0.15 × Document Verification Risk +
  0.10 × Historical Anomaly / ML Risk +
  0.10 × Re-verification Requirement
```

### 2. GIS Risk Score (0–100)
```text
GIS Risk =
  0.30 × Coordinate Missing / Out of Bounds +
  0.30 × Boundary Missing / Corrupt +
  0.20 × Geometry Closure Anomaly +
  0.20 × Land Area Discrepancy
```

### 3. SLA & Delay Risk Score (0–100)
```text
SLA Risk =
  0.40 × Milestone Deadline Proximity +
  0.30 × Stage Pending Duration +
  0.20 × Cumulative Historical Delay +
  0.10 × Downstream Dependency Pressure
```

### 4. Project Risk Score (0–100)
```text
Project Risk =
  0.25 × SLA Risk +
  0.20 × Stage Bottleneck Risk +
  0.20 × Average Data Quality Risk +
  0.15 × Field Verification Lag +
  0.10 × Open Grievance Escalation +
  0.10 × Overall Workflow Delay
```

### 5. District Priority Score (0–100)
```text
District Priority =
  0.30 × Average Project SLA Delay +
  0.20 × Field Verification Backlog +
  0.15 × High-Risk Parcel Volume +
  0.15 × Multi-Attempt Repeated Issues +
  0.10 × Citizen Grievance Escalation +
  0.10 × Data Quality Incompleteness
```

### 6. Statewide Strategic Priority Score (0–100)
```text
State Priority =
  0.30 × Average Project Risk +
  0.25 × Statewide SLA Lag +
  0.20 × Maximum District Bottleneck Severity +
  0.15 × District Workload Discrepancy +
  0.10 × Statewide Grievance Pressure
```

---

## Role-Based Access Control (RBAC) & Clearance Matrix

| Role | Permitted Intelligence Scope | UI Views Integrated |
| :--- | :--- | :--- |
| **Field Officer** | Scoped district priority queue, parcel-level GIS & verification risk, on-site recommendation actions | `Field Verification`, `R&R Queue`, `Parcel Details` |
| **District Authority** | Full district project risk, verification backlog, early warnings, stage bottlenecks | `District Dashboard`, `Parcels`, `Workflow` |
| **State Authority** | Cross-district risk ranking, statewide bottleneck diagnostics, strategic policy insights | `State Command Center`, Statewide Overview |
| **Citizen** | **Strictly Forbidden:** Cannot access internal DSS scores, risk weights, officer backlog, or internal decisions | `Citizen Portal` (Public status, DBT status only) |

---

## API Endpoints Reference

| Route | Method | Description | Role Clearance |
| :--- | :--- | :--- | :--- |
| `/api/dss/parcel/{id}` | GET | Retrieve full DSS score, components, and recommendation for parcel | Field Officer, Authority |
| `/api/dss/project/{id}` | GET | Retrieve composite project health, SLA risk, and bottlenecks | District / State Authority |
| `/api/dss/district/{id}` | GET | District priority index, verification backlog, and interventions | District / State Authority |
| `/api/dss/state` | GET | Statewide cross-district rankings and early warnings | State Authority |
| `/api/dss/priority-parcels` | GET | Ranked queue of high-risk parcels requiring attention | Field Officer, Authority |
| `/api/dss/bottlenecks` | GET | Lifecycle stage delay analysis and primary bottlenecks | Authority |
| `/api/dss/early-warnings` | GET | Real-time warnings (SLA approaching, overdue verifications) | Authority, Field Officer |
| `/api/dss/decision` | POST | Record human decision (`accept`, `modify`, `reject`) | Authorized Officers |
| `/api/dss/decision-history` | GET | Audit ledger of all historical AI-recommended decisions | Authorized Officers |
| `/api/dss/ask` | POST | Factual, grounded explanation queries ("Why is this high risk?") | Authorized Officers |

---

## Database Entities

- `dss_scores`: Caches multi-vector score snapshots and versioned algorithm outputs.
- `dss_decisions`: Immutable audit trail recording decision UUID, officer email, role, action taken (`accept`/`modify`/`reject`), modified notes, and automated workflow triggers.
- `dss_early_warnings`: Active trigger alerts for SLA breaches, verification backlogs, and geospatial discrepancies.
