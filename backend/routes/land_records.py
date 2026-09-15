
from fastapi import APIRouter,HTTPException,Header,UploadFile,File
from fastapi.responses import Response
from backend.core import conn,current_user,audit,UPLOADS,enforce_district_scope,check_resource_district
from backend.services.ml_service import predict,FEATURES,train_new
from backend.services.risk_service import stage_risk
from backend.services.explain_service import explain
from backend.services.validation_service import validate_land_record
from backend.services.pdf_report import generate_parcel_report
import uuid, hashlib, json, os
router=APIRouter()
@router.post("/validate")
def validate(record:dict,authorization:str=Header(None)):
 if not current_user(authorization): raise HTTPException(401,"Authentication required")
 return validate_land_record(record)
def _features(p):
 d={k:p.get(k,0) for k in FEATURES}; d["project_type"]=p.get("project_type") or "Road"; d["land_required"]=p.get("land_required",p.get("area",0)); return d
@router.get("/")
def list_parcels(authorization:str=Header(None),survey_no:str="",subdivision:str="",village:str="",taluk:str="",district:str="",risk_category:str="",project_id:str="",record_id:str="",acquisition_status:str="",q:str="",unassigned:bool=False,limit:int=100,offset:int=0):
 u = current_user(authorization)
 if not u: raise HTTPException(401,"Authentication required")
 district = enforce_district_scope(u, district)
 query_sql="SELECT * FROM parcels WHERE 1=1"; args=[]
 if unassigned:
  query_sql += " AND (project_id IS NULL OR project_id = '')"
 elif project_id:
  query_sql += " AND project_id = ?"; args.append(project_id)
 
 if district and district.strip() and district.lower() != "all":
  query_sql += " AND lower(district) = ?"; args.append(district.strip().lower())
  
 for col,val in [("survey_no",survey_no),("subdivision",subdivision),("village",village),("taluk",taluk),("risk_category",risk_category),("record_id",record_id),("acquisition_status",acquisition_status)]:
  if val and val.strip(): query_sql+=f" AND {col} LIKE ?"; args.append("%"+val.strip()+"%")

 if q and q.strip():
  q_term = "%" + q.strip() + "%"
  query_sql += " AND (survey_no LIKE ? OR subdivision LIKE ? OR village LIKE ? OR taluk LIKE ? OR record_id LIKE ? OR owner_reference LIKE ?)"
  args.extend([q_term, q_term, q_term, q_term, q_term, q_term])

 c=conn()
 total = c.execute(query_sql.replace("SELECT *", "SELECT count(*)"), args).fetchone()[0]
 query_sql+=" ORDER BY id DESC LIMIT ? OFFSET ?"; args += [min(max(limit,1),1000),max(offset,0)]
 rows=[dict(r) for r in c.execute(query_sql,args).fetchall()]; c.close(); return {"items":rows,"count":len(rows),"total":total,"limit":limit,"offset":offset}

@router.get("/mine")
def get_my_parcels(authorization: str = Header(None)):
 u = current_user(authorization)
 if not u or u["role"] != "citizen":
  raise HTTPException(403, "Citizen access required")
 c = conn()
 rows = [dict(r) for r in c.execute("""
  SELECT id, record_id, survey_no, subdivision, village, taluk, district,
         area, area_unit, classification, land_use, project_id, acquisition_status,
         latitude, longitude, owner_reference
  FROM parcels 
  WHERE lower(owner_reference)=lower(?) 
  ORDER BY id ASC
 """, (u["email"],)).fetchall()]
 c.close()
 return {"items": rows, "count": len(rows)}

