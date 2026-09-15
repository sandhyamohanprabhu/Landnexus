import React, { useState, useEffect } from "react";
import { api } from "./api";

export default function DataQualityPage({ district, user, onSelectParcel }) {
  // 6 Sub-sections: "overview" | "duplicates" | "validation" | "cross_db" | "queue" | "audit"
  const [activeTab, setActiveTab] = useState("overview");
  
  // Data states
  const [analytics, setAnalytics] = useState(null);
  const [cases, setCases] = useState([]);
  const [queue, setQueue] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  // Filters
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [minScore, setMinScore] = useState(60);
  const [queuePriority, setQueuePriority] = useState("ALL");

  // Scanning state
  const [scanning, setScanning] = useState(false);
  const [scanNotice, setScanNotice] = useState("");

  // Side-by-side comparison modal state
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [caseDetail, setCaseDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  
  // Decision form state
  const [decisionReason, setDecisionReason] = useState("");
  const [masterRecordId, setMasterRecordId] = useState(null);
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [decisionFeedback, setDecisionFeedback] = useState("");

  // Cross-DB Verification state
  const [verifyParcelId, setVerifyParcelId] = useState("");
  const [verifyingExternal, setVerifyingExternal] = useState(false);
  const [externalResults, setExternalResults] = useState(null);

  const fetchOverview = async () => {
    try {
      const data = await api(`/data-quality/analytics?district=${district || "Coimbatore"}`);
      setAnalytics(data);
    } catch (e) {
      console.error("Failed to load data quality analytics:", e);
    }
  };

  const fetchCases = async () => {
    setLoading(true);
    try {
      let q = `/data-quality/duplicate-cases?district=${district || "Coimbatore"}&min_score=${minScore}`;
      if (statusFilter !== "ALL") q += `&status=${statusFilter}`;
      const res = await api(q);
      setCases(res.cases || []);
    } catch (e) {
      console.error("Failed to load duplicate cases:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchQueue = async () => {
    try {
      const res = await api(`/data-quality/verification-queue?district=${district || "Coimbatore"}&priority=${queuePriority}`);
      setQueue(res.queue || []);
    } catch (e) {
      console.error("Failed to load verification queue:", e);
    }
  };

  const fetchValidation = async () => {
    try {
      const res = await api(`/data-quality/cross-record-validation?district=${district || "Coimbatore"}`);
      setAnomalies(res.anomalies || []);
    } catch (e) {
      console.error("Failed to load cross-record anomalies:", e);
    }
  };

  const fetchAuditHistory = async () => {
    try {
      const res = await api(`/data-quality/audit-history?district=${district || "Coimbatore"}`);
      setAuditLogs(res.audit_logs || []);
    } catch (e) {
      console.error("Failed to load audit history:", e);
    }
  };

  useEffect(() => {
    fetchOverview();
    if (activeTab === "duplicates") fetchCases();
    else if (activeTab === "queue") fetchQueue();
    else if (activeTab === "validation") fetchValidation();
    else if (activeTab === "audit") fetchAuditHistory();
  }, [district, activeTab, statusFilter, minScore, queuePriority]);

  const handleTriggerScan = async () => {
    setScanning(true);
    setScanNotice("");
    try {
      const res = await api("/data-quality/scan", {
        method: "POST",
        body: JSON.stringify({ district, threshold: minScore })
      });
      setScanNotice(`Scan completed: ${res.potential_duplicates_found} potential duplicate candidate(s) detected.`);
      fetchOverview();
      fetchCases();
    } catch (e) {
      setScanNotice(`Scan failed: ${e.message}`);
    } finally {
      setScanning(false);
    }
  };

  const handleOpenComparison = async (caseId) => {
    setSelectedCaseId(caseId);
    setLoadingDetail(true);
    setCaseDetail(null);
    setDecisionFeedback("");
    setDecisionReason("");
    try {
      const data = await api(`/data-quality/duplicate-cases/${caseId}`);
      setCaseDetail(data);
      setMasterRecordId(data.record_a?.id);
    } catch (e) {
      alert("Failed to load case detail: " + e.message);
      setSelectedCaseId(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleSubmitDecision = async (decisionType) => {
    if (!decisionReason.trim()) {
      alert("Decision reason is mandatory for statutory compliance and audit trail.");
      return;
    }
    setSubmittingDecision(true);
    setDecisionFeedback("");
    try {
      const res = await api(`/data-quality/duplicate-cases/${selectedCaseId}/decision`, {
        method: "POST",
        body: JSON.stringify({
          decision: decisionType,
          reason: decisionReason.trim(),
          master_record_id: masterRecordId
        })
      });
      setDecisionFeedback(`Decision recorded successfully: ${decisionType}`);
      fetchOverview();
      fetchCases();
      if (activeTab === "queue") fetchQueue();
      setTimeout(() => {
        setSelectedCaseId(null);
        setCaseDetail(null);
      }, 1500);
    } catch (e) {
      setDecisionFeedback(`Error: ${e.message}`);
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleRunCrossDb = async (e) => {
    e?.preventDefault();
    if (!verifyParcelId) {
      alert("Please enter a numeric Parcel ID");
      return;
    }
    setVerifyingExternal(true);
    setExternalResults(null);
    try {
      const res = await api(`/data-quality/verify-external/${verifyParcelId}`, {
        method: "POST",
        body: JSON.stringify({ include_demo: true })
      });
      setExternalResults(res);
      fetchOverview();
    } catch (e) {
      alert("Verification error: " + e.message);
    } finally {
      setVerifyingExternal(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* ── Top Header & Statutory Notice ── */}
      <div style={{ background: "#ffffff", padding: "20px", borderRadius: "10px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "14px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
              <span style={{ fontSize: "12px", background: "#f0fdf4", color: "#166534", border: "1px solid #bbf7d0", padding: "3px 8px", borderRadius: "4px", fontWeight: 700 }}>
                ⚖️ SIH 26016 DATA INTEGRITY MODULE
              </span>
              <span style={{ fontSize: "12px", color: "#64748b" }}>
                Jurisdiction: <b>{district || "Coimbatore"} District</b>
              </span>
            </div>
            <h2 style={{ margin: "0 0 6px 0", color: "#0f172a", fontSize: "22px", fontWeight: 800 }}>
              Data Quality, Duplicate Detection & Cross-Database Verification
            </h2>
            <div style={{ fontSize: "13px", color: "#475569", maxWidth: "850px" }}>
              Comprehensive multi-level matching, side-by-side legal comparison, cross-record consistency checking, and multi-registry verification for authoritative land acquisition governance.
            </div>
          </div>

          <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={handleTriggerScan}
              disabled={scanning}
              style={{
                background: scanning ? "#94a3b8" : "#0f6c70",
                color: "#ffffff",
                border: "none",
                padding: "9px 18px",
                borderRadius: "6px",
                fontWeight: 700,
                fontSize: "13px",
                cursor: scanning ? "not-allowed" : "pointer",
                boxShadow: "0 2px 6px rgba(15,108,112,0.25)",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px"
              }}
            >
              {scanning ? "Scanning District Parcels..." : "🔍 Run Potential Duplicate Scan"}
            </button>
          </div>
        </div>

        {scanNotice && (
          <div style={{ marginTop: "12px", padding: "8px 12px", background: "#f0fdfa", color: "#0f766e", border: "1px solid #ccfbf1", borderRadius: "6px", fontSize: "13px", fontWeight: 600 }}>
            ℹ️ {scanNotice}
          </div>
        )}

        <div style={{ marginTop: "14px", padding: "10px 14px", background: "#fef3c7", borderLeft: "4px solid #f59e0b", borderRadius: "4px", fontSize: "12px", color: "#78350f" }}>
          <b>CRITICAL STATUTORY ACCURACY RULE:</b> Candidate duplicate scores represent <i>"Potential Duplicate – Review Required"</i> based on additive signals (Survey Stem, Subdivision, Village, Owner, Area). The system <b>never deletes or auto-merges</b> records automatically without formal officer review and recorded justification.
        </div>
      </div>

      {/* ── KPI Summary Cards ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "14px" }}>
        <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>TOTAL DISTRICT PARCELS</div>
          <div style={{ fontSize: "24px", fontWeight: 800, color: "#0f172a", marginTop: "4px" }}>
            {analytics?.parcels?.total?.toLocaleString("en-IN") || "—"}
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>Active cadastral ledger</div>
        </div>

        <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "11px", color: "#b45309", fontWeight: 700, textTransform: "uppercase" }}>POTENTIAL DUPLICATE CASES</div>
          <div style={{ fontSize: "24px", fontWeight: 800, color: "#b45309", marginTop: "4px" }}>
            {analytics?.duplicate_detection?.total_cases || 0}
          </div>
          <div style={{ fontSize: "11px", color: "#b45309", marginTop: "2px" }}>
            {analytics?.duplicate_detection?.new_review_required || 0} Pending Officer Review
          </div>
        </div>

        <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "11px", color: "#166534", fontWeight: 700, textTransform: "uppercase" }}>CONFIRMED DUPLICATES</div>
          <div style={{ fontSize: "24px", fontWeight: 800, color: "#166534", marginTop: "4px" }}>
            {analytics?.duplicate_detection?.confirmed_duplicates || 0}
          </div>
          <div style={{ fontSize: "11px", color: "#166534", marginTop: "2px" }}>
            Resolution Rate: {analytics?.duplicate_detection?.resolution_rate_pct || 0}%
          </div>
        </div>

        <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "11px", color: "#0369a1", fontWeight: 700, textTransform: "uppercase" }}>CROSS-DATABASE QUERIES</div>
          <div style={{ fontSize: "24px", fontWeight: 800, color: "#0369a1", marginTop: "4px" }}>
            {analytics?.cross_db_verification?.total_verifications || 0}
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
            {analytics?.cross_db_verification?.matches || 0} verified matches logged
          </div>
        </div>
      </div>

      {/* ── 6 SUB-SECTIONS NAVIGATION BAR ── */}
      <div style={{ display: "flex", gap: "6px", borderBottom: "2px solid #e2e8f0", paddingBottom: "2px", flexWrap: "wrap" }}>
        {[
          ["overview", "📊 Overview"],
          ["duplicates", `🔍 Duplicate Detection (${cases.length || analytics?.duplicate_detection?.total_cases || 0})`],
          ["validation", "⚖️ Cross-Record Validation"],
          ["cross_db", "🌐 Cross-Database Verification"],
          ["queue", "⏳ Verification Queue"],
          ["audit", "📜 Audit History"]
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            style={{
              background: activeTab === key ? "#0f6c70" : "#f8fafc",
              color: activeTab === key ? "#ffffff" : "#475569",
              border: `1px solid ${activeTab === key ? "#0f6c70" : "#cbd5e1"}`,
              borderBottom: "none",
              padding: "8px 14px",
              borderRadius: "6px 6px 0 0",
              fontWeight: 700,
              fontSize: "12px",
              cursor: "pointer",
              transition: "all 0.15s ease"
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── 1. OVERVIEW TAB ── */}
      {activeTab === "overview" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div style={{ background: "#ffffff", padding: "20px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <h3 style={{ margin: "0 0 14px 0", fontSize: "16px", fontWeight: 800, color: "#0f172a" }}>
              District Data Quality Health & Resolution Status
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
              <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "13px", fontWeight: 700, color: "#0f6c70", marginBottom: "8px" }}>
                  Duplicate Case Status Breakdown
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>🟡 New (Review Required):</span>
                    <b>{analytics?.duplicate_detection?.new_review_required || 0}</b>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>🔴 Confirmed Duplicates:</span>
                    <b>{analytics?.duplicate_detection?.confirmed_duplicates || 0}</b>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>🟢 Marked Not Duplicate:</span>
                    <b>{analytics?.duplicate_detection?.marked_not_duplicate || 0}</b>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>🔵 Field Verification Pending:</span>
                    <b>{analytics?.duplicate_detection?.field_verification_requested || 0}</b>
                  </div>
                </div>
              </div>

              <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "13px", fontWeight: 700, color: "#0f6c70", marginBottom: "8px" }}>
                  Cross-Database Integration Health
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Total Provider Calls:</span>
                    <b>{analytics?.cross_db_verification?.total_verifications || 0}</b>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Authoritative Matches:</span>
                    <b style={{ color: "#166534" }}>{analytics?.cross_db_verification?.matches || 0}</b>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Unconnected Gateways:</span>
                    <b style={{ color: "#64748b" }}>{analytics?.cross_db_verification?.not_connected_count || 0}</b>
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                    {analytics?.cross_db_verification?.notice}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 2. DUPLICATE DETECTION TAB ── */}
      {activeTab === "duplicates" && (
        <div style={{ background: "#ffffff", padding: "20px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
            <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 800, color: "#0f172a" }}>
              Potential Duplicate Candidates (Review Required)
            </h3>

            <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
                <span>Status:</span>
                <select
                  value={statusFilter}
                  onChange={e => setStatusFilter(e.target.value)}
                  style={{ padding: "4px 8px", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                >
                  <option value="ALL">All Statuses</option>
                  <option value="NEW">New (Unreviewed)</option>
                  <option value="CONFIRMED_DUPLICATE">Confirmed Duplicate</option>
                  <option value="NOT_DUPLICATE">Marked Not Duplicate</option>
                  <option value="FIELD_VERIFICATION_REQUESTED">Field Verification</option>
                  <option value="INSUFFICIENT_INFORMATION">More Info Required</option>
                </select>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
                <span>Min Score:</span>
                <select
                  value={minScore}
                  onChange={e => setMinScore(Number(e.target.value))}
                  style={{ padding: "4px 8px", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                >
                  <option value={60}>60+ (Potential)</option>
                  <option value={75}>75+ (High Similarity)</option>
                  <option value={90}>90+ (Critical Match)</option>
                </select>
              </div>
            </div>
          </div>

          {loading ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#64748b" }}>Loading duplicate candidate queue...</div>
          ) : cases.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", background: "#f8fafc", borderRadius: "8px", border: "1px dashed #cbd5e1" }}>
              <div style={{ fontSize: "16px", fontWeight: 700, color: "#166534" }}>✓ No unresolved duplicates matching filter</div>
              <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
                Run "Run Potential Duplicate Scan" above to analyze district records.
              </div>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Case ID</th>
                    <th>Record A (Primary)</th>
                    <th>Record B (Candidate)</th>
                    <th>Similarity Score</th>
                    <th>Match Signals</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c, i) => {
                    const score = c.similarity_score;
                    const scoreBg = score >= 80 ? "#fee2e2" : score >= 60 ? "#fef3c7" : "#e0f2fe";
                    const scoreText = score >= 80 ? "#991b1b" : score >= 60 ? "#92400e" : "#0369a1";
                    
                    return (
                      <tr key={c.case_id || i}>
                        <td>
                          <span style={{ fontFamily: "monospace", fontSize: "11px", fontWeight: 700, color: "#0f6c70" }}>
                            {c.case_id}
                          </span>
                        </td>
                        <td>
                          <div><b>Survey: {c.rec_a_survey || "N/A"}</b></div>
                          <div style={{ fontSize: "11px", color: "#64748b" }}>
                            {c.rec_a_village || "Village"} · {c.rec_a_area} Acres
                          </div>
                          <div style={{ fontSize: "11px", color: "#0f172a" }}>
                            👤 {c.rec_a_owner_masked || "Owner Protected"}
                          </div>
                        </td>
                        <td>
                          <div><b>Survey: {c.rec_b_survey || "N/A"}</b></div>
                          <div style={{ fontSize: "11px", color: "#64748b" }}>
                            {c.rec_b_village || "Village"} · {c.rec_b_area} Acres
                          </div>
                          <div style={{ fontSize: "11px", color: "#0f172a" }}>
                            👤 {c.rec_b_owner_masked || "Owner Protected"}
                          </div>
                        </td>
                        <td>
                          <span style={{
                            background: scoreBg,
                            color: scoreText,
                            padding: "3px 8px",
                            borderRadius: "12px",
                            fontSize: "11px",
                            fontWeight: 800,
                            display: "inline-block"
                          }}>
                            {score}/100 ({c.confidence_band || "REVIEW"})
                          </span>
                          <div style={{ fontSize: "10px", color: "#64748b", marginTop: "2px" }}>
                            Review Required
                          </div>
                        </td>
                        <td>
                          <div style={{ fontSize: "11px", color: "#334155", maxWidth: "240px", lineHeight: "1.4" }}>
                            {Array.isArray(c.primary_reasons) ? c.primary_reasons.slice(0, 2).map((r, idx) => (
                              <div key={idx}>• {r}</div>
                            )) : "—"}
                            {Array.isArray(c.primary_reasons) && c.primary_reasons.length > 2 && (
                              <small style={{ color: "#0f6c70" }}>+{c.primary_reasons.length - 2} more signals</small>
                            )}
                          </div>
                        </td>
                        <td>
                          <span style={{
                            background: c.status === "CONFIRMED_DUPLICATE" ? "#fee2e2" : c.status === "NOT_DUPLICATE" ? "#dcfce7" : "#f1f5f9",
                            color: c.status === "CONFIRMED_DUPLICATE" ? "#991b1b" : c.status === "NOT_DUPLICATE" ? "#166534" : "#334155",
                            padding: "3px 8px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            fontWeight: 700
                          }}>
                            {c.status}
                          </span>
                        </td>
                        <td>
                          <button
                            type="button"
                            onClick={() => handleOpenComparison(c.case_id)}
                            style={{
                              background: "#0f6c70",
                              color: "#ffffff",
                              border: "none",
                              padding: "5px 10px",
                              borderRadius: "4px",
                              fontSize: "11px",
                              fontWeight: 700,
                              cursor: "pointer"
                            }}
                          >
                            Review & Compare ↗
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── 3. CROSS-RECORD VALIDATION TAB ── */}
      {activeTab === "validation" && (
        <div style={{ background: "#ffffff", padding: "20px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
          <h3 style={{ margin: "0 0 8px 0", fontSize: "16px", fontWeight: 800, color: "#0f172a" }}>
            Cross-Record Cadastral Consistency Validation
          </h3>
          <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 16px 0" }}>
            Automated checks for spatial bounding violations, missing GPS coordinates, and extent discrepancies.
          </p>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Parcel Key</th>
                  <th>Survey Number</th>
                  <th>Location</th>
                  <th>Severity</th>
                  <th>Consistency Anomalies</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a, i) => (
                  <tr key={a.parcel_id || i}>
                    <td><code>{a.record_id || `P-${a.parcel_id}`}</code></td>
                    <td><b>{a.survey_no}</b></td>
                    <td>{a.village}, {a.district}</td>
                    <td>
                      <span style={{
                        background: a.severity === "CRITICAL" ? "#fee2e2" : a.severity === "HIGH" ? "#fef2f2" : "#fef3c7",
                        color: a.severity === "CRITICAL" ? "#991b1b" : a.severity === "HIGH" ? "#b91c1c" : "#92400e",
                        padding: "2px 6px",
                        borderRadius: "4px",
                        fontSize: "11px",
                        fontWeight: 700
                      }}>
                        {a.severity}
                      </span>
                    </td>
                    <td>
                      <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "11px", color: "#334155" }}>
                        {a.anomalies?.map((reason, idx) => (
                          <li key={idx}>{reason}</li>
                        ))}
                      </ul>
                    </td>
                    <td>
                      <button
                        type="button"
                        onClick={() => onSelectParcel ? onSelectParcel({ id: a.parcel_id, ...a }) : null}
                        style={{
                          background: "#f1f5f9",
                          border: "1px solid #cbd5e1",
                          padding: "4px 8px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          cursor: "pointer",
                          fontWeight: 600
                        }}
                      >
                        Inspect Parcel ↗
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── 4. CROSS-DATABASE VERIFICATION TAB ── */}
      {activeTab === "cross_db" && (
        <div style={{ background: "#ffffff", padding: "20px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
          <h3 style={{ margin: "0 0 8px 0", fontSize: "16px", fontWeight: 800, color: "#0f172a" }}>
            Cross-Database Authoritative Verification Gateway
          </h3>
          <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 16px 0" }}>
            Queries external state & national registries (DILRMP, State LRMS, Sub-Registrar deed registry, Cadastral GIS). When live endpoints are unconfigured, authoritative systems truthfully report <code>NOT_CONNECTED</code>.
          </p>

          <form onSubmit={handleRunCrossDb} style={{ display: "flex", gap: "10px", alignItems: "center", marginBottom: "20px", flexWrap: "wrap" }}>
            <label style={{ fontSize: "13px", fontWeight: 700 }}>Query Parcel ID:</label>
            <input
              type="number"
              value={verifyParcelId}
              onChange={e => setVerifyParcelId(e.target.value)}
              placeholder="e.g. 101"
              required
              style={{ padding: "6px 12px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px", width: "160px" }}
            />
            <button
              type="submit"
              disabled={verifyingExternal}
              style={{
                background: "#0f6c70",
                color: "#ffffff",
                border: "none",
                padding: "7px 16px",
                borderRadius: "6px",
                fontWeight: 700,
                fontSize: "13px",
                cursor: verifyingExternal ? "not-allowed" : "pointer"
              }}
            >
              {verifyingExternal ? "Querying External Registries..." : "🔍 Run Multi-Database Query"}
            </button>
          </form>

          {externalResults && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ padding: "10px", background: "#f8fafc", borderRadius: "6px", border: "1px solid #e2e8f0", fontSize: "12px", color: "#475569" }}>
                <b>Notice:</b> {externalResults.truthful_notice}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "14px" }}>
                {externalResults.verifications?.map((v, idx) => {
                  const isMatch = v.status === "VERIFIED_MATCH";
                  const isNotConnected = v.status === "NOT_CONNECTED";
                  const isDemo = v.is_demo;

                  return (
                    <div
                      key={idx}
                      style={{
                        background: isDemo ? "#fffbeb" : "#ffffff",
                        border: `1px solid ${isDemo ? "#fde68a" : "#e2e8f0"}`,
                        borderRadius: "8px",
                        padding: "14px",
                        boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
                      }}
                    >
                      {isDemo && (
                        <div style={{ display: "inline-block", background: "#fef3c7", color: "#92400e", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 800, marginBottom: "6px" }}>
                          ⚠️ DEMONSTRATION DATA – NOT GOVERNMENT SOURCE
                        </div>
                      )}
                      
                      <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f172a" }}>
                        {v.provider_name}
                      </div>
                      <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "8px" }}>
                        Source Type: <code>{v.source_type}</code>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "8px", margin: "8px 0" }}>
                        <span style={{
                          background: isMatch ? "#dcfce7" : isNotConnected ? "#f1f5f9" : "#fee2e2",
                          color: isMatch ? "#166534" : isNotConnected ? "#475569" : "#991b1b",
                          padding: "3px 8px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: 800
                        }}>
                          {v.status}
                        </span>
                      </div>

                      <div style={{ fontSize: "12px", color: "#334155", lineHeight: "1.5" }}>
                        {v.details}
                      </div>

                      {v.disclaimer && (
                        <div style={{ fontSize: "11px", color: "#64748b", marginTop: "8px", fontStyle: "italic" }}>
                          * {v.disclaimer}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── 5. VERIFICATION QUEUE TAB ── */}
      {activeTab === "queue" && (
        <div style={{ background: "#ffffff", padding: "20px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
            <div>
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 800, color: "#0f172a" }}>
                Prioritized Verification Queue
              </h3>
              <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "#64748b" }}>
                Dynamically weighted based on exact identifier conflicts, similarity score, and acquisition lifecycle impact.
              </p>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
              <span>Priority:</span>
              <select
                value={queuePriority}
                onChange={e => setQueuePriority(e.target.value)}
                style={{ padding: "4px 8px", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "12px" }}
              >
                <option value="ALL">All Priorities</option>
                <option value="CRITICAL">Critical Priority</option>
                <option value="HIGH">High Priority</option>
                <option value="MEDIUM">Medium Priority</option>
              </select>
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Case ID</th>
                  <th>Record A (Primary)</th>
                  <th>Record B (Candidate)</th>
                  <th>Score</th>
                  <th>Statutory Impact</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((q, idx) => (
                  <tr key={q.case_id || idx}>
                    <td>
                      <span style={{
                        background: q.priority === "CRITICAL" ? "#fee2e2" : q.priority === "HIGH" ? "#fef2f2" : "#fef3c7",
                        color: q.priority === "CRITICAL" ? "#991b1b" : q.priority === "HIGH" ? "#b91c1c" : "#92400e",
                        padding: "3px 8px",
                        borderRadius: "12px",
                        fontSize: "11px",
                        fontWeight: 800
                      }}>
                        {q.priority}
                      </span>
                    </td>
                    <td><code>{q.case_id}</code></td>
                    <td><b>{q.rec_a_survey}</b> ({q.rec_a_village})</td>
                    <td><b>{q.rec_b_survey}</b> ({q.rec_b_village})</td>
                    <td><b>{q.similarity_score}/100</b></td>
                    <td style={{ fontSize: "11px", color: "#475569" }}>{q.statutory_impact}</td>
                    <td>
                      <button
                        type="button"
                        onClick={() => handleOpenComparison(q.case_id)}
                        style={{
                          background: "#0f6c70",
                          color: "#fff",
                          border: "none",
                          padding: "5px 10px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: 700,
                          cursor: "pointer"
                        }}
                      >
                        Inspect ↗
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── 6. AUDIT HISTORY TAB ── */}
      {activeTab === "audit" && (
        <div style={{ background: "#ffffff", padding: "20px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
          <h3 style={{ margin: "0 0 12px 0", fontSize: "16px", fontWeight: 800, color: "#0f172a" }}>
            Data Quality & Duplicate Investigation Audit Trail
          </h3>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Actor</th>
                  <th>Action</th>
                  <th>Target</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((l, i) => (
                  <tr key={l.id || i}>
                    <td style={{ fontSize: "11px", color: "#64748b" }}>
                      {(l.created_at || "").slice(0, 19).replace("T", " ")}
                    </td>
                    <td><small>{l.user_email}</small></td>
                    <td>
                      <span style={{ background: "#f1f5f9", padding: "2px 6px", borderRadius: "4px", fontSize: "11px", fontWeight: 700 }}>
                        {l.action}
                      </span>
                    </td>
                    <td><code>{l.target}</code></td>
                    <td style={{ fontSize: "11px", color: "#334155" }}>{l.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── SIDE-BY-SIDE RECORD COMPARISON MODAL ── */}
      {selectedCaseId && (
        <div style={{
          position: "fixed",
          top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(15, 23, 42, 0.75)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 9999,
          padding: "20px"
        }}>
          <div style={{
            background: "#ffffff",
            borderRadius: "12px",
            maxWidth: "960px",
            width: "100%",
            maxHeight: "92vh",
            overflowY: "auto",
            padding: "24px",
            boxShadow: "0 20px 25px -5px rgba(0,0,0,0.3)"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px", borderBottom: "1px solid #e2e8f0", paddingBottom: "12px" }}>
              <div>
                <div style={{ fontSize: "11px", fontWeight: 700, color: "#0f6c70", textTransform: "uppercase" }}>
                  DUPLICATE CASE INVESTIGATION · {selectedCaseId}
                </div>
                <h3 style={{ margin: "4px 0 0 0", color: "#0f172a", fontSize: "18px", fontWeight: 800 }}>
                  Side-by-Side Land Record Comparison
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedCaseId(null)}
                style={{ background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "50%", width: "32px", height: "32px", cursor: "pointer", fontWeight: 700 }}
              >
                ✕
              </button>
            </div>

            {loadingDetail ? (
              <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>Loading side-by-side comparison...</div>
            ) : caseDetail ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {/* Score & Assessment Card */}
                <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                  <div>
                    <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>CALCULATED SIMILARITY SCORE</div>
                    <div style={{ fontSize: "20px", fontWeight: 800, color: "#b45309" }}>
                      {caseDetail.comparison?.similarity_score}/100 ({caseDetail.comparison?.confidence_band} CONFIDENCE)
                    </div>
                    <div style={{ fontSize: "12px", color: "#475569" }}>
                      Status: <b>{caseDetail.case?.status}</b> · {caseDetail.comparison?.assessment}
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "8px", fontSize: "11px" }}>
                    <span style={{ background: "#dcfce7", color: "#166534", padding: "3px 8px", borderRadius: "4px", fontWeight: 700 }}>
                      ✓ {caseDetail.comparison?.summary?.match_count} Matches
                    </span>
                    <span style={{ background: "#fee2e2", color: "#991b1b", padding: "3px 8px", borderRadius: "4px", fontWeight: 700 }}>
                      ✕ {caseDetail.comparison?.summary?.mismatch_count} Mismatches
                    </span>
                    <span style={{ background: "#f1f5f9", color: "#475569", padding: "3px 8px", borderRadius: "4px", fontWeight: 700 }}>
                      ? {caseDetail.comparison?.summary?.missing_count} Missing
                    </span>
                  </div>
                </div>

                {/* Signal reasons */}
                <div style={{ background: "#fff", padding: "12px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                  <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: "6px" }}>
                    Additive Signal Breakdown:
                  </div>
                  <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "#334155", lineHeight: "1.6" }}>
                    {caseDetail.comparison?.reasons?.map((r, idx) => (
                      <li key={idx}>{r}</li>
                    ))}
                  </ul>
                </div>

                {/* Side-by-Side Table */}
                <div className="table-wrap">
                  <table style={{ width: "100%", fontSize: "12px" }}>
                    <thead>
                      <tr>
                        <th style={{ width: "20%" }}>Cadastral Field</th>
                        <th style={{ width: "32%" }}>Record A ({caseDetail.record_a?.record_id || `ID: ${caseDetail.record_a?.id}`})</th>
                        <th style={{ width: "32%" }}>Record B ({caseDetail.record_b?.record_id || `ID: ${caseDetail.record_b?.id}`})</th>
                        <th style={{ width: "16%" }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {caseDetail.comparison?.fields?.map((f, idx) => {
                        const isMatch = f.status === "MATCH";
                        const isMismatch = f.status === "MISMATCH";
                        const isMissing = f.status === "MISSING";
                        const badgeBg = isMatch ? "#dcfce7" : isMismatch ? "#fee2e2" : isMissing ? "#f1f5f9" : "#fef3c7";
                        const badgeColor = isMatch ? "#166534" : isMismatch ? "#991b1b" : isMissing ? "#64748b" : "#92400e";

                        return (
                          <tr key={idx}>
                            <td><b>{f.label}</b></td>
                            <td style={{ fontFamily: ["survey_no", "coordinates"].includes(f.key) ? "monospace" : "inherit" }}>
                              {f.record_a || "—"}
                            </td>
                            <td style={{ fontFamily: ["survey_no", "coordinates"].includes(f.key) ? "monospace" : "inherit" }}>
                              {f.record_b || "—"}
                            </td>
                            <td>
                              <span style={{
                                background: badgeBg,
                                color: badgeColor,
                                padding: "2px 6px",
                                borderRadius: "4px",
                                fontSize: "10px",
                                fontWeight: 800
                              }}>
                                {f.status}
                              </span>
                              {f.note && (
                                <div style={{ fontSize: "10px", color: "#64748b", marginTop: "2px" }}>
                                  {f.note}
                                </div>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* ── Officer Decision Section ── */}
                <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid #cbd5e1" }}>
                  <h4 style={{ margin: "0 0 10px 0", color: "#0f172a", fontSize: "14px", fontWeight: 800 }}>
                    Human-in-the-Loop Officer Decision & Justification
                  </h4>

                  {decisionFeedback && (
                    <div style={{ padding: "8px 12px", background: "#f0fdf4", color: "#166534", borderRadius: "4px", fontSize: "12px", fontWeight: 700, marginBottom: "10px" }}>
                      {decisionFeedback}
                    </div>
                  )}

                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                        Master Record Selection (If Confirming Duplicate):
                      </label>
                      <select
                        value={masterRecordId || ""}
                        onChange={e => setMasterRecordId(Number(e.target.value))}
                        style={{ padding: "6px", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "12px", width: "100%", maxWidth: "450px" }}
                      >
                        <option value={caseDetail.record_a?.id}>
                          Keep Record A ({caseDetail.record_a?.record_id} - Survey {caseDetail.record_a?.survey_no}) as Master
                        </option>
                        <option value={caseDetail.record_b?.id}>
                          Keep Record B ({caseDetail.record_b?.record_id} - Survey {caseDetail.record_b?.survey_no}) as Master
                        </option>
                      </select>
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, display: "block", marginBottom: "4px" }}>
                        Statutory Reason / Justification (Mandatory for Audit Trail):
                      </label>
                      <textarea
                        rows={2}
                        value={decisionReason}
                        onChange={e => setDecisionReason(e.target.value)}
                        placeholder="e.g. Verified against Sub-Registrar Volume 45 deed. Distinct holding partitioned under 2024 family deed."
                        style={{ width: "100%", padding: "8px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", boxSizing: "border-box" }}
                      />
                    </div>

                    <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "6px" }}>
                      <button
                        type="button"
                        disabled={submittingDecision}
                        onClick={() => handleSubmitDecision("CONFIRMED_DUPLICATE")}
                        style={{
                          background: "#dc2626",
                          color: "#fff",
                          border: "none",
                          padding: "7px 14px",
                          borderRadius: "6px",
                          fontWeight: 700,
                          fontSize: "12px",
                          cursor: submittingDecision ? "not-allowed" : "pointer"
                        }}
                      >
                        ✓ Confirm Duplicate (Flag Secondary)
                      </button>

                      <button
                        type="button"
                        disabled={submittingDecision}
                        onClick={() => handleSubmitDecision("NOT_DUPLICATE")}
                        style={{
                          background: "#16a34a",
                          color: "#fff",
                          border: "none",
                          padding: "7px 14px",
                          borderRadius: "6px",
                          fontWeight: 700,
                          fontSize: "12px",
                          cursor: submittingDecision ? "not-allowed" : "pointer"
                        }}
                      >
                        ✕ Mark Not Duplicate (Distinct Holdings)
                      </button>

                      <button
                        type="button"
                        disabled={submittingDecision}
                        onClick={() => handleSubmitDecision("FIELD_VERIFICATION_REQUESTED")}
                        style={{
                          background: "#0284c7",
                          color: "#fff",
                          border: "none",
                          padding: "7px 14px",
                          borderRadius: "6px",
                          fontWeight: 700,
                          fontSize: "12px",
                          cursor: submittingDecision ? "not-allowed" : "pointer"
                        }}
                      >
                        📍 Request Field Inspection
                      </button>

                      <button
                        type="button"
                        disabled={submittingDecision}
                        onClick={() => handleSubmitDecision("INSUFFICIENT_INFORMATION")}
                        style={{
                          background: "#64748b",
                          color: "#fff",
                          border: "none",
                          padding: "7px 14px",
                          borderRadius: "6px",
                          fontWeight: 700,
                          fontSize: "12px",
                          cursor: submittingDecision ? "not-allowed" : "pointer"
                        }}
                      >
                        ? Require More Documents
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
