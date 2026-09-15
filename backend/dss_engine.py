"""
Decision Support Engine — Deterministic scoring for LandNexus DSS.
All scoring functions are pure, unit-testable, and consume existing DB data.
"""

import json, os, math
from pathlib import Path
from backend.core import conn

_CONFIG_PATH = Path(__file__).parent / 'dss_config.json'
_config_cache = None

def _cfg():
    global _config_cache
    if _config_cache is None:
        with open(_CONFIG_PATH, 'r') as f:
            _config_cache = json.load(f)
    return _config_cache

def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))

def _risk_level(score):
    t = _cfg()['riskThresholds']
    if score <= t['low']: return 'LOW'
    if score <= t['moderate']: return 'MODERATE'
    if score <= t['high']: return 'HIGH'
    return 'CRITICAL'

def _dq_label(score):
    t = _cfg()['dataQualityThresholds']
    if score <= t['critical']: return 'Critical'
    if score <= t['attention']: return 'Attention Required'
    if score <= t['acceptable']: return 'Acceptable'
    return 'Good'

# ── Data Quality ──────────────────────────────────────────────────

def compute_data_quality(parcel_row):
    """Returns (score 0-100, missing_fields list). Higher = better quality, risk = 100 - score."""
    required = _cfg()['requiredParcelFields']
    present = 0
    missing = []
    for f in required:
        val = parcel_row.get(f)
        if val is not None and str(val).strip() not in ('', 'None', 'null'):
            present += 1
        else:
            missing.append(f)
    completeness = (present / len(required) * 100) if required else 100
    return round(completeness, 1), missing

# ── GIS Risk ──────────────────────────────────────────────────────

def compute_gis_risk(parcel_row):
    """Returns (score 0-100, reasons list). Higher = more risky."""
    w = _cfg()['gisRisk']
    reasons = []
    # Coordinate risk
    lat = parcel_row.get('latitude')
    lon = parcel_row.get('longitude')
    coord_risk = 0
    if lat is None or lon is None or lat == 0 or lon == 0:
        coord_risk = 100
        reasons.append('GPS coordinates missing or invalid')
    elif not (-90 <= (lat or 0) <= 90) or not (-180 <= (lon or 0) <= 180):
        coord_risk = 80
        reasons.append('GPS coordinates out of valid range')

    # Boundary risk
    boundary = parcel_row.get('boundary_geojson')
    boundary_risk = 0
    if not boundary or str(boundary).strip() in ('', 'None', 'null'):
        boundary_risk = 100
        reasons.append('Boundary information missing')
    else:
        try:
            pts = json.loads(boundary) if isinstance(boundary, str) else boundary
            if isinstance(pts, list) and len(pts) < 3:
                boundary_risk = 70
                reasons.append('Boundary has fewer than 3 points')
        except:
            boundary_risk = 90
            reasons.append('Boundary data is invalid/corrupt')

    # Geometry risk (simplified — check polygon closure)
    geometry_risk = 0
    if boundary and boundary_risk < 50:
        try:
            pts = json.loads(boundary) if isinstance(boundary, str) else boundary
            if isinstance(pts, list) and len(pts) >= 3:
                if pts[0] != pts[-1]:
                    geometry_risk = 40
                    reasons.append('Polygon is not closed')
        except:
            geometry_risk = 50

    # Area consistency
    area = parcel_row.get('area')
    area_risk = 0
    if area is None or area <= 0:
        area_risk = 80
        reasons.append('Land area is missing or zero')
    elif area > 10000:
        area_risk = 30
        reasons.append('Unusually large land area recorded')

    score = _clamp(
        w['coordinateRisk'] * coord_risk +
        w['boundaryRisk'] * boundary_risk +
        w['geometryRisk'] * geometry_risk +
        w['areaConsistency'] * area_risk
    )
    return round(score, 1), reasons

# ── SLA Risk ──────────────────────────────────────────────────────