@router.get("/{parcel_id}")
def get_parcel(parcel_id:str,authorization:str=Header(None)):
 u = current_user(authorization)
 if not u: raise HTTPException(401,"Authentication required")
 c=conn()
 p = None
 if str(parcel_id).isdigit():
  p = c.execute("SELECT * FROM parcels WHERE id=?",(int(parcel_id),)).fetchone()
 if not p:
  p = c.execute("SELECT * FROM parcels WHERE record_id=?",(str(parcel_id),)).fetchone()
 if not p:
  p = c.execute("SELECT * FROM parcels WHERE id=?",(str(parcel_id),)).fetchone()
 if not p:
  c.close()
  raise HTTPException(404,"Parcel not found")
  
 check_resource_district(u, p["district"], "Parcel")
 d=dict(p)
 actual_id = d["id"]
 
 try:
  d["stage_risk"]=stage_risk(d)
 except Exception:
  d["stage_risk"]={}
 try:
  d["explanation"]=explain(d)
 except Exception:
  d["explanation"]={}

 # Project linkage
 proj_id = d.get("project_id")
 if proj_id:
  pr = c.execute("SELECT * FROM projects WHERE project_id=?", (proj_id,)).fetchone()
  d["project"] = dict(pr) if pr else None
 else:
  d["project"] = None

 # Documents and OCR extractions
 docs = [dict(x) for x in c.execute("SELECT * FROM documents WHERE parcel_id=? ORDER BY id DESC",(actual_id,)).fetchall()]
 for doc in docs:
  did = doc.get("document_id")
  if did:
   try:
    ocr = c.execute("SELECT * FROM ocr_extractions WHERE document_id=? ORDER BY id DESC LIMIT 1", (did,)).fetchone()
    doc["ocr"] = dict(ocr) if ocr else None
   except Exception:
    doc["ocr"] = None
 d["documents"] = docs

 # Compensation
 try:
  d["compensation"] = [dict(x) for x in c.execute("SELECT * FROM compensation WHERE parcel_id=? ORDER BY id DESC", (actual_id,)).fetchall()]
 except Exception:
  d["compensation"] = []

 # Rehabilitation
 try:
  d["rehabilitation"] = [dict(x) for x in c.execute("SELECT * FROM r_and_r WHERE parcel_id=? ORDER BY id DESC", (actual_id,)).fetchall()]
 except Exception:
  d["rehabilitation"] = []
 try:
  d["rr_families"] = [dict(x) for x in c.execute("SELECT * FROM rr_families WHERE parcel_id=? ORDER BY id DESC", (actual_id,)).fetchall()]
 except Exception:
  d["rr_families"] = []

 # Field verifications and assignments
 try:
  d["field_verifications"] = [dict(x) for x in c.execute("SELECT * FROM field_verifications WHERE parcel_id=? ORDER BY id DESC", (actual_id,)).fetchall()]
 except Exception:
  d["field_verifications"] = []
 try:
  d["field_assignments"] = [dict(x) for x in c.execute("SELECT * FROM field_assignments WHERE parcel_id=? ORDER BY id DESC", (actual_id,)).fetchall()]
 except Exception:
  d["field_assignments"] = []

 # Grievances
 try:
  d["grievances"] = [dict(x) for x in c.execute("SELECT * FROM grievances WHERE parcel_id=? ORDER BY id DESC", (actual_id,)).fetchall()]
 except Exception:
  d["grievances"] = []

 # Alerts
 try:
  d["alerts"] = [dict(x) for x in c.execute("SELECT * FROM alerts WHERE parcel_id=? ORDER BY id DESC",(actual_id,)).fetchall()]
 except Exception:
  d["alerts"] = []

 # Audit trail
 try:
  d["audit"] = [dict(x) for x in c.execute("SELECT * FROM audit_logs WHERE entity_id=? OR entity_id=? ORDER BY id DESC LIMIT 50",(str(actual_id), str(d.get("record_id")))).fetchall()]
 except Exception:
  d["audit"] = []

 # GIS geometry and Google Maps integration
 lat = d.get("latitude")
 lon = d.get("longitude")
 has_coords = (lat is not None and lon is not None and str(lat).strip() != "" and str(lon).strip() != "")
 boundary_raw = d.get("boundary_geojson")
 boundary = None
 if boundary_raw:
  try:
   boundary = json.loads(boundary_raw)
  except Exception:
   boundary = None

 d["gis"] = {
  "has_coordinates": bool(has_coords),
  "latitude": float(lat) if has_coords else None,
  "longitude": float(lon) if has_coords else None,
  "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if has_coords else None,
  "has_boundary": bool(boundary),
  "boundary": boundary,
  "boundary_label": "Synthetic demonstration boundary" if boundary else "Synthetic demonstration location — exact parcel boundary not established.",
  "disclaimer": "Demonstration GIS geometry — not an authoritative cadastral boundary."
 }

 # Data Quality & Duplicate Detection
 try:
  dup_cases = [dict(x) for x in c.execute("SELECT * FROM duplicate_cases WHERE record_a_id=? OR record_b_id=? ORDER BY id DESC", (actual_id, actual_id)).fetchall()]
  cross_db = [dict(x) for x in c.execute("SELECT * FROM cross_db_verifications WHERE parcel_id=? ORDER BY id DESC LIMIT 5", (actual_id,)).fetchall()]
  d["data_quality"] = {
   "duplicate_flag": bool(d.get("duplicate_flag") or any(cs.get("status") == "CONFIRMED_DUPLICATE" for cs in dup_cases)),
   "master_parcel_id": d.get("master_parcel_id"),
   "duplicate_cases_count": len(dup_cases),
   "duplicate_cases": dup_cases,
   "cross_db_count": len(cross_db),
   "cross_db_verifications": cross_db,
   "assessment": "Potential Duplicate – Review Required" if dup_cases else "Verified Clean"
  }
 except Exception:
  d["data_quality"] = {"duplicate_cases_count": 0, "cross_db_count": 0, "assessment": "Verified Clean"}

 c.close()
 return d

