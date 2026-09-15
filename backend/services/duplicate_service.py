import re
import math
import json
import uuid
from typing import Dict, Any, List, Tuple, Optional
from backend.core import conn, audit

def normalize_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip().lower()
    s = re.sub(r'[\s\-_]+', ' ', s)
    return s.strip()

def normalize_survey_no(survey: Any) -> str:
    """
    Normalizes survey numbers:
    - ' 124 / 2 ' -> '124/2'
    - '0124-02' -> '124/2'
    - Handles spaces, leading zeroes, slash/dash variations.
    """
    if survey is None:
        return ""
    s = str(survey).strip().upper()
    s = re.sub(r'[\-_]+', '/', s)
    s = re.sub(r'\s*/\s*', '/', s)
    parts = s.split('/')
    norm_parts = []
    for p in parts:
        p_clean = p.strip()
        if p_clean.isdigit():
            norm_parts.append(str(int(p_clean)))
        else:
            m = re.match(r'^0*([1-9]\d*|[0-9])(.*)$', p_clean)
            if m:
                norm_parts.append(m.group(1) + m.group(2).strip())
            else:
                norm_parts.append(p_clean)
    return '/'.join(norm_parts)

def normalize_subdivision(sub: Any) -> str:
    if sub is None:
        return ""
    s = str(sub).strip().upper()
    s = re.sub(r'[\s\-_]+', '', s)
    m = re.match(r'^0*([1-9]\d*|[0-9])(.*)$', s)
    if m:
        return m.group(1) + m.group(2)
    return s

def is_distinct_subdivision(srv1: str, srv2: str, sub1: str, sub2: str) -> bool:
    """
    Checks if two records represent distinct partitioned holdings
    (e.g., 3428/1A vs 3428/2A, or subdivision 1 vs 2).
    """
    parts1 = srv1.split('/') if srv1 else []
    parts2 = srv2.split('/') if srv2 else []
    if len(parts1) > 1 and len(parts2) > 1:
        if parts1[0] == parts2[0] and parts1[1:] != parts2[1:]:
            return True
    if sub1 and sub2 and sub1 != sub2:
        return True
    return False

def tokenize_name(name: Any) -> set:
    if not name:
        return set()
    s = str(name).lower()
    for prefix in ['thiru', 'tmt', 'smt', 'mr', 'mrs', 'dr', 'shri', 'late', 'selvi', 'kumar']:
        s = re.sub(r'\b' + prefix + r'\b', '', s)
    s = re.sub(r'[^\w\s]', ' ', s)
    tokens = {t for t in s.split() if len(t) > 1}
    return tokens

def compute_name_similarity(name1: Any, name2: Any) -> float:
    t1 = tokenize_name(name1)
    t2 = tokenize_name(name2)
    if not t1 or not t2:
        n1 = normalize_str(name1)
        n2 = normalize_str(name2)
        if not n1 or not n2:
            return 0.0
        return 1.0 if n1 == n2 else 0.0
    
    intersection = t1.intersection(t2)
    union = t1.union(t2)
    jaccard = len(intersection) / len(union) if union else 0.0
    
    if t1.issubset(t2) or t2.issubset(t1):
        return max(jaccard, 0.9)
    return jaccard

def compute_haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
    try:
        if None in (lat1, lon1, lat2, lon2):
            return None
        r = 6371000
        phi1 = math.radians(float(lat1))
        phi2 = math.radians(float(lat2))
        delta_phi = math.radians(float(lat2) - float(lat1))
        delta_lambda = math.radians(float(lon2) - float(lon1))
        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c
    except Exception:
        return None

