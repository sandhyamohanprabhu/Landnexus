from fastapi import APIRouter,Header,HTTPException
from backend.core import conn,current_user,audit,enforce_district_scope,check_resource_district
import uuid
router=APIRouter()
from typing import Optional

@router.get("/")
def alerts(district: Optional[str] = None, authorization:str=Header(None),status:str=""):
 u = current_user(authorization)
 if not u: raise HTTPException(401,"Authentication required")
 district = enforce_district_scope(u, district)
 c=conn(); q="SELECT a.* FROM alerts a LEFT JOIN projects p ON p.project_id=a.project_id LEFT JOIN parcels pa ON pa.id=a.parcel_id WHERE 1=1"; args=[]; 
 if status: q+=" AND a.status=?"; args.append(status)
 if district and district.lower() != "all":
  q+=" AND (lower(p.district)=? OR lower(pa.district)=?)"; args.extend([district.lower(), district.lower()])
 q+=" ORDER BY a.id DESC LIMIT 500"; rows=[dict(x) for x in c.execute(q,args).fetchall()]; c.close(); return rows

@router.get("/operations")
def operations(district: Optional[str] = None, authorization: str = Header(None)):
 u = current_user(authorization)
 if not u: raise HTTPException(401,"Authentication required")
 district = enforce_district_scope(u, district)
 c=conn()
 where = "WHERE 1=1"
 args = []
 if district and district.lower() != "all":
  where += " AND (lower(p.district) = ? OR lower(pa.district) = ?)"
  args.extend([district.lower(), district.lower()])
 rows=[dict(x) for x in c.execute(f"""
	 SELECT a.*, p.project_name, COALESCE(p.district, pa.district) AS district, p.current_stage,
					pa.record_id, pa.survey_no, pa.village, pa.taluk,
					CASE WHEN a.status='Open' THEN 'Unread' ELSE 'Read' END AS read_status,
					CASE
						WHEN lower(a.type) LIKE '%risk%' OR lower(a.severity) IN ('high','critical') THEN 'Risk'
						WHEN lower(a.type) LIKE '%deadline%' OR lower(a.type) LIKE '%sla%' THEN 'SLA'
						WHEN lower(a.type) LIKE '%project%' OR lower(a.type) LIKE '%stage%' THEN 'Project'
						WHEN lower(a.type) LIKE '%grievance%' THEN 'Grievance'
						WHEN lower(a.type) LIKE '%verification%' OR lower(a.type) LIKE '%parcel%' THEN 'Verification'
						ELSE 'Other'
					END AS category
	 FROM alerts a LEFT JOIN projects p ON p.project_id=a.project_id LEFT JOIN parcels pa ON pa.id=a.parcel_id
	 {where}
	 ORDER BY a.id DESC LIMIT 500
 """, args).fetchall()]; c.close(); return rows

@router.post("/")
def create(a:dict,authorization:str=Header(None)):
 u=current_user(authorization)
 if not u or u["role"] not in ("authority","admin","acquisition_officer","district_authority"): raise HTTPException(403,"Insufficient permissions")
 c=conn()
 if a.get("project_id"):
  p = c.execute("SELECT district FROM projects WHERE project_id=?", (a["project_id"],)).fetchone()
  if p: check_resource_district(u, p["district"], "Project")
 if a.get("parcel_id"):
  pa = c.execute("SELECT district FROM parcels WHERE id=?", (a["parcel_id"],)).fetchone()
  if pa: check_resource_district(u, pa["district"], "Parcel")
 aid="ALT-"+uuid.uuid4().hex[:10].upper()
 c.execute("INSERT INTO alerts(alert_id,project_id,parcel_id,type,severity,trigger,message,recommended_action,assigned_to,due_date) VALUES(?,?,?,?,?,?,?,?,?,?)",(aid,a.get("project_id"),a.get("parcel_id"),a.get("type","Delay Risk"),a.get("severity","HIGH"),a.get("trigger","Manual"),a.get("message","Review required"),a.get("recommended_action","Review case"),a.get("assigned_to"),a.get("due_date"))); c.commit(); c.close(); audit(u["email"],"ALERT_GENERATED","alert",aid); return {"alert_id":aid}

@router.patch("/{alert_id}")
def update(alert_id:str,p:dict,authorization:str=Header(None)):
 u=current_user(authorization)
 if not u: raise HTTPException(401,"Authentication required")
 status=p.get("status"); allowed=("Open","Acknowledged","In Progress","Resolved")
 if status not in allowed: raise HTTPException(400,"Invalid status")
 c=conn()
 row = c.execute("""
  SELECT a.alert_id, COALESCE(pr.district, pa.district) as district
  FROM alerts a
  LEFT JOIN projects pr ON a.project_id=pr.project_id
  LEFT JOIN parcels pa ON a.parcel_id=pa.id
  WHERE a.alert_id=?
 """, (alert_id,)).fetchone()
 if not row:
  c.close(); raise HTTPException(404, "Alert not found")
 if row["district"]:
  check_resource_district(u, row["district"], "Alert")
 cur=c.execute("UPDATE alerts SET status=?,acknowledged_at=CASE WHEN ?='Acknowledged' THEN CURRENT_TIMESTAMP ELSE acknowledged_at END,resolved_at=CASE WHEN ?='Resolved' THEN CURRENT_TIMESTAMP ELSE resolved_at END WHERE alert_id=?",(status,status,status,alert_id)); c.commit(); c.close()
 audit(u["email"],"ALERT_STATUS_UPDATED","alert",alert_id,new_value=status); return {"message":"Alert updated"}