@router.get("/{parcel_id}/pdf")
def get_parcel_pdf(parcel_id:str,authorization:str=Header(None)):
 u = current_user(authorization)
 if not u: raise HTTPException(401,"Authentication required")
 c = conn()
 p = None
 if str(parcel_id).isdigit():
  p = c.execute("SELECT * FROM parcels WHERE id=?",(int(parcel_id),)).fetchone()
 if not p:
  p = c.execute("SELECT * FROM parcels WHERE record_id=?",(str(parcel_id),)).fetchone()
 if not p:
  p = c.execute("SELECT * FROM parcels WHERE id=?",(str(parcel_id),)).fetchone()
 if not p:
  c.close()
  raise HTTPException(404,"Parcel not found")

 pd = dict(p)
 check_resource_district(u, pd["district"], "Parcel")
 try:
  pdf_bytes = generate_parcel_report(c, pd["id"], user_info=u)
 except Exception as e:
  c.close()
  raise HTTPException(500, f"Error generating parcel PDF report: {str(e)}")
 c.close()
 audit(u["email"], "EXPORT_PARCEL_PDF", "parcel", pd["id"], new_value=f"Generated PDF report for parcel {pd['id']}")
 return Response(
  content=pdf_bytes,
  media_type="application/pdf",
  headers={
   "Content-Disposition": f'attachment; filename="landnexus_parcel_{pd["id"]}_{pd.get("record_id", "dossier")}.pdf"'
  }
 )