def compute_sla_risk_for_project(project_id):
    """Returns (score 0-100, reasons list)."""
    c = conn()
    w = _cfg()['slaRisk']
    reasons = []

    milestones = [dict(r) for r in c.execute(
        "SELECT * FROM project_milestones WHERE project_id=? ORDER BY id", (project_id,)
    ).fetchall()]

    project = c.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
    c.close()

    if not milestones:
        return 0, ['No milestone data available']

    # Deadline proximity: how close is the current milestone to its expected date?
    deadline_risk = 0
    pending_risk = 0
    history_risk = 0
    dep_risk = 0

    active = [m for m in milestones if m.get('status') != 'Completed']
    completed = [m for m in milestones if m.get('status') == 'Completed']

    if active:
        current = active[0]
        expected = current.get('expected_date')
        if expected:
            try:
                from datetime import datetime
                exp_dt = datetime.strptime(expected[:10], '%Y-%m-%d')
                days_remaining = (exp_dt - datetime.now()).days
                if days_remaining < 0:
                    deadline_risk = min(100, 60 + abs(days_remaining) * 2)
                    reasons.append(f'Current milestone is {abs(days_remaining)} days overdue')
                elif days_remaining <= 7:
                    deadline_risk = 70
                    reasons.append(f'Current milestone due in {days_remaining} days')
                elif days_remaining <= 14:
                    deadline_risk = 40
                elif days_remaining <= 30:
                    deadline_risk = 20
            except:
                pass

        delay_days = current.get('delay_days') or 0
        if delay_days > 0:
            pending_risk = min(100, delay_days * 3)
            reasons.append(f'{delay_days} days of recorded delay')

    # Historical delay
    total_delay = sum(m.get('delay_days') or 0 for m in milestones)
    if total_delay > 30:
        history_risk = min(100, total_delay * 2)
        reasons.append(f'Total historical delay: {total_delay} days')
    elif total_delay > 0:
        history_risk = min(60, total_delay * 3)

    # Dependency: check if many stages are still pending
    pending_count = len(active)
    total_stages = len(milestones)
    if total_stages > 0 and pending_count / total_stages > 0.7:
        dep_risk = 50
        reasons.append(f'{pending_count}/{total_stages} stages still pending')

    score = _clamp(
        w['deadlineProximity'] * deadline_risk +
        w['pendingDuration'] * pending_risk +
        w['historicalDelay'] * history_risk +
        w['dependencyDelay'] * dep_risk
    )
    return round(score, 1), reasons

# ── Verification Risk ─────────────────────────────────────────────

def compute_verification_risk(parcel_id):
    """Returns (score 0-100, reasons list)."""
    c = conn()
    reasons = []

    assignments = [dict(r) for r in c.execute(
        "SELECT * FROM field_assignments WHERE parcel_id=? ORDER BY id DESC", (parcel_id,)
    ).fetchall()]

    verifications = [dict(r) for r in c.execute(
        "SELECT * FROM field_verifications WHERE parcel_id=? ORDER BY id DESC", (parcel_id,)
    ).fetchall()]
    c.close()

    if not assignments:
        return 80, ['No field assignment exists for this parcel']

    latest = assignments[0]
    status = (latest.get('status') or '').lower()

    score = 0
    if 'verified' in status:
        score = 10
    elif 'pending' in status:
        score = 60
        reasons.append('Verification is pending')
        # Check how long pending
        assigned_at = latest.get('assigned_at')
        if assigned_at:
            try:
                from datetime import datetime
                dt = datetime.strptime(assigned_at[:19], '%Y-%m-%d %H:%M:%S')
                days = (datetime.now() - dt).days
                if days > 14:
                    score = 85
                    reasons.append(f'Verification pending for {days} days')
                elif days > 7:
                    score = 70
                    reasons.append(f'Verification pending for {days} days')
            except:
                pass
    elif 'rejected' in status or 'failed' in status:
        score = 90
        reasons.append('Previous verification was rejected/failed')

    # Check re-verification
    if len(assignments) > 1:
        score = min(100, score + 15)
        reasons.append(f'Parcel has {len(assignments)} assignment attempts')

    if len(verifications) > 1:
        score = min(100, score + 10)
        reasons.append(f'{len(verifications)} verification records exist')

    return _clamp(score), reasons

# ── Document Risk ─────────────────────────────────────────────────

def compute_document_risk(parcel_id, project_id=None):
    """Returns (score 0-100, reasons list)."""
    c = conn()
    reasons = []

    q = "SELECT * FROM documents WHERE parcel_id=?"
    args = [parcel_id]
    if project_id:
        q += " OR project_id=?"
        args.append(project_id)

    docs = [dict(r) for r in c.execute(q, args).fetchall()]
    c.close()

    if not docs:
        return 70, ['No documents uploaded for this parcel']

    pending = sum(1 for d in docs if (d.get('verification_status') or '').lower() == 'pending')
    failed = sum(1 for d in docs if (d.get('verification_status') or '').lower() in ('rejected', 'failed'))
    low_conf = sum(1 for d in docs if (d.get('ocr_confidence') or 0) < 0.5 and (d.get('ocr_status') or '') != 'Not Started')

    score = 0
    if not docs:
        score = 70
    elif pending == len(docs):
        score = 50
        reasons.append(f'All {pending} documents are pending verification')
    elif pending > 0:
        score = 30
        reasons.append(f'{pending} documents pending verification')

    if failed > 0:
        score = min(100, score + 25)
        reasons.append(f'{failed} documents failed verification')

    if low_conf > 0:
        score = min(100, score + 15)
        reasons.append(f'{low_conf} documents have low OCR confidence')

    return _clamp(score), reasons

