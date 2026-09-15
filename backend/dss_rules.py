"""
Rule Engine & Recommendation Layer for LandNexus DSS.
Converts deterministic scores and facts into actionable recommendations,
structured evidence packages, and explanatory narratives.
"""

def generate_parcel_recommendation(parcel_score_data):
    """
    Given parcel score dict from dss_engine.compute_parcel_score,
    produce recommendation, suggested actions, and evidence package.
    """
    score = parcel_score_data.get('priority_score', 0)
    risk_level = parcel_score_data.get('risk_level', 'LOW')
    comps = parcel_score_data.get('components', {})

    dq = comps.get('data_quality', {})
    gis = comps.get('gis_risk', {})
    sla = comps.get('sla_risk', {})
    ver = comps.get('verification_risk', {})
    doc = comps.get('document_risk', {})
    reverif = comps.get('reverification', {})

    rec_title = ""
    suggested_actions = []
    evidence = []

    # Rule 1: Reverification required or repeated attempts
    if reverif.get('score', 0) > 50 or (ver.get('score', 0) >= 80 and 'rejected' in str(ver.get('reasons', []))):
        rec_title = "Prioritize field re-verification and resolve conflicting records"
        suggested_actions.append("Assign senior field officer for on-site boundary re-verification")
        suggested_actions.append("Cross-reference title documents with Patta/Chitta records")
        evidence.append("Multiple assignment attempts or rejected verification on record")

    # Rule 2: GIS & Boundary incompleteness
    elif gis.get('score', 0) >= 60:
        if any("Boundary" in r for r in gis.get('reasons', [])):
            rec_title = "Re-verify parcel boundary and GPS evidence"
            suggested_actions.append("Capture closed polygon boundary coordinates in field")
            suggested_actions.append("Verify geo-coordinates against master revenue village maps")
            evidence.append("Boundary geometry is missing or unclosed")
        else:
            rec_title = "Capture missing geo-coordinates and field evidence"
            suggested_actions.append("Collect geo-tagged photographic evidence from parcel location")
            evidence.append("Valid GPS coordinates missing from parcel registry")

    # Rule 3: Data Quality issues
    elif dq.get('risk', 0) >= 50:
        missing_str = ", ".join(dq.get('missing_fields', []))
        rec_title = f"Complete mandatory parcel registry fields: {missing_str}"
        suggested_actions.append(f"Update missing registry attributes ({missing_str}) before progressing stage")
        evidence.append(f"Data completeness is {dq.get('score', 0)}% (Threshold: 75%)")

    # Rule 4: SLA or Workflow Delays
    elif sla.get('score', 0) >= 60 or ver.get('score', 0) >= 60:
        rec_title = "Expedite pending field verification to prevent statutory SLA breach"
        suggested_actions.append("Prompt field officer to conclude pending inspection report")
        suggested_actions.append("Escalate to District Collectorate if inspection exceeds timeline")
        evidence.append(f"Statutory verification timeline nearing or exceeding threshold")

    # Rule 5: Low Risk / On Track
    else:
        rec_title = "Proceed with standard workflow milestones"
        suggested_actions.append("Validate inspection checklist and advance to award stage")
        evidence.append("All baseline data quality, GIS, and verification criteria satisfied")

    # Compile structured evidence package
    for r in parcel_score_data.get('reasons', []):
        if r not in evidence:
            evidence.append(r)

    return {
        "recommendation": rec_title,
        "suggested_actions": suggested_actions,
        "evidence": evidence,
        "risk_level": risk_level,
        "priority_score": score,
        "requires_human_review": risk_level in ("HIGH", "CRITICAL"),
        "confidence": parcel_score_data.get('confidence', 'MEDIUM')
    }

