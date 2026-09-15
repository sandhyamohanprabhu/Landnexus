
from fastapi import APIRouter, Header, HTTPException
from backend.core import current_user, conn
from backend.routes.dashboard import STATE_DISTRICTS
import json
from pathlib import Path

router = APIRouter()
GEO = Path(__file__).resolve().parents[2] / "data/coimbatore/19_gis_parcels.geojson"

@router.get("/parcels")
def gis_parcels(
    authorization: str = Header(None),
    survey_no: str = "",
    village: str = "",
    taluk: str = "",
    district: str = "",
    state: str = "",
    risk_category: str = "",
    limit: int = 5000
):
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Authentication required")

    user_district = u.get("district_scope")
    user_state = u.get("state_scope")

    # 1. District scope check (District Authority & Field Officer)
    if user_district:
        if district and district.strip() and district.strip().lower() not in ("all", "all districts", user_district.strip().lower()):
            raise HTTPException(403, f"Cross-district access forbidden: account is permanently scoped to {user_district}, cannot access {district}")
        district = user_district
        effective_state = user_state
    elif user_state:
        # 2. State Authority scope check
        if state and state.strip() and state.strip().lower() != user_state.strip().lower():
            raise HTTPException(403, f"Cross-state access forbidden: account is scoped to {user_state}, cannot access {state}")
        valid_state_districts = [d.lower() for d in STATE_DISTRICTS.get(user_state, [])]
        if district and district.strip() and district.strip().lower() not in ("all", "all districts"):
            if valid_state_districts and district.strip().lower() not in valid_state_districts:
                raise HTTPException(403, f"Cross-state access forbidden: account is scoped to {user_state}, cannot access district {district}")
        effective_state = user_state
    else:
        # 3. National Authority / Admin scope check
        if state and state.strip() and state.strip().lower() not in ("all", "all states"):
            effective_state = state.strip()
        else:
            effective_state = None

    c = conn()

    # Determine scope for available districts & truthful statistics
    if effective_state:
        scope_dists = STATE_DISTRICTS.get(effective_state, [])
        ph = ",".join(["?"] * len(scope_dists))
        scope_where = f"WHERE lower(district) IN ({ph})"
        scope_args = [d.lower() for d in scope_dists]
    else:
        scope_where = ""
        scope_args = []

    # Query truthful counts from actual database
    dist_counts_rows = c.execute(f"""
        SELECT district,
               count(*) as total_parcels,
               count(latitude) as gis_linked,
               count(*) - count(latitude) as gis_unlinked
        FROM parcels {scope_where}
        GROUP BY district
        ORDER BY district
    """, scope_args).fetchall()

    district_breakdown = {}
    actual_districts = []
    total_eligible_parcels = 0
    total_gis_linked = 0
    total_gis_unlinked = 0

    for dr in dist_counts_rows:
        d_name = dr["district"]
        actual_districts.append(d_name)
        tot = dr["total_parcels"]
        linked = dr["gis_linked"]
        unlinked = dr["gis_unlinked"]
        district_breakdown[d_name] = {
            "district": d_name,
            "total_parcels": tot,
            "gis_linked": linked,
            "gis_unlinked": unlinked
        }
        total_eligible_parcels += tot
        total_gis_linked += linked
        total_gis_unlinked += unlinked

    # Build parcel query
    where = "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
    args = []

    is_all = not district or district.strip().lower() in ("all", "all districts")
    if not is_all:
        where += " AND lower(district) = ?"
        args.append(district.strip().lower())
    elif effective_state:
        ph = ",".join(["?"] * len(scope_dists))
        where += f" AND lower(district) IN ({ph})"
        args.extend([d.lower() for d in scope_dists])

    if taluk and taluk.strip() and taluk.lower() != "all":
        where += " AND lower(taluk) = ?"
        args.append(taluk.strip().lower())

    if survey_no:
        where += " AND survey_no LIKE ?"
        args.append(f"%{survey_no}%")

    if village:
        where += " AND village LIKE ?"
        args.append(f"%{village}%")

    if risk_category and risk_category.strip() and risk_category.upper() != "ALL":
        where += " AND risk_category = ?"
        args.append(risk_category.upper())

    query_limit = min(max(limit, 1), 10000)
    order_clause = "ORDER BY district ASC, id DESC" if is_all else "ORDER BY id DESC"

    rows = c.execute(f"""
        SELECT id, record_id, survey_no, subdivision, village, taluk, district,
               latitude, longitude, risk_category, risk_score, area, project_id, acquisition_status
        FROM parcels {where}
        {order_clause} LIMIT ?
    """, args + [query_limit]).fetchall()

    # Get available taluks for current selection
    taluk_where = "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
    taluk_args = []
    if not is_all:
        taluk_where += " AND lower(district) = ?"
        taluk_args.append(district.strip().lower())
    elif effective_state:
        ph = ",".join(["?"] * len(scope_dists))
        taluk_where += f" AND lower(district) IN ({ph})"
        taluk_args.extend([d.lower() for d in scope_dists])

    taluk_rows = c.execute(f"SELECT DISTINCT taluk FROM parcels {taluk_where} AND taluk IS NOT NULL ORDER BY taluk", taluk_args).fetchall()
    available_taluks = [r[0] for r in taluk_rows if r[0]]

    c.close()

    features = []
    for r in rows:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [r["longitude"], r["latitude"]]
            },
            "properties": {
                "id": r["id"],
                "record_id": r["record_id"],
                "survey_no": r["survey_no"],
                "subdivision": r["subdivision"],
                "village": r["village"],
                "taluk": r["taluk"],
                "district": r["district"],
                "risk_category": r["risk_category"],
                "risk_score": r["risk_score"],
                "area": r["area"],
                "project_id": r["project_id"],
                "acquisition_status": r["acquisition_status"]
            }
        })

    # Available districts list for frontend filter (actual districts from dataset)
    if user_district:
        available_districts_list = [user_district]
    else:
        available_districts_list = ["All Districts"] + actual_districts

    return {
        "type": "FeatureCollection",
        "features": features,
        "count": len(features),
        "state": effective_state or "All States",
        "district": district if not is_all else "All Districts",
        "available_districts": available_districts_list,
        "available_taluks": available_taluks,
        "district_breakdown": district_breakdown,
        "stats": {
            "total_eligible_parcels": total_eligible_parcels,
            "total_gis_linked": total_gis_linked,
            "total_gis_unlinked": total_gis_unlinked,
            "visible_parcels": len(features)
        },
        "source_classification": "SYNTHETIC DEMO POINTS",
        "cadastral_geometry": False,
        "disclaimer": "Demonstration GIS geometry — not an authoritative cadastral boundary. Authoritative revenue cadastral boundary maps require certified integration with Tamil Nadu TNGIS / DILRMP."
    }
@router.get("/config")
def gis_config(authorization:str=Header(None)):
 if not current_user(authorization): raise HTTPException(401,"Authentication required")
 return {"base_map":"OpenStreetMap","source_classification":"SYNTHETIC DEMO","authorized_cadastral_adapter":True,"tngis_portal":"https://tngis.tn.gov.in/apps.html"}