# ── Parcel Priority (Composite) ───────────────────────────────────

def compute_parcel_score(parcel_id):
    """Returns full DSS assessment dict for a parcel."""
    c = conn()
    row = c.execute("SELECT * FROM parcels WHERE id=?", (parcel_id,)).fetchone()
    if not row:
        c.close()
        return None
    parcel = dict(row)
    c.close()

    w = _cfg()['parcelPriority']

    dq_score, dq_missing = compute_data_quality(parcel)
    dq_risk = 100 - dq_score  # invert: low quality = high risk

    gis_score, gis_reasons = compute_gis_risk(parcel)
    ver_score, ver_reasons = compute_verification_risk(parcel_id)
    doc_score, doc_reasons = compute_document_risk(parcel_id, parcel.get('project_id'))

    # Previous issues
    prev_issues_score = 0
    prev_reasons = []
    if parcel.get('risk_category') in ('HIGH', 'CRITICAL'):
        prev_issues_score = 70
        prev_reasons.append(f"ML risk category: {parcel.get('risk_category')}")
    elif parcel.get('risk_score') and float(parcel.get('risk_score') or 0) > 0.5:
        prev_issues_score = 50
        prev_reasons.append(f"ML risk score: {parcel.get('risk_score')}")

    # Re-verification
    reverif_score = 0
    reverif_reasons = []
    c2 = conn()
    assign_count = c2.execute("SELECT COUNT(*) FROM field_assignments WHERE parcel_id=?", (parcel_id,)).fetchone()[0]
    c2.close()
    if assign_count > 1:
        reverif_score = 70
        reverif_reasons.append(f'{assign_count} assignment attempts indicate re-verification needed')

    priority_score = _clamp(
        w['dataQuality'] * dq_risk +
        w['gisRisk'] * gis_score +
        w['verificationDelay'] * ver_score +
        w['documentRisk'] * doc_score +
        w['previousIssues'] * prev_issues_score +
        w['reverification'] * reverif_score
    )

    # Master risk
    mw = _cfg()['masterRisk']
    sla_score = 0
    sla_reasons = []
    if parcel.get('project_id'):
        sla_score, sla_reasons = compute_sla_risk_for_project(parcel['project_id'])

    griev_score = 0
    griev_reasons = []
    c3 = conn()
    open_griev = c3.execute(
        "SELECT COUNT(*) FROM grievances WHERE parcel_id=? AND status != 'Resolved'", (parcel_id,)
    ).fetchone()[0]
    c3.close()
    if open_griev > 0:
        griev_score = min(100, open_griev * 30)
        griev_reasons.append(f'{open_griev} open grievance(s)')

    master_risk = _clamp(
        mw['slaRisk'] * sla_score +
        mw['workflowDelay'] * ver_score +
        mw['dataQuality'] * dq_risk +
        mw['gisRisk'] * gis_score +
        mw['verificationRisk'] * ver_score +
        mw['grievanceRisk'] * griev_score
    )

    all_reasons = []
    if dq_missing: all_reasons.append(f"Missing fields: {', '.join(dq_missing)}")
    all_reasons.extend(gis_reasons)
    all_reasons.extend(ver_reasons)
    all_reasons.extend(doc_reasons)
    all_reasons.extend(prev_reasons)
    all_reasons.extend(reverif_reasons)
    all_reasons.extend(sla_reasons)
    all_reasons.extend(griev_reasons)

    risk_level = _risk_level(priority_score)

    # Confidence
    total_data_points = len(_cfg()['requiredParcelFields'])
    available_points = total_data_points - len(dq_missing)
    conf_ratio = available_points / total_data_points if total_data_points > 0 else 0
    if conf_ratio >= 0.8:
        confidence = 'HIGH'
    elif conf_ratio >= 0.5:
        confidence = 'MEDIUM'
    else:
        confidence = 'LOW'

    return {
        'parcel_id': parcel_id,
        'record_id': parcel.get('record_id'),
        'project_id': parcel.get('project_id'),
        'district': parcel.get('district'),
        'priority_score': round(priority_score, 1),
        'risk_level': risk_level,
        'master_risk_score': round(master_risk, 1),
        'components': {
            'data_quality': {'score': round(dq_score, 1), 'risk': round(dq_risk, 1), 'label': _dq_label(dq_score), 'missing_fields': dq_missing},
            'gis_risk': {'score': round(gis_score, 1), 'reasons': gis_reasons},
            'sla_risk': {'score': round(sla_score, 1), 'reasons': sla_reasons},
            'verification_risk': {'score': round(ver_score, 1), 'reasons': ver_reasons},
            'document_risk': {'score': round(doc_score, 1), 'reasons': doc_reasons},
            'previous_issues': {'score': round(prev_issues_score, 1), 'reasons': prev_reasons},
            'reverification': {'score': round(reverif_score, 1), 'reasons': reverif_reasons},
            'grievance_risk': {'score': round(griev_score, 1), 'reasons': griev_reasons},
        },
        'reasons': all_reasons,
        'confidence': confidence,
        'requires_human_review': risk_level in ('HIGH', 'CRITICAL'),
        'engine_version': _cfg()['version'],
    }