def score_duplicate_pair(p1: Dict[str, Any], p2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes explainable duplicate score (0-100) and breakdown reasons.
    Strictly marked as 'Potential Duplicate – Review Required'.
    """
    score = 0.0
    reasons = []

    # 1. Normalized Survey Number (+30)
    srv1 = normalize_survey_no(p1.get("survey_no"))
    srv2 = normalize_survey_no(p2.get("survey_no"))
    sub1 = normalize_subdivision(p1.get("subdivision"))
    sub2 = normalize_subdivision(p2.get("subdivision"))

    srv_match = False
    distinct_subs = is_distinct_subdivision(srv1, srv2, sub1, sub2)

    if srv1 and srv2:
        if srv1 == srv2:
            score += 30.0
            srv_match = True
            reasons.append(f"Normalized Survey Number match ({srv1})")
        else:
            stem1 = srv1.split('/')[0]
            stem2 = srv2.split('/')[0]
            if stem1 == stem2 and stem1:
                # Same stem
                if distinct_subs:
                    reasons.append(f"Distinct subdivisions of survey stem {stem1} ({srv1} vs {srv2}) – partitioned holdings")
                else:
                    score += 15.0
                    reasons.append(f"Matching base survey number stem ({stem1})")

    # 2. Subdivision (+10)
    if sub1 and sub2:
        if sub1 == sub2 and not distinct_subs:
            score += 10.0
            reasons.append(f"Identical subdivision ({sub1})")
    elif not sub1 and not sub2:
        pass

    # 3. Village (+20)
    v1 = normalize_str(p1.get("village"))
    v2 = normalize_str(p2.get("village"))
    if v1 and v2 and v1 == v2:
        score += 20.0
        reasons.append(f"Same Village jurisdiction ({p1.get('village', '').strip()})")

    # 4. Taluk (+15)
    t1 = normalize_str(p1.get("taluk"))
    t2 = normalize_str(p2.get("taluk"))
    if t1 and t2 and t1 == t2:
        score += 15.0
        reasons.append(f"Same Taluk ({p1.get('taluk', '').strip()})")

    # 5. District (+10)
    d1 = normalize_str(p1.get("district"))
    d2 = normalize_str(p2.get("district"))
    if d1 and d2 and d1 == d2:
        score += 10.0
        reasons.append(f"Same District ({p1.get('district', '').strip()})")

    # 6. Owner Name Similarity (+10 max)
    name1 = p1.get("owner_reference") or p1.get("owner_name")
    name2 = p2.get("owner_reference") or p2.get("owner_name")
    if name1 and name2:
        sim = compute_name_similarity(name1, name2)
        if sim >= 0.8:
            score += 10.0
            reasons.append(f"Owner name high similarity ({round(sim * 100)}% match: '{name1}' vs '{name2}')")
        elif sim >= 0.5:
            score += 5.0
            reasons.append(f"Owner name partial token match ({round(sim * 100)}% match)")
    
    # 7. Area Tolerance Match (+5)
    try:
        a1 = float(p1.get("area") or 0.0)
        a2 = float(p2.get("area") or 0.0)
        if a1 > 0 and a2 > 0:
            diff_pct = abs(a1 - a2) / max(a1, a2)
            if diff_pct <= 0.05:
                score += 5.0
                reasons.append(f"Area extent within 5% tolerance ({a1} vs {a2})")
            elif diff_pct <= 0.15:
                score += 2.0
                reasons.append(f"Area extent within 15% tolerance ({a1} vs {a2})")
    except Exception:
        pass

    # 8. Coordinates Proximity (+5 max)
    lat1, lon1 = p1.get("latitude"), p1.get("longitude")
    lat2, lon2 = p2.get("latitude"), p2.get("longitude")
    dist_m = compute_haversine_meters(lat1, lon1, lat2, lon2)
    if dist_m is not None:
        if dist_m <= 50.0:
            score += 5.0
            reasons.append(f"Spatial boundary proximity ({round(dist_m, 1)}m < 50m)")
        elif dist_m <= 200.0:
            score += 2.0
            reasons.append(f"Spatial boundary proximity ({round(dist_m, 1)}m)")

    # False-positive guard 1: Distinct subdivisions
    if distinct_subs:
        score = min(score, 45.0)
        reasons.append("Guarded: Partitioned subdivisions represent distinct legal holdings")

    # False-positive guard 2:
    # If survey numbers are completely different and village is same:
    # A single owner owning multiple parcels in the same village is NOT a duplicate.
    if v1 and v2 and v1 == v2 and srv1 and srv2 and srv1 != srv2 and not srv_match:
        stem1 = srv1.split('/')[0]
        stem2 = srv2.split('/')[0]
        if stem1 != stem2:
            score = min(score, 40.0)
            reasons.append("Guarded: Different survey numbers with same owner indicates distinct legal holdings")

    score = min(round(score, 1), 100.0)
    confidence_band = "HIGH" if score >= 80.0 else "MEDIUM" if score >= 60.0 else "LOW"

    return {
        "similarity_score": score,
        "confidence_band": confidence_band,
        "assessment": "Potential Duplicate – Review Required",
        "reasons": reasons,
        "is_potential_duplicate": score >= 60.0
    }

def mask_private_name(name: Optional[str]) -> str:
    if not name:
        return "N/A"
    s = str(name).strip()
    words = s.split()
    masked_words = []
    for w in words:
        if len(w) <= 2:
            masked_words.append(w)
        elif len(w) <= 4:
            masked_words.append(w[0] + "*" * (len(w) - 1))
        else:
            masked_words.append(w[:2] + "*" * (len(w) - 3) + w[-1])
    return " ".join(masked_words)

def compare_records(record_a: Dict[str, Any], record_b: Dict[str, Any], mask_privacy: bool = True) -> Dict[str, Any]:
    fields = []
    matches = 0
    mismatches = 0
    missing = 0
    uncertain = 0

    def add_field(key: str, label: str, val_a: Any, val_b: Any, status: str, note: str = ""):
        nonlocal matches, mismatches, missing, uncertain
        if status == "MATCH":
            matches += 1
        elif status == "MISMATCH":
            mismatches += 1
        elif status == "MISSING":
            missing += 1
        else:
            uncertain += 1
        fields.append({
            "key": key,
            "label": label,
            "record_a": str(val_a) if val_a is not None else "",
            "record_b": str(val_b) if val_b is not None else "",
            "status": status,
            "note": note
        })

    # 1. Survey Number
    srv_a = normalize_survey_no(record_a.get("survey_no"))
    srv_b = normalize_survey_no(record_b.get("survey_no"))
    if not srv_a or not srv_b:
        add_field("survey_no", "Survey Number", record_a.get("survey_no"), record_b.get("survey_no"), "MISSING", "Survey number missing on one or both records")
    elif srv_a == srv_b:
        add_field("survey_no", "Survey Number", record_a.get("survey_no"), record_b.get("survey_no"), "MATCH", f"Normalized exact match ({srv_a})")
    elif srv_a.split('/')[0] == srv_b.split('/')[0]:
        add_field("survey_no", "Survey Number", record_a.get("survey_no"), record_b.get("survey_no"), "UNCERTAIN", "Matching base survey stem")
    else:
        add_field("survey_no", "Survey Number", record_a.get("survey_no"), record_b.get("survey_no"), "MISMATCH", "Different survey numbers")

    # 2. Subdivision
    sub_a = normalize_subdivision(record_a.get("subdivision"))
    sub_b = normalize_subdivision(record_b.get("subdivision"))
    if not sub_a and not sub_b:
        add_field("subdivision", "Subdivision", "—", "—", "MATCH", "Neither record specifies subdivision")
    elif not sub_a or not sub_b:
        add_field("subdivision", "Subdivision", record_a.get("subdivision") or "—", record_b.get("subdivision") or "—", "MISSING", "Subdivision specified on one record only")
    elif sub_a == sub_b:
        add_field("subdivision", "Subdivision", record_a.get("subdivision"), record_b.get("subdivision"), "MATCH", "Identical subdivision")
    else:
        add_field("subdivision", "Subdivision", record_a.get("subdivision"), record_b.get("subdivision"), "MISMATCH", "Distinct subdivisions")

    # 3. Village
    v_a = normalize_str(record_a.get("village"))
    v_b = normalize_str(record_b.get("village"))
    if not v_a or not v_b:
        add_field("village", "Village", record_a.get("village"), record_b.get("village"), "MISSING")
    elif v_a == v_b:
        add_field("village", "Village", record_a.get("village"), record_b.get("village"), "MATCH")
    else:
        add_field("village", "Village", record_a.get("village"), record_b.get("village"), "MISMATCH")

    # 4. Taluk
    t_a = normalize_str(record_a.get("taluk"))
    t_b = normalize_str(record_b.get("taluk"))
    if not t_a or not t_b:
        add_field("taluk", "Taluk", record_a.get("taluk"), record_b.get("taluk"), "MISSING")
    elif t_a == t_b:
        add_field("taluk", "Taluk", record_a.get("taluk"), record_b.get("taluk"), "MATCH")
    else:
        add_field("taluk", "Taluk", record_a.get("taluk"), record_b.get("taluk"), "MISMATCH")

    # 5. District
    d_a = normalize_str(record_a.get("district"))
    d_b = normalize_str(record_b.get("district"))
    if not d_a or not d_b:
        add_field("district", "District", record_a.get("district"), record_b.get("district"), "MISSING")
    elif d_a == d_b:
        add_field("district", "District", record_a.get("district"), record_b.get("district"), "MATCH")
    else:
        add_field("district", "District", record_a.get("district"), record_b.get("district"), "MISMATCH")

    # 6. Owner Reference
    name_a = record_a.get("owner_reference") or record_a.get("owner_name")
    name_b = record_b.get("owner_reference") or record_b.get("owner_name")
    disp_a = mask_private_name(name_a) if mask_privacy else (name_a or "—")
    disp_b = mask_private_name(name_b) if mask_privacy else (name_b or "—")
    if not name_a or not name_b:
        add_field("owner_reference", "Owner Name", disp_a, disp_b, "MISSING", "Owner name missing on one or both records")
    else:
        sim = compute_name_similarity(name_a, name_b)
        if sim >= 0.8:
            add_field("owner_reference", "Owner Name", disp_a, disp_b, "MATCH", f"High name similarity ({round(sim * 100)}%)")
        elif sim >= 0.4:
            add_field("owner_reference", "Owner Name", disp_a, disp_b, "UNCERTAIN", f"Partial token match ({round(sim * 100)}%)")
        else:
            add_field("owner_reference", "Owner Name", disp_a, disp_b, "MISMATCH", "Different owner names")

    # 7. Area
    try:
        area_a = float(record_a.get("area") or 0.0)
        area_b = float(record_b.get("area") or 0.0)
        if area_a <= 0 or area_b <= 0:
            add_field("area", "Area (Extent)", record_a.get("area"), record_b.get("area"), "MISSING")
        else:
            diff = abs(area_a - area_b) / max(area_a, area_b)
            if diff <= 0.05:
                add_field("area", "Area (Extent)", f"{area_a} {record_a.get('area_unit', 'acres')}", f"{area_b} {record_b.get('area_unit', 'acres')}", "MATCH", f"Variance within 5% ({round(diff*100, 1)}%)")
            elif diff <= 0.15:
                add_field("area", "Area (Extent)", f"{area_a}", f"{area_b}", "UNCERTAIN", f"Variance within 15% ({round(diff*100, 1)}%)")
            else:
                add_field("area", "Area (Extent)", f"{area_a}", f"{area_b}", "MISMATCH", f"Variance {round(diff*100, 1)}%")
    except Exception:
        add_field("area", "Area (Extent)", record_a.get("area"), record_b.get("area"), "MISSING")

    # 8. Land Classification
    c_a = normalize_str(record_a.get("classification"))
    c_b = normalize_str(record_b.get("classification"))
    if not c_a or not c_b:
        add_field("classification", "Classification", record_a.get("classification") or "—", record_b.get("classification") or "—", "MISSING")
    elif c_a == c_b:
        add_field("classification", "Classification", record_a.get("classification"), record_b.get("classification"), "MATCH")
    else:
        add_field("classification", "Classification", record_a.get("classification"), record_b.get("classification"), "MISMATCH")

    # 9. Project Linkage
    p_a = record_a.get("project_id")
    p_b = record_b.get("project_id")
    if p_a and p_b and p_a == p_b:
        add_field("project_id", "Project Linkage", p_a, p_b, "MATCH", "Same project assignment")
    elif not p_a and not p_b:
        add_field("project_id", "Project Linkage", "—", "—", "MATCH", "Neither assigned to project")
    else:
        add_field("project_id", "Project Linkage", p_a or "—", p_b or "—", "MISMATCH", "Assigned to different projects")

    # 10. Coordinates
    dist = compute_haversine_meters(record_a.get("latitude"), record_a.get("longitude"), record_b.get("latitude"), record_b.get("longitude"))
    if dist is None:
        add_field("coordinates", "GPS Coordinates", "Coordinates missing", "Coordinates missing", "MISSING")
    elif dist <= 50.0:
        add_field("coordinates", "GPS Coordinates", f"{record_a.get('latitude')}, {record_a.get('longitude')}", f"{record_b.get('latitude')}, {record_b.get('longitude')}", "MATCH", f"Separation: {round(dist, 1)}m (<50m)")
    elif dist <= 200.0:
        add_field("coordinates", "GPS Coordinates", f"{record_a.get('latitude')}, {record_a.get('longitude')}", f"{record_b.get('latitude')}, {record_b.get('longitude')}", "UNCERTAIN", f"Separation: {round(dist, 1)}m")
    else:
        add_field("coordinates", "GPS Coordinates", f"{record_a.get('latitude')}, {record_a.get('longitude')}", f"{record_b.get('latitude')}, {record_b.get('longitude')}", "MISMATCH", f"Separation: {round(dist, 1)}m")

    scored = score_duplicate_pair(record_a, record_b)

    return {
        "record_a_id": record_a.get("id"),
        "record_b_id": record_b.get("id"),
        "record_a_key": record_a.get("record_id") or f"P-{record_a.get('id')}",
        "record_b_key": record_b.get("record_id") or f"P-{record_b.get('id')}",
        "similarity_score": scored["similarity_score"],
        "confidence_band": scored["confidence_band"],
        "assessment": scored["assessment"],
        "reasons": scored["reasons"],
        "fields": fields,
        "summary": {
            "total_fields": len(fields),
            "match_count": matches,
            "mismatch_count": mismatches,
            "missing_count": missing,
            "uncertain_count": uncertain
        }
    }

def scan_parcels_for_duplicates(district: Optional[str] = None, project_id: Optional[str] = None, threshold: float = 60.0) -> List[Dict[str, Any]]:
    c = conn()
    query = "SELECT * FROM parcels WHERE 1=1"
    params = []
    if district and district.lower() != "all":
        query += " AND lower(district)=lower(?)"
        params.append(district.strip())
    if project_id:
        query += " AND project_id=?"
        params.append(project_id.strip())
    
    rows = c.execute(query, params).fetchall()
    parcels = [dict(r) for r in rows]

    # Efficient Blocking Index: partition by (district_norm, village_norm, survey_stem)
    blocks: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for p in parcels:
        d_norm = normalize_str(p.get("district"))
        v_norm = normalize_str(p.get("village"))
        srv_norm = normalize_survey_no(p.get("survey_no"))
        stem = srv_norm.split('/')[0] if srv_norm else ""
        if not stem:
            continue
        blk_key = (d_norm, v_norm, stem)
        blocks.setdefault(blk_key, []).append(p)

    candidate_cases = []

    for blk_key, block_parcels in blocks.items():
        n = len(block_parcels)
        if n < 2:
            continue
        for i in range(n):
            for j in range(i + 1, n):
                p1 = block_parcels[i]
                p2 = block_parcels[j]
                
                rec_a, rec_b = (p1, p2) if p1["id"] < p2["id"] else (p2, p1)
                
                scored = score_duplicate_pair(rec_a, rec_b)
                if scored["similarity_score"] >= threshold:
                    existing = c.execute(
                        "SELECT * FROM duplicate_cases WHERE record_a_id=? AND record_b_id=?",
                        (rec_a["id"], rec_b["id"])
                    ).fetchone()

                    if existing:
                        case_dict = dict(existing)
                        case_dict["primary_reasons"] = json.loads(case_dict["primary_reasons"]) if isinstance(case_dict["primary_reasons"], str) else case_dict["primary_reasons"]
                        candidate_cases.append(case_dict)
                    else:
                        case_id = f"DUP-CASE-{uuid.uuid4().hex[:8].upper()}"
                        reasons_json = json.dumps(scored["reasons"])
                        c.execute("""
                            INSERT INTO duplicate_cases(
                                case_id, record_a_id, record_b_id, similarity_score,
                                confidence_band, primary_reasons, status, district
                            ) VALUES(?, ?, ?, ?, ?, ?, 'NEW', ?)
                        """, (
                            case_id, rec_a["id"], rec_b["id"], scored["similarity_score"],
                            scored["confidence_band"], reasons_json, rec_a.get("district") or blk_key[0].capitalize()
                        ))
                        c.execute("UPDATE parcels SET duplicate_flag=1 WHERE id IN (?, ?)", (rec_a["id"], rec_b["id"]))
                        candidate_cases.append({
                            "case_id": case_id,
                            "record_a_id": rec_a["id"],
                            "record_b_id": rec_b["id"],
                            "similarity_score": scored["similarity_score"],
                            "confidence_band": scored["confidence_band"],
                            "primary_reasons": scored["reasons"],
                            "status": "NEW",
                            "district": rec_a.get("district") or blk_key[0].capitalize(),
                            "assessment": scored["assessment"]
                        })

    c.commit()
    c.close()
    return candidate_cases
