from pathlib import Path
import sqlite3, hashlib, hmac, base64, json, time, secrets
from fastapi import HTTPException

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; DB=DATA/'survi.db'; MODEL_DIR=ROOT/'models'; MODEL_DIR.mkdir(exist_ok=True); UPLOADS=ROOT/'uploads'; UPLOADS.mkdir(exist_ok=True)
AUTH_EMAIL='Tngov@cbe.ac.in'; AUTH_PASSWORD='Tngov@CBE#2026'

def conn():
 c=sqlite3.connect(DB, timeout=30.0); c.row_factory=sqlite3.Row; return c

def hash_password(p):
 salt=secrets.token_bytes(16); dk=hashlib.pbkdf2_hmac('sha256',p.encode(),salt,120000); return base64.b64encode(salt+dk).decode()

def verify(p,stored):
 try:
  raw=base64.b64decode(stored); return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',p.encode(),raw[:16],120000),raw[16:])
 except: return False

def secret_key(): return 'SURVI-TNGOV-MASTER-CHANGE-IN-PRODUCTION-2026'

def token(email, role, district_scope=None, state_scope=None):
 payload={'email':email,'role':role,'district_scope':district_scope,'state_scope':state_scope,'exp':int(time.time())+8*3600}
 raw=base64.urlsafe_b64encode(json.dumps(payload,separators=(',',':')).encode()).decode().rstrip('=')
 sig=hmac.new(secret_key().encode(),raw.encode(),hashlib.sha256).hexdigest()
 return raw+'.'+sig

def current_user(authorization):
 if not authorization or not isinstance(authorization, str) or not authorization.startswith('Bearer '): return None
 try:
  raw,sig=authorization[7:].split('.',1); expected=hmac.new(secret_key().encode(),raw.encode(),hashlib.sha256).hexdigest()
  if not hmac.compare_digest(sig,expected): return None
  p=json.loads(base64.urlsafe_b64decode(raw+'==='));
  if p['exp']<time.time(): return None
  c=conn(); u=c.execute('SELECT * FROM users WHERE lower(email)=lower(?) AND active=1',(p['email'],)).fetchone(); c.close(); return dict(u) if u else None
 except: return None

def enforce_state_scope(u, requested_state: str = None) -> str:
 if not u:
  raise HTTPException(401, "Authentication required")
 scope = u.get("state_scope")
 if scope:
  if requested_state and requested_state.strip() and requested_state.strip().lower() != scope.strip().lower():
   raise HTTPException(403, f"Cross-state access forbidden: account is scoped to {scope}, cannot access {requested_state}")
  return scope
 return requested_state.strip() if (requested_state and requested_state.strip()) else "Tamil Nadu"

def enforce_district_scope(u, requested_district: str = None) -> str:
 if not u:
  raise HTTPException(401, "Authentication required")
 scope = u.get("district_scope")
 if scope:
  if requested_district and requested_district.strip() and requested_district.strip().lower() != "all" and requested_district.strip().lower() != scope.strip().lower():
   raise HTTPException(403, f"Cross-district access forbidden: account is permanently scoped to {scope}, cannot access {requested_district}")
  return scope

 state_scope = u.get("state_scope")
 if state_scope and requested_district and requested_district.strip():
  # Validate that the requested district belongs to this state
  from backend.routes.dashboard import STATE_DISTRICTS
  allowed_districts = [d.lower() for d in STATE_DISTRICTS.get(state_scope, [])]
  if allowed_districts and requested_district.strip().lower() not in allowed_districts and requested_district.strip().lower() != "all":
   raise HTTPException(403, f"Cross-state access forbidden: account is scoped to {state_scope}, cannot access district {requested_district}")

 if requested_district and requested_district.strip():
  return requested_district.strip()
 
 if u.get("role") in ("national_authority", "admin", "state_authority") and not u.get("district_scope"):
  return "all"

 state = u.get("state_scope")
 return "Palakkad" if (state and state.lower() == "kerala") else "Coimbatore"