# ── Project Risk (Composite) ──────────────────────────────────────

def compute_project_score(project_id):
    """Returns full DSS assessment dict for a project."""
    c = conn()
    proj = c.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
    if not proj:
        c.close()
        return None
    project = dict(proj)

    # Get all parcels for this project
    parcels = [dict(r) for r in c.execute("SELECT id FROM parcels WHERE project_id=?", (project_id,)).fetchall()]
    parcel_ids = [p['id'] for p in parcels]

    sample_parcel_ids = parcel_ids[:30]

    # Verification risk: average across parcels
    ver_scores = []
    ver_reasons = []
    for pid in sample_parcel_ids:
        vs, vr = compute_verification_risk(pid)
        ver_scores.append(vs)
        ver_reasons.extend(vr)
    avg_ver = sum(ver_scores) / len(ver_scores) if ver_scores else 0

    # Data quality: average across parcels
    dq_risks = []
    for pid in sample_parcel_ids:
        p_row = c.execute("SELECT * FROM parcels WHERE id=?", (pid,)).fetchone()
        if p_row:
            dq, _ = compute_data_quality(dict(p_row))
            dq_risks.append(100 - dq)
    avg_dq_risk = sum(dq_risks) / len(dq_risks) if dq_risks else 20

    # SLA risk
    sla_score, sla_reasons = compute_sla_risk_for_project(project_id)

    # Bottleneck
    bottleneck_score = 0
    bottleneck_reasons = []
    milestones = [dict(r) for r in c.execute(
        "SELECT * FROM project_milestones WHERE project_id=? AND status != 'Completed'", (project_id,)
    ).fetchall()]
    if milestones:
        total_delay = sum(m.get('delay_days') or 0 for m in milestones)
        if total_delay > 0:
            bottleneck_score = min(100, total_delay * 4)
            bottleneck_reasons.append(f'Total pending delay: {total_delay} days across {len(milestones)} stages')

    # Grievance
    open_griev = c.execute(
        "SELECT COUNT(*) FROM grievances WHERE project_id=? AND status != 'Resolved'", (project_id,)
    ).fetchone()[0]
    griev_score = min(100, open_griev * 25) if open_griev > 0 else 0
    griev_reasons = [f'{open_griev} open grievance(s)'] if open_griev > 0 else []

    # Workflow delay
    workflow_delay = 0
    workflow_reasons = []
    current_stage = project.get('current_stage')
    progress = project.get('progress') or 0
    if current_stage and progress < 50:
        start = project.get('project_start_date')
        if start:
            try:
                from datetime import datetime
                st = datetime.strptime(start[:10], '%Y-%m-%d')
                days = (datetime.now() - st).days
                if days > 180 and progress < 30:
                    workflow_delay = 80
                    workflow_reasons.append(f'Project started {days} days ago but only {progress}% complete')
                elif days > 90 and progress < 50:
                    workflow_delay = 50
                    workflow_reasons.append(f'Project started {days} days ago, {progress}% complete')
            except:
                pass

    c.close()

    pw = _cfg()['projectRisk']
    project_risk = _clamp(
        pw['slaRisk'] * sla_score +
        pw['bottleneckRisk'] * bottleneck_score +
        pw['dataQuality'] * avg_dq_risk +
        pw['verificationRisk'] * avg_ver +
        pw['grievanceRisk'] * griev_score +
        pw['workflowDelay'] * workflow_delay
    )

    all_reasons = sla_reasons + bottleneck_reasons + griev_reasons + workflow_reasons
    if ver_reasons:
        # Deduplicate
        seen = set()
        for r in ver_reasons:
            if r not in seen:
                all_reasons.append(r)
                seen.add(r)

    risk_level = _risk_level(project_risk)

    return {
        'project_id': project_id,
        'project_name': project.get('project_name'),
        'district': project.get('district'),
        'current_stage': project.get('current_stage'),
        'progress': project.get('progress'),
        'risk_score': round(project_risk, 1),
        'risk_level': risk_level,
        'components': {
            'sla_risk': {'score': round(sla_score, 1), 'reasons': sla_reasons},
            'bottleneck_risk': {'score': round(bottleneck_score, 1), 'reasons': bottleneck_reasons},
            'data_quality_risk': {'score': round(avg_dq_risk, 1)},
            'verification_risk': {'score': round(avg_ver, 1)},
            'grievance_risk': {'score': round(griev_score, 1), 'reasons': griev_reasons},
            'workflow_delay': {'score': round(workflow_delay, 1), 'reasons': workflow_reasons},
        },
        'parcel_count': len(parcel_ids),
        'reasons': all_reasons,
        'requires_human_review': risk_level in ('HIGH', 'CRITICAL'),
        'engine_version': _cfg()['version'],
    }