def generate_project_recommendation(project_score_data):
    """
    Given project score dict from dss_engine.compute_project_score,
    produce executive recommendation, bottlenecks, and interventions.
    """
    score = project_score_data.get('risk_score', 0)
    risk_level = project_score_data.get('risk_level', 'LOW')
    comps = project_score_data.get('components', {})

    sla = comps.get('sla_risk', {})
    btn = comps.get('bottleneck_risk', {})
    ver = comps.get('verification_risk', {})
    grv = comps.get('grievance_risk', {})

    recommendation = ""
    suggested_actions = []
    evidence = []

    if btn.get('score', 0) >= 60 or sla.get('score', 0) >= 60:
        recommendation = "Intervene on stage bottleneck to recover project schedule"
        suggested_actions.append("Reallocate field resources to accelerate pending milestones")
        suggested_actions.append("Convene inter-departmental review meeting on delayed clearances")
        evidence.append("Critical milestone delay or stage bottleneck detected")
    elif grv.get('score', 0) >= 50:
        recommendation = "Address escalated citizen grievances before issuing final award"
        suggested_actions.append("Direct Land Acquisition Officer to hold public hearing on objections")
        evidence.append("Unresolved citizen objections and compensation disputes pending")
    elif ver.get('score', 0) >= 50:
        recommendation = "Accelerate parcel field verification backlog"
        suggested_actions.append("Deploy additional survey personnel to affected taluks")
        evidence.append("Significant volume of parcels awaiting physical verification")
    else:
        recommendation = "Maintain current acquisition tempo; milestones on schedule"
        suggested_actions.append("Continue regular bi-weekly monitoring")
        evidence.append("Project risks within manageable limits")

    for r in project_score_data.get('reasons', []):
        if r not in evidence:
            evidence.append(r)

    return {
        "recommendation": recommendation,
        "suggested_actions": suggested_actions,
        "evidence": evidence,
        "risk_level": risk_level,
        "risk_score": score,
        "requires_human_review": risk_level in ("HIGH", "CRITICAL")
    }

def explain_dss_assessment(entity_type, entity_id, score_data, rec_data, question=None):
    """
    Deterministic factual explainer (Layer 2) that strictly references
    structured facts and does not hallucinate.
    """
    summary = ""
    if entity_type == 'parcel':
        p_id = score_data.get('record_id') or score_data.get('parcel_id')
        score = score_data.get('priority_score', 0)
        lvl = score_data.get('risk_level', 'LOW')
        rec = rec_data.get('recommendation', '')
        evs = rec_data.get('evidence', [])

        if question:
            q_lower = question.lower()
            if "why" in q_lower or "priority" in q_lower or "risk" in q_lower:
                summary = (
                    f"Parcel {p_id} is evaluated as {lvl} priority (Score: {score}/100). "
                    f"The primary risk contributors are: {'; '.join(evs[:4]) if evs else 'None'}. "
                    f"AI Recommendation: {rec}."
                )
            elif "missing" in q_lower:
                missing = score_data.get('components', {}).get('data_quality', {}).get('missing_fields', [])
                if missing:
                    summary = f"The following mandatory fields are currently missing: {', '.join(missing)}."
                else:
                    summary = "All mandatory core fields are present in the registry record."
            elif "re-verify" in q_lower or "verify" in q_lower:
                ver_reasons = score_data.get('components', {}).get('verification_risk', {}).get('reasons', [])
                summary = (
                    f"Verification status analysis: {'; '.join(ver_reasons) if ver_reasons else 'No verification anomalies detected'}. "
                    f"Action suggested: {rec}."
                )
            else:
                summary = (
                    f"Summary for Parcel {p_id}: Assessed priority {score}/100 ({lvl}). "
                    f"Recommendation: {rec}. Key Evidence: {', '.join(evs[:3])}."
                )
        else:
            summary = (
                f"Parcel {p_id} carries a composite DSS score of {score}/100 ({lvl}). "
                f"Evidence indicates: {'; '.join(evs[:3]) if evs else 'Stable parameters'}. "
                f"Recommended human action: {rec}."
            )
    elif entity_type == 'project':
        p_name = score_data.get('project_name') or entity_id
        score = score_data.get('risk_score', 0)
        lvl = score_data.get('risk_level', 'LOW')
        rec = rec_data.get('recommendation', '')
        evs = rec_data.get('evidence', [])
        summary = (
            f"Project '{p_name}' is currently at {lvl} operational risk ({score}/100). "
            f"Key observations: {'; '.join(evs[:3]) if evs else 'Operating normally'}. "
            f"Recommended executive action: {rec}."
        )
    else:
        summary = f"Decision Support evaluation for {entity_type} {entity_id}: {rec_data.get('recommendation')}."

    return {
        "summary": summary,
        "recommendation": rec_data.get('recommendation'),
        "risk_level": score_data.get('risk_level'),
        "score": score_data.get('priority_score') or score_data.get('risk_score'),
        "evidence": rec_data.get('evidence', []),
        "suggested_actions": rec_data.get('suggested_actions', []),
        "human_review_required": True,
        "disclaimer": "AI recommends based strictly on verified records. Human authority retains final decision authority."
    }