def check_resource_district(u, resource_district: str, resource_name: str = "resource"):
 if not u:
  raise HTTPException(401, "Authentication required")
 scope = u.get("district_scope")
 if scope:
  if not resource_district or resource_district.strip().lower() != scope.strip().lower():
   raise HTTPException(403, f"Cross-district access forbidden: {resource_name} belongs to {resource_district}, but account is scoped to {scope}")

def audit(user, action, target, details='', *args, **kwargs):
 nv = kwargs.get('new_value', '')
 extra = ' '.join(str(a) for a in args)
 d_parts = [str(details)]
 if extra: d_parts.append(extra)
 if nv: d_parts.append(f"value={nv}")
 for k, v in kwargs.items():
  if k != 'new_value': d_parts.append(f"{k}={v}")
 full_details = ' | '.join(p for p in d_parts if p)
 c = conn()
 c.execute('INSERT INTO audit(user_email,action,target,details) VALUES(?,?,?,?)', (str(user), str(action), str(target), full_details))
 c.commit(); c.close()

def init_db():
 DATA.mkdir(exist_ok=True); c=conn(); c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL,district_scope TEXT,state_scope TEXT,active INTEGER DEFAULT 1,is_authority INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS parcels(id INTEGER PRIMARY KEY AUTOINCREMENT,record_id TEXT UNIQUE,survey_no TEXT,subdivision TEXT,village TEXT,taluk TEXT,district TEXT,area REAL,classification TEXT,project_id TEXT,latitude REAL,longitude REAL,validation_status TEXT,risk_category TEXT,risk_probability REAL,risk_score REAL,delay_probability REAL,training_label TEXT,created_by TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY AUTOINCREMENT,parcel_id INTEGER,filename TEXT,path TEXT,uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,user_email TEXT,action TEXT,target TEXT,details TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS model_versions(id INTEGER PRIMARY KEY AUTOINCREMENT,version TEXT UNIQUE,model_path TEXT,training_rows INTEGER,accuracy REAL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS projects(project_id TEXT PRIMARY KEY,project_name TEXT,project_type TEXT,district TEXT,taluk TEXT,total_land_required REAL,affected_parcels INTEGER,affected_families INTEGER,project_start_date TEXT,expected_completion_date TEXT);
CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY AUTOINCREMENT,document_id TEXT UNIQUE NOT NULL,project_id TEXT,parcel_id INTEGER,document_name TEXT,path TEXT,format TEXT,uploaded_by TEXT,verification_status TEXT DEFAULT 'Pending',ocr_status TEXT DEFAULT 'Not Started',ocr_confidence REAL DEFAULT 0.0,remarks TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS ocr_extractions(id INTEGER PRIMARY KEY AUTOINCREMENT,document_id TEXT NOT NULL,field_name TEXT NOT NULL,value TEXT,confidence REAL DEFAULT 1.0,validation_status TEXT DEFAULT 'Pending',human_verified INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS privacy_analyses(id INTEGER PRIMARY KEY AUTOINCREMENT,document_id TEXT UNIQUE NOT NULL,parcel_id INTEGER,project_id TEXT,risk_score INTEGER DEFAULT 0,risk_level TEXT DEFAULT 'LOW',total_detected INTEGER DEFAULT 0,critical_count INTEGER DEFAULT 0,sensitive_count INTEGER DEFAULT 0,controlled_count INTEGER DEFAULT 0,operational_count INTEGER DEFAULT 0,raw_summary TEXT,analyzed_by TEXT,analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS privacy_detections(id INTEGER PRIMARY KEY AUTOINCREMENT,document_id TEXT NOT NULL,field_key TEXT NOT NULL,field_label TEXT NOT NULL,detected_value_masked TEXT NOT NULL,detected_value_hash TEXT,category TEXT NOT NULL,default_visibility TEXT NOT NULL,confidence REAL DEFAULT 1.0,detection_method TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS privacy_access_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,document_id TEXT NOT NULL,parcel_id INTEGER,project_id TEXT,field_key TEXT NOT NULL,requested_by TEXT NOT NULL,requested_role TEXT NOT NULL,purpose TEXT NOT NULL,reason TEXT NOT NULL,duration_hours INTEGER DEFAULT 24,status TEXT DEFAULT 'Pending',reviewed_by TEXT,reviewed_at TEXT,rejection_reason TEXT,expires_at TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS privacy_policies(id INTEGER PRIMARY KEY AUTOINCREMENT,policy_code TEXT UNIQUE NOT NULL,role TEXT NOT NULL,purpose TEXT NOT NULL,field_category TEXT NOT NULL,allowed_visibility TEXT NOT NULL,requires_authorization INTEGER DEFAULT 0,description TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS ocr_learning_records(id INTEGER PRIMARY KEY AUTOINCREMENT,document_id TEXT NOT NULL,parcel_id INTEGER,project_id TEXT,field_name TEXT NOT NULL,original_value TEXT,corrected_value TEXT,language TEXT,script TEXT,ocr_engine TEXT,processing_mode TEXT,verified_by TEXT NOT NULL,verifier_role TEXT,verified_at TEXT DEFAULT CURRENT_TIMESTAMP,model_version TEXT DEFAULT 'v1.0.0-baseline',status TEXT DEFAULT 'Pending Retraining');
CREATE TABLE IF NOT EXISTS duplicate_cases(id INTEGER PRIMARY KEY AUTOINCREMENT,case_id TEXT UNIQUE NOT NULL,record_a_id INTEGER NOT NULL,record_b_id INTEGER NOT NULL,similarity_score REAL NOT NULL,confidence_band TEXT NOT NULL,primary_reasons TEXT NOT NULL,status TEXT DEFAULT 'NEW',decision TEXT,decision_reason TEXT,decision_evidence TEXT,master_record_id INTEGER,assigned_officer TEXT,resolved_by TEXT,resolved_at TEXT,district TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS cross_db_verifications(id INTEGER PRIMARY KEY AUTOINCREMENT,verification_id TEXT UNIQUE NOT NULL,parcel_id INTEGER NOT NULL,source_name TEXT NOT NULL,source_type TEXT NOT NULL,status TEXT NOT NULL,is_demo INTEGER DEFAULT 0,matched_fields TEXT,mismatched_fields TEXT,details TEXT,verified_at TEXT DEFAULT CURRENT_TIMESTAMP,verified_by TEXT);
CREATE INDEX IF NOT EXISTS idx_dup_cases_dist ON duplicate_cases(district);
CREATE INDEX IF NOT EXISTS idx_dup_cases_records ON duplicate_cases(record_a_id, record_b_id);
CREATE INDEX IF NOT EXISTS idx_cross_db_parcel ON cross_db_verifications(parcel_id);
CREATE TABLE IF NOT EXISTS workflow(project_id TEXT,stage TEXT,status TEXT,notes TEXT,updated_by TEXT,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(project_id,stage));''')
 
 cols = [r['name'] for r in c.execute("PRAGMA table_info(users)").fetchall()]
 if 'district_scope' not in cols:
  c.execute("ALTER TABLE users ADD COLUMN district_scope TEXT")
 if 'state_scope' not in cols:
  c.execute("ALTER TABLE users ADD COLUMN state_scope TEXT")

 doc_cols = [r['name'] for r in c.execute("PRAGMA table_info(documents)").fetchall()]
 for col_def in [
     ("language", "TEXT DEFAULT 'en'"),
     ("language_confidence", "REAL DEFAULT 1.0"),
     ("ocr_engine", "TEXT DEFAULT 'Tesseract OCR'"),
     ("processing_mode", "TEXT DEFAULT 'auto'"),
     ("processed_path", "TEXT"),
     ("verified_by", "TEXT"),
     ("verified_at", "TEXT"),
     ("rejection_reason", "TEXT"),
     ("duplicate_flag", "INTEGER DEFAULT 0"),
 ]:
     if col_def[0] not in doc_cols:
         c.execute(f"ALTER TABLE documents ADD COLUMN {col_def[0]} {col_def[1]}")

 ocr_cols = [r['name'] for r in c.execute("PRAGMA table_info(ocr_extractions)").fetchall()]
 for col_def in [
     ("original_value", "TEXT"),
     ("corrected_value", "TEXT"),
     ("field_confidence", "REAL DEFAULT 1.0"),
     ("uncertainty_label", "TEXT DEFAULT 'Engine confidence'"),
     ("notes", "TEXT"),
 ]:
     if col_def[0] not in ocr_cols:
         c.execute(f"ALTER TABLE ocr_extractions ADD COLUMN {col_def[0]} {col_def[1]}")

 fa_cols = [r['name'] for r in c.execute("PRAGMA table_info(field_assignments)").fetchall()]
 if 'project_id' not in fa_cols:
  c.execute("ALTER TABLE field_assignments ADD COLUMN project_id TEXT")
 if 'district' not in fa_cols:
  c.execute("ALTER TABLE field_assignments ADD COLUMN district TEXT")
 if 'state' not in fa_cols:
  c.execute("ALTER TABLE field_assignments ADD COLUMN state TEXT")

 p_cols = [r['name'] for r in c.execute("PRAGMA table_info(parcels)").fetchall()]
 if 'duplicate_flag' not in p_cols:
  c.execute("ALTER TABLE parcels ADD COLUMN duplicate_flag INTEGER DEFAULT 0")
 if 'master_parcel_id' not in p_cols:
  c.execute("ALTER TABLE parcels ADD COLUMN master_parcel_id INTEGER")
 if 'boundary_geojson' not in p_cols:
  c.execute("ALTER TABLE parcels ADD COLUMN boundary_geojson TEXT")


 # Seed default Coimbatore authority
 row=c.execute('SELECT * FROM users WHERE lower(email)=lower(?)',(AUTH_EMAIL,)).fetchone()
 if not row: c.execute('INSERT INTO users(email,password_hash,role,district_scope,state_scope,is_authority) VALUES(?,?,?, "Coimbatore", "Tamil Nadu", 1)',(AUTH_EMAIL,hash_password(AUTH_PASSWORD),'authority'))
 else: c.execute('UPDATE users SET is_authority=1,role="authority",district_scope="Coimbatore",state_scope="Tamil Nadu",active=1 WHERE lower(email)=lower(?)',(AUTH_EMAIL,))
 
 # Complete authorized accounts suite with guaranteed credentials (Pass: Tngov@CBE#2026)
 accounts = [
  # National Authority & System Administrators
  ("national.admin@landnexus.gov", hash_password(AUTH_PASSWORD), "national_authority", None, None, 1),
  ("admin@survi.gov.in", hash_password(AUTH_PASSWORD), "admin", None, None, 1),
  ("admin@cbe.ac.in", hash_password(AUTH_PASSWORD), "admin", None, None, 1),
  # State Authorities
  ("state.tamilnadu@tngov.in", hash_password(AUTH_PASSWORD), "state_authority", None, "Tamil Nadu", 1),
  ("state.kerala@kerala.gov.in", hash_password(AUTH_PASSWORD), "state_authority", None, "Kerala", 1),
  ("state@cbe.ac.in", hash_password(AUTH_PASSWORD), "state_authority", None, "Tamil Nadu", 1),
  # District Authorities (All 5 Districts + Demo)
  ("district.coimbatore@tngov.in", hash_password(AUTH_PASSWORD), "district_authority", "Coimbatore", "Tamil Nadu", 1),
  ("district.tiruppur@tngov.in", hash_password(AUTH_PASSWORD), "district_authority", "Tiruppur", "Tamil Nadu", 1),
  ("district.erode@tngov.in", hash_password(AUTH_PASSWORD), "district_authority", "Erode", "Tamil Nadu", 1),
  ("district.salem@tngov.in", hash_password(AUTH_PASSWORD), "district_authority", "Salem", "Tamil Nadu", 1),
  ("district.namakkal@tngov.in", hash_password(AUTH_PASSWORD), "district_authority", "Namakkal", "Tamil Nadu", 1),
  ("district@cbe.ac.in", hash_password(AUTH_PASSWORD), "district_authority", "Coimbatore", "Tamil Nadu", 1),
  # Acquisition Officers (All 5 Districts)
  ("officer.coimbatore@tngov.in", hash_password(AUTH_PASSWORD), "acquisition_officer", "Coimbatore", "Tamil Nadu", 0),
  ("officer.tiruppur@tngov.in", hash_password(AUTH_PASSWORD), "acquisition_officer", "Tiruppur", "Tamil Nadu", 0),
  ("officer.erode@tngov.in", hash_password(AUTH_PASSWORD), "acquisition_officer", "Erode", "Tamil Nadu", 0),
  ("officer.salem@tngov.in", hash_password(AUTH_PASSWORD), "acquisition_officer", "Salem", "Tamil Nadu", 0),
  ("officer.namakkal@tngov.in", hash_password(AUTH_PASSWORD), "acquisition_officer", "Namakkal", "Tamil Nadu", 0),
  # Field Officers (All 5 Districts + Demo)
  ("field.coimbatore@tngov.in", hash_password(AUTH_PASSWORD), "field_officer", "Coimbatore", "Tamil Nadu", 0),
  ("field.tiruppur@tngov.in", hash_password(AUTH_PASSWORD), "field_officer", "Tiruppur", "Tamil Nadu", 0),
  ("field.erode@tngov.in", hash_password(AUTH_PASSWORD), "field_officer", "Erode", "Tamil Nadu", 0),
  ("field.salem@tngov.in", hash_password(AUTH_PASSWORD), "field_officer", "Salem", "Tamil Nadu", 0),
  ("field.namakkal@tngov.in", hash_password(AUTH_PASSWORD), "field_officer", "Namakkal", "Tamil Nadu", 0),
  ("field@cbe.ac.in", hash_password(AUTH_PASSWORD), "field_officer", "Coimbatore", "Tamil Nadu", 0),
  # Citizen Accounts (Demo & Synthetic Landowners)
  ("citizen@cbe.ac.in", hash_password(AUTH_PASSWORD), "citizen", "Coimbatore", "Tamil Nadu", 0),
  ("citizen@demo.in", hash_password(AUTH_PASSWORD), "citizen", "Coimbatore", "Tamil Nadu", 0),
  ("citizen.demo.syn001@example.com", hash_password(AUTH_PASSWORD), "citizen", "Coimbatore", "Tamil Nadu", 0),
  ("citizen.demo.syn002@example.com", hash_password(AUTH_PASSWORD), "citizen", "Coimbatore", "Tamil Nadu", 0),
  ("citizen.demo.syn003@example.com", hash_password(AUTH_PASSWORD), "citizen", "Coimbatore", "Tamil Nadu", 0),
  ("citizen.demo.syn004@example.com", hash_password(AUTH_PASSWORD), "citizen", "Coimbatore", "Tamil Nadu", 0),
  ("citizen.demo.syn005@example.com", hash_password(AUTH_PASSWORD), "citizen", "Coimbatore", "Tamil Nadu", 0),
 ]
 for email, pwd_hash, role, dist, state_sc, is_auth in accounts:
  u_row = c.execute("SELECT id FROM users WHERE lower(email)=lower(?)", (email,)).fetchone()
  if not u_row:
   c.execute("INSERT INTO users(email, password_hash, role, district_scope, state_scope, active, is_authority) VALUES(?,?,?,?,?,1,?)", (email, pwd_hash, role, dist, state_sc, is_auth))
  else:
   c.execute("UPDATE users SET password_hash=?, role=?, district_scope=?, state_scope=?, is_authority=?, active=1 WHERE lower(email)=lower(?)", (pwd_hash, role, dist, state_sc, is_auth, email))

 # Ensure demo accounts are verified with district and state scopes
 c.execute("UPDATE users SET district_scope='Coimbatore', state_scope='Tamil Nadu' WHERE lower(email) IN ('district@cbe.ac.in', 'field@cbe.ac.in', 'citizen@cbe.ac.in')")

 try:
  import pandas as pd; csv=ROOT/'data/coimbatore/06_acquisition_projects.csv'
  if csv.exists() and c.execute('SELECT count(*) n FROM projects').fetchone()['n']==0:
   df=pd.read_csv(csv).fillna('')
   for _,r in df.iterrows(): c.execute('INSERT OR IGNORE INTO projects VALUES(?,?,?,?,?,?,?,?,?,?)',tuple(r.get(k,'') for k in ['project_id','project_name','project_type','district','taluk','total_land_required','affected_parcels','affected_families','project_start_date','expected_completion_date']))
 except Exception: pass
 c.commit(); c.close()

def init_rr_tables():
 c=conn()
 c.executescript('''
CREATE TABLE IF NOT EXISTS rr_families(id INTEGER PRIMARY KEY AUTOINCREMENT,family_id TEXT UNIQUE NOT NULL,parcel_id INTEGER REFERENCES parcels(id),project_id TEXT REFERENCES projects(project_id),district TEXT NOT NULL,taluk TEXT NOT NULL,village TEXT NOT NULL,survey_no TEXT,family_head TEXT NOT NULL,members INTEGER DEFAULT 4,impact_type TEXT,displacement_status TEXT DEFAULT 'Displaced',is_vulnerable INTEGER DEFAULT 0,rr_stage TEXT NOT NULL DEFAULT 'Affected Family Identified',exceptional_state TEXT,compensation_status TEXT DEFAULT 'Not Started',housing_status TEXT DEFAULT 'Pending',livelihood_status TEXT DEFAULT 'Not Assessed',verification_status TEXT DEFAULT 'Not Started',grievance_status TEXT DEFAULT 'No Grievance',readiness_percentage REAL DEFAULT 0,readiness_band TEXT DEFAULT 'Critical',risk_level TEXT DEFAULT 'High',compensation_entitled REAL DEFAULT 0,compensation_paid REAL DEFAULT 0,pending_action TEXT,remarks TEXT,identified_date TEXT,last_updated TEXT DEFAULT CURRENT_TIMESTAMP,created_at TEXT DEFAULT CURRENT_TIMESTAMP,edge_case_tag TEXT,verified_by TEXT,verified_at TEXT);
CREATE INDEX IF NOT EXISTS idx_rrf_district ON rr_families(district);
CREATE INDEX IF NOT EXISTS idx_rrf_project ON rr_families(project_id);
CREATE INDEX IF NOT EXISTS idx_rrf_rr_stage ON rr_families(rr_stage);
CREATE INDEX IF NOT EXISTS idx_rrf_readiness ON rr_families(readiness_percentage);
CREATE INDEX IF NOT EXISTS idx_rrf_risk ON rr_families(risk_level);
CREATE TABLE IF NOT EXISTS rr_grievances(id INTEGER PRIMARY KEY AUTOINCREMENT,family_id TEXT NOT NULL REFERENCES rr_families(family_id),project_id TEXT,district TEXT,grievance_type TEXT,description TEXT,status TEXT DEFAULT 'Open',assigned_to TEXT,resolution TEXT,raised_date TEXT,resolved_date TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_rrg_family ON rr_grievances(family_id);
CREATE INDEX IF NOT EXISTS idx_rrg_district ON rr_grievances(district);
CREATE INDEX IF NOT EXISTS idx_rrg_status ON rr_grievances(status);
CREATE TABLE IF NOT EXISTS rr_field_verifications(id INTEGER PRIMARY KEY AUTOINCREMENT,family_id TEXT NOT NULL REFERENCES rr_families(family_id),district TEXT,officer_email TEXT,verification_type TEXT DEFAULT 'Family Verification',status TEXT DEFAULT 'Pending',remarks TEXT,evidence_notes TEXT,assigned_date TEXT,completed_date TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_rrf_verify_family ON rr_field_verifications(family_id);
''')
 if c.execute('SELECT COUNT(*) FROM rr_families').fetchone()[0]==0:
  try:
   import subprocess,sys
   subprocess.run([sys.executable,'scripts/seed_rr.py'],cwd=str(ROOT),timeout=120)
  except Exception: pass
 if c.execute("SELECT COUNT(*) FROM parcels WHERE district='Erode'").fetchone()[0]==0:
  try:
   import subprocess,sys
   subprocess.run([sys.executable,'scripts/seed_districts.py'],cwd=str(ROOT),timeout=120)
  except Exception: pass
 c.commit(); c.close()

init_db()
try: init_rr_tables()
except Exception: pass