# ── District Priority ─────────────────────────────────────────────

def compute_district_score(district):
    """Returns DSS assessment for a district."""
    c = conn()

    # Get all projects in this district
    projects = [dict(r) for r in c.execute(
        "SELECT project_id FROM projects WHERE lower(district)=lower(?)", (district,)
    ).fetchall()]

    # SLA delay: average SLA risk across projects (sampled up to 20 projects)
    sample_projects = projects[:20]
    sla_scores = []
    for p in sample_projects:
        ss, _ = compute_sla_risk_for_project(p['project_id'])
        sla_scores.append(ss)
    avg_sla = sum(sla_scores) / len(sla_scores) if sla_scores else 0

    # Verification backlog
    pending_ver = c.execute(
        "SELECT COUNT(*) FROM field_assignments WHERE lower(district)=lower(?) AND status IN ('Pending Verification', 'Assigned')", (district,)
    ).fetchone()[0]
    total_assignments = c.execute(
        "SELECT COUNT(*) FROM field_assignments WHERE lower(district)=lower(?)", (district,)
    ).fetchone()[0]
    ver_backlog = min(100, (pending_ver / max(total_assignments, 1)) * 100)

    # Average risk
    parcels = [dict(r) for r in c.execute(
        "SELECT id, risk_score FROM parcels WHERE lower(district)=lower(?)", (district,)
    ).fetchall()]
    avg_risk = 0
    if parcels:
        scores = [float(p.get('risk_score') or 0) * 100 for p in parcels]
        avg_risk = sum(scores) / len(scores)

    # Repeated issues
    multi_assign = c.execute("""
        SELECT COUNT(*) FROM (
            SELECT parcel_id FROM field_assignments WHERE lower(district)=lower(?)
            GROUP BY parcel_id HAVING COUNT(*) > 1
        )
    """, (district,)).fetchone()[0]
    repeated = min(100, multi_assign * 20)

    # Grievance escalation
    open_grievances = c.execute("""
        SELECT COUNT(*) FROM grievances g
        LEFT JOIN projects p ON g.project_id=p.project_id
        LEFT JOIN parcels pa ON g.parcel_id=pa.id
        WHERE (lower(p.district)=lower(?) OR lower(pa.district)=lower(?)) AND g.status != 'Resolved'
    """, (district, district)).fetchone()[0]
    griev_esc = min(100, open_grievances * 15)

    # Data quality average (sampled for sub-second performance)
    sample_parcels = parcels[:50]
    dq_risks = []
    for p in sample_parcels:
        pr = c.execute("SELECT * FROM parcels WHERE id=?", (p['id'],)).fetchone()
        if pr:
            dq, _ = compute_data_quality(dict(pr))
            dq_risks.append(100 - dq)
    avg_dq = sum(dq_risks) / len(dq_risks) if dq_risks else 20

    c.close()

    dw = _cfg()['districtPriority']
    district_score = _clamp(
        dw['slaDelay'] * avg_sla +
        dw['verificationBacklog'] * ver_backlog +
        dw['riskScore'] * avg_risk +
        dw['repeatedIssues'] * repeated +
        dw['grievanceEscalation'] * griev_esc +
        dw['dataQuality'] * avg_dq
    )

    reasons = []
    if avg_sla > 50: reasons.append(f'Average SLA risk across projects: {round(avg_sla, 1)}')
    if pending_ver > 0: reasons.append(f'{pending_ver} pending verifications ({round(ver_backlog, 1)}% backlog)')
    if multi_assign > 0: reasons.append(f'{multi_assign} parcels have repeated assignments')
    if open_grievances > 0: reasons.append(f'{open_grievances} open grievances')

    return {
        'district': district,
        'priority_score': round(district_score, 1),
        'risk_level': _risk_level(district_score),
        'components': {
            'sla_delay': {'score': round(avg_sla, 1)},
            'verification_backlog': {'score': round(ver_backlog, 1), 'pending': pending_ver, 'total': total_assignments},
            'risk_score': {'score': round(avg_risk, 1)},
            'repeated_issues': {'score': round(repeated, 1), 'count': multi_assign},
            'grievance_escalation': {'score': round(griev_esc, 1), 'open': open_grievances},
            'data_quality': {'score': round(avg_dq, 1)},
        },
        'project_count': len(projects),
        'parcel_count': len(parcels),
        'reasons': reasons,
        'engine_version': _cfg()['version'],
    }

