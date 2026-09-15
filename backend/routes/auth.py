
from fastapi import APIRouter,HTTPException,Header,Request
from pydantic import BaseModel
from backend.core import conn,verify,hash_password,token,current_user,audit,AUTH_EMAIL
router=APIRouter()
class Login(BaseModel): email:str; password:str
class UserIn(BaseModel): email:str; password:str; role:str
class CitizenRegister(BaseModel):
 full_name: str
 email: str
 password: str
 phone: str = ""
 survey_no: str
 district: str

@router.post("/login")
def login(x:Login):
 email = (x.email or "").strip()
 pwd = x.password or ""
 c=conn(); u=c.execute("SELECT * FROM users WHERE lower(email)=lower(?) AND active=1",(email,)).fetchone(); c.close()
 if not u or not verify(pwd,u["password_hash"]): raise HTTPException(401,"Invalid credentials")
 u_dict = dict(u)
 return {
  "access_token": token(u_dict["email"], u_dict["role"], u_dict.get("district_scope"), u_dict.get("state_scope")),
  "token_type": "bearer",
  "user": {
   "email": u_dict["email"],
   "role": u_dict["role"],
   "is_authority": bool(u_dict.get("is_authority")),
   "district_scope": u_dict.get("district_scope"),
   "state_scope": u_dict.get("state_scope")
  }
 }

@router.post("/citizen/register")
def citizen_register(x: CitizenRegister):
 email = (x.email or "").strip()
 pwd = x.password or ""
 survey_no = (x.survey_no or "").strip()
 district = (x.district or "").strip()

 if not email or "@" not in email:
  raise HTTPException(400, "Valid email address is required")
 if len(pwd) < 6:
  raise HTTPException(400, "Password must be at least 6 characters")
 if not survey_no or not district:
  raise HTTPException(400, "Survey number and district are required")

 c = conn()
 try:
  existing = c.execute("SELECT id FROM users WHERE lower(email)=lower(?)", (email,)).fetchone()
  if existing:
   raise HTTPException(400, "An account with this email already exists")

  # Strictly verify if matching parcel exists in the database
  # IMPORTANT RULE: Citizen registration must NEVER create fake government land records!
  parcel = c.execute("""
   SELECT id, survey_no, district, village, taluk, owner_reference 
   FROM parcels 
   WHERE lower(district)=lower(?) AND lower(survey_no)=lower(?)
   ORDER BY id ASC LIMIT 1
  """, (district, survey_no)).fetchone()

  if not parcel:
   # Do NOT create a parcel. Return verification required message
   raise HTTPException(404, "Survey number not found. Verification required.")

  # Link citizen to the existing parcel
  c.execute("UPDATE parcels SET owner_reference=? WHERE id=?", (email, parcel["id"]))

  # Determine state scope dynamically from parcel district
  p_dist = str(parcel["district"]).strip()
  kerala_districts = ["palakkad", "ernakulam", "thrissur", "thiruvananthapuram"]
  state_sc = "Kerala" if p_dist.lower() in kerala_districts else "Tamil Nadu"

  # Insert user record
  c.execute("""
   INSERT INTO users(email, password_hash, role, district_scope, state_scope, active, is_authority)
   VALUES(?, ?, 'citizen', ?, ?, 1, 0)
  """, (email, hash_password(pwd), p_dist, state_sc))
  c.commit()

  u_dict = {
   "email": email,
   "role": "citizen",
   "district_scope": p_dist,
   "state_scope": state_sc,
   "is_authority": False
  }

  audit(email, "CITIZEN_REGISTER", "user", email, new_value=f"linked_parcel_{parcel['id']}")

  return {
   "message": "Citizen registration successful. Linked to verified land parcel.",
   "access_token": token(u_dict["email"], u_dict["role"], u_dict["district_scope"], u_dict["state_scope"]),
   "token_type": "bearer",
   "user": u_dict,
   "parcel": {
    "parcel_id": parcel["id"],
    "survey_no": parcel["survey_no"],
    "district": parcel["district"],
    "village": parcel["village"],
    "taluk": parcel["taluk"]
   }
  }
 finally:
  c.close()

@router.get("/me")
def me(authorization:str=Header(None)):
 u=current_user(authorization)
 if not u: raise HTTPException(401,"Authentication required")
 return {
  "email": u["email"],
  "role": u["role"],
  "is_authority": bool(u.get("is_authority")),
  "district_scope": u.get("district_scope"),
  "state_scope": u.get("state_scope")
 }
@router.get("/users")
def users(authorization:str=Header(None)):
 u=current_user(authorization)
 if not u or u["role"] not in ("authority", "national_authority", "admin"): raise HTTPException(403,"Authority or Admin only")
 c=conn(); rows=[dict(r) for r in c.execute("SELECT id,email,role,district_scope,state_scope,active,is_authority,created_at FROM users ORDER BY id").fetchall()]; c.close(); return rows
@router.post("/users")
def add_user(x:UserIn,authorization:str=Header(None)):
 u=current_user(authorization)
 if not u or u["role"] not in ("authority", "national_authority", "admin"): raise HTTPException(403,"Authority or Admin only")
 allowed_roles = ("admin", "authority", "national_authority", "state_authority", "district_authority", "acquisition_officer", "field_officer", "citizen")
 if x.role not in allowed_roles or x.email.strip().lower()==AUTH_EMAIL.lower(): raise HTTPException(400,"Invalid role or protected authority account")
 if len(x.password)<8: raise HTTPException(400,"Password must be at least 8 characters")
 c=conn()
 try: c.execute("INSERT INTO users(email,password_hash,role) VALUES(?,?,?)",(x.email.strip(),hash_password(x.password),x.role)); c.commit()
 except Exception: raise HTTPException(400,"Unable to create user: duplicate or invalid account")
 finally: c.close()
 audit(u["email"],"CREATE_USER","user",x.email.strip(),new_value=x.role); return {"message":"User created"}
@router.delete("/users/{user_id}")
def disable_user(user_id:int,authorization:str=Header(None)):
 u=current_user(authorization)
 if not u or u["role"] not in ("authority", "national_authority", "admin"): raise HTTPException(403,"Authority or Admin only")
 c=conn(); row=c.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
 if not row: c.close(); raise HTTPException(404,"User not found")
 if row["is_authority"] or row["email"].lower()==AUTH_EMAIL.lower() or row["email"].lower()=="national.admin@landnexus.gov": c.close(); raise HTTPException(400,"Permanent Authority accounts cannot be disabled")
 c.execute("UPDATE users SET active=0 WHERE id=?",(user_id,)); c.commit(); c.close(); audit(u["email"],"DISABLE_USER","user",row["email"]); return {"message":"User disabled"}
