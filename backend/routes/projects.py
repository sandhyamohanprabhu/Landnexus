from fastapi import APIRouter,HTTPException,Header
from backend.core import current_user,conn,audit,enforce_district_scope,check_resource_district
from datetime import date
router=APIRouter(); STAGES=["Proposal","Scrutiny","Approval","Notification","Survey","Award","Compensation","Legal Dispute / Resolution","Rehabilitation & Resettlement","Possession","Closure / Completion"]
WORKFLOW_STAGES=["Proposal","SIA / Survey","Notification","Legal Dispute / Resolution","Approval","Award","Compensation","Possession","Rehabilitation","Closure / Completion"]
WORKFLOW_LABELS={"Proposal":"Proposal","SIA / Survey":"SIA / Survey","Notification":"Notification","Legal Dispute / Resolution":"Objections","Approval":"Approval","Award":"Award","Compensation":"Compensation","Possession":"Possession","Rehabilitation":"Rehabilitation","Closure / Completion":"Completed"}
CURRENT_STAGE_ALIASES={"Survey":"SIA / Survey","Rehabilitation & Resettlement":"Rehabilitation"}
TRANSITION_ALERTS={"SIA / Survey":"Acquisition Survey Started","Notification":"Land Acquisition Notification Stage Started","Legal Dispute / Resolution":"Objection Period Started","Approval":"Project Awaiting Approval","Award":"Land Acquisition Award Issued","Compensation":"Compensation Process Started","Possession":"Land Possession Stage Started","Rehabilitation":"Rehabilitation / R&R Stage Started","Closure / Completion":"Land Acquisition Completed"}
def guard(a,roles=("authority","admin","acquisition_officer","district_authority")):
 u=current_user(a)
 if not u or u["role"] not in roles: raise HTTPException(403,"Insufficient permissions")
 return u

def _notification_target(c, actor, district):
 role="district_authority" if actor["role"] in ("state_authority","authority","admin") else "state_authority"
 users=c.execute("SELECT email FROM users WHERE role=? AND active=1 ORDER BY id",(role,)).fetchall()
 return next((r["email"] for r in users if district and district.lower() in r["email"].lower()), users[0]["email"] if users else None)