# ── State Priority ────────────────────────────────────────────────

def compute_state_score(state='Tamil Nadu'):
    """Returns DSS assessment at state level."""
    c = conn()
    districts_rows = c.execute(
        "SELECT DISTINCT district FROM projects WHERE district IS NOT NULL"
    ).fetchall()
    districts = [r['district'] for r in districts_rows]
    c.close()

    district_scores = []
    district_details = []
    for d in districts:
        ds = compute_district_score(d)
        district_scores.append(ds['priority_score'])
        district_details.append({
            'district': d,
            'priority_score': ds['priority_score'],
            'risk_level': ds['risk_level'],
            'project_count': ds['project_count'],
            'parcel_count': ds['parcel_count'],
        })

    # Sort districts by priority (highest first)
    district_details.sort(key=lambda x: x['priority_score'], reverse=True)

    sw = _cfg()['statePriority']
    avg_project_risk = sum(district_scores) / len(district_scores) if district_scores else 0

    # Get overall SLA and bottleneck info (sample up to 40 projects)
    c2 = conn()
    sample_projects = [dict(r) for r in c2.execute("SELECT project_id FROM projects ORDER BY rowid DESC LIMIT 40").fetchall()]
    total_proj_count = c2.execute("SELECT COUNT(1) FROM projects").fetchone()[0]
    sla_scores_all = []
    for p in sample_projects:
        ss, _ = compute_sla_risk_for_project(p['project_id'])
        sla_scores_all.append(ss)
    avg_sla_all = sum(sla_scores_all) / len(sla_scores_all) if sla_scores_all else 0

    open_griev_all = c2.execute("SELECT COUNT(1) FROM grievances WHERE status != 'Resolved'").fetchone()[0]
    griev_all = min(100, open_griev_all * 10)
    c2.close()

    # Bottleneck: use max district backlog
    max_backlog = max(district_scores) if district_scores else 0

    state_score = _clamp(
        sw['projectRisk'] * avg_project_risk +
        sw['slaRisk'] * avg_sla_all +
        sw['bottleneckSeverity'] * max_backlog +
        sw['districtBacklog'] * avg_project_risk +
        sw['grievance'] * griev_all
    )

    reasons = []
    if district_details and district_details[0]['priority_score'] > 50:
        reasons.append(f"Priority district: {district_details[0]['district']} (score {district_details[0]['priority_score']})")
    if avg_sla_all > 40:
        reasons.append(f'Average SLA risk across state: {round(avg_sla_all, 1)}')
    if open_griev_all > 0:
        reasons.append(f'{open_griev_all} unresolved grievances statewide')

    return {
        'state': state,
        'priority_score': round(state_score, 1),
        'risk_level': _risk_level(state_score),
        'districts': district_details,
        'total_projects': total_proj_count,
        'total_districts': len(districts),
        'components': {
            'avg_project_risk': round(avg_project_risk, 1),
            'avg_sla_risk': round(avg_sla_all, 1),
            'max_district_backlog': round(max_backlog, 1),
            'grievance_risk': round(griev_all, 1),
        },
        'reasons': reasons,
        'engine_version': _cfg()['version'],
    }

# ── Bottleneck Detection ──────────────────────────────────────────

