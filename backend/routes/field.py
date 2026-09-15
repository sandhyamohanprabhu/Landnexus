
from fastapi import APIRouter,Header,HTTPException,UploadFile,File
from backend.core import conn,current_user,audit,UPLOADS,enforce_district_scope,check_resource_district
import uuid
router=APIRouter()
def _officer_emails(u: dict):
    emails = [u["email"].lower()]
    if u["email"].lower() in ("field.coimbatore@tngov.in", "field@cbe.ac.in"):
        emails.extend(["field.coimbatore@tngov.in", "field@cbe.ac.in"])
    return list(dict.fromkeys(emails))

@router.get("/officers")
def officers(district: str = None, authorization: str = Header(None)):
    u = current_user(authorization)
    if not u or u["role"] not in ("district_authority", "authority", "admin", "acquisition_officer", "state_authority", "national_authority"):
        raise HTTPException(403, "Officer directory access required")
    c = conn()
    target_district = u.get("district_scope") or district
    if target_district and u["role"] == "district_authority":
        rows = [dict(x) for x in c.execute(
            "SELECT id,email,role,district_scope FROM users WHERE role='field_officer' AND active=1 AND (district_scope IS NULL OR lower(district_scope)=lower(?)) ORDER BY email",
            (target_district,)
        ).fetchall()]
    elif district and district.lower() != "all":
        rows = [dict(x) for x in c.execute(
            "SELECT id,email,role,district_scope FROM users WHERE role='field_officer' AND active=1 AND (district_scope IS NULL OR lower(district_scope)=lower(?)) ORDER BY email",
            (district,)
        ).fetchall()]
    else:
        rows = [dict(x) for x in c.execute(
            "SELECT id,email,role,district_scope FROM users WHERE role='field_officer' AND active=1 ORDER BY email"
        ).fetchall()]
    c.close()
    return rows