def _transition(project_id, next_stage, authorization):
 u=guard(authorization, roles=("district_authority","authority","admin","acquisition_officer"))
 if next_stage not in WORKFLOW_STAGES: raise HTTPException(422,"Invalid acquisition stage")
 c=conn(); project=c.execute("SELECT * FROM projects WHERE project_id=?",(project_id,)).fetchone()
 if not project: c.close(); raise HTTPException(404,"Project not found")
 check_resource_district(u, project["district"], "Project")
 current=CURRENT_STAGE_ALIASES.get(project["current_stage"],project["current_stage"]); current_idx=WORKFLOW_STAGES.index(current) if current in WORKFLOW_STAGES else -1; next_idx=WORKFLOW_STAGES.index(next_stage)
 if current_idx < 0: c.close(); raise HTTPException(409,f"Current project stage {project['current_stage']} is not in the acquisition lifecycle")
 if next_idx != current_idx+1:
  required=WORKFLOW_LABELS[WORKFLOW_STAGES[current_idx+1]] if current_idx+1 < len(WORKFLOW_STAGES) else None
  message=f"Cannot move project from {WORKFLOW_LABELS[current]} directly to {WORKFLOW_LABELS[next_stage]}." if not required else f"Cannot move project from {WORKFLOW_LABELS[current]} directly to {WORKFLOW_LABELS[next_stage]}. Complete {required} first."
  c.close(); raise HTTPException(409,message)
 if current=="Proposal" and next_stage=="SIA / Survey":
  pending=c.execute("""SELECT COUNT(1) FROM parcels p LEFT JOIN field_assignments a ON a.parcel_id=p.id AND a.status='Verified' WHERE p.project_id=? AND a.id IS NULL""",(project_id,)).fetchone()[0]
  if pending: c.close(); raise HTTPException(409,f"{pending} linked parcel(s) are still pending field verification.")
 current_row=c.execute("SELECT id FROM project_milestones WHERE project_id=? AND stage=? ORDER BY id LIMIT 1",(project_id,current)).fetchone()
 if current_row: c.execute("UPDATE project_milestones SET status='Completed',actual_date=COALESCE(actual_date,date('now')),responsible_officer=COALESCE(responsible_officer,?),updated_at=CURRENT_TIMESTAMP WHERE id=?",(u["email"],current_row["id"]))
 else: c.execute("INSERT INTO project_milestones(project_id,stage,status,actual_date,responsible_officer) VALUES(?,?, 'Completed',date('now'),?)",(project_id,current,u["email"]))
 next_row=c.execute("SELECT id FROM project_milestones WHERE project_id=? AND stage=? ORDER BY id LIMIT 1",(project_id,next_stage)).fetchone()
 if next_row: c.execute("UPDATE project_milestones SET status='In Progress',planned_date=COALESCE(planned_date,date('now')),expected_date=COALESCE(expected_date,date('now','+30 day')),responsible_officer=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(u["email"],next_row["id"]))
 else: c.execute("INSERT INTO project_milestones(project_id,stage,status,planned_date,expected_date,responsible_officer) VALUES(?,?, 'In Progress',date('now'),date('now','+30 day'),?)",(project_id,next_stage,u["email"]))
 progress=round((next_idx/(len(WORKFLOW_STAGES)-1))*100,1); status="Completed" if next_stage=="Closure / Completion" else "Active"; c.execute("UPDATE projects SET current_stage=?,project_status=?,progress=?,last_updated=CURRENT_TIMESTAMP WHERE project_id=?",(next_stage,status,progress,project_id)); c.execute("UPDATE parcels SET acquisition_status=?,last_updated=CURRENT_TIMESTAMP WHERE project_id=?",(WORKFLOW_LABELS[next_stage],project_id))
 alert_id=None; target=_notification_target(c,u,project["district"])
 if target:
  import uuid
  alert_id="ALT-"+uuid.uuid4().hex[:10].upper(); c.execute("INSERT INTO alerts(alert_id,project_id,type,severity,trigger,message,recommended_action,assigned_to,status) VALUES(?,?,?,?,?,?,?,?,?)",(alert_id,project_id,TRANSITION_ALERTS[next_stage],"INFO",u["role"],f"{project['project_name']} moved to {WORKFLOW_LABELS[next_stage]}.",f"Review {WORKFLOW_LABELS[next_stage]} stage",target,"Open"))
 c.commit(); c.close(); audit(u["email"],"WORKFLOW_TRANSITION","project",project_id,new_value=next_stage); return {"message":"Workflow transition completed","project_id":project_id,"previous_stage":current,"current_stage":next_stage,"current_stage_label":WORKFLOW_LABELS[next_stage],"progress":progress,"project_status":status,"alert_id":alert_id}
@router.get("/")
def list_projects(district: str = "", authorization: str = Header(None), limit: int = 100, offset: int = 0):
 u = current_user(authorization)
 if not u: raise HTTPException(401, "Authentication required")
 district = enforce_district_scope(u, district)
 c = conn()
 where = "WHERE 1=1"
 args = []
 if district and district.strip() and district.lower() != "all":
  where += " AND district = ?"
  args.append(district.strip())
 args += [min(limit, 500), offset]
 rows = [dict(r) for r in c.execute(f"SELECT * FROM projects {where} ORDER BY rowid DESC LIMIT ? OFFSET ?", args).fetchall()]
 c.close()
 return {"items": rows, "count": len(rows)}

@router.get("/{project_id}")
def get_project(project_id:str,authorization:str=Header(None)):
 u = current_user(authorization)
 if not u: raise HTTPException(401,"Authentication required")
 c=conn(); r=c.execute("SELECT * FROM projects WHERE project_id=?",(project_id,)).fetchone()
 if not r: c.close(); raise HTTPException(404,"Project not found")
 check_resource_district(u, r["district"], "Project")
 d=dict(r); d["workflow"]=[dict(x) for x in c.execute("SELECT * FROM project_milestones WHERE project_id=? ORDER BY id",(project_id,)).fetchall()]
 d["parcels"]=[dict(x) for x in c.execute("""
  SELECT p.*,
    f.assignment_id,
    f.officer_email AS assigned_officer,
    f.status AS raw_assignment_status,
    f.assigned_at,
    f.assigned_by,
    COALESCE(f.display_status, 'Not Assigned') AS assignment_status,
    COALESCE(f.verified_count, 0) AS verification_count
  FROM parcels p
  LEFT JOIN (
    SELECT a.id AS assignment_id, a.parcel_id, a.officer_email, a.assigned_by, a.status,
           a.created_at AS assigned_at,
           CASE 
             WHEN a.status = 'Verified' THEN 'Verified (' || a.officer_email || ')'
             WHEN a.officer_email IS NOT NULL AND a.officer_email != '' THEN 'Assigned to ' || a.officer_email
             ELSE 'Not Assigned'
           END AS display_status,
           (SELECT COUNT(1) FROM field_verifications fv WHERE fv.parcel_id = a.parcel_id AND fv.status = 'Verified') AS verified_count
    FROM field_assignments a
    WHERE a.id = (SELECT MAX(a2.id) FROM field_assignments a2 WHERE a2.parcel_id = a.parcel_id)
  ) f ON f.parcel_id = p.id
  WHERE p.project_id = ?
  ORDER BY p.id DESC LIMIT 500
 """, (project_id,)).fetchall()]
 d["linked_parcel_count"]=len(d["parcels"])
 d["linked_land_area"]=round(sum(float(p.get("area") or 0) for p in d["parcels"]),2)
 d["verified_parcel_count"]=sum(1 for p in d["parcels"] if p.get("raw_assignment_status")=="Verified" or "verified" in str(p.get("assignment_status","")).lower())
 d["pending_verification_count"]=sum(1 for p in d["parcels"] if p.get("raw_assignment_status")=="Pending Verification" or "assigned" in str(p.get("assignment_status","")).lower())
 d["unassigned_parcel_count"]=sum(1 for p in d["parcels"] if p.get("assignment_status")=="Not Assigned")
 risk_order={"CRITICAL":4,"HIGH":3,"MEDIUM":2,"LOW":1}
 risks=[p.get("risk_category") for p in d["parcels"] if p.get("risk_category")]
 d["project_risk"]=max(risks,key=lambda x:risk_order.get(x,0)) if risks else "N/A"
 c.close()
 return d

@router.post("/{project_id}/parcels/batch-assign")
def batch_assign_parcels(project_id: str, payload: dict, authorization: str = Header(None)):
  u = guard(authorization, roles=("district_authority", "authority", "admin", "state_authority", "acquisition_officer"))
  parcel_ids = payload.get("parcel_ids", [])
  officer_email = payload.get("officer_email")
  if not parcel_ids or not isinstance(parcel_ids, list):
   raise HTTPException(400, "parcel_ids must be a non-empty list of IDs")
  c = conn()
  project = c.execute("SELECT project_id, district FROM projects WHERE project_id=?", (str(project_id),)).fetchone()
  if not project: c.close(); raise HTTPException(404, "Project not found")
  check_resource_district(u, project["district"], "Project")
  
  officer = None
  if officer_email:
    officer_row = c.execute("SELECT email, district_scope, state_scope FROM users WHERE lower(email)=lower(?) AND role='field_officer' AND active=1", (officer_email,)).fetchone()
    if officer_row:
      officer = dict(officer_row)
  
  assigned_ids = []
  for pid in parcel_ids:
   row_raw = c.execute("SELECT id, survey_no, village, taluk, district, owner_reference, project_id FROM parcels WHERE id=?", (pid,)).fetchone()
   if row_raw:
    row = dict(row_raw)
    check_resource_district(u, row["district"], "Parcel")
    if not row["project_id"] or row["project_id"].strip() == "":
     c.execute("UPDATE parcels SET project_id=?, last_updated=CURRENT_TIMESTAMP WHERE id=?", (str(project_id), pid))
    assigned_ids.append(pid)

    if officer:
      officer_state = officer.get("state_scope") or u.get("state_scope") or "Tamil Nadu"
      existing = c.execute("SELECT id FROM field_assignments WHERE parcel_id=? AND lower(officer_email)=lower(?) AND status NOT IN ('Cancelled', 'Revoked', 'Rejected')", (pid, officer["email"])).fetchone()
      if not existing:
        c.execute("INSERT INTO field_assignments(parcel_id,officer_email,assigned_by,status,project_id,district,state) VALUES(?,?,?,?,?,?,?)",
                  (pid, officer["email"], u["email"], "Pending Verification", str(project_id), row["district"], officer_state))

      fam = c.execute("SELECT family_id FROM rr_families WHERE parcel_id=?", (pid,)).fetchone()
      if not fam:
        fam = c.execute("SELECT family_id FROM rr_families WHERE survey_no=? AND lower(district)=lower(?)", (row["survey_no"], row["district"])).fetchone()
      fam_id = fam["family_id"] if fam else f"FAM-{pid}"
      if not fam:
        landowner = row.get("owner_reference") or row.get("village") or "Landowner Family"
        c.execute("""
            INSERT OR IGNORE INTO rr_families (
                family_id, parcel_id, survey_no, family_head, members, district, taluk, village,
                project_id, displacement_status, rr_stage, exceptional_state, readiness_percentage,
                readiness_band, risk_level, compensation_status, housing_status, livelihood_status, grievance_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (fam_id, pid, row["survey_no"], landowner, 4, row["district"], row.get("taluk") or "Central", row.get("village") or "Village", str(project_id), "Physically Displaced", "Baseline Survey", "Pending Verification", 0, "At Risk (<50%)", "Medium", "Pending Evaluation", "Pending Allotment", "Pending Training", "No Open Grievances"))

      rv = c.execute("SELECT id FROM rr_field_verifications WHERE family_id=? AND lower(officer_email)=lower(?)", (fam_id, officer["email"])).fetchone()
      if not rv:
        c.execute("""
            INSERT INTO rr_field_verifications (
                family_id, officer_email, district, verification_type, status, assigned_date
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (fam_id, officer["email"], row["district"], "Ground Verification", "Pending Verification"))

  count = c.execute("SELECT count(*) FROM parcels WHERE project_id=?", (str(project_id),)).fetchone()[0]
  c.execute("UPDATE projects SET affected_parcels=?, number_of_parcels=? WHERE project_id=?", (count, count, str(project_id)))
  c.commit(); c.close()
  audit(u["email"], "BATCH_ASSIGN_PARCELS", "project", str(project_id), new_value=str(assigned_ids))
  return {
   "message": f"Successfully processed {len(assigned_ids)} parcels for {project_id}",
   "project_id": str(project_id),
   "assigned_count": len(assigned_ids),
   "total_linked_parcels": count,
   "assigned_parcel_ids": assigned_ids
  }

@router.post("/{project_id}/parcels/{parcel_id}")
def link_parcel(project_id:str, parcel_id:int, authorization:str=Header(None)):
 u=guard(authorization, roles=("district_authority","authority","admin","state_authority","acquisition_officer"))
 c=conn(); project=c.execute("SELECT project_id, district FROM projects WHERE project_id=?",(str(project_id),)).fetchone(); parcel=c.execute("SELECT id,project_id,district FROM parcels WHERE id=?",(parcel_id,)).fetchone()
 if not project: c.close(); raise HTTPException(404,"Project not found")
 if not parcel: c.close(); raise HTTPException(404,"Parcel not found")
 check_resource_district(u, project["district"], "Project")
 check_resource_district(u, parcel["district"], "Parcel")
 if parcel["project_id"]==str(project_id): c.close(); raise HTTPException(409,"Parcel is already linked to this project.")
 c.execute("UPDATE parcels SET project_id=?,last_updated=CURRENT_TIMESTAMP WHERE id=?",(str(project_id),parcel_id))
 count = c.execute("SELECT count(*) FROM parcels WHERE project_id=?", (str(project_id),)).fetchone()[0]
 c.execute("UPDATE projects SET affected_parcels=?, number_of_parcels=? WHERE project_id=?", (count, count, str(project_id)))
 c.commit(); c.close(); audit(u["email"],"LINK_PARCEL_TO_PROJECT","parcel",parcel_id,new_value=str(project_id)); return {"message":"Parcel linked to project","project_id":str(project_id),"parcel_id":parcel_id}

@router.post("/{project_id}/parcels/{parcel_id}/unassign")
def unassign_parcel(project_id: str, parcel_id: int, authorization: str = Header(None)):
 u = guard(authorization, roles=("district_authority", "authority", "admin", "state_authority", "acquisition_officer"))
 c = conn()
 parcel = c.execute("SELECT id, project_id, district FROM parcels WHERE id=?", (parcel_id,)).fetchone()
 if not parcel: c.close(); raise HTTPException(404, "Parcel not found")
 check_resource_district(u, parcel["district"], "Parcel")
 if parcel["project_id"] != str(project_id):
  c.close(); raise HTTPException(400, "Parcel is not assigned to this project")
 
 c.execute("UPDATE parcels SET project_id=NULL, last_updated=CURRENT_TIMESTAMP WHERE id=?", (parcel_id,))
 count = c.execute("SELECT count(*) FROM parcels WHERE project_id=?", (str(project_id),)).fetchone()[0]
 c.execute("UPDATE projects SET affected_parcels=?, number_of_parcels=? WHERE project_id=?", (count, count, str(project_id)))
 c.commit(); c.close()
 audit(u["email"], "UNASSIGN_PARCEL_FROM_PROJECT", "parcel", parcel_id, new_value="UNASSIGNED")
 return {"message": "Parcel released to unassigned pool", "project_id": str(project_id), "parcel_id": parcel_id, "remaining_parcels": count}
import uuid

@router.post("/")
def create_project(p:dict,authorization:str=Header(None)):
 u=guard(authorization, roles=("authority","admin","state_authority","acquisition_officer","district_authority"))
 check_resource_district(u, p.get("district"), "Project")
 req=["project_id","project_name","project_type","district","taluk"]; miss=[x for x in req if not p.get(x)]
 if miss: raise HTTPException(400,{"missing_fields":miss})
 p["current_stage"] = "Proposal"
 p["progress"] = 0
 c=conn()
 try:
  # Keep the compensation fields compatible with both existing and migrated databases.
  columns = {row[1] for row in c.execute("PRAGMA table_info(projects)").fetchall()}
  if "fixed_cent_rate" not in columns: c.execute("ALTER TABLE projects ADD COLUMN fixed_cent_rate REAL DEFAULT 0")
  if "total_land_area_cost" not in columns: c.execute("ALTER TABLE projects ADD COLUMN total_land_area_cost REAL DEFAULT 0")
  if "estimated_land_cost" not in columns: c.execute("ALTER TABLE projects ADD COLUMN estimated_land_cost REAL DEFAULT 0")

  land_area = float(p.get("land_required") or 0)
  cent_rate = float(p.get("fixed_cent_rate") or 0)
  if land_area < 0 or cent_rate < 0: raise ValueError("Land area and fixed cent rate cannot be negative")
  total_land_cost = land_area * 100 * cent_rate
  p["total_land_area_cost"] = total_land_cost
  p["estimated_land_cost"] = total_land_cost

  c.execute("""INSERT INTO projects(project_id,project_name,project_type,department,authority,district,taluk,village,description,priority,land_required,number_of_parcels,affected_parcels,affected_families,estimated_project_cost,estimated_land_cost,fixed_cent_rate,total_land_area_cost,project_start_date,planned_completion_date,current_stage,project_status,progress,responsible_officer) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
  [p.get(k, "") for k in ["project_id","project_name","project_type","department","authority","district","taluk","village","description","priority","land_required","number_of_parcels","affected_parcels","affected_families","estimated_project_cost","estimated_land_cost","fixed_cent_rate","total_land_area_cost","project_start_date","planned_completion_date","current_stage","project_status","progress","responsible_officer"]])
  for s in STAGES: c.execute("INSERT INTO project_milestones(project_id,stage) VALUES(?,?)",(p["project_id"],s))
  c.execute("UPDATE project_milestones SET status='In Progress',planned_date=date('now'),expected_date=date('now','+30 day') WHERE project_id=? AND stage='Proposal'",(p["project_id"],))
  aid="ALT-"+uuid.uuid4().hex[:10].upper()
  assigned_to = _notification_target(c,u,p.get("district"))
  msg = f"{p.get('project_name')} has been created by State Authority."
  c.execute("INSERT INTO alerts(alert_id,project_id,type,severity,trigger,message,assigned_to,status) VALUES(?,?,?,?,?,?,?,?)",
    (aid, p.get("project_id"), "New Project Created", "INFO", "State Authority", msg, assigned_to, "Open"))
  c.commit()
 except Exception as e:
  c.rollback(); c.close(); raise HTTPException(400,f"Unable to create project; project_id may already exist. {str(e)}")
 c.close(); audit(u["email"],"CREATE_PROJECT","project",p["project_id"]); return {"message":"Project created","project_id":p["project_id"],"fixed_cent_rate":float(p.get("fixed_cent_rate") or 0),"total_land_area_cost":float(p.get("total_land_area_cost") or 0)}
@router.patch("/{project_id}")
def edit_project(project_id:str,p:dict,authorization:str=Header(None)):
 u=guard(authorization); allowed=["project_name","priority","description","current_stage","project_status","progress","responsible_officer","planned_completion_date","actual_completion_date"]
 sets=[k+"=?" for k in allowed if k in p]; args=[p[k] for k in allowed if k in p]
 if not sets: raise HTTPException(400,"No supported fields")
 c=conn(); args.append(project_id); cur=c.execute("UPDATE projects SET "+",".join(sets)+",last_updated=CURRENT_TIMESTAMP WHERE project_id=?",args); c.commit(); c.close()
 if not cur.rowcount: raise HTTPException(404,"Project not found")
 audit(u["email"],"EDIT_PROJECT","project",project_id,new_value=str(p)); return {"message":"Project updated"}
@router.post("/{project_id}/workflow/transition")
def transition(project_id:str,p:dict,authorization:str=Header(None)):
 return _transition(project_id,p.get("next_stage") or p.get("stage"),authorization)
@router.put("/{project_id}/workflow/{stage}")
def update_workflow(project_id:str,stage:str,payload:dict,authorization:str=Header(None)):
 return _transition(project_id,stage,authorization)