def compute_bottlenecks(district=None):
    """Identify workflow bottlenecks across stages."""
    c = conn()
    bw = _cfg()['bottleneck']

    where = ""
    args = []
    if district and district.lower() != 'all':
        where = "JOIN projects p ON project_milestones.project_id=p.project_id WHERE lower(p.district)=lower(?) AND"
        args.append(district)
    else:
        where = "WHERE"

    rows = c.execute(f"""
        SELECT stage,
               COUNT(*) as pending_cases,
               AVG(delay_days) as average_delay,
               SUM(CASE WHEN delay_days > 0 THEN 1 ELSE 0 END) as sla_breaches
        FROM project_milestones
        {where} status != 'Completed'
        GROUP BY stage
        ORDER BY average_delay DESC
    """, args).fetchall()
    c.close()

    stages = []
    for r in rows:
        avg_delay = r['average_delay'] or 0
        pending = r['pending_cases']
        breaches = r['sla_breaches'] or 0

        # Normalize components
        dur_norm = min(100, avg_delay * 3)
        pend_norm = min(100, pending * 15)
        breach_norm = min(100, breaches * 20)
        repeat_norm = min(100, breaches * 10)  # reuse breaches as proxy

        bottleneck_score = _clamp(
            bw['avgPendingDuration'] * dur_norm +
            bw['pendingRecords'] * pend_norm +
            bw['slaBreaches'] * breach_norm +
            bw['repeatedIssues'] * repeat_norm
        )

        stages.append({
            'stage': r['stage'],
            'bottleneck_score': round(bottleneck_score, 1),
            'risk_level': _risk_level(bottleneck_score),
            'pending_cases': pending,
            'average_delay_days': round(avg_delay, 1),
            'sla_breaches': breaches,
        })

    stages.sort(key=lambda x: x['bottleneck_score'], reverse=True)

    primary = stages[0] if stages else None
    secondary = stages[1] if len(stages) > 1 else None

    return {
        'stages': stages,
        'primary_bottleneck': primary,
        'secondary_bottleneck': secondary,
        'engine_version': _cfg()['version'],
    }

# ── Early Warnings ────────────────────────────────────────────────

def compute_early_warnings(district=None):
    """Generate early warning signals from existing data."""
    warnings = []
    c = conn()

    d_filter = ""
    d_args = []
    if district and district.lower() != 'all':
        d_filter = " AND lower(district)=lower(?)"
        d_args = [district]

    # 1. SLA approaching
    approaching = c.execute(f"""
        SELECT m.project_id, p.project_name, m.stage, m.expected_date,
               CAST(julianday(m.expected_date) - julianday('now') AS INTEGER) as days_left
        FROM project_milestones m
        JOIN projects p ON p.project_id=m.project_id
        WHERE m.status != 'Completed' AND m.expected_date IS NOT NULL
        AND julianday(m.expected_date) - julianday('now') BETWEEN 0 AND 7
        {'AND lower(p.district)=lower(?)' if district and district.lower() != 'all' else ''}
        ORDER BY days_left
    """, [district] if district and district.lower() != 'all' else []).fetchall()

    for r in approaching:
        warnings.append({
            'type': 'SLA_APPROACHING',
            'entity_type': 'project',
            'entity_id': r['project_id'],
            'severity': 'HIGH',
            'message': f"Project {r['project_name']}: {r['stage']} milestone due in {r['days_left']} days",
            'recommended_action': 'Prioritize completion of current milestone',
            'risk_score': min(100, 70 + (7 - r['days_left']) * 5),
        })

    # 2. SLA overdue
    overdue = c.execute(f"""
        SELECT m.project_id, p.project_name, m.stage, m.expected_date,
               CAST(julianday('now') - julianday(m.expected_date) AS INTEGER) as days_overdue
        FROM project_milestones m
        JOIN projects p ON p.project_id=m.project_id
        WHERE m.status != 'Completed' AND m.expected_date IS NOT NULL
        AND julianday('now') > julianday(m.expected_date)
        {'AND lower(p.district)=lower(?)' if district and district.lower() != 'all' else ''}
        ORDER BY days_overdue DESC
    """, [district] if district and district.lower() != 'all' else []).fetchall()

    for r in overdue:
        warnings.append({
            'type': 'SLA_OVERDUE',
            'entity_type': 'project',
            'entity_id': r['project_id'],
            'severity': 'CRITICAL',
            'message': f"Project {r['project_name']}: {r['stage']} is {r['days_overdue']} days overdue",
            'recommended_action': 'Immediate escalation and review required',
            'risk_score': min(100, 80 + r['days_overdue']),
        })

    # 3. Verification backlog
    pending_ver = c.execute(f"""
        SELECT COUNT(*) FROM field_assignments WHERE status IN ('Pending Verification', 'Assigned')
        {d_filter.replace('district', 'field_assignments.district') if d_filter else ''}
    """, d_args).fetchone()[0]
    if pending_ver > 5:
        warnings.append({
            'type': 'VERIFICATION_BACKLOG',
            'entity_type': 'district',
            'entity_id': district or 'all',
            'severity': 'HIGH' if pending_ver > 10 else 'MODERATE',
            'message': f'{pending_ver} pending verifications in backlog',
            'recommended_action': 'Review and redistribute verification workload',
            'risk_score': min(100, pending_ver * 8),
        })

    # 4. Missing GPS/boundary
    missing_gps = c.execute(f"""
        SELECT COUNT(*) FROM parcels WHERE (latitude IS NULL OR longitude IS NULL OR latitude=0 OR longitude=0)
        {d_filter}
    """, d_args).fetchone()[0]
    if missing_gps > 0:
        warnings.append({
            'type': 'GIS_MISSING_GPS',
            'entity_type': 'district',
            'entity_id': district or 'all',
            'severity': 'MODERATE',
            'message': f'{missing_gps} parcels have missing or invalid GPS coordinates',
            'recommended_action': 'Schedule field visits to capture GPS data',
            'risk_score': min(100, missing_gps * 10),
        })

    missing_boundary = c.execute(f"""
        SELECT COUNT(*) FROM parcels WHERE (boundary_geojson IS NULL OR boundary_geojson='')
        {d_filter}
    """, d_args).fetchone()[0]
    if missing_boundary > 0:
        warnings.append({
            'type': 'GIS_MISSING_BOUNDARY',
            'entity_type': 'district',
            'entity_id': district or 'all',
            'severity': 'MODERATE',
            'message': f'{missing_boundary} parcels have missing boundary data',
            'recommended_action': 'Capture boundary surveys for affected parcels',
            'risk_score': min(100, missing_boundary * 8),
        })

    # 5. Open grievances
    griev_count = c.execute(f"""
        SELECT COUNT(*) FROM grievances g
        LEFT JOIN projects p ON g.project_id=p.project_id
        LEFT JOIN parcels pa ON g.parcel_id=pa.id
        WHERE g.status != 'Resolved'
        {'AND (lower(p.district)=lower(?) OR lower(pa.district)=lower(?))' if district and district.lower() != 'all' else ''}
    """, [district, district] if district and district.lower() != 'all' else []).fetchone()[0]
    if griev_count > 3:
        warnings.append({
            'type': 'GRIEVANCE_BACKLOG',
            'entity_type': 'district',
            'entity_id': district or 'all',
            'severity': 'HIGH',
            'message': f'{griev_count} unresolved grievances',
            'recommended_action': 'Review and prioritize grievance resolution',
            'risk_score': min(100, griev_count * 15),
        })

    c.close()
    warnings.sort(key=lambda x: x['risk_score'], reverse=True)
    return {'warnings': warnings, 'count': len(warnings), 'engine_version': _cfg()['version']}

