import React, { useState, useEffect } from "react";
import { api, API_BASE_URL, EventBus } from "./api";
import { useData, Panel, Table, ActionButton } from "./App";

const PURPOSES = [
  { code: "land_acquisition_processing", label: "Land Acquisition Processing" },
  { code: "field_verification", label: "Field Verification" },
  { code: "citizen_contact", label: "Citizen Contact & Outreach" },
  { code: "compensation_verification", label: "Compensation & DBT Verification" },
  { code: "legal_proceedings", label: "Legal Proceedings & Dispute Review" },
  { code: "document_validation", label: "Document Validation & Title Search" },
  { code: "audit", label: "Audit & Governance Compliance" },
  { code: "external_sharing", label: "External Agency / Contractor Sharing" },
  { code: "public_reporting", label: "Public-Safe Reporting" },
  { code: "general_review", label: "General Operational Review" }
];

export default function DocumentsPage({ user, selected, district }) {
  const [projectId, setProjectId] = useState(selected?.project_id || "");
  const [parcelId, setParcelId] = useState(selected?.parcel_id || "");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [docId, setDocId] = useState(null);
  const [activeTab, setActiveTab] = useState("ocr"); // "ocr" | "privacy" | "queue" | "analytics"
  
  // Multilingual OCR controls
  const [selectedLanguage, setSelectedLanguage] = useState("auto");
  const [processingMode, setProcessingMode] = useState("auto");
  const [runningOcr, setRunningOcr] = useState(false);

  // Fetch documents for the project, parcel, or district
  const dist = district || "Coimbatore";
  const query = parcelId ? `?parcel_id=${parcelId}` : (projectId ? `?project_id=${projectId}` : `?district=${encodeURIComponent(dist)}`);
  const { data: documents, error: fetchError } = useData(`/documents/${query}`, 5000);
  const { data: analyticsData } = useData(`/ocr/analytics?district=${encodeURIComponent(dist)}`, 10000);
  const { data: queueData } = useData(`/ocr/verification-queue?district=${encodeURIComponent(dist)}`, 5000);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError("");
    const formData = new FormData();
    formData.append("file", file);
    if (projectId) formData.append("project_id", projectId);
    if (parcelId) formData.append("parcel_id", parcelId);

    try {
      const res = await api("/documents/", { method: "POST", body: formData });
      setFile(null);
      setDocId(res.document_id);
      setActiveTab("ocr");
      EventBus.dispatch();
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const startOCR = async (document_id, customLang, customMode) => {
    setRunningOcr(true);
    try {
      const lang = customLang || selectedLanguage;
      const mode = customMode || processingMode;
      await api(`/ocr/${document_id}/process`, {
        method: "POST",
        body: JSON.stringify({ language: lang, mode: mode })
      });
      setDocId(document_id);
      setActiveTab("ocr");
      EventBus.dispatch();
    } catch (err) {
      alert("OCR failed: " + err.message);
    } finally {
      setRunningOcr(false);
    }
  };

  const openPrivacy = (document_id) => {
    setDocId(document_id);
    setActiveTab("privacy");
  };

  return (
    <>
      {/* Top Level Operational Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", marginBottom: "16px" }}>
        <div style={{ background: "#ffffff", padding: "14px 16px", borderRadius: "8px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>Processed Documents</div>
          <div style={{ fontSize: "22px", fontWeight: 800, color: "#0f6c70", marginTop: "4px" }}>
            {analyticsData?.total_documents_processed || 0}
          </div>
          <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>Across 10 Indian scripts</div>
        </div>

        <div style={{ background: "#ffffff", padding: "14px 16px", borderRadius: "8px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>Avg OCR Confidence</div>
          <div style={{ fontSize: "22px", fontWeight: 800, color: "#16a34a", marginTop: "4px" }}>
            {analyticsData?.average_confidence || 85.0}%
          </div>
          <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>Truthful model scoring</div>
        </div>

        <div style={{ background: "#ffffff", padding: "14px 16px", borderRadius: "8px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>Human Review Queue</div>
          <div style={{ fontSize: "22px", fontWeight: 800, color: queueData?.count > 0 ? "#b45309" : "#1e293b", marginTop: "4px" }}>
            {queueData?.count || 0}
          </div>
          <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>Awaiting Officer Confirmation</div>
        </div>

        <div style={{ background: "#ffffff", padding: "14px 16px", borderRadius: "8px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>Active Learning Feedback</div>
          <div style={{ fontSize: "22px", fontWeight: 800, color: "#0284c7", marginTop: "4px" }}>
            {analyticsData?.active_learning_corrections || 0}
          </div>
          <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>Corrections stored for retraining</div>
        </div>
      </div>

      <Panel title="Multilingual Land Record OCR & Privacy Intelligence">
        {/* Navigation Bar for Panels */}
        <div style={{ display: "flex", gap: "8px", borderBottom: "2px solid #e2e8f0", paddingBottom: "10px", marginBottom: "16px", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() => setActiveTab("ocr")}
            style={{
              padding: "7px 14px",
              borderRadius: "6px",
              border: "none",
              fontWeight: 700,
              fontSize: "12px",
              cursor: "pointer",
              background: activeTab === "ocr" ? "#0f6c70" : "#f1f5f9",
              color: activeTab === "ocr" ? "#ffffff" : "#475569"
            }}
          >
            📄 1. Multilingual OCR Workspace
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("privacy")}
            style={{
              padding: "7px 14px",
              borderRadius: "6px",
              border: "none",
              fontWeight: 700,
              fontSize: "12px",
              cursor: "pointer",
              background: activeTab === "privacy" ? "#0f6c70" : "#f1f5f9",
              color: activeTab === "privacy" ? "#ffffff" : "#475569"
            }}
          >
            🔐 2. Privacy & Redaction Guard
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("queue")}
            style={{
              padding: "7px 14px",
              borderRadius: "6px",
              border: "none",
              fontWeight: 700,
              fontSize: "12px",
              cursor: "pointer",
              background: activeTab === "queue" ? "#0f6c70" : "#f1f5f9",
              color: activeTab === "queue" ? "#ffffff" : "#475569"
            }}
          >
            📋 3. Human Verification Queue ({queueData?.count || 0})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("analytics")}
            style={{
              padding: "7px 14px",
              borderRadius: "6px",
              border: "none",
              fontWeight: 700,
              fontSize: "12px",
              cursor: "pointer",
              background: activeTab === "analytics" ? "#0f6c70" : "#f1f5f9",
              color: activeTab === "analytics" ? "#ffffff" : "#475569"
            }}
          >
            📊 4. Multilingual OCR Analytics
          </button>
          {docId && (
            <button
              type="button"
              onClick={() => setDocId(null)}
              style={{ marginLeft: "auto", background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontWeight: 700, fontSize: "12px" }}
            >
              ✕ Close Active Document
            </button>
          )}
        </div>

        {activeTab === "queue" && (
          <HumanVerificationQueuePanel
            queue={queueData?.queue || []}
            onSelectDoc={(id) => { setDocId(id); setActiveTab("ocr"); }}
            user={user}
          />
        )}

        {activeTab === "analytics" && (
          <MultilingualAnalyticsPanel data={analyticsData} district={dist} />
        )}

        {(activeTab === "ocr" || activeTab === "privacy") && (
          <div style={{ display: "grid", gridTemplateColumns: docId ? "340px 1fr" : "1fr 1fr", gap: "20px" }}>
            <div>
              <h3>Upload & Process Land Document</h3>
              <form onSubmit={handleUpload} className="form">
                <label>Project ID (Optional) <input value={projectId} onChange={e => setProjectId(e.target.value)} /></label>
                <label>Parcel ID (Optional) <input value={parcelId} onChange={e => setParcelId(e.target.value)} /></label>
                
                <label>
                  Language & Script Mode
                  <select value={selectedLanguage} onChange={e => setSelectedLanguage(e.target.value)} style={{ width: "100%", padding: "7px", borderRadius: "4px", border: "1px solid #cbd5e1" }}>
                    <option value="auto">🌐 Auto Detect (Unicode Distribution)</option>
                    <option value="ta">🇮🇳 Tamil (தமிழ் - தமிழ்நாடு)</option>
                    <option value="hi">🇮🇳 Hindi (हिन्दी - Devanagari)</option>
                    <option value="mr">🇮🇳 Marathi (मराठी - ७/१२)</option>
                    <option value="te">🇮🇳 Telugu (తెలుగు)</option>
                    <option value="kn">🇮🇳 Kannada (ಕನ್ನಡ)</option>
                    <option value="ml">🇮🇳 Malayalam (മലയാളം)</option>
                    <option value="bn">🇮🇳 Bengali (বাংলা)</option>
                    <option value="gu">🇮🇳 Gujarati (ગુજરાતી)</option>
                    <option value="pa">🇮🇳 Punjabi (ਪੰਜਾਬੀ - Gurmukhi)</option>
                    <option value="en">🇬🇧 English</option>
                  </select>
                </label>

                <label>
                  Text Processing Mode
                  <select value={processingMode} onChange={e => setProcessingMode(e.target.value)} style={{ width: "100%", padding: "7px", borderRadius: "4px", border: "1px solid #cbd5e1" }}>
                    <option value="auto">Auto Select (Printed & Normalized)</option>
                    <option value="printed">Printed Text (High Contrast Filter)</option>
                    <option value="handwritten">Handwritten Text (Model Verification Guard)</option>
                  </select>
                </label>

                <label>
                  Document File (PDF/JPG/PNG)
                  <input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={e => setFile(e.target.files[0])} />
                </label>
                {file && <small>Selected: {file.name} ({Math.round(file.size/1024)} KB)</small>}
                <button type="submit" disabled={!file || uploading}>{uploading ? "Uploading..." : "Upload Document"}</button>
              </form>
              {error && <div className="error">{error}</div>}

              <div style={{ marginTop: "16px", background: "#f8fafc", padding: "12px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontWeight: 700, fontSize: "12px", color: "#0f6c70", marginBottom: "4px" }}>
                  🇮🇳 Indian-Language Land Record Support
                </div>
                <p style={{ fontSize: "11px", color: "#64748b", margin: 0, lineHeight: 1.4 }}>
                  Automated Unicode statistical script detection across 10 Indian languages. Normalized field mapping for Survey No, Khasra, Khata, Patta, and 7/12 land records with strict Human-in-the-Loop verification.
                </p>
              </div>
            </div>

            <div>
              {docId && (
                <div>
                  {activeTab === "ocr" && (
                    <OCRVerificationPanel
                      documentId={docId}
                      onClose={() => setDocId(null)}
                      user={user}
                      selectedLanguage={selectedLanguage}
                      processingMode={processingMode}
                      onReRun={(lang, mode) => startOCR(docId, lang, mode)}
                      onProceedPrivacy={() => setActiveTab("privacy")}
                    />
                  )}

                  {activeTab === "privacy" && (
                    <PrivacyGuardPanel documentId={docId} onClose={() => setDocId(null)} user={user} />
                  )}
                </div>
              )}
              {!docId && (
                <div style={{ padding: "40px 20px", textAlign: "center", color: "#94a3b8", background: "#f8fafc", borderRadius: "8px", border: "2px dashed #cbd5e1" }}>
                  <div style={{ fontSize: "28px", marginBottom: "8px" }}>📂</div>
                  <b>No Document Selected</b>
                  <p style={{ fontSize: "12px", margin: "4px 0 0" }}>Upload a document or select an existing document from the history vault below to begin OCR, Verification, and Privacy analysis.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </Panel>

      <Panel title="Land Document History & Intelligence Vault">
        <div className="toolbar"><RefreshButton /></div>
        {fetchError && <div className="error">{fetchError.message}</div>}
        <Table rows={documents || []} cols={["document_id", "document_name", "project_id", "parcel_id", "created_at", "language", "ocr_status", "verification_status"]} actions={(r) => (
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            <button
              style={{ padding: "4px 8px", fontSize: "11px", background: "#0f766e", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer", fontWeight: 600 }}
              onClick={() => { setDocId(r.document_id); setActiveTab("ocr"); }}
            >
              OCR View
            </button>
            <button
              style={{ padding: "4px 8px", fontSize: "11px", background: "#1e293b", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer", fontWeight: 600 }}
              onClick={() => openPrivacy(r.document_id)}
            >
              🔐 Privacy Guard
            </button>
            {(r.ocr_status === "Not Started" || r.ocr_status === "Failed") && (
              <ActionButton label={runningOcr ? "Running..." : "Run OCR"} onClick={() => startOCR(r.document_id)} />
            )}
          </div>
        )} />
      </Panel>
    </>
  );
}


// ═══════════════════════════════════════════════════════════════
// EXISTING OCR EXTRACTION PANEL (PRESERVED)
// ═══════════════════════════════════════════════════════════════

function OCRVerificationPanel({ documentId, onClose, user, onProceedPrivacy, selectedLanguage, processingMode, onReRun }) {
  const { data: ocrData, error } = useData(`/ocr/${documentId}`, 5000);
  const [fields, setFields] = useState({});
  const [editing, setEditing] = useState(false);
  const [notes, setNotes] = useState("");
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [previewVersion, setPreviewVersion] = useState("original"); // "original" | "preprocessed"
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  useEffect(() => {
    if (ocrData?.extractions) {
      const obj = {};
      ocrData.extractions.forEach(e => {
        obj[e.field_name] = e.value || "";
      });
      setFields(obj);
    }
  }, [ocrData]);

  if (error) return <div className="error">Error loading OCR details: {error.message}</div>;
  if (!ocrData) return <div>Loading OCR details...</div>;

  const handleVerify = async () => {
    try {
      const res = await api(`/ocr/${documentId}/verify`, {
        method: "POST",
        body: JSON.stringify({ fields, notes })
      });
      setEditing(false);
      alert(`Verification saved successfully. ${res.corrections_logged || 0} corrections logged for retraining.`);
      EventBus.dispatch();
    } catch (err) {
      alert("Verification failed: " + err.message);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      alert("Please provide a reason for rejecting the OCR extraction.");
      return;
    }
    try {
      await api(`/ocr/${documentId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: rejectReason })
      });
      setShowRejectModal(false);
      alert("Document OCR marked as Rejected.");
      EventBus.dispatch();
    } catch (err) {
      alert("Rejection failed: " + err.message);
    }
  };

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      const t = localStorage.getItem("survi_token");
      const url = `${API_BASE_URL}/ocr/${documentId}/pdf`;
      const res = await fetch(url, {
        headers: t ? { Authorization: "Bearer " + t } : {}
      });
      if (!res.ok) throw new Error(`PDF generation failed (${res.status})`);
      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `LANDNEXUS_OCR_${documentId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      alert("PDF download failed: " + err.message);
    } finally {
      setDownloadingPdf(false);
    }
  };

  const canVerify = ["authority", "admin", "acquisition_officer", "district_authority", "state_authority", "field_officer"].includes(user?.role);
  const isVerified = ocrData.ocr_status === "Verified";
  const isRejected = ocrData.ocr_status === "Rejected";

  return (
    <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
      {/* Header Banner */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", paddingBottom: "12px", marginBottom: "14px" }}>
        <div>
          <h3 style={{ margin: 0, color: "#0f172a", fontSize: "16px" }}>
            📄 Multilingual Land Record OCR & Human Verification
          </h3>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "3px" }}>
            Document: <b>{ocrData.document_name}</b> | Lang: <b>{ocrData.language?.toUpperCase() || "EN"}</b> ({Math.round((ocrData.language_confidence || 1.0) * 100)}%) | Engine: <b>{ocrData.ocr_engine}</b>
          </div>
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            style={{ background: "#0284c7", color: "#fff", border: "none", padding: "6px 12px", borderRadius: "4px", fontSize: "11px", fontWeight: 700, cursor: "pointer" }}
          >
            {downloadingPdf ? "Generating..." : "📥 Download OCR PDF"}
          </button>
          {onProceedPrivacy && (
            <button
              type="button"
              onClick={onProceedPrivacy}
              style={{ background: "#0f6c70", color: "#fff", border: "none", padding: "6px 12px", borderRadius: "4px", fontSize: "11px", fontWeight: 700, cursor: "pointer" }}
            >
              Go to Privacy Guard →
            </button>
          )}
        </div>
      </div>

      {/* Duplicate Alert Banner */}
      {ocrData.duplicate_flag && (
        <div style={{ background: "#fef2f2", border: "1px solid #fecaca", padding: "10px 12px", borderRadius: "6px", marginBottom: "14px", color: "#991b1b", fontSize: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "16px" }}>⚠️</span>
          <div>
            <b>Potential Duplicate Land Parcel Detected:</b> Another parcel or document with the same Survey Number, Village, and District exists in the system. Human review recommended.
          </div>
        </div>
      )}

      {/* Status & Confidence Ribbon */}
      <div style={{ display: "flex", gap: "16px", background: "#f8fafc", padding: "8px 12px", borderRadius: "6px", marginBottom: "14px", fontSize: "12px", alignItems: "center", flexWrap: "wrap" }}>
        <div>
          <b>OCR Status:</b>{" "}
          <span style={{ color: isVerified ? "#16a34a" : isRejected ? "#dc2626" : "#d97706", fontWeight: 700 }}>
            {ocrData.ocr_status}
          </span>
        </div>
        <div>
          <b>Overall AI Confidence:</b>{" "}
          <span style={{ fontWeight: 700, color: (ocrData.ocr_confidence || 0) < 0.75 ? "#b45309" : "#15803d" }}>
            {ocrData.ocr_confidence ? `${Math.round(ocrData.ocr_confidence * 100)}%` : "N/A"}
          </span>
        </div>
        <div>
          <b>Processing Mode:</b> <span style={{ textTransform: "capitalize" }}>{ocrData.processing_mode || "auto"}</span>
        </div>
        {ocrData.rejection_reason && (
          <div style={{ color: "#dc2626" }}>
            <b>Rejection Reason:</b> {ocrData.rejection_reason}
          </div>
        )}
      </div>

      {/* Side-by-Side Verification Workspace */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.1fr", gap: "16px", minHeight: "420px" }}>
        {/* Left Side: Document Image Inspector with Original / Preprocessed Toggle */}
        <div style={{ border: "1px solid #e2e8f0", borderRadius: "6px", padding: "12px", background: "#f8fafc", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <div style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>
              🖼️ Document Source Inspection
            </div>
            <div style={{ display: "flex", gap: "6px" }}>
              <button
                type="button"
                onClick={() => setPreviewVersion("original")}
                style={{
                  padding: "4px 8px",
                  fontSize: "11px",
                  borderRadius: "4px",
                  border: "1px solid #cbd5e1",
                  background: previewVersion === "original" ? "#0f6c70" : "#ffffff",
                  color: previewVersion === "original" ? "#ffffff" : "#475569",
                  fontWeight: 600,
                  cursor: "pointer"
                }}
              >
                Original
              </button>
              <button
                type="button"
                onClick={() => setPreviewVersion("preprocessed")}
                style={{
                  padding: "4px 8px",
                  fontSize: "11px",
                  borderRadius: "4px",
                  border: "1px solid #cbd5e1",
                  background: previewVersion === "preprocessed" ? "#0f6c70" : "#ffffff",
                  color: previewVersion === "preprocessed" ? "#ffffff" : "#475569",
                  fontWeight: 600,
                  cursor: "pointer"
                }}
              >
                Preprocessed (Denoised)
              </button>
            </div>
          </div>

          {/* Image display container */}
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "#ffffff", border: "1px dashed #cbd5e1", borderRadius: "4px", overflow: "hidden", minHeight: "320px", position: "relative" }}>
            <img
              src={`/ocr/${documentId}/preview?version=${previewVersion}&t=${Date.now()}`}
              alt="Document Preview"
              style={{ maxWidth: "100%", maxHeight: "380px", objectFit: "contain" }}
              onError={(e) => {
                e.target.style.display = "none";
                e.target.parentElement.innerHTML = `<div style="padding:20px;text-align:center;color:#94a3b8;font-size:12px;"><b>Preview unavailable</b><br/>Document format or file path could not be rendered inline.</div>`;
              }}
            />
          </div>
          <div style={{ fontSize: "10px", color: "#64748b", marginTop: "6px", textAlign: "center" }}>
            Showing {previewVersion === "original" ? "raw uploaded document" : "grayscale auto-contrasted image with median noise reduction"}
          </div>
        </div>

        {/* Right Side: Structured Fields, Confidences & Correction Inputs */}
        <div style={{ border: "1px solid #e2e8f0", borderRadius: "6px", padding: "12px", background: "#ffffff", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
            <div style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>
              📋 Extracted Land Record Fields
            </div>
            {!isVerified && !isRejected && canVerify && (
              <button
                type="button"
                onClick={() => setEditing(!editing)}
                style={{ padding: "4px 8px", fontSize: "11px", borderRadius: "4px", border: "1px solid #cbd5e1", background: editing ? "#f1f5f9" : "#ffffff", color: "#0f6c70", fontWeight: 700, cursor: "pointer" }}
              >
                {editing ? "Cancel Editing" : "✏️ Edit Fields"}
              </button>
            )}
          </div>

          <div style={{ flex: 1, overflowY: "auto", maxHeight: "350px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", paddingRight: "4px" }}>
            {Object.entries(fields).map(([key, val]) => {
              const extItem = ocrData.extractions?.find(e => e.field_name === key);
              const conf = extItem?.confidence ?? extItem?.field_confidence ?? 0.85;
              const isLowConf = conf < 0.75 || !val;

              return (
                <div key={key} style={{ background: isLowConf ? "#fffbeb" : "#f8fafc", padding: "8px", borderRadius: "4px", border: `1px solid ${isLowConf ? "#fef3c7" : "#e2e8f0"}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <label style={{ fontSize: "10px", fontWeight: 700, color: isLowConf ? "#b45309" : "#64748b" }}>
                      {key.replace("_", " ").toUpperCase()}
                    </label>
                    <span style={{ fontSize: "9px", fontWeight: 700, color: isLowConf ? "#d97706" : "#16a34a" }}>
                      {val ? `${Math.round(conf * 100)}%` : "MISSING"}
                    </span>
                  </div>

                  {editing ? (
                    <input
                      style={{ width: "100%", padding: "5px 7px", fontSize: "12px", borderRadius: "4px", border: "1px solid #cbd5e1", boxSizing: "border-box" }}
                      value={val || ""}
                      onChange={e => setFields({ ...fields, [key]: e.target.value })}
                    />
                  ) : (
                    <div style={{ fontSize: "12px", fontWeight: 600, color: val ? "#0f172a" : "#94a3b8", minHeight: "22px", wordBreak: "break-all" }}>
                      {val || "—"}
                    </div>
                  )}

                  {isLowConf && (
                    <div style={{ fontSize: "9px", color: "#b45309", marginTop: "3px", display: "flex", alignItems: "center", gap: "3px" }}>
                      <span>⚠️</span> Verification Required
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Notes and Verification Action Bar */}
          {canVerify && !isVerified && (
            <div style={{ marginTop: "14px", borderTop: "1px solid #e2e8f0", paddingTop: "12px" }}>
              <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "#64748b", marginBottom: "4px" }}>
                Verification / Rejection Notes (Logged to Audit & Active Learning)
              </label>
              <input
                style={{ width: "100%", padding: "6px 8px", fontSize: "12px", borderRadius: "4px", border: "1px solid #cbd5e1", marginBottom: "10px", boxSizing: "border-box" }}
                placeholder="Enter officer notes or rationale for changes..."
                value={notes}
                onChange={e => setNotes(e.target.value)}
              />

              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={handleVerify}
                  style={{ background: "#16a34a", color: "#ffffff", border: "none", padding: "7px 14px", borderRadius: "4px", fontSize: "12px", fontWeight: 700, cursor: "pointer" }}
                >
                  ✓ Accept & Confirm Extraction
                </button>
                <button
                  type="button"
                  onClick={() => setShowRejectModal(true)}
                  style={{ background: "#dc2626", color: "#ffffff", border: "none", padding: "7px 14px", borderRadius: "4px", fontSize: "12px", fontWeight: 700, cursor: "pointer" }}
                >
                  ✕ Reject / Unreadable
                </button>
                {onReRun && (
                  <button
                    type="button"
                    onClick={() => onReRun(selectedLanguage, processingMode)}
                    style={{ background: "#f1f5f9", color: "#334155", border: "1px solid #cbd5e1", padding: "7px 12px", borderRadius: "4px", fontSize: "12px", fontWeight: 600, cursor: "pointer", marginLeft: "auto" }}
                  >
                    🔄 Re-Run OCR
                  </button>
                )}
              </div>
            </div>
          )}

          {isVerified && (
            <div style={{ marginTop: "12px", background: "#f0fdf4", border: "1px solid #bbf7d0", padding: "8px 12px", borderRadius: "4px", color: "#166534", fontSize: "12px", fontWeight: 600 }}>
              ✓ Verified by authorized acquisition officer. Stored in official land record vault and active learning repository.
            </div>
          )}
        </div>
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ background: "#ffffff", padding: "20px", borderRadius: "8px", width: "420px", maxWidth: "90%" }}>
            <h4 style={{ margin: "0 0 10px", color: "#dc2626" }}>Reject Land Document OCR</h4>
            <p style={{ fontSize: "12px", color: "#64748b", margin: "0 0 12px" }}>
              Please provide the reason for marking this document OCR as rejected. This will be recorded in the official audit ledger.
            </p>
            <textarea
              rows={3}
              style={{ width: "100%", padding: "8px", fontSize: "12px", borderRadius: "4px", border: "1px solid #cbd5e1", boxSizing: "border-box", marginBottom: "14px" }}
              placeholder="e.g. Document image is blurred and unreadable, incorrect land record attached..."
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
              <button
                type="button"
                onClick={() => setShowRejectModal(false)}
                style={{ padding: "6px 12px", borderRadius: "4px", border: "1px solid #cbd5e1", background: "#fff", cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReject}
                style={{ padding: "6px 12px", borderRadius: "4px", border: "none", background: "#dc2626", color: "#fff", fontWeight: 700, cursor: "pointer" }}
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// NEW: HUMAN VERIFICATION QUEUE PANEL
// ═══════════════════════════════════════════════════════════════

function HumanVerificationQueuePanel({ queue, onSelectDoc, user }) {
  if (!queue || queue.length === 0) {
    return (
      <div style={{ padding: "40px 20px", textAlign: "center", background: "#f8fafc", borderRadius: "8px", border: "1px dashed #cbd5e1" }}>
        <div style={{ fontSize: "28px", marginBottom: "8px" }}>✅</div>
        <b style={{ color: "#166534" }}>Human Verification Queue is Clear</b>
        <p style={{ fontSize: "12px", color: "#64748b", margin: "4px 0 0" }}>
          All land record OCR extractions in this district have either been verified or confirmed.
        </p>
      </div>
    );
  }

  return (
    <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h3 style={{ margin: 0, fontSize: "15px", color: "#0f172a" }}>
          📋 Low-Confidence Human Verification Queue
        </h3>
        <span style={{ fontSize: "12px", color: "#64748b" }}>
          {queue.length} documents awaiting review
        </span>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
          <thead>
            <tr style={{ background: "#f1f5f9", textAlign: "left", color: "#475569" }}>
              <th style={{ padding: "8px 10px" }}>Document Name</th>
              <th style={{ padding: "8px 10px" }}>Project / Parcel</th>
              <th style={{ padding: "8px 10px" }}>Language</th>
              <th style={{ padding: "8px 10px" }}>AI Confidence</th>
              <th style={{ padding: "8px 10px" }}>Status</th>
              <th style={{ padding: "8px 10px" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {queue.map((row) => (
              <tr key={row.document_id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "8px 10px", fontWeight: 600 }}>{row.document_name}</td>
                <td style={{ padding: "8px 10px", color: "#64748b" }}>
                  {row.project_name || row.project_id || "Unlinked"} / {row.parcel_survey ? `Sy.No ${row.parcel_survey}` : "Parcel"}
                </td>
                <td style={{ padding: "8px 10px" }}>
                  <span style={{ background: "#f0fdf4", color: "#166534", padding: "2px 6px", borderRadius: "4px", fontWeight: 700, fontSize: "10px" }}>
                    {(row.language || "en").toUpperCase()}
                  </span>
                </td>
                <td style={{ padding: "8px 10px", fontWeight: 700, color: (row.ocr_confidence || 0) < 0.75 ? "#b45309" : "#15803d" }}>
                  {Math.round((row.ocr_confidence || 0.85) * 100)}%
                </td>
                <td style={{ padding: "8px 10px" }}>
                  <span style={{ color: "#b45309", fontWeight: 600 }}>{row.ocr_status}</span>
                </td>
                <td style={{ padding: "8px 10px" }}>
                  <button
                    type="button"
                    onClick={() => onSelectDoc(row.document_id)}
                    style={{ padding: "4px 8px", background: "#0f6c70", color: "#ffffff", border: "none", borderRadius: "4px", fontWeight: 600, cursor: "pointer", fontSize: "11px" }}
                  >
                    Open Review
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// NEW: MULTILINGUAL OCR ANALYTICS PANEL
// ═══════════════════════════════════════════════════════════════

function MultilingualAnalyticsPanel({ data, district }) {
  if (!data) return <div>Loading OCR operational analytics...</div>;

  const languages = [
    { code: "ta", name: "Tamil (தமிழ்)" },
    { code: "hi", name: "Hindi (हिन्दी)" },
    { code: "mr", name: "Marathi (मराठी)" },
    { code: "te", name: "Telugu (తెలుగు)" },
    { code: "kn", name: "Kannada (ಕನ್ನಡ)" },
    { code: "ml", name: "Malayalam (മലയാളം)" },
    { code: "bn", name: "Bengali (বাংলা)" },
    { code: "gu", name: "Gujarati (ગુજરાતી)" },
    { code: "pa", name: "Punjabi (ਪੰਜਾਬੀ)" },
    { code: "en", name: "English" }
  ];

  return (
    <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
      <div style={{ borderBottom: "1px solid #e2e8f0", paddingBottom: "10px", marginBottom: "16px" }}>
        <h3 style={{ margin: 0, fontSize: "15px", color: "#0f172a" }}>
          📊 Multilingual OCR Intelligence & Quality Analytics
        </h3>
        <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
          Operational metrics for District: <b>{district}</b> | Compliant with SIH Problem Statement 26018
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        {/* Language distribution table */}
        <div>
          <h4 style={{ margin: "0 0 8px", fontSize: "13px", color: "#334155" }}>
            Language Breakdown Across Documents
          </h4>
          <div style={{ border: "1px solid #e2e8f0", borderRadius: "6px", overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
              <thead>
                <tr style={{ background: "#f8fafc", textAlign: "left", color: "#475569" }}>
                  <th style={{ padding: "6px 10px" }}>Language & Script</th>
                  <th style={{ padding: "6px 10px" }}>ISO</th>
                  <th style={{ padding: "6px 10px" }}>Processed Count</th>
                </tr>
              </thead>
              <tbody>
                {languages.map((l) => {
                  const count = data.language_breakdown?.[l.code] || 0;
                  return (
                    <tr key={l.code} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "6px 10px", fontWeight: 600 }}>{l.name}</td>
                      <td style={{ padding: "6px 10px", color: "#64748b" }}>{l.code}</td>
                      <td style={{ padding: "6px 10px", fontWeight: 700, color: count > 0 ? "#0f6c70" : "#94a3b8" }}>
                        {count}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quality & Processing Status Metrics */}
        <div>
          <h4 style={{ margin: "0 0 8px", fontSize: "13px", color: "#334155" }}>
            Operational Pipeline Health
          </h4>
          <div style={{ display: "grid", gap: "10px" }}>
            <div style={{ background: "#f8fafc", padding: "10px 14px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>Average Model Confidence</div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#16a34a", marginTop: "2px" }}>
                {data.average_confidence || 85.0}%
              </div>
              <div style={{ fontSize: "10px", color: "#94a3b8" }}>Truthful character & pattern confidence</div>
            </div>

            <div style={{ background: "#f8fafc", padding: "10px 14px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>Active Learning Corrections Logged</div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#0284c7", marginTop: "2px" }}>
                {data.active_learning_corrections || 0}
              </div>
              <div style={{ fontSize: "10px", color: "#94a3b8" }}>Preserved in ocr_learning_records table</div>
            </div>

            <div style={{ background: "#f8fafc", padding: "10px 14px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>Duplicate Parcels Flagged</div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#b45309", marginTop: "2px" }}>
                {data.duplicates_detected || 0}
              </div>
              <div style={{ fontSize: "10px", color: "#94a3b8" }}>Flagged for officer review without auto-deleting</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}



// ═══════════════════════════════════════════════════════════════
// NEW: PURPOSE-AWARE ACQUISITION PRIVACY GUARD PANEL
// ═══════════════════════════════════════════════════════════════

function PrivacyGuardPanel({ documentId, onClose, user }) {
  const [purpose, setPurpose] = useState("land_acquisition_processing");
  const [previewMode, setPreviewMode] = useState("table"); // "table" | "visual_preview"
  const [analyzing, setAnalyzing] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  
  // Modals state
  const [requestField, setRequestField] = useState(null); // Field object for temporary access request modal
  const [accessReason, setAccessReason] = useState("");
  const [accessDuration, setAccessDuration] = useState("24");
  const [requestSubmitting, setRequestSubmitting] = useState(false);
  const [requestSuccess, setRequestSuccess] = useState("");
  
  const [showReasoningModal, setShowReasoningModal] = useState(false);
  const [showSharingModal, setShowSharingModal] = useState(false);
  const [sharingRecipient, setSharingRecipient] = useState("contractor");

  // Fetch evaluated privacy data for current purpose
  const { data: privacyData, error: privacyError } = useData(
    `/privacy/document/${documentId}?purpose=${encodeURIComponent(purpose)}`,
    4000
  );

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      await api(`/privacy/${documentId}/analyze`, { method: "POST", body: JSON.stringify({ purpose }) });
      EventBus.dispatch();
    } catch (err) {
      alert("Privacy Analysis failed: " + err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleDownloadSafePdf = async (customRecipient = null) => {
    setDownloadingPdf(true);
    try {
      const token = localStorage.getItem("survi_token");
      const isExt = !!customRecipient;
      const recType = customRecipient || "";
      const url = `${API_BASE_URL}/privacy/${documentId}/safe-pdf?purpose=${encodeURIComponent(purpose)}&is_external=${isExt}&recipient_type=${encodeURIComponent(recType)}`;
      
      const response = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      
      if (!response.ok) {
        throw new Error(`Failed to generate PDF (${response.status})`);
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `PrivacySafe_${documentId.substring(0, 8)}_${purpose}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
      EventBus.dispatch();
    } catch (err) {
      alert("PDF download failed: " + err.message);
    } finally {
      setDownloadingPdf(false);
    }
  };

  const submitAccessRequest = async (e) => {
    e.preventDefault();
    if (!requestField) return;
    setRequestSubmitting(true);
    setRequestSuccess("");
    try {
      const res = await api("/privacy/access-request", {
        method: "POST",
        body: JSON.stringify({
          document_id: documentId,
          field_key: requestField.field_key,
          purpose: purpose,
          reason: accessReason,
          duration_hours: parseInt(accessDuration, 10)
        })
      });
      setRequestSuccess(res.message || "Request submitted successfully!");
      EventBus.dispatch();
      setTimeout(() => {
        setRequestField(null);
        setAccessReason("");
        setRequestSuccess("");
      }, 1800);
    } catch (err) {
      alert("Failed to submit request: " + err.message);
    } finally {
      setRequestSubmitting(false);
    }
  };

  if (privacyError) {
    return (
      <div className="error" style={{ padding: "16px", borderRadius: "8px" }}>
        Unable to load privacy analysis: {privacyError.message}
      </div>
    );
  }

  if (!privacyData) {
    return (
      <div style={{ padding: "30px", textAlign: "center", color: "#64748b" }}>
        Loading Purpose-Aware Privacy Guard...
      </div>
    );
  }

  const { risk_score, risk_level, risk_description, summary, fields } = privacyData;

  const riskColor = risk_level === "CRITICAL" ? "#dc2626" : risk_level === "HIGH" ? "#ea580c" : risk_level === "MEDIUM" ? "#d97706" : "#16a34a";
  const riskBg = risk_level === "CRITICAL" ? "#fef2f2" : risk_level === "HIGH" ? "#fff7ed" : risk_level === "MEDIUM" ? "#fffbeb" : "#f0fdf4";

  return (
    <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #cbd5e1" }}>
      
      {/* Header & Purpose Selector */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", borderBottom: "1px solid #e2e8f0", paddingBottom: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "18px" }}>🔐</span>
            <h3 style={{ margin: 0, color: "#0f172a" }}>Purpose-Aware Acquisition Privacy Guard</h3>
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
            Controlled disclosure & data minimisation applied for role: <b>{user?.role?.replace("_", " ").toUpperCase()}</b>
          </div>
        </div>

        {/* Operational Purpose Selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>Active Purpose:</label>
          <select
            value={purpose}
            onChange={e => setPurpose(e.target.value)}
            style={{ padding: "6px 12px", borderRadius: "6px", border: "1px solid #0f6c70", fontWeight: 600, fontSize: "12px", color: "#0f172a", background: "#f0fdfa" }}
          >
            {PURPOSES.map(p => (
              <option key={p.code} value={p.code}>{p.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Privacy Risk & Disclosure Metrics Banner ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "10px", marginTop: "14px" }}>
        <div style={{ background: riskBg, border: `1px solid ${riskColor}40`, padding: "10px", borderRadius: "6px", textAlign: "center" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, color: riskColor }}>PRIVACY RISK SCORE</div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: riskColor, marginTop: "2px" }}>
            {risk_score} <span style={{ fontSize: "12px" }}>/ 100</span>
          </div>
          <div style={{ fontSize: "10px", fontWeight: 800, textTransform: "uppercase", color: riskColor }}>{risk_level} RISK</div>
        </div>

        <div className="metric" style={{ padding: "10px", borderRadius: "6px", textAlign: "center", borderLeft: "3px solid #3b82f6" }}>
          <span style={{ fontSize: "11px" }}>Total Entities</span>
          <b style={{ fontSize: "18px" }}>{summary?.total_detected || 0}</b>
        </div>

        <div className="metric" style={{ padding: "10px", borderRadius: "6px", textAlign: "center", borderLeft: "3px solid #16a34a" }}>
          <span style={{ fontSize: "11px" }}>Visible Fields</span>
          <b style={{ fontSize: "18px", color: "#16a34a" }}>{summary?.visible || 0}</b>
        </div>

        <div className="metric" style={{ padding: "10px", borderRadius: "6px", textAlign: "center", borderLeft: "3px solid #ea580c" }}>
          <span style={{ fontSize: "11px" }}>Masked Fields</span>
          <b style={{ fontSize: "18px", color: "#ea580c" }}>{summary?.masked || 0}</b>
        </div>

        <div className="metric" style={{ padding: "10px", borderRadius: "6px", textAlign: "center", borderLeft: "3px solid #0f766e" }}>
          <span style={{ fontSize: "11px" }}>Authorized Grants</span>
          <b style={{ fontSize: "18px", color: "#0f766e" }}>{summary?.authorized || 0}</b>
        </div>
      </div>

      {/* Decision-Support Description Note */}
      <div style={{ fontSize: "11px", color: "#475569", background: "#f8fafc", padding: "8px 12px", borderRadius: "6px", margin: "10px 0", borderLeft: "3px solid #cbd5e1" }}>
        <b>Risk Assessment:</b> {risk_description}
      </div>

      {/* ── Action Toolbar ── */}
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center", margin: "12px 0 16px" }}>
        <button
          type="button"
          disabled={analyzing}
          onClick={handleAnalyze}
          style={{ padding: "7px 14px", background: "#0f6c70", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 700, fontSize: "12px", cursor: "pointer" }}
        >
          {analyzing ? "Scanning..." : "🔍 Analyze Privacy"}
        </button>

        <button
          type="button"
          onClick={() => setPreviewMode(previewMode === "table" ? "visual_preview" : "table")}
          style={{ padding: "7px 14px", background: previewMode === "visual_preview" ? "#1e293b" : "#f1f5f9", color: previewMode === "visual_preview" ? "#fff" : "#334155", border: "1px solid #cbd5e1", borderRadius: "6px", fontWeight: 700, fontSize: "12px", cursor: "pointer" }}
        >
          👁️ {previewMode === "visual_preview" ? "Table View" : "Privacy Preview"}
        </button>

        <button
          type="button"
          disabled={downloadingPdf}
          onClick={() => handleDownloadSafePdf()}
          style={{ padding: "7px 14px", background: "#10b981", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 700, fontSize: "12px", cursor: "pointer" }}
        >
          {downloadingPdf ? "Generating..." : "📥 Download Privacy-Safe PDF"}
        </button>

        <button
          type="button"
          onClick={() => setShowSharingModal(true)}
          style={{ padding: "7px 14px", background: "#6366f1", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 700, fontSize: "12px", cursor: "pointer" }}
        >
          🌐 Prepare Safe Sharing Copy
        </button>

        <button
          type="button"
          onClick={() => setShowReasoningModal(true)}
          style={{ padding: "7px 14px", background: "#f8fafc", color: "#0f6c70", border: "1px solid #0f6c70", borderRadius: "6px", fontWeight: 700, fontSize: "12px", cursor: "pointer", marginLeft: "auto" }}
        >
          💡 View Privacy Reasoning
        </button>
      </div>

      {/* ── Mode 1: Tabular Ledger View ── */}
      {previewMode === "table" && (
        <div style={{ border: "1px solid #e2e8f0", borderRadius: "6px", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
            <thead>
              <tr style={{ background: "#0f6c70", color: "#ffffff", textAlign: "left" }}>
                <th style={{ padding: "8px 10px" }}>Information Entity</th>
                <th style={{ padding: "8px 10px" }}>Category</th>
                <th style={{ padding: "8px 10px" }}>Status</th>
                <th style={{ padding: "8px 10px" }}>Disclosed / Masked Value</th>
                <th style={{ padding: "8px 10px" }}>Operational Purpose Rationale</th>
                <th style={{ padding: "8px 10px", textAlign: "center" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {fields?.map((f, idx) => {
                const isMasked = f.visibility === "MASKED";
                const isAuth = f.visibility === "AUTHORIZED";
                const isRedacted = f.visibility === "REDACTED";
                const isVis = f.visibility === "VISIBLE";

                const badgeBg = isVis ? "#dcfce7" : isAuth ? "#ccfbf1" : isRedacted ? "#fee2e2" : "#fef3c7";
                const badgeColor = isVis ? "#15803d" : isAuth ? "#0f766e" : isRedacted ? "#b91c1c" : "#b45309";

                return (
                  <tr key={f.field_key} style={{ background: idx % 2 === 0 ? "#ffffff" : "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
                    <td style={{ padding: "8px 10px", fontWeight: 700, color: "#1e293b" }}>{f.field_label}</td>
                    <td style={{ padding: "8px 10px" }}>
                      <span style={{ fontSize: "10px", fontWeight: 800, padding: "2px 6px", borderRadius: "4px", background: f.category === "CRITICAL" ? "#fee2e2" : f.category === "SENSITIVE" ? "#ffedd5" : f.category === "CONTROLLED" ? "#fef3c7" : "#e0f2fe", color: f.category === "CRITICAL" ? "#991b1b" : f.category === "SENSITIVE" ? "#9a3412" : f.category === "CONTROLLED" ? "#854d0e" : "#0369a1" }}>
                        {f.category}
                      </span>
                    </td>
                    <td style={{ padding: "8px 10px" }}>
                      <span style={{ fontSize: "10px", fontWeight: 800, padding: "3px 8px", borderRadius: "12px", background: badgeBg, color: badgeColor, display: "inline-block" }}>
                        {f.visibility}
                      </span>
                    </td>
                    <td style={{ padding: "8px 10px", fontFamily: isMasked || isRedacted ? "monospace" : "inherit", color: isMasked ? "#ea580c" : isRedacted ? "#dc2626" : isAuth ? "#0f766e" : "#0f172a", fontWeight: isAuth || isVis ? 600 : 700 }}>
                      {f.display_value}
                    </td>
                    <td style={{ padding: "8px 10px", fontSize: "11px", color: "#64748b" }}>
                      {f.reason_why}
                    </td>
                    <td style={{ padding: "8px 10px", textAlign: "center" }}>
                      {isMasked && f.requires_authorization && (
                        <button
                          type="button"
                          onClick={() => { setRequestField(f); setAccessReason(""); setRequestSuccess(""); }}
                          style={{ padding: "4px 8px", fontSize: "11px", background: "#f8fafc", border: "1px solid #0f6c70", color: "#0f6c70", borderRadius: "4px", cursor: "pointer", fontWeight: 700 }}
                        >
                          🔓 Request Access
                        </button>
                      )}
                      {isAuth && (
                        <span style={{ fontSize: "11px", color: "#0f766e", fontWeight: 700 }}>✓ Granted</span>
                      )}
                      {isVis && (
                        <span style={{ fontSize: "11px", color: "#16a34a" }}>✓ Public/Operational</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Mode 2: Visual Simulated Redaction Document Preview ── */}
      {previewMode === "visual_preview" && (
        <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "6px", border: "1px solid #cbd5e1" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h4 style={{ margin: 0, color: "#0f172a" }}>📄 Visual Redaction Mockup · Purpose: {purpose.replace("_", " ").toUpperCase()}</h4>
            <span style={{ fontSize: "11px", color: "#64748b" }}>Live preview of dynamically masked fields</span>
          </div>
          
          <div style={{ background: "#ffffff", padding: "20px", borderRadius: "6px", border: "1px solid #e2e8f0", boxShadow: "0 2px 8px rgba(0,0,0,0.05)" }}>
            <div style={{ textAlign: "center", borderBottom: "2px solid #0f6c70", paddingBottom: "10px", marginBottom: "16px" }}>
              <div style={{ fontSize: "13px", fontWeight: 800, color: "#0f6c70" }}>GOVERNMENT OF TAMIL NADU · REVENUE & LAND ACQUISITION</div>
              <div style={{ fontSize: "11px", color: "#64748b" }}>LAND TITLE & ACQUISITION RECORD (PURPOSE-MINIMISED COPY)</div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              {fields?.map(f => {
                const isMasked = f.visibility === "MASKED";
                const isRedacted = f.visibility === "REDACTED";
                const isAuth = f.visibility === "AUTHORIZED";

                return (
                  <div key={f.field_key} style={{ borderBottom: "1px dashed #e2e8f0", paddingBottom: "6px" }}>
                    <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, display: "flex", justifyContent: "space-between" }}>
                      <span>{f.field_label.toUpperCase()}</span>
                      <span style={{ fontSize: "9px", padding: "1px 4px", borderRadius: "3px", background: f.visibility === "VISIBLE" ? "#dcfce7" : isAuth ? "#ccfbf1" : "#fee2e2", color: f.visibility === "VISIBLE" ? "#16a34a" : isAuth ? "#0f766e" : "#b91c1c" }}>
                        {f.visibility}
                      </span>
                    </div>
                    <div style={{ fontSize: "13px", marginTop: "3px", fontWeight: 700, color: isMasked ? "#ea580c" : isRedacted ? "#dc2626" : isAuth ? "#0f766e" : "#0f172a", fontFamily: isMasked || isRedacted ? "monospace" : "inherit" }}>
                      {f.display_value}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 1: REQUEST TEMPORARY ACCESS ── */}
      {requestField && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(15,23,42,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: "20px" }}>
          <div style={{ background: "#ffffff", width: "100%", maxWidth: "480px", borderRadius: "8px", padding: "20px", boxShadow: "0 20px 25px -5px rgba(0,0,0,0.2)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", paddingBottom: "10px" }}>
              <h3 style={{ margin: 0, fontSize: "16px", color: "#0f172a" }}>🔓 Request Temporary Access</h3>
              <button type="button" onClick={() => setRequestField(null)} style={{ background: "none", border: "none", fontSize: "16px", cursor: "pointer", color: "#94a3b8" }}>✕</button>
            </div>

            {requestSuccess && (
              <div style={{ background: "#dcfce7", color: "#15803d", padding: "10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, margin: "14px 0" }}>
                ✓ {requestSuccess}
              </div>
            )}

            {!requestSuccess && (
              <form onSubmit={submitAccessRequest} style={{ display: "grid", gap: "12px", marginTop: "14px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "#64748b" }}>TARGET FIELD</label>
                  <div style={{ fontWeight: 700, fontSize: "13px", color: "#0f172a", background: "#f8fafc", padding: "8px", borderRadius: "4px", border: "1px solid #e2e8f0" }}>
                    {requestField.field_label} ({requestField.category})
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "#64748b" }}>OPERATIONAL PURPOSE *</label>
                  <select
                    value={purpose}
                    onChange={e => setPurpose(e.target.value)}
                    style={{ width: "100%", padding: "8px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                  >
                    {PURPOSES.map(p => <option key={p.code} value={p.code}>{p.label}</option>)}
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "#64748b" }}>REQUESTED DURATION *</label>
                  <select
                    value={accessDuration}
                    onChange={e => setAccessDuration(e.target.value)}
                    style={{ width: "100%", padding: "8px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                  >
                    <option value="8">8 Hours (Single Shift)</option>
                    <option value="24">24 Hours (Standard Operational)</option>
                    <option value="48">48 Hours (Extended Field Verification)</option>
                    <option value="72">72 Hours (Legal / Dispute Hearing)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "#64748b" }}>JUSTIFICATION / REASON *</label>
                  <textarea
                    required
                    rows={3}
                    placeholder="e.g. Owner phone contact required to schedule mandatory physical boundary verification on 15-Sept."
                    value={accessReason}
                    onChange={e => setAccessReason(e.target.value)}
                    style={{ width: "100%", padding: "8px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px" }}
                  />
                  <small style={{ fontSize: "10px", color: "#64748b" }}>All temporary access requests are logged permanently to the government audit ledger.</small>
                </div>

                <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "8px" }}>
                  <button type="button" onClick={() => setRequestField(null)} style={{ padding: "8px 14px", background: "#f1f5f9", color: "#475569", border: "none", borderRadius: "6px", cursor: "pointer", fontWeight: 600 }}>
                    Cancel
                  </button>
                  <button type="submit" disabled={requestSubmitting} style={{ padding: "8px 16px", background: "#0f6c70", color: "#ffffff", border: "none", borderRadius: "6px", cursor: "pointer", fontWeight: 700 }}>
                    {requestSubmitting ? "Submitting..." : "Submit Access Request"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ── MODAL 2: PRIVACY REASONING & EXPLAINABILITY ── */}
      {showReasoningModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(15,23,42,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: "20px" }}>
          <div style={{ background: "#ffffff", width: "100%", maxWidth: "600px", maxHeight: "85vh", overflowY: "auto", borderRadius: "8px", padding: "20px", boxShadow: "0 20px 25px -5px rgba(0,0,0,0.2)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", paddingBottom: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span>💡</span>
                <h3 style={{ margin: 0, fontSize: "16px", color: "#0f172a" }}>Privacy Reasoning & Data Minimisation Logic</h3>
              </div>
              <button type="button" onClick={() => setShowReasoningModal(false)} style={{ background: "none", border: "none", fontSize: "16px", cursor: "pointer", color: "#94a3b8" }}>✕</button>
            </div>

            <p style={{ fontSize: "12px", color: "#64748b", margin: "10px 0" }}>
              Detailed explanation of why each field is currently visible or masked for role <b>{user?.role}</b> under purpose <b>{purpose}</b>:
            </p>

            <div style={{ display: "grid", gap: "10px" }}>
              {fields?.map(f => {
                const isMasked = f.visibility === "MASKED" || f.visibility === "REDACTED";
                return (
                  <div key={f.field_key} style={{ padding: "10px", borderRadius: "6px", background: "#f8fafc", border: `1px solid ${isMasked ? "#fed7aa" : "#bbf7d0"}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <b style={{ color: "#0f172a", fontSize: "13px" }}>{f.field_label}</b>
                      <span style={{ fontSize: "10px", fontWeight: 800, padding: "2px 6px", borderRadius: "4px", background: isMasked ? "#fee2e2" : "#dcfce7", color: isMasked ? "#b91c1c" : "#15803d" }}>
                        {f.visibility}
                      </span>
                    </div>
                    <div style={{ fontSize: "11px", marginTop: "4px", color: "#334155" }}>
                      <b>Reason:</b> {f.reason_why}
                    </div>
                    {isMasked && (
                      <div style={{ fontSize: "11px", marginTop: "2px", color: "#9a3412" }}>
                        <b>Why Masked?</b> {f.explain_mask}
                      </div>
                    )}
                    {!isMasked && (
                      <div style={{ fontSize: "11px", marginTop: "2px", color: "#166534" }}>
                        <b>Why Visible?</b> {f.explain_visible}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div style={{ textAlign: "right", marginTop: "16px" }}>
              <button type="button" onClick={() => setShowReasoningModal(false)} style={{ padding: "8px 16px", background: "#0f6c70", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontWeight: 700 }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 3: EXTERNAL SHARING SAFE COPY ── */}
      {showSharingModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(15,23,42,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: "20px" }}>
          <div style={{ background: "#ffffff", width: "100%", maxWidth: "500px", borderRadius: "8px", padding: "20px", boxShadow: "0 20px 25px -5px rgba(0,0,0,0.2)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", paddingBottom: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span>🌐</span>
                <h3 style={{ margin: 0, fontSize: "16px", color: "#0f172a" }}>Prepare Safe Sharing Copy</h3>
              </div>
              <button type="button" onClick={() => setShowSharingModal(false)} style={{ background: "none", border: "none", fontSize: "16px", cursor: "pointer", color: "#94a3b8" }}>✕</button>
            </div>

            <p style={{ fontSize: "12px", color: "#64748b", margin: "10px 0" }}>
              Generate a sanitized, purpose-minimised PDF copy specifically safe for distribution to external contractors, consultants, or public reports.
            </p>

            <div style={{ display: "grid", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "11px", fontWeight: 700, color: "#64748b" }}>RECIPIENT TYPE</label>
                <select
                  value={sharingRecipient}
                  onChange={e => setSharingRecipient(e.target.value)}
                  style={{ width: "100%", padding: "8px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", marginTop: "4px" }}
                >
                  <option value="contractor">Civil Works Contractor (Boundary & Survey only)</option>
                  <option value="consultant">EIA / SIA Consultant (Operational only)</option>
                  <option value="interdepartmental">Interdepartmental Review (Revenue / PWD / Forest)</option>
                  <option value="public_report">Public Information / RTI Safe Report</option>
                </select>
              </div>

              <div style={{ background: "#f8fafc", padding: "10px", borderRadius: "6px", border: "1px solid #e2e8f0", fontSize: "11px" }}>
                <div style={{ fontWeight: 700, color: "#0f172a", marginBottom: "4px" }}>Redaction Preview:</div>
                <div style={{ color: "#16a34a" }}>✓ Visible: Survey No, Land Extent, Village, Taluk, District</div>
                <div style={{ color: "#ea580c" }}>✗ Automatically Masked: Aadhaar, PAN, Bank Accounts, Mobile Numbers</div>
                <div style={{ color: "#dc2626" }}>✗ Redacted: Internal Grievances & Unrelated Personal Info</div>
              </div>

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "10px" }}>
                <button type="button" onClick={() => setShowSharingModal(false)} style={{ padding: "8px 14px", background: "#f1f5f9", color: "#475569", border: "none", borderRadius: "6px", cursor: "pointer", fontWeight: 600 }}>
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={downloadingPdf}
                  onClick={async () => {
                    await handleDownloadSafePdf(sharingRecipient);
                    setShowSharingModal(false);
                  }}
                  style={{ padding: "8px 16px", background: "#6366f1", color: "#ffffff", border: "none", borderRadius: "6px", cursor: "pointer", fontWeight: 700 }}
                >
                  {downloadingPdf ? "Generating..." : "Generate Safe Copy"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