@router.post("/")
def add(parcel:dict,authorization:str=Header(None)):
 u=current_user(authorization)
 if not u or u["role"] not in ("authority","admin","acquisition_officer","district_authority"): raise HTTPException(403,"Insufficient permissions")
 check_resource_district(u, parcel.get("district"), "Parcel")
 required=["record_id","survey_no","subdivision","village","taluk","district","area","classification","project_id","latitude","longitude","training_label"]
 missing=[x for x in required if parcel.get(x) in (None,"")]
 if missing: raise HTTPException(400,{"missing_fields":missing})
 valid=validate_land_record(parcel)
 if not valid["valid"]: raise HTTPException(400,valid)
 c=conn()
 if not c.execute("SELECT 1 FROM projects WHERE project_id=?",(parcel["project_id"],)).fetchone(): c.close(); raise HTTPException(400,"Project does not exist")
 if c.execute("SELECT 1 FROM parcels WHERE survey_no=? AND subdivision=? AND village=? AND taluk=? AND district=?",(parcel["survey_no"],parcel["subdivision"],parcel["village"],parcel["taluk"],parcel["district"])).fetchone(): c.close(); raise HTTPException(409,"Duplicate survey/subdivision parcel")
 f=_features(parcel)
 try: pred=predict(f)
 except Exception as e: c.close(); raise HTTPException(503,"ML prediction unavailable: "+str(e))
 c.execute("""INSERT INTO parcels(record_id,survey_no,subdivision,village,taluk,district,owner_reference,case_reference,area,area_unit,classification,land_use,project_id,acquisition_status,latitude,longitude,training_label,project_type,affected_families,legal_disputes,compensation_pending,approval_pending,documentation_pending,rehabilitation_pending,notification_pending,award_pending,possession_pending,stakeholder_responsiveness,environmental_risk,weather_risk,historical_delay,delay_days,remarks,validation_status,risk_category,risk_probability,risk_score,delay_probability,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
 [parcel["record_id"],parcel["survey_no"],parcel["subdivision"],parcel["village"],parcel["taluk"],parcel["district"],parcel.get("owner_reference",""),parcel.get("case_reference",""),float(parcel["area"]),parcel.get("area_unit","acres"),parcel["classification"],parcel.get("land_use",""),parcel["project_id"],parcel.get("acquisition_status","Proposal"),float(parcel["latitude"]),float(parcel["longitude"]),parcel["training_label"].upper(),f["project_type"],int(parcel.get("affected_families",0)),*[int(parcel.get(k,0) or 0) for k in ["legal_disputes","compensation_pending","approval_pending","documentation_pending","rehabilitation_pending","notification_pending","award_pending","possession_pending"]],float(parcel.get("stakeholder_responsiveness",80)),float(parcel.get("environmental_risk",20)),float(parcel.get("weather_risk",20)),float(parcel.get("historical_delay",0)),float(parcel.get("delay_days",0)),parcel.get("remarks",""),"VALID",pred["risk_category"],pred["risk_probability"],pred["risk_score"],pred["risk_probability"],u["email"]])
 pid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
 # Permanent supervised-learning record in DB
 c.execute("INSERT INTO training_examples(parcel_id,project_id,features_json,label,delay_days,verified_by) VALUES(?,?,?,?,?,?)",(pid,parcel["project_id"],json.dumps(f),parcel["training_label"].upper(),parcel.get("delay_days",0),u["email"]))
 c.execute("INSERT INTO risk_predictions(parcel_id,project_id,risk_score,risk_category,delay_probability,model_version) VALUES(?,?,?,?,?,?)",(pid,parcel["project_id"],pred["risk_score"],pred["risk_category"],pred["risk_probability"],"active"))
 c.commit(); c.close()
 audit(u["email"],"ADD_PARCEL","parcel",pid,new_value=json.dumps({"label":parcel["training_label"].upper()}))
 return {"message":"Parcel saved and verified training example persisted","parcel_id":pid,"prediction":pred,"stages":stage_risk(f),"explanation":explain(f),"training_example_persisted":True}
@router.put("/{parcel_id}")
def update(parcel_id:str,payload:dict,authorization:str=Header(None)):
 u=current_user(authorization)
 if not u or u["role"] not in ("authority","admin","acquisition_officer","field_officer","district_authority"): raise HTTPException(403,"Insufficient permissions")
 c=conn()
 old = None
 if str(parcel_id).isdigit():
  old = c.execute("SELECT * FROM parcels WHERE id=?",(int(parcel_id),)).fetchone()
 if not old:
  old = c.execute("SELECT * FROM parcels WHERE record_id=?",(str(parcel_id),)).fetchone()
 if not old:
  old = c.execute("SELECT * FROM parcels WHERE id=?",(str(parcel_id),)).fetchone()
 if not old: c.close(); raise HTTPException(404,"Parcel not found")
 check_resource_district(u, old["district"], "Parcel")
 actual_id = old["id"]
 allowed=["acquisition_status","remarks","compensation_pending","approval_pending","documentation_pending","rehabilitation_pending","notification_pending","award_pending","possession_pending","legal_disputes","stakeholder_responsiveness","environmental_risk","weather_risk","delay_days","training_label"]
 sets=[]; args=[]
 for k in allowed:
  if k in payload: sets.append(k+"=?"); args.append(payload[k])
 if not sets: c.close(); raise HTTPException(400,"No supported fields to update")
 sets.append("last_updated=CURRENT_TIMESTAMP"); args.append(actual_id); c.execute("UPDATE parcels SET "+",".join(sets)+" WHERE id=?",args); c.commit(); c.close(); audit(u["email"],"UPDATE_PARCEL","parcel",actual_id,new_value=json.dumps(payload)); return {"message":"Parcel updated"}

@router.post("/{parcel_id}/evidence")
def evidence(parcel_id:str,file:UploadFile=File(...),authorization:str=Header(None)):
 u=current_user(authorization)
 if not u or u["role"] not in ("authority","admin","acquisition_officer","field_officer","district_authority"): raise HTTPException(403,"Insufficient permissions")
 ext=os.path.splitext(file.filename or "")[1].lower()
 if ext not in (".pdf",".png",".jpg",".jpeg",".tif",".tiff",".webp"): raise HTTPException(400,"Unsupported document type")
 data=file.file.read(10*1024*1024+1)
 if len(data)>10*1024*1024: raise HTTPException(413,"File exceeds 10 MB limit")
 c=conn()
 row = None
 if str(parcel_id).isdigit():
  row = c.execute("SELECT id,project_id,district FROM parcels WHERE id=?",(int(parcel_id),)).fetchone()
 if not row:
  row = c.execute("SELECT id,project_id,district FROM parcels WHERE record_id=?",(str(parcel_id),)).fetchone()
 if not row:
  row = c.execute("SELECT id,project_id,district FROM parcels WHERE id=?",(str(parcel_id),)).fetchone()
 if not row: c.close(); raise HTTPException(404,"Parcel not found")
 check_resource_district(u, row["district"], "Parcel")
 actual_id = row["id"]
 safe=uuid.uuid4().hex+ext; path=UPLOADS/safe; path.write_bytes(data); sha=hashlib.sha256(data).hexdigest(); did="DOC-"+uuid.uuid4().hex[:12].upper()
 c.execute("INSERT INTO documents(document_id,project_id,parcel_id,document_type,document_name,path,format,uploaded_by,sha256) VALUES(?,?,?,?,?,?,?,?,?)",(did,row["project_id"],actual_id,"Evidence",file.filename,safe,ext[1:],u["email"],sha)); c.commit(); c.close(); audit(u["email"],"UPLOAD_DOCUMENT","parcel",actual_id,new_value=file.filename); return {"message":"Document uploaded","document_id":did,"sha256":sha}