@router.post("/assign")
def assign(p: dict, authorization: str = Header(None)):
    u = current_user(authorization)
    if not u or u["role"] not in ("district_authority", "authority", "admin", "acquisition_officer", "state_authority", "national_authority"):
        raise HTTPException(403, "Insufficient permissions")
    c = conn()
    parcel_row = c.execute(
        "SELECT id, project_id, survey_no, village, taluk, district, owner_reference FROM parcels WHERE id=?",
        (p.get("parcel_id"),)
    ).fetchone()
    officer_row = c.execute(
        "SELECT email, district_scope, state_scope FROM users WHERE lower(email)=lower(?) AND role='field_officer' AND active=1",
        (p.get("officer_email"),)
    ).fetchone()
    if not parcel_row:
        c.close()
        raise HTTPException(404, "Parcel not found")
    if not officer_row:
        c.close()
        raise HTTPException(404, "Field officer not found")
    parcel = dict(parcel_row)
    officer = dict(officer_row)
    check_resource_district(u, parcel["district"], "Parcel")
    if officer.get("district_scope"):
        check_resource_district(officer, parcel["district"], "Field Officer Assignment")
    if p.get("project_id") and parcel["project_id"] != str(p["project_id"]):
        c.close()
        raise HTTPException(400, "Parcel is not linked to the selected project")
    if c.execute(
        "SELECT 1 FROM field_assignments WHERE parcel_id=? AND lower(officer_email)=lower(?) AND status NOT IN ('Cancelled','Revoked','Rejected')",
        (parcel["id"], officer["email"])
    ).fetchone():
        c.close()
        raise HTTPException(409, "Parcel is already assigned to this field officer")
    officer_state = officer.get("state_scope") or u.get("state_scope") or "Tamil Nadu"
    cur = c.execute(
        "INSERT INTO field_assignments(parcel_id,officer_email,assigned_by,status,project_id,district,state) VALUES(?,?,?,?,?,?,?)",
        (parcel["id"], officer["email"], u["email"], "Pending Verification", parcel["project_id"], parcel["district"], officer_state)
    )
    assignment_id = cur.lastrowid

    # Sync rr_families and rr_field_verifications so R&R workflow sees the assignment
    fam = c.execute("SELECT family_id FROM rr_families WHERE parcel_id=?", (parcel["id"],)).fetchone()
    if not fam:
        fam = c.execute(
            "SELECT family_id FROM rr_families WHERE survey_no=? AND lower(district)=lower(?)",
            (parcel["survey_no"], parcel["district"])
        ).fetchone()
    fam_id = fam["family_id"] if fam else f"FAM-{parcel['id']}"
    if not fam:
        landowner = parcel.get("owner_reference") or parcel.get("village") or "Landowner Family"
        c.execute("""
            INSERT OR IGNORE INTO rr_families (
                family_id, parcel_id, survey_no, family_head, members, district, taluk, village,
                project_id, displacement_status, rr_stage, exceptional_state, readiness_percentage,
                readiness_band, risk_level, compensation_status, housing_status, livelihood_status, grievance_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fam_id, parcel["id"], parcel["survey_no"], landowner, 4,
            parcel["district"], parcel.get("taluk") or "Central", parcel.get("village") or "Village",
            parcel["project_id"], "Physically Displaced", "Baseline Survey", "Pending Verification",
            0, "At Risk (<50%)", "Medium", "Pending Evaluation", "Pending Allotment", "Pending Training", "No Open Grievances"
        ))

    rv = c.execute(
        "SELECT id FROM rr_field_verifications WHERE family_id=? AND lower(officer_email)=lower(?)",
        (fam_id, officer["email"])
    ).fetchone()
    if not rv:
        c.execute("""
            INSERT INTO rr_field_verifications (
                family_id, officer_email, district, verification_type, status, assigned_date
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (fam_id, officer["email"], parcel["district"], "Ground Verification", "Pending Verification"))

    district_users = c.execute("SELECT email FROM users WHERE role='district_authority' AND active=1 ORDER BY id").fetchall()
    district_email = next(
        (r["email"] for r in district_users if (parcel["district"] or "").lower() in r["email"].lower()),
        district_users[0]["email"] if district_users else None
    )
    aid = "ALT-" + uuid.uuid4().hex[:10].upper()
    message = f"Parcel {parcel['id']} ({parcel['survey_no']}) assigned for field verification."
    c.execute(
        "INSERT INTO alerts(alert_id,project_id,parcel_id,type,severity,trigger,message,recommended_action,assigned_to,status) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (aid, parcel["project_id"], parcel["id"], "New Parcels Assigned for Verification", "INFO", "District Officer", message, "Complete field verification", officer["email"], "Open")
    )
    c.commit()
    c.close()
    audit(u["email"], "ASSIGN_FIELD_PARCEL", "parcel", p["parcel_id"], new_value=officer["email"])
    return {
        "message": "Field officer assignment completed",
        "assignment_id": assignment_id,
        "parcel_id": parcel["id"],
        "project_id": parcel["project_id"],
        "officer_email": officer["email"],
        "assigned_by": u["email"],
        "state": officer_state,
        "district": parcel["district"],
        "assignment_status": "Pending Verification",
        "status": "Pending Verification",
        "alert_id": aid,
        "district_officer": district_email
    }

@router.get("/assigned")
def assigned(district: str = None, authorization: str = Header(None)):
    u = current_user(authorization)
    if not u or u["role"] not in ("field_officer", "district_authority", "authority", "admin"):
        raise HTTPException(403, "Field officer access required")
    district = enforce_district_scope(u, district)
    c = conn()
    
    query = """
     SELECT a.id AS assignment_id, a.parcel_id AS parcel_id, a.officer_email,
            a.assigned_by, a.status AS assignment_status, a.created_at AS assigned_at,
            a.state AS state, a.district AS assignment_district,
            p.record_id, p.survey_no, p.subdivision, p.village, p.taluk, p.district,
            p.project_id, p.acquisition_status, p.owner_reference AS landowner,
            v.id AS verification_id,
            v.status AS verification_status, v.created_at AS verified_at,
            rf.family_id, rf.family_head, rf.members, rf.rr_stage,
            rf.exceptional_state AS rr_status, rf.readiness_percentage,
            rf.verification_status AS rr_verification_status, rf.livelihood_status,
            rf.compensation_status, rf.housing_status, rf.grievance_status
     FROM field_assignments a
     JOIN parcels p ON p.id=a.parcel_id
     LEFT JOIN field_verifications v ON v.id=(
      SELECT MAX(id) FROM field_verifications WHERE parcel_id=a.parcel_id AND (officer_email=a.officer_email OR lower(officer_email)=lower(a.officer_email))
     )
     LEFT JOIN rr_families rf ON (rf.parcel_id=a.parcel_id OR (rf.survey_no=p.survey_no AND lower(rf.district)=lower(p.district)))
    """
    where_parts = []
    params = []
    
    if u["role"] == "field_officer":
        officer_emails = _officer_emails(u)
        placeholders = ",".join("?" for _ in officer_emails)
        where_parts.append(f"lower(a.officer_email) IN ({placeholders})")
        params.extend(officer_emails)
        
        # Strict state scoping
        officer_state = u.get("state_scope") or "Tamil Nadu"
        where_parts.append("(a.state IS NULL OR lower(a.state) = lower(?))")
        params.append(officer_state.strip())
        
        # Strict district scoping
        target_dist = u.get("district_scope") or district
        if target_dist and target_dist.lower() != "all":
            where_parts.append("lower(p.district) = lower(?)")
            params.append(target_dist.strip())
            
        # Active/pending assignments
        where_parts.append("a.status NOT IN ('Cancelled', 'Revoked', 'Rejected')")
    elif u["role"] == "district_authority":
        target_dist = u.get("district_scope") or district
        if target_dist and target_dist.lower() != "all":
            where_parts.append("lower(p.district) = lower(?)")
            params.append(target_dist.strip())
    elif district and district.lower() != "all":
        where_parts.append("lower(p.district) = lower(?)")
        params.append(district.strip())
        
    if where_parts:
        query += " WHERE " + " AND ".join(where_parts)
    query += " ORDER BY a.id DESC"
    
    rows = [dict(x) for x in c.execute(query, params).fetchall()]
    for r in rows:
        if not r.get("landowner"):
            r["landowner"] = r.get("family_head") or "Landowner"
    c.close()
    return rows

@router.get("/assignments/mine")
def assignments_mine(authorization: str = Header(None)):
    """Alias for field officers to fetch their own assignments.
    Returns the same data as /assigned without requiring a district query param.
    """
    return assigned(district=None, authorization=authorization)
@router.post("/{parcel_id}/verify")
def verify(parcel_id: int, p: dict, authorization: str = Header(None)):
    u = current_user(authorization)
    if not u or u["role"] != "field_officer":
        raise HTTPException(403, "Field officer required")
    c = conn()
    officer_emails = _officer_emails(u)
    placeholders = ",".join("?" for _ in officer_emails)
    assignment = c.execute(f"""SELECT a.id assignment_id,a.parcel_id,p.project_id,p.survey_no,p.district
     FROM field_assignments a JOIN parcels p ON p.id=a.parcel_id
     WHERE a.parcel_id=? AND lower(a.officer_email) IN ({placeholders})""", (parcel_id, *officer_emails)).fetchone()
    if not assignment:
        c.close()
        raise HTTPException(403, "Parcel is not assigned to this field officer")
    check_resource_district(u, assignment["district"], "Parcel")
    verification = c.execute(f"""SELECT id FROM field_verifications
     WHERE parcel_id=? AND lower(officer_email) IN ({placeholders}) ORDER BY id DESC LIMIT 1""", (parcel_id, *officer_emails)).fetchone()
    if verification:
        verification_id = verification["id"]
    else:
        cur = c.execute("INSERT INTO field_verifications(parcel_id,officer_email,gps_lat,gps_lon,status,remarks) VALUES(?,?,?,?,?,?)",
                        (parcel_id, u["email"], p.get("gps_lat"), p.get("gps_lon"), "Verified", p.get("remarks", "")))
        verification_id = cur.lastrowid
    c.execute(f"UPDATE field_assignments SET status='Verified' WHERE parcel_id=? AND lower(officer_email) IN ({placeholders})", (parcel_id, *officer_emails))
    district_users = c.execute("SELECT email FROM users WHERE role='district_authority' AND active=1 ORDER BY id").fetchall()
    district_email = next((r["email"] for r in district_users if (assignment["district"] or "").lower() in r["email"].lower()), district_users[0]["email"] if district_users else None)
    alert = c.execute("""SELECT alert_id FROM alerts WHERE type='Field Verification Completed' AND parcel_id=? AND assigned_to=? ORDER BY id DESC LIMIT 1""", (parcel_id, district_email)).fetchone()
    if alert:
        alert_id = alert["alert_id"]
    else:
        aid = "ALT-" + uuid.uuid4().hex[:10].upper()
        c.execute("""INSERT INTO alerts(alert_id,project_id,parcel_id,type,severity,trigger,message,recommended_action,assigned_to,status)
         VALUES(?,?,?,?,?,?,?,?,?,?)""", (aid, assignment["project_id"], parcel_id, "Field Verification Completed", "INFO", "Field Officer", f"Field verification completed for survey {assignment['survey_no']}.", "Review verified field evidence", district_email, "Open"))
        alert_id = aid
    c.commit()
    c.close()
    audit(u["email"], "FIELD_VERIFICATION_SUBMITTED", "parcel", parcel_id)
    return {
        "message": "Field verification completed",
        "assignment_id": assignment["assignment_id"],
        "parcel_id": parcel_id,
        "verification_id": verification_id,
        "assignment_status": "Verified",
        "verification_status": "Verified",
        "status": "Verified",
        "alert_id": alert_id
    }

@router.post("/assignments/{assignment_id}/verify")
def verify_assignment(assignment_id: int, p: dict, authorization: str = Header(None)):
    u = current_user(authorization)
    if not u or u["role"] != "field_officer":
        raise HTTPException(403, "Field officer required")
    c = conn()
    officer_emails = _officer_emails(u)
    placeholders = ",".join("?" for _ in officer_emails)
    assignment = c.execute(f"SELECT parcel_id FROM field_assignments WHERE id=? AND lower(officer_email) IN ({placeholders})", (assignment_id, *officer_emails)).fetchone()
    c.close()
    if not assignment:
        raise HTTPException(403, "Assignment is not assigned to this field officer")
    return verify(assignment["parcel_id"], p, authorization)