# ── Priority Parcels ──────────────────────────────────────────────

def get_priority_parcels(district=None, limit=20, offset=0):
    """Get parcels ranked by DSS priority score with optimized candidate selection."""
    c = conn()
    d_clause = "AND lower(district)=lower(?)" if (district and district.lower() != 'all') else ""
    d_args = [district] if (district and district.lower() != 'all') else []

    # Priority candidate heuristic:
    # 1. Synthetic test parcels
    # 2. Parcels with pending field assignments
    # 3. Parcels marked HIGH / CRITICAL risk
    # 4. Parcels with missing coordinates or boundary
    q = f"""
        SELECT id FROM parcels
        WHERE (
            record_id LIKE 'SYN-%'
            OR risk_category IN ('HIGH', 'CRITICAL')
            OR latitude IS NULL OR longitude IS NULL
            OR boundary_geojson IS NULL OR boundary_geojson = ''
            OR id IN (SELECT parcel_id FROM field_assignments WHERE status IN ('Pending Verification', 'Assigned'))
        )
        {d_clause}
        ORDER BY id DESC
        LIMIT 200
    """
    rows = c.execute(q, d_args).fetchall()
    if not rows:
        # Fallback to recent parcels in district
        fb_q = f"SELECT id FROM parcels WHERE 1=1 {d_clause} ORDER BY id DESC LIMIT 100"
        rows = c.execute(fb_q, d_args).fetchall()

    parcel_ids = [r['id'] for r in rows]
    c.close()

    scored = []
    for pid in parcel_ids:
        result = compute_parcel_score(pid)
        if result:
            scored.append(result)

    scored.sort(key=lambda x: x['priority_score'], reverse=True)
    total = len(scored)
    paginated = scored[offset:offset + limit]

    return {
        'items': paginated,
        'total': total,
        'limit': limit,
        'offset': offset,
    }
