import React, { useEffect, useState, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle, Polygon, CircleMarker } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import icon from "leaflet/dist/images/marker-icon.png";
import iconShadow from "leaflet/dist/images/marker-shadow.png";
import iconRetina from "leaflet/dist/images/marker-icon-2x.png";
import DocumentsPage from "./DocumentsPage";
import DataQualityPage from "./DataQualityPage";
import { DSSCard, DSSBadge, AskAiModal } from "./components/DSSCard";
import TutorialEngine from "./components/TutorialEngine";
import { api, API_BASE_URL as API, EventBus } from "./api";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: iconRetina,
  iconUrl: icon,
  shadowUrl: iconShadow,
});

const AUTH_LOGIN_PATH = "/auth/login";
const AUTH_ME_PATH = "/auth/me";

const DISTRICTS = ["Coimbatore", "Tiruppur", "Erode", "Salem", "Namakkal"];
const DISTRICT_CENTROIDS = {
  Coimbatore: [11.0168, 76.9558],
  Tiruppur: [11.1085, 77.3411],
  Erode: [11.3410, 77.7172],
  Salem: [11.6643, 78.1460],
  Namakkal: [11.2189, 78.1674],
  Palakkad: [10.7867, 76.6548],
  Ernakulam: [9.9816, 76.2999],
  Thrissur: [10.5276, 76.2144],
  Thiruvananthapuram: [8.5241, 76.9366],
  all: [11.1271, 77.8500],
  "All Districts": [11.1271, 77.8500]
};

const TALUK_CENTROIDS = {
  Annur: [11.2330, 77.1060],
  "Coimbatore North": [11.0500, 76.9600],
  "Coimbatore South": [10.9800, 76.9600],
  Kinathukadavu: [10.8200, 77.0200],
  Madukkarai: [10.9000, 76.9500],
  Mettupalayam: [11.3000, 76.9500],
  Perur: [10.9500, 76.9000],
  Sulur: [11.0300, 77.1300]
};

const nav = [
  ["dashboard", "Command Center"], ["state_dashboard", "State Authority Dashboard"], 
  ["district_dashboard", "District Authority Dashboard"], ["projects", "Projects"], 
  ["parcels", "Land Parcels"], ["data_quality", "Data Quality & Verification"], ["gis", "GIS Intelligence"], ["workflow", "Acquisition Workflow"], 
  ["sla", "SLA & Timeline"], ["bottlenecks", "Bottleneck Detection"], ["field", "Field Verification"], 
  ["documents", "Documents / OCR"], ["risk", "Risk Intelligence"], ["alerts", "Alerts"], 
  ["sms_centre", "📱 SMS Notification Centre"],
  ["analytics", "Analytics"], ["intelligence", "Advanced Intelligence"], ["reports", "Reports / MIS"], ["grievances", "Grievances"], 
  ["rr", "R&R Workflow"],
  ["ml", "ML Monitoring"], ["users", "Users"], ["audit", "Audit Trail"], ["citizen_dash", "Citizen View"]
];
const tamil = { "Command Center": "கட்டளை மையம்", "Projects": "திட்டங்கள்", "Land Parcels": "நிலப்பகுதிகள்", "Data Quality & Verification": "தர மதிப்பீடு மற்றும் சரிபார்ப்பு", "GIS Intelligence": "GIS நுண்ணறிவு", "Acquisition Workflow": "கையகப்படுத்தல் பணிப்பாய்வு", "SLA & Timeline": "SLA மற்றும் காலவரிசை", "Bottleneck Detection": "தாமதங்களை கண்டறிதல்", "Field Verification": "கள சரிபார்ப்பு", "Documents / OCR": "ஆவணங்கள் / OCR", "Risk Intelligence": "இடர் நுண்ணறிவு", "Alerts": "எச்சரிக்கைகள்", "📱 SMS Notification Centre": "📱 எஸ்எம்எஸ் அறிவிப்பு மையம்", "SMS Notification Centre": "எஸ்எம்எஸ் அறிவிப்பு மையம்", "Analytics": "பகுப்பாய்வு", "Advanced Intelligence": "மேம்பட்ட நுண்ணறிவு", "Reports / MIS": "அறிக்கைகள்", "Grievances": "குறைகள்", "R&R Workflow": "மறுவாழ்வு பணிப்பாய்வு", "ML Monitoring": "ML கண்காணிப்பு", "Users": "பயனர்கள்", "Audit Trail": "தணிக்கை பதிவு", "Citizen View": "குடிமக்கள் பார்வை" };


function Login({ onLogin }) {
  const [mode, setMode] = useState("official"); // "official" | "citizen_login" | "citizen_register"
  const [e, setE] = useState("district.coimbatore@tngov.in");
  const [p, setP] = useState("Tngov@CBE#2026");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  // Citizen Registration Form State
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regPhone, setRegPhone] = useState("");
  const [regSurveyNo, setRegSurveyNo] = useState("");
  const [regDistrict, setRegDistrict] = useState("Coimbatore");
  const [regSuccess, setRegSuccess] = useState("");

  const handleLogin = async (loginEmail, loginPwd) => {
    const cleanEmail = (loginEmail || "").trim();
    const cleanPwd = loginPwd || "";
    if (!cleanEmail) {
      setErr("Please enter your official or registered email address.");
      return;
    }
    if (!cleanPwd) {
      setErr("Please enter your password.");
      return;
    }
    setLoading(true); setErr(""); setRegSuccess("");
    try {
      let x = await api(AUTH_LOGIN_PATH, { method: "POST", body: JSON.stringify({ email: cleanEmail, password: cleanPwd }) });
      if (!x || !x.access_token || !x.user) {
        throw Error("Login succeeded but no user session was returned by the server.");
      }
      localStorage.setItem("survi_token", x.access_token);
      onLogin(x.user);
    } catch (x) { setErr(x.message || "Login failed. Please check your credentials and try again."); }
    finally { setLoading(false); }
  };

  const handleCitizenRegister = async (ev) => {
    ev.preventDefault();
    setLoading(true); setErr(""); setRegSuccess("");
    try {
      let x = await api("/auth/citizen/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: (regName || "").trim(),
          email: (regEmail || "").trim(),
          password: regPassword,
          phone: (regPhone || "").trim(),
          survey_no: (regSurveyNo || "").trim(),
          district: (regDistrict || "").trim()
        })
      });
      if (!x || !x.access_token || !x.user) {
        throw Error("Registration succeeded but no user session was returned.");
      }
      setRegSuccess("Account registered and linked to verified land parcel! Logging in...");
      localStorage.setItem("survi_token", x.access_token);
      setTimeout(() => onLogin(x.user), 1000);
    } catch (x) {
      setErr(x.message || "Registration failed. Verification required.");
    } finally {
      setLoading(false);
    }
  };

  const selectPreset = (email, pwd = "Tngov@CBE#2026") => {
    setE(email);
    setP(pwd);
    setErr("");
    setRegSuccess("");
  };

  return (
    <div className="login">
      <div className="login-card" style={{ maxWidth: "520px" }}>
        <div className="brand-mark">L</div>
        <h1 style={{ margin: "4px 0" }}>LANDNEXUS</h1>
        <p style={{ color: "#64748b", fontSize: "13px", marginTop: 0 }}>
          {mode === "official" ? "State & District Authority Land Acquisition Intelligence" : "Citizen Land Acquisition & R&R Portal"}
        </p>

        {/* Mode Switcher Tabs */}
        <div style={{ display: "flex", background: "#e2e8f0", borderRadius: "8px", padding: "3px", marginBottom: "16px" }}>
          <button
            type="button"
            onClick={() => { setMode("official"); setE("district.coimbatore@tngov.in"); setP("Tngov@CBE#2026"); setErr(""); setRegSuccess(""); }}
            style={{
              flex: 1, padding: "8px", border: "none", borderRadius: "6px", cursor: "pointer",
              fontWeight: 700, fontSize: "12px",
              background: mode === "official" ? "#ffffff" : "transparent",
              color: mode === "official" ? "#0f172a" : "#64748b",
              boxShadow: mode === "official" ? "0 1px 3px rgba(0,0,0,0.1)" : "none"
            }}
          >
            🏛️ Official Login
          </button>
          <button
            type="button"
            onClick={() => { setMode("citizen_login"); setE("citizen@cbe.ac.in"); setP("Tngov@CBE#2026"); setErr(""); setRegSuccess(""); }}
            style={{
              flex: 1, padding: "8px", border: "none", borderRadius: "6px", cursor: "pointer",
              fontWeight: 700, fontSize: "12px",
              background: mode.startsWith("citizen") ? "#ffffff" : "transparent",
              color: mode.startsWith("citizen") ? "#0f172a" : "#64748b",
              boxShadow: mode.startsWith("citizen") ? "0 1px 3px rgba(0,0,0,0.1)" : "none"
            }}
          >
            👤 Citizen Portal
          </button>
        </div>

        {err && <div className="error" style={{ marginBottom: "12px", textAlign: "left" }}>{err}</div>}
        {regSuccess && <div style={{ background: "#e6f4ea", color: "#16704a", padding: "10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, marginBottom: "12px" }}>{regSuccess}</div>}

        {/* Mode 1: Official Login */}
        {mode === "official" && (
          <form onSubmit={(ev) => { ev.preventDefault(); handleLogin(e, p); }} style={{ textAlign: "left" }}>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155", display: "block", marginBottom: "4px" }}>
              Official Email Address
            </label>
            <input value={e} onChange={x => setE(x.target.value)} placeholder="Official email (e.g. district.coimbatore@tngov.in)" style={{ width: "100%", marginBottom: "10px" }} />
            
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155", display: "block", marginBottom: "4px" }}>
              Secure Password
            </label>
            <input type="password" value={p} onChange={x => setP(x.target.value)} placeholder="Password (Default: Tngov@CBE#2026)" style={{ width: "100%", marginBottom: "12px" }} />
            
            <button type="submit" disabled={loading} style={{ width: "100%", padding: "10px", fontSize: "13px", fontWeight: 700 }}>
              {loading ? "Authenticating Official..." : "Secure Login"}
            </button>

            {/* Quick 1-Click Role Fill Buttons */}
            <div style={{ fontSize: "11px", color: "#475569", marginTop: "14px", lineHeight: "1.6", background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontWeight: 800, color: "#0f172a", marginBottom: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span>⚡ 1-Click Role Presets (Pass: Tngov@CBE#2026)</span>
              </div>

              {/* National & State Authorities */}
              <div style={{ fontSize: "10px", fontWeight: 800, color: "#64748b", textTransform: "uppercase", marginBottom: "4px" }}>National & State Authorities:</div>
              <div style={{ display: "flex", gap: "5px", flexWrap: "wrap", marginBottom: "8px" }}>
                <button type="button" onClick={() => selectPreset("national.admin@landnexus.gov")} style={{ padding: "4px 8px", fontSize: "10.5px", background: e === "national.admin@landnexus.gov" ? "#2563eb" : "#eff6ff", color: e === "national.admin@landnexus.gov" ? "#ffffff" : "#1d4ed8", border: "1px solid #bfdbfe", borderRadius: "4px", cursor: "pointer", fontWeight: 600 }}>
                  🌐 National Authority
                </button>
                <button type="button" onClick={() => selectPreset("state.tamilnadu@tngov.in")} style={{ padding: "4px 8px", fontSize: "10.5px", background: e === "state.tamilnadu@tngov.in" ? "#0f766e" : "#f0fdfa", color: e === "state.tamilnadu@tngov.in" ? "#ffffff" : "#0f766e", border: "1px solid #99f6e4", borderRadius: "4px", cursor: "pointer", fontWeight: 600 }}>
                  🏛️ State (Tamil Nadu)
                </button>
                <button type="button" onClick={() => selectPreset("state.kerala@kerala.gov.in")} style={{ padding: "4px 8px", fontSize: "10.5px", background: e === "state.kerala@kerala.gov.in" ? "#0f766e" : "#f0fdfa", color: e === "state.kerala@kerala.gov.in" ? "#ffffff" : "#0f766e", border: "1px solid #99f6e4", borderRadius: "4px", cursor: "pointer", fontWeight: 600 }}>
                  🌴 State (Kerala)
                </button>
                <button type="button" onClick={() => selectPreset("admin@survi.gov.in")} style={{ padding: "4px 8px", fontSize: "10.5px", background: e === "admin@survi.gov.in" ? "#475569" : "#f1f5f9", color: e === "admin@survi.gov.in" ? "#ffffff" : "#334155", border: "1px solid #cbd5e1", borderRadius: "4px", cursor: "pointer", fontWeight: 600 }}>
                  ⚙️ Admin
                </button>
              </div>

              {/* District Authorities */}
              <div style={{ fontSize: "10px", fontWeight: 800, color: "#64748b", textTransform: "uppercase", marginBottom: "4px" }}>District Authorities (5 Districts):</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))", gap: "4px", marginBottom: "8px" }}>
                {["coimbatore", "tiruppur", "erode", "salem", "namakkal"].map(dist => {
                  const targetEmail = `district.${dist}@tngov.in`;
                  const isSel = e === targetEmail;
                  return (
                    <button key={dist} type="button" onClick={() => selectPreset(targetEmail)} style={{ padding: "4px 6px", fontSize: "10px", background: isSel ? "#0f6c70" : "#f8fafc", color: isSel ? "#ffffff" : "#0f172a", border: isSel ? "1px solid #0f6c70" : "1px solid #cbd5e1", borderRadius: "4px", cursor: "pointer", fontWeight: 600, textTransform: "capitalize" }}>
                      ★ {dist}
                    </button>
                  );
                })}
              </div>

              {/* Field Officers */}
              <div style={{ fontSize: "10px", fontWeight: 800, color: "#64748b", textTransform: "uppercase", marginBottom: "4px" }}>Field Verification Officers:</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))", gap: "4px", marginBottom: "8px" }}>
                {["coimbatore", "tiruppur", "erode", "salem", "namakkal"].map(dist => {
                  const targetEmail = `field.${dist}@tngov.in`;
                  const isSel = e === targetEmail;
                  return (
                    <button key={dist} type="button" onClick={() => selectPreset(targetEmail)} style={{ padding: "4px 6px", fontSize: "10px", background: isSel ? "#d97706" : "#fffbeb", color: isSel ? "#ffffff" : "#92400e", border: isSel ? "1px solid #d97706" : "1px solid #fde68a", borderRadius: "4px", cursor: "pointer", fontWeight: 600, textTransform: "capitalize" }}>
                      📍 {dist}
                    </button>
                  );
                })}
              </div>

              {/* Acquisition Officers */}
              <div style={{ fontSize: "10px", fontWeight: 800, color: "#64748b", textTransform: "uppercase", marginBottom: "4px" }}>Acquisition Officers:</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))", gap: "4px", marginBottom: "8px" }}>
                {["coimbatore", "tiruppur", "erode", "salem", "namakkal"].map(dist => {
                  const targetEmail = `officer.${dist}@tngov.in`;
                  const isSel = e === targetEmail;
                  return (
                    <button key={dist} type="button" onClick={() => selectPreset(targetEmail)} style={{ padding: "4px 6px", fontSize: "10px", background: isSel ? "#7c3aed" : "#faf5ff", color: isSel ? "#ffffff" : "#6b21a8", border: isSel ? "1px solid #7c3aed" : "1px solid #e9d5ff", borderRadius: "4px", cursor: "pointer", fontWeight: 600, textTransform: "capitalize" }}>
                      📋 {dist}
                    </button>
                  );
                })}
              </div>

              {/* Direct Demo / Preview Helpers */}
              <div style={{ borderTop: "1px solid #e2e8f0", paddingTop: "8px", marginTop: "8px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                <button
                  type="button"
                  onClick={() => {
                    onLogin({
                      email: "district.coimbatore@tngov.in",
                      role: "district_authority",
                      district_scope: "Coimbatore",
                      state_scope: "Tamil Nadu",
                      is_authority: true
                    });
                  }}
                  style={{
                    padding: "6px 8px",
                    background: "#f0fdf4",
                    color: "#166534",
                    border: "1px dashed #22c55e",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontWeight: 700,
                    fontSize: "10.5px"
                  }}
                >
                  ⚡ Direct UI Preview
                </button>
                <button
                  type="button"
                  onClick={() => {
                    localStorage.removeItem("landnexus_tour_completed");
                    onLogin({
                      email: "district.coimbatore@tngov.in",
                      role: "district_authority",
                      district_scope: "Coimbatore",
                      state_scope: "Tamil Nadu",
                      is_authority: true
                    });
                  }}
                  style={{
                    padding: "6px 8px",
                    background: "rgba(6, 182, 212, 0.1)",
                    color: "#0891b2",
                    border: "1px dashed #06b6d4",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontWeight: 700,
                    fontSize: "10.5px"
                  }}
                >
                  🎮 Guided Tour Demo
                </button>
              </div>
            </div>
          </form>
        )}

        {/* Mode 2: Citizen Login */}
        {mode === "citizen_login" && (
          <form onSubmit={(ev) => { ev.preventDefault(); handleLogin(e, p); }} style={{ textAlign: "left" }}>
            <div style={{ marginBottom: "12px", fontSize: "12px", color: "#475569" }}>
              Sign in with your registered citizen email to track your land acquisition compensation, R&R entitlement, and grievances.
            </div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155", display: "block", marginBottom: "4px" }}>
              Registered Citizen Email
            </label>
            <input value={e} onChange={x => setE(x.target.value)} placeholder="Registered email (e.g. citizen@cbe.ac.in)" style={{ width: "100%", marginBottom: "10px" }} />
            
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155", display: "block", marginBottom: "4px" }}>
              Citizen Password
            </label>
            <input type="password" value={p} onChange={x => setP(x.target.value)} placeholder="Password (Default: Tngov@CBE#2026)" style={{ width: "100%", marginBottom: "12px" }} />
            
            <button type="submit" disabled={loading} style={{ width: "100%", padding: "10px", fontSize: "13px", fontWeight: 700, background: "#0f6c70" }}>
              {loading ? "Authenticating Citizen..." : "Citizen Sign-In"}
            </button>

            {/* Demo Citizen Presets */}
            <div style={{ marginTop: "12px", padding: "10px", background: "#f8fafc", borderRadius: "6px", border: "1px solid #e2e8f0", fontSize: "11px" }}>
              <div style={{ fontWeight: 700, color: "#334155", marginBottom: "4px" }}>Demo Landowner Accounts:</div>
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                <button type="button" onClick={() => selectPreset("citizen@cbe.ac.in")} style={{ padding: "4px 8px", fontSize: "10.5px", background: "#f0fdf4", color: "#166534", border: "1px solid #bbf7d0", borderRadius: "4px", cursor: "pointer", fontWeight: 600 }}>
                  👤 citizen@cbe.ac.in
                </button>
                <button type="button" onClick={() => selectPreset("citizen.demo.syn001@example.com")} style={{ padding: "4px 8px", fontSize: "10.5px", background: "#f0fdf4", color: "#166534", border: "1px solid #bbf7d0", borderRadius: "4px", cursor: "pointer", fontWeight: 600 }}>
                  👤 citizen.demo.syn001@example.com
                </button>
              </div>
            </div>

            <div style={{ marginTop: "14px", fontSize: "12px", color: "#475569", textAlign: "center" }}>
              New landowner / affected citizen?{" "}
              <button
                type="button"
                onClick={() => { setMode("citizen_register"); setErr(""); setRegSuccess(""); }}
                style={{ background: "none", border: "none", color: "#0f6c70", fontWeight: 700, cursor: "pointer", textDecoration: "underline" }}
              >
                Register with Survey Number
              </button>
            </div>
          </form>
        )}

        {/* Mode 3: Citizen Self-Registration */}
        {mode === "citizen_register" && (
          <form onSubmit={handleCitizenRegister} style={{ textAlign: "left", display: "grid", gap: "10px" }}>
            <div style={{ fontSize: "12px", color: "#475569", marginBottom: "4px" }}>
              Enter your government survey number and district to link your verified land records.
            </div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155" }}>
              Full Name *
              <input required value={regName} onChange={x => setRegName(x.target.value)} placeholder="Thiru / Tmt. Full Name" style={{ width: "100%", marginTop: "2px" }} />
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
              <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155" }}>
                District *
                <select value={regDistrict} onChange={x => setRegDistrict(x.target.value)} style={{ width: "100%", marginTop: "2px", padding: "8px", borderRadius: "6px", border: "1px solid #cbd5e1" }}>
                  {DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </label>
              <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155" }}>
                Survey Number *
                <input required value={regSurveyNo} onChange={x => setRegSurveyNo(x.target.value)} placeholder="e.g. 100/1/2" style={{ width: "100%", marginTop: "2px" }} />
              </label>
            </div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155" }}>
              Email Address *
              <input type="email" required value={regEmail} onChange={x => setRegEmail(x.target.value)} placeholder="yourname@gmail.com" style={{ width: "100%", marginTop: "2px" }} />
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
              <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155" }}>
                Password *
                <input type="password" required value={regPassword} onChange={x => setRegPassword(x.target.value)} placeholder="Min 6 chars" style={{ width: "100%", marginTop: "2px" }} />
              </label>
              <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155" }}>
                Phone Number
                <input value={regPhone} onChange={x => setRegPhone(x.target.value)} placeholder="+91..." style={{ width: "100%", marginTop: "2px" }} />
              </label>
            </div>
            <button type="submit" disabled={loading} style={{ background: "#0f6c70", marginTop: "6px", padding: "10px", fontWeight: 700 }}>
              {loading ? "Verifying & Registering..." : "Verify & Register Land Record"}
            </button>
            <div style={{ textAlign: "center", marginTop: "6px", fontSize: "12px" }}>
              Already registered?{" "}
              <button
                type="button"
                onClick={() => { setMode("citizen_login"); setErr(""); setRegSuccess(""); }}
                style={{ background: "none", border: "none", color: "#0f6c70", fontWeight: 700, cursor: "pointer", textDecoration: "underline" }}
              >
                Sign In
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function Cards({ d }) {
  const safe = d || {};
  let cards = [
    ["Total Projects", safe.total_projects], ["Active Projects", safe.active_projects], 
    ["Completed Projects", safe.completed_projects], ["Delayed Projects", safe.delayed_projects], 
    ["Total Parcels", safe.total_parcels], ["Affected Families", safe.affected_families], 
    ["High Risk", safe.high_risk_projects], ["Critical", safe.critical_projects], 
    ["Pending Compensation", safe.pending_compensation], ["Paid Compensation", safe.paid_compensation], 
    ["Legal Disputes", safe.legal_disputes], ["SLA Breaches", safe.sla_breaches]
  ];
  return <div className="cards">{cards.map(c => <div className="metric" key={c[0]}><span>{c[0]}</span><b>{c[1] ?? 0}</b></div>)}</div>;
}

function CreateProjectForm({ defaultDistrict = "Coimbatore", onSuccess, onCancel }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    project_id: "PRJ-" + new Date().getFullYear() + "-DIST-" + Math.floor(Math.random()*1000).toString().padStart(3, '0'),
    project_name: "", project_type: "Rail", district: defaultDistrict, taluk: "", village: "",
    land_required: 0, priority: "High", project_start_date: "", planned_completion_date: "",
    description: "", department: "", estimated_project_cost: 0, remarks: ""
  });

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true); setError("");
    try {
      await api("/projects/", { method: "POST", body: JSON.stringify(form) });
      onSuccess();
    } catch (err) {
      setError(err.message || "Failed to create project.");
    }
    setLoading(false);
  };

  return (
    <div style={{ background: "#fff", padding: "20px", border: "1px solid #ddd", marginBottom: "20px", borderRadius: "8px" }}>
      <h3>Create New Project</h3>
      <form onSubmit={submit} className="form" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}>
        <label>Project ID <input value={form.project_id} readOnly style={{ background: "#f5f5f5" }} /></label>
        <label>Project Name* <input required value={form.project_name} onChange={e => setForm({...form, project_name: e.target.value})} /></label>
        <label>Project Type 
          <select value={form.project_type} onChange={e => setForm({...form, project_type: e.target.value})}>
            <option>Rail</option><option>Road</option><option>Airport</option><option>Irrigation</option><option>Industrial</option>
          </select>
        </label>
        <label>District* 
          <select value={form.district} onChange={e => setForm({...form, district: e.target.value})}>
            {DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <label>Taluk* <input required value={form.taluk} onChange={e => setForm({...form, taluk: e.target.value})} /></label>
        <label>Village <input value={form.village} onChange={e => setForm({...form, village: e.target.value})} /></label>
        <label>Est. Land Area (Acres) <input type="number" step="0.01" value={form.land_required} onChange={e => setForm({...form, land_required: parseFloat(e.target.value)})} /></label>
        <label>Priority
          <select value={form.priority} onChange={e => setForm({...form, priority: e.target.value})}>
             <option>High</option><option>Medium</option><option>Low</option>
          </select>
        </label>
        <label>Proposed Start Date <input type="date" value={form.project_start_date} onChange={e => setForm({...form, project_start_date: e.target.value})} /></label>
        <label>Target Completion Date <input type="date" value={form.planned_completion_date} onChange={e => setForm({...form, planned_completion_date: e.target.value})} /></label>
        <label>Department / Agency <input value={form.department} onChange={e => setForm({...form, department: e.target.value})} /></label>
        <label>Est. Project Cost (₹) <input type="number" value={form.estimated_project_cost} onChange={e => setForm({...form, estimated_project_cost: parseFloat(e.target.value)})} /></label>
        <label style={{ gridColumn: "1 / -1" }}>Description <textarea value={form.description} onChange={e => setForm({...form, description: e.target.value})} /></label>
        
        <div style={{ gridColumn: "1 / -1", display: "flex", gap: "10px" }}>
          <button type="submit" disabled={loading}>{loading ? "Saving..." : "Create Project"}</button>
          <button type="button" onClick={onCancel} style={{ background: "#ccc", color: "#333" }}>Cancel</button>
        </div>
      </form>
      {error && <div className="error" style={{ marginTop: "10px" }}>{error}</div>}
    </div>
  );
}

function useData(path, refreshMs = 0) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    if (!path) {
      setData(null);
      setError(null);
      return undefined;
    }
    const fetcher = () => api(path).then(setData).catch(setError);
    fetcher();
    const unsubscribe = EventBus.subscribe(fetcher);
    const timer = refreshMs > 0 ? setInterval(fetcher, refreshMs) : null;
    return () => { unsubscribe(); if (timer) clearInterval(timer); };
  }, [path, refreshMs]);
  return { data, error };
}

function StateDashboard({ user, district, onSelectDistrict }) {
  const userState = user?.state_scope || "Tamil Nadu";
  const [selectedState, setSelectedState] = useState(userState);
  const [selectedDist, setSelectedDist] = useState(district || (userState === "Kerala" ? "Palakkad" : "Coimbatore"));
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    if (district && district !== selectedDist) {
      setSelectedDist(district);
    }
  }, [district]);

  // If user is locked to a state (e.g. Kerala authority or TN authority)
  const canSwitchState = !user?.state_scope || user.role === "authority" || user.role === "admin";

  const { data: d, error: stateErr } = useData(
    `/dashboard/state?state=${encodeURIComponent(selectedState)}${selectedDist ? `&district=${encodeURIComponent(selectedDist)}` : ""}`,
    5000
  );

  const { data: dssState } = useData("/dss/state", 10000);

  const stateDistricts = selectedState === "Kerala" 
    ? ["Palakkad", "Ernakulam", "Thrissur", "Thiruvananthapuram"] 
    : ["Coimbatore", "Tiruppur", "Erode", "Salem", "Namakkal"];

  if (stateErr) return (
    <Panel title="State Authority Dashboard">
      <div className="error">
        Access Denied ({stateErr.status || "Error"}): {stateErr.message || "Cross-state access forbidden."}
      </div>
    </Panel>
  );

  if (!d) return <Panel title={`State Authority Dashboard (${selectedState})`}>Loading…</Panel>;

  let cards = [
    ["Total Projects", d.total_projects], ["Active Projects", d.active_projects],
    ["Completed Projects", d.completed_projects], ["Total Parcels", d.total_parcels],
    ["Affected Families", d.affected_families], ["High Risk", d.high_risk_projects],
    ["Critical", d.critical_projects], ["Pending Compensation", d.pending_compensation],
    ["Legal Disputes", d.legal_disputes], ["Delayed Projects", d.delayed_projects],
    ["SLA Breaches", d.sla_breaches], ["Escalated Cases", d.escalated_cases]
  ];

  return (
    <>
      {/* State Authority Header & State Selector */}
      <div data-tutorial="scope-badge" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <h2 style={{ margin: 0, color: "#0f172a" }}>State Authority Command Center · {selectedState}</h2>
          <div style={{ fontSize: "12px", color: "#64748b", marginTop: "2px" }}>
            State-level monitoring, district performance metrics and bottleneck diagnostics
          </div>
        </div>

        {/* State Selector Buttons (Restricted by user state_scope) */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {canSwitchState ? (
            <div style={{ display: "flex", background: "#e2e8f0", borderRadius: "20px", padding: "3px" }}>
              {["Tamil Nadu", "Kerala"].map(st => {
                const isSel = selectedState === st;
                return (
                  <button
                    key={st}
                    type="button"
                    onClick={() => {
                      setSelectedState(st);
                      const newDist = st === "Kerala" ? "Palakkad" : "Coimbatore";
                      setSelectedDist(newDist);
                      if (onSelectDistrict) onSelectDistrict(newDist);
                    }}
                    style={{
                      background: isSel ? "#0f6c70" : "transparent",
                      color: isSel ? "#ffffff" : "#334155",
                      border: "none",
                      padding: "6px 14px",
                      borderRadius: "16px",
                      fontSize: "12px",
                      fontWeight: 700,
                      cursor: "pointer"
                    }}
                  >
                    {st === "Tamil Nadu" ? "🏛️ Tamil Nadu" : "🌴 Kerala"}
                  </button>
                );
              })}
            </div>
          ) : (
            <div style={{
              background: "#0f6c70", color: "#fff", padding: "6px 14px",
              borderRadius: "20px", fontSize: "12px", fontWeight: 700
            }}>
              🔒 {user.state_scope} (Permanent State Scope)
            </div>
          )}

          {!showCreate && (
            <button
              onClick={() => setShowCreate(true)}
              style={{ background: "#0056b3", color: "white", padding: "8px 16px", borderRadius: "6px" }}
            >
              + Create Project
            </button>
          )}
        </div>
      </div>

      {/* District Filter Pill Bar for this State */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "16px", flexWrap: "wrap" }}>
        <span style={{ fontSize: "11px", fontWeight: 800, color: "#64748b", textTransform: "uppercase" }}>
          Filter District:
        </span>
        <button
          type="button"
          onClick={() => setSelectedDist("")}
          style={{
            background: !selectedDist ? "#0f6c70" : "#ffffff",
            color: !selectedDist ? "#ffffff" : "#334155",
            border: `1px solid ${!selectedDist ? "#0f6c70" : "#cbd5e1"}`,
            padding: "4px 10px", borderRadius: "14px", fontSize: "11px", fontWeight: 700, cursor: "pointer"
          }}
        >
          All {selectedState} Districts
        </button>
        {stateDistricts.map(dName => {
          const isSel = selectedDist === dName;
          return (
            <button
              key={dName}
              type="button"
              onClick={() => {
                setSelectedDist(dName);
                if (onSelectDistrict) onSelectDistrict(dName);
              }}
              style={{
                background: isSel ? "#0f6c70" : "#ffffff",
                color: isSel ? "#ffffff" : "#334155",
                border: `1px solid ${isSel ? "#0f6c70" : "#cbd5e1"}`,
                padding: "4px 10px", borderRadius: "14px", fontSize: "11px", fontWeight: isSel ? 700 : 500, cursor: "pointer"
              }}
            >
              {dName}
            </button>
          );
        })}
      </div>

      {showCreate && (
        <CreateProjectForm
          defaultDistrict={selectedDist || stateDistricts[0]}
          onSuccess={() => setShowCreate(false)}
          onCancel={() => setShowCreate(false)}
        />
      )}

      {/* ── State AI Decision Support & Strategic Priority ── */}
      {dssState && (
        <div data-tutorial="state-dss-radar">
          <Panel title={`🤖 Statewide AI Decision Support & Cross-District Priority · ${dssState.state || selectedState}`}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "10px", marginBottom: "16px" }}>
              <div className="metric" style={{ borderLeft: "4px solid #1a73e8" }}>
                <span>State Priority Score</span>
                <b style={{ color: "#1a73e8" }}>{dssState.priority_score}/100</b>
                <div style={{ marginTop: "4px" }}><DSSBadge level={dssState.risk_level} /></div>
              </div>
              <div className="metric" style={{ borderLeft: "4px solid #f59e0b" }}>
                <span>Avg Statewide SLA Risk</span>
                <b style={{ color: "#f59e0b" }}>{dssState.components?.avg_sla_risk || 0}/100</b>
                <span style={{ fontSize: "11px", color: "#64748b" }}>Cross-project lag</span>
              </div>
              <div className="metric" style={{ borderLeft: "4px solid #ef4444" }}>
                <span>Max District Backlog</span>
                <b style={{ color: "#ef4444" }}>{dssState.components?.max_district_backlog || 0}/100</b>
                <span style={{ fontSize: "11px", color: "#64748b" }}>Peak district pressure</span>
              </div>
              <div className="metric" style={{ borderLeft: "4px solid #10b981" }}>
                <span>Active Districts Scoped</span>
                <b style={{ color: "#10b981" }}>{dssState.total_districts || 5} Districts</b>
                <span style={{ fontSize: "11px", color: "#64748b" }}>{dssState.total_projects || 0} Projects Monitored</span>
              </div>
            </div>

            <div className="grid2">
              <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  🏛️ District Urgency Ranking (Composite Priority)
                </div>
                <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid #cbd5e1", textAlign: "left" }}>
                      <th style={{ padding: "4px 8px" }}>District</th>
                      <th style={{ padding: "4px 8px" }}>Score</th>
                      <th style={{ padding: "4px 8px" }}>Risk</th>
                      <th style={{ padding: "4px 8px" }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(dssState.district_rankings || []).map(distItem => (
                      <tr key={distItem.district} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "6px 8px" }}><b>{distItem.district}</b></td>
                        <td style={{ padding: "6px 8px" }}>{distItem.score}/100</td>
                        <td style={{ padding: "6px 8px" }}><DSSBadge level={distItem.risk_level} /></td>
                        <td style={{ padding: "6px 8px" }}>
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedDist(distItem.district);
                              if (onSelectDistrict) onSelectDistrict(distItem.district);
                            }}
                            style={{ padding: "3px 8px", background: "#0f6c70", color: "#fff", border: "none", borderRadius: "4px", fontSize: "11px", cursor: "pointer" }}
                          >
                            Filter →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  🎯 State Strategic Recommendations
                </div>
                <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "#475569" }}>
                  {dssState.reasons?.length ? (
                    dssState.reasons.map((r, i) => (
                      <li key={i} style={{ marginBottom: "6px" }}><b>Policy note:</b> {r}</li>
                    ))
                  ) : (
                    <li>All state operational parameters performing within normal bounds.</li>
                  )}
                </ul>
              </div>
            </div>
          </Panel>
        </div>
      )}

      <div data-tutorial="state-metrics">
        <Panel title={`State Overview · ${selectedState} (${selectedDist || "All Districts"})`}>
          <div className="cards">
            {cards.map(c => <div className="metric" key={c[0]}><span>{c[0]}</span><b>{c[1] ?? 0}</b></div>)}
          </div>
        </Panel>
      </div>

      <div className="grid2">
        <Panel title="Risk Distribution"><Bars data={d.risk_distribution} label="category" /></Panel>
        <Panel title="Projects by Stage"><Bars data={d.projects_by_stage} label="stage" /></Panel>
      </div>
      <div className="grid2">
        <Panel title={`${selectedState} District Performance`}>
          <Table rows={d.district_performance || []} cols={["district", "projects", "avg_progress"]} />
        </Panel>
        <Panel title="Major Acquisition Bottlenecks">
          <Table rows={d.bottlenecks || []} cols={["stage", "count"]} />
        </Panel>
      </div>
      <div className="grid2">
        <Panel title="R&R Status Breakdown">
          <Table rows={d.rr_progress || []} cols={["status", "count"]} />
        </Panel>
      </div>
      <PrivacyGovernanceSection district={selectedDist || "Coimbatore"} user={user} />
    </>
  );
}

function PrivacyGovernanceSection({ district, user }) {
  const dist = district || "Coimbatore";
  const { data: gov, error } = useData(`/privacy/governance?district=${encodeURIComponent(dist)}`, 5000);
  const [rejectingId, setRejectingId] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [showAuditModal, setShowAuditModal] = useState(false);
  const [approvingDuration, setApprovingDuration] = useState("24");

  if (error || !gov) return null;

  const m = gov.metrics || {};
  const pending = gov.recent_requests?.filter(r => r.status === "Pending") || [];
  const canApprove = ["authority", "admin", "state_authority", "district_authority"].includes(user?.role);

  const handleApprove = async (id) => {
    try {
      await api(`/privacy/access-request/${id}/approve`, {
        method: "POST",
        body: JSON.stringify({ duration_hours: parseInt(approvingDuration, 10) })
      });
      EventBus.dispatch();
    } catch (e) {
      alert("Approval failed: " + e.message);
    }
  };

  const handleReject = async (id) => {
    try {
      await api(`/privacy/access-request/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: rejectReason || "Rejected under data minimisation policy" })
      });
      setRejectingId(null);
      setRejectReason("");
      EventBus.dispatch();
    } catch (e) {
      alert("Rejection failed: " + e.message);
    }
  };

  return (
    <>
      <Panel title={`🔐 Purpose-Aware Privacy Governance & Access Control · ${dist}`}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "10px" }}>
          <div style={{ fontSize: "12px", color: "#64748b" }}>
            Real-time tracking of sensitive data detection, automatic masking, and time-bound disclosure approvals
          </div>
          <button
            type="button"
            onClick={() => setShowAuditModal(true)}
            style={{ padding: "6px 12px", background: "#f8fafc", color: "#0f6c70", border: "1px solid #0f6c70", borderRadius: "6px", fontSize: "11px", fontWeight: 700, cursor: "pointer" }}
          >
            📋 View Privacy Audit Ledger
          </button>
        </div>

        <div className="cards">
          <div className="metric"><span>📑 Documents Analyzed</span><b>{m.documents_analyzed ?? 0}</b></div>
          <div className="metric" style={{ borderLeft: "4px solid #ea580c" }}><span>⚠️ Sensitive Entities</span><b style={{ color: "#ea580c" }}>{m.sensitive_fields_detected ?? 0}</b></div>
          <div className="metric" style={{ borderLeft: "4px solid #10b981" }}><span>🔒 Fields Masked</span><b style={{ color: "#10b981" }}>{m.fields_automatically_masked ?? 0}</b></div>
          <div className="metric" style={{ borderLeft: "4px solid #3b82f6" }}><span>📄 Privacy PDFs</span><b style={{ color: "#3b82f6" }}>{m.privacy_safe_pdfs_generated ?? 0}</b></div>
          <div className="metric" style={{ borderLeft: "4px solid #f59e0b" }}><span>⏳ Pending Requests</span><b style={{ color: "#f59e0b" }}>{m.pending_access_requests ?? 0}</b></div>
          <div className="metric"><span>✓ Approved Grants</span><b>{m.approved_access_requests ?? 0}</b></div>
          <div className="metric"><span>✗ Rejected Requests</span><b>{m.rejected_access_requests ?? 0}</b></div>
          <div className="metric"><span>⌛ Expired Access</span><b>{m.expired_access_requests ?? 0}</b></div>
        </div>

        {/* Pending Requests Queue */}
        {pending.length > 0 && (
          <div style={{ marginTop: "16px", background: "#fffbeb", padding: "14px", borderRadius: "6px", border: "1px solid #fde68a" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <b style={{ color: "#92400e", fontSize: "13px" }}>⚠️ Pending Temporary Access Requests ({pending.length})</b>
              <span style={{ fontSize: "11px", color: "#b45309" }}>Requires Authority Authorization</span>
            </div>

            <div style={{ display: "grid", gap: "8px" }}>
              {pending.map(req => (
                <div key={req.id} style={{ background: "#ffffff", padding: "10px", borderRadius: "6px", border: "1px solid #fef3c7", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                  <div>
                    <div style={{ fontSize: "12px", fontWeight: 700, color: "#0f172a" }}>
                      Field: <span style={{ color: "#b45309" }}>{req.field_key.toUpperCase()}</span> | Document: {req.document_name || req.document_id?.substring(0, 10)}
                    </div>
                    <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                      Requested By: <b>{req.requested_by}</b> ({req.requested_role}) | Purpose: <b>{req.purpose?.replace("_", " ")}</b>
                    </div>
                    <div style={{ fontSize: "11px", color: "#334155", fontStyle: "italic", marginTop: "2px" }}>
                      "{req.reason}"
                    </div>
                  </div>

                  {canApprove && (
                    <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                      <select
                        value={approvingDuration}
                        onChange={e => setApprovingDuration(e.target.value)}
                        style={{ padding: "4px", fontSize: "11px", borderRadius: "4px", border: "1px solid #cbd5e1" }}
                      >
                        <option value="8">8 hrs</option>
                        <option value="24">24 hrs</option>
                        <option value="48">48 hrs</option>
                      </select>
                      <button
                        type="button"
                        onClick={() => handleApprove(req.id)}
                        style={{ padding: "5px 12px", background: "#10b981", color: "#fff", border: "none", borderRadius: "4px", fontSize: "11px", fontWeight: 700, cursor: "pointer" }}
                      >
                        ✓ Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => setRejectingId(req.id)}
                        style={{ padding: "5px 10px", background: "#ef4444", color: "#fff", border: "none", borderRadius: "4px", fontSize: "11px", fontWeight: 700, cursor: "pointer" }}
                      >
                        ✗ Reject
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </Panel>

      {/* Reject Reason Dialog */}
      {rejectingId && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(15,23,42,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: "20px" }}>
          <div style={{ background: "#ffffff", padding: "20px", borderRadius: "8px", maxWidth: "420px", width: "100%" }}>
            <h4 style={{ margin: "0 0 10px", color: "#0f172a" }}>Reject Access Request</h4>
            <label style={{ fontSize: "12px", color: "#64748b" }}>Provide reason for rejection:</label>
            <textarea
              rows={3}
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              placeholder="e.g. Field verification can be completed with land survey number only."
              style={{ width: "100%", padding: "8px", borderRadius: "6px", border: "1px solid #cbd5e1", marginTop: "6px", fontSize: "12px" }}
            />
            <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", marginTop: "12px" }}>
              <button type="button" onClick={() => setRejectingId(null)} style={{ padding: "6px 12px", background: "#f1f5f9", border: "none", borderRadius: "4px", cursor: "pointer" }}>Cancel</button>
              <button type="button" onClick={() => handleReject(rejectingId)} style={{ padding: "6px 14px", background: "#ef4444", color: "#fff", border: "none", borderRadius: "4px", fontWeight: 700, cursor: "pointer" }}>Confirm Reject</button>
            </div>
          </div>
        </div>
      )}

      {/* Privacy Audit Modal */}
      {showAuditModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(15,23,42,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: "20px" }}>
          <div style={{ background: "#ffffff", padding: "20px", borderRadius: "8px", maxWidth: "750px", width: "100%", maxHeight: "85vh", overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", paddingBottom: "10px", marginBottom: "12px" }}>
              <h3 style={{ margin: 0, color: "#0f172a" }}>📋 Privacy Guard Audit & Disclosure Ledger</h3>
              <button type="button" onClick={() => setShowAuditModal(false)} style={{ background: "none", border: "none", fontSize: "16px", cursor: "pointer", color: "#94a3b8" }}>✕</button>
            </div>

            <p style={{ fontSize: "11px", color: "#64748b", margin: "0 0 10px" }}>
              Cryptographic audit records of all privacy analyses, masking events, temporary access approvals, and safe PDF generations. Zero raw PII is recorded.
            </p>

            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
              <thead>
                <tr style={{ background: "#0f6c70", color: "#ffffff", textAlign: "left" }}>
                  <th style={{ padding: "6px 8px" }}>Time (UTC)</th>
                  <th style={{ padding: "6px 8px" }}>Actor</th>
                  <th style={{ padding: "6px 8px" }}>Action</th>
                  <th style={{ padding: "6px 8px" }}>Target</th>
                  <th style={{ padding: "6px 8px" }}>Audit Details</th>
                </tr>
              </thead>
              <tbody>
                {gov.recent_audits?.map((a, i) => (
                  <tr key={a.id || i} style={{ background: i % 2 === 0 ? "#ffffff" : "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
                    <td style={{ padding: "6px 8px", color: "#64748b" }}>{a.created_at?.substring(0, 19)}</td>
                    <td style={{ padding: "6px 8px", fontWeight: 600 }}>{a.user_email}</td>
                    <td style={{ padding: "6px 8px" }}>
                      <span style={{ fontSize: "10px", fontWeight: 800, padding: "2px 6px", borderRadius: "4px", background: "#e0f2fe", color: "#0369a1" }}>
                        {a.action}
                      </span>
                    </td>
                    <td style={{ padding: "6px 8px" }}>{a.target}</td>
                    <td style={{ padding: "6px 8px", color: "#334155" }}>{a.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div style={{ textAlign: "right", marginTop: "14px" }}>
              <button type="button" onClick={() => setShowAuditModal(false)} style={{ padding: "6px 14px", background: "#0f6c70", color: "#fff", border: "none", borderRadius: "4px", cursor: "pointer", fontWeight: 700 }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function DistrictDashboard({ district, go, user, onOpenSMS }) {
  const dist = district || "Coimbatore";
  const { data: d, error: dashboardError } = useData(`/dashboard/district?district=${encodeURIComponent(dist)}`, 5000);
  const { data: alertsList, error: alertsError } = useData(`/alerts/?district=${encodeURIComponent(dist)}&status=Open`, 5000);
  const { data: projectList, error: projectsError } = useData(`/projects/?district=${encodeURIComponent(dist)}&limit=500`, 5000);
  const { data: smsStats } = useData(`/api/sms/stats?district=${encodeURIComponent(dist)}`, 5000);
  
  // DSS Intelligence Data
  const { data: dssDistrictData } = useData(`/dss/district/${encodeURIComponent(dist)}`, 10000);
  const { data: dssBottlenecks } = useData(`/dss/bottlenecks?district=${encodeURIComponent(dist)}`, 10000);
  const { data: dssEarlyWarnings } = useData(`/dss/early-warnings?district=${encodeURIComponent(dist)}`, 10000);
  const { data: dssPriorityParcels } = useData(`/dss/priority-parcels?district=${encodeURIComponent(dist)}&limit=5`, 10000);
  
  if (dashboardError) return <Panel title={`District Authority Dashboard (${dist})`}><div className="error">Unable to load district dashboard ({dashboardError.status || "network error"}): {dashboardError.message}</div></Panel>;
  if (!d) return <Panel title={`District Authority Dashboard (${dist})`}>Loading…</Panel>;
  let cards = [["Total Projects", d.total_projects], ["Active Projects", d.active_projects], ["Completed Projects", d.completed_projects], ["Total Parcels", d.total_parcels], ["Affected Families", d.affected_families], ["High/Critical Risk", d.high_risk_projects + d.critical_projects], ["Total Compensation", d.total_compensation], ["Paid Compensation", d.paid_compensation], ["Pending Compensation", d.pending_compensation], ["Legal Disputes", d.legal_disputes], ["Delayed Projects", d.delayed_projects], ["SLA Breaches", d.sla_breaches], ["Pending Field Verification", d.pending_verification], ["Escalated Cases", d.escalated_cases]];
  
  // Filter alerts for this district user
  const myAlerts = (alertsList || []).filter(a => a.assigned_to === user?.email || (a.district && a.district.toLowerCase() === dist.toLowerCase()));

  return (
    <>
      {myAlerts.length > 0 && (
        <Panel title={`Notifications (${myAlerts.length})`}>
          {myAlerts.map(a => (
            <div className="notice" key={a.alert_id} style={{ cursor: "pointer", borderLeft: "4px solid #0056b3" }} onClick={() => go({ project_id: a.project_id })}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <b>{a.title || a.type}</b>
                <small>{new Date(a.created_at).toLocaleString()}</small>
              </div>
              <p style={{ margin: "5px 0" }}>{a.message}</p>
              <small>Project: {a.project_id} | Priority: {a.severity}</small>
            </div>
          ))}
        </Panel>
      )}

      {/* ── AI District Decision Support Center (DSS) ── */}
      {dssDistrictData && (
        <div data-tutorial="dss-center">
          <Panel title={`🤖 AI District Decision Support Center · ${dist}`}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "10px", marginBottom: "16px" }}>
              <div className="metric" style={{ borderLeft: "4px solid #1a73e8" }}>
                <span>District Priority Score</span>
                <b style={{ color: "#1a73e8" }}>{dssDistrictData.priority_score}/100</b>
                <div style={{ marginTop: "4px" }}><DSSBadge level={dssDistrictData.risk_level} /></div>
              </div>
              <div className="metric" style={{ borderLeft: "4px solid #f59e0b" }}>
                <span>Verification Backlog</span>
                <b style={{ color: "#f59e0b" }}>{dssDistrictData.components?.verification_backlog?.pending || 0} Cases</b>
                <span style={{ fontSize: "11px", color: "#64748b" }}>Rate: {dssDistrictData.components?.verification_backlog?.score}%</span>
              </div>
              <div className="metric" style={{ borderLeft: "4px solid #ef4444" }}>
                <span>SLA Project Delay</span>
                <b style={{ color: "#ef4444" }}>{dssDistrictData.components?.sla_delay?.score}/100</b>
                <span style={{ fontSize: "11px", color: "#64748b" }}>Weighted schedule lag</span>
              </div>
              <div className="metric" style={{ borderLeft: "4px solid #10b981" }}>
                <span>Data Quality Index</span>
                <b style={{ color: "#10b981" }}>{100 - (dssDistrictData.components?.data_quality?.score || 0)}%</b>
                <span style={{ fontSize: "11px", color: "#64748b" }}>Core field compliance</span>
              </div>
            </div>

            {/* Early Warnings Bar */}
            {dssEarlyWarnings?.warnings && dssEarlyWarnings.warnings.length > 0 && (
              <div style={{ marginBottom: "16px" }}>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "#b42318", textTransform: "uppercase", marginBottom: "6px" }}>
                  ⚠️ Active Early Warnings ({dssEarlyWarnings.warnings.length})
                </div>
                <div style={{ display: "grid", gap: "8px" }}>
                  {dssEarlyWarnings.warnings.slice(0, 3).map((w, idx) => (
                    <div key={idx} style={{ background: "#fff5f5", borderLeft: "4px solid #dc2626", padding: "8px 12px", borderRadius: "0 6px 6px 0", fontSize: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <b>{w.message}</b>
                        <div style={{ color: "#64748b", marginTop: "2px" }}>Action: {w.recommended_action}</div>
                      </div>
                      <DSSBadge level={w.severity} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Primary Bottleneck & Recommended Interventions */}
            <div className="grid2">
              <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  🎯 Top AI Recommended Strategic Actions
                </div>
                <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "#475569" }}>
                  {dssDistrictData.reasons?.length ? (
                    dssDistrictData.reasons.map((r, i) => (
                      <li key={i} style={{ marginBottom: "4px" }}><b>Intervention needed:</b> {r}</li>
                    ))
                  ) : (
                    <li>All operational parameters within safe thresholds.</li>
                  )}
                  {dssBottlenecks?.primary_bottleneck && (
                    <li style={{ color: "#b42318", marginTop: "4px" }}>
                      <b>Stage Bottleneck:</b> {dssBottlenecks.primary_bottleneck.stage} stage has {dssBottlenecks.primary_bottleneck.pending_cases} pending cases.
                    </li>
                  )}
                </ul>
              </div>

              <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  ⚡ Highest Priority Parcels Awaiting Attention
                </div>
                <div style={{ display: "grid", gap: "6px" }}>
                  {(dssPriorityParcels?.items || []).slice(0, 3).map(p => (
                    <div key={p.parcel_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#ffffff", padding: "6px 10px", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "11px" }}>
                      <span><b>{p.record_id || `P-${p.parcel_id}`}</b> (Survey {p.district})</span>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <DSSBadge level={p.risk_level} />
                        <button
                          type="button"
                          onClick={() => go({ parcel_id: p.parcel_id, id: p.parcel_id })}
                          style={{ padding: "3px 8px", background: "#0f6c70", color: "#fff", border: "none", borderRadius: "3px", cursor: "pointer", fontSize: "10px" }}
                        >
                          Inspect
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Panel>
        </div>
      )}

      {/* ── Privacy Governance & Access Approvals ── */}
      <PrivacyGovernanceSection district={dist} user={user} />

      {/* ── SMPP SMS Notification Gateway Live Summary ── */}
      <Panel title={`📱 SMPP Citizen Notification Gateway · ${dist}`}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: "10px" }}>
          <div style={{ fontSize: "13px", color: "#64748b" }}>
            Real-time SMS broadcast delivery across land parcels, field verification notices & compensation DBT alerts
          </div>
          {onOpenSMS && (
            <button
              className="primary"
              style={{
                padding: "8px 16px",
                fontSize: "13px",
                cursor: "pointer",
                fontWeight: 600,
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                borderRadius: "6px",
                background: "#0f766e",
                color: "#ffffff",
                border: "none"
              }}
              onClick={onOpenSMS}
            >
              <span>📱 Open SMS Notification Centre</span>
              <span>↗</span>
            </button>
          )}
        </div>
        <div className="cards">
          <div className="metric"><span>📱 Total SMS Sent</span><b>{smsStats?.total_sent ?? 0}</b></div>
          <div className="metric" style={{ borderLeft: "4px solid #10b981" }}><span>📨 Delivered</span><b style={{ color: "#10b981" }}>{smsStats?.delivered ?? 0}</b></div>
          <div className="metric" style={{ borderLeft: "4px solid #f59e0b" }}><span>⏳ Pending / In-Flight</span><b style={{ color: "#f59e0b" }}>{smsStats?.pending ?? 0}</b></div>
          <div className="metric" style={{ borderLeft: "4px solid #ef4444" }}><span>❌ Delivery Failed</span><b style={{ color: "#ef4444" }}>{smsStats?.failed ?? 0}</b></div>
          <div className="metric"><span>📊 Delivery Rate</span><b>{smsStats?.delivery_rate ?? "0%"}</b></div>
          <div className="metric"><span>👥 Registered Citizens</span><b>{smsStats?.valid_mobile_parcels ?? 0}</b></div>
        </div>
      </Panel>

      <Panel title={`District Project List · ${dist}`}>
        {projectsError && <div className="error">Unable to load projects ({projectsError.status || "network error"}): {projectsError.message}</div>}
        {!projectsError && !projectList && <p>Loading projects...</p>}
        {projectList && <Table rows={projectList.items || []} cols={["project_id", "project_name", "district", "taluk", "village", "current_stage", "project_status", "progress"]} onClick={go} />}
      </Panel>

      <div data-tutorial="district-kpis">
        <Panel title={`District Authority Dashboard · ${dist}`}>
          <div className="cards">{cards.map(c => <div className="metric" key={c[0]}><span>{c[0]}</span><b>{c[1] ?? 0}</b></div>)}</div>
          <div style={{ marginTop: 20 }}><b>Payment Completion:</b> <progress value={d.payment_completion || 0} max={100} style={{ width: "100%" }} /> {d.payment_completion || 0}%</div>
        </Panel>
      </div>
      <div className="grid2">
        <Panel title="Taluk-wise Project Overview"><Table rows={d.taluk_overview || []} cols={["taluk", "projects", "avg_progress"]} /></Panel>
        <Panel title="Priority Actions">{d.priority_actions?.length ? d.priority_actions.map((p, i) => <div className="notice" key={i}><b>{p.task}</b> - Project: {p.project_id}</div>) : <p>No immediate priority actions.</p>}</Panel>
      </div>
      <div className="grid2">
        <Panel title="Compensation Paid Report"><Table rows={d.compensation_paid_report || []} cols={["project_id", "survey_no", "taluk", "owner_reference", "approved_amount", "paid_amount", "status"]} /></Panel>
        <Panel title="Pending Compensation Report"><Table rows={d.compensation_pending_report || []} cols={["project_id", "survey_no", "taluk", "owner_reference", "assessed_amount", "pending_amount", "status"]} /></Panel>
      </div>
      <Panel title="Officer Workload"><div className="cards">{d.officer_workload?.length ? d.officer_workload.map((w, i) => <div className="metric" key={i}><span>{w.assigned_to}</span><b>{w.count} pending</b></div>) : <p>No active assignments.</p>}</div></Panel>
      {d.rr_summary && d.rr_summary.rr_total_families > 0 && (
        <>
          <Panel title={`R&R Rehabilitation Summary · ${dist}`}>
            <div className="cards">
              {[
                ["R&R Families", d.rr_summary.rr_total_families],
                ["Avg Readiness", `${d.rr_summary.rr_avg_readiness || 0}%`],
                ["Completed", d.rr_summary.rr_completed || 0],
                ["On Track", d.rr_summary.rr_on_track || 0],
                ["Attention Required", d.rr_summary.rr_attention || 0],
                ["Delayed", d.rr_summary.rr_delayed || 0],
                ["Critical", d.rr_summary.rr_critical || 0],
                ["Pending Verification", d.rr_summary.rr_pending_verification || 0],
                ["Verified", d.rr_summary.rr_verified || 0],
                ["Open Grievances", d.rr_summary.rr_open_grievances || 0],
                ["Vulnerable Families", d.rr_summary.rr_vulnerable || 0],
              ].map(c => <div className="metric" key={c[0]}><span>{c[0]}</span><b>{c[1]}</b></div>)}
            </div>
          </Panel>
          {d.rr_recent_verifications?.length > 0 && (
            <Panel title="Recent R&R Field Verifications">
              <Table rows={d.rr_recent_verifications} cols={["family_id", "family_head", "survey_no", "village", "verification_status", "verified_by", "verified_at", "readiness_percentage", "readiness_band"]} />
            </Panel>
          )}
        </>
      )}
    </>
  );
}

function Dashboard({ district, user }) {
  const { data: d, error } = useData(`/dashboard/?district=${encodeURIComponent(district || "Coimbatore")}`, 5000);
  if (error) return (
    <Panel title={`Command Center (${district || "All"})`}>
      <div className="error" style={{ padding: "16px", borderRadius: "8px", background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b" }}>
        <p style={{ margin: "0 0 8px 0", fontWeight: 700 }}>⚠️ Backend connection unavailable</p>
        <p style={{ margin: 0, fontSize: "13px" }}>
          {error.message || "Unable to reach the backend API. Please verify VITE_API_URL and ensure the backend service is running."}
        </p>
      </div>
    </Panel>
  );
  if (!d) return <Panel title={`Command Center (${district || "All"})`}>Loading…</Panel>;
  return (
    <>
      <Cards d={d} />
      <div className="grid2">
        <Panel title="Priority Actions (Today)">{d.priority_actions?.length ? d.priority_actions.map((p, i) => <div className="notice" key={i}><b>{p.task}</b> - Project: {p.project_id}</div>) : <p>No immediate priority actions.</p>}</Panel>
        <Panel title="Officer Workload">{d.officer_workload?.length ? d.officer_workload.map((w, i) => <div className="metric" key={i}><span>{w.assigned_to}</span><b>{w.count} pending</b></div>) : <p>No active assignments.</p>}</Panel>
      </div>
      <div className="grid2">
        <Panel title="Risk Distribution"><Bars data={d.risk_distribution} label="category" /></Panel>
        <Panel title="Projects by Stage"><Bars data={d.projects_by_stage} label="stage" /></Panel>
      </div>
      <PrivacyGovernanceSection district={district || "Coimbatore"} user={user} />
      <Panel title="Platform posture">
        <div className="banner">DATA → PARCEL → PROJECT → WORKFLOW → EVIDENCE → GIS → RISK → EXPLAINABLE AI → ACTION → ALERT → OUTCOME → TRAINING → MODEL VERSION → AUDIT</div>
      </Panel>
    </>
  );
}

function Bars({ data, label }) {
  return <div>{data?.map(x => <div className="bar" key={x[label]}><span>{x[label]}</span><i style={{ width: `${Math.min(100, (x.count / (Math.max(...data.map(a => a.count), 1))) * 100)}%` }}></i><b>{x.count}</b></div>)}</div>;
}

function Panel({ title, children }) {
  return <section className="panel"><div className="panel-head"><h2>{title}</h2></div>{children}</section>;
}

function Table({ rows, cols, onClick, actions }) {
  if (!rows || rows.length === 0) return <p>No records found.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{cols.map(c => <th key={c}>{c.replaceAll("_", " ")}</th>)}{actions && <th>Actions</th>}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id || r.project_id || r.record_id || i} onClick={() => onClick && onClick(r)}>
              {cols.map(c => <td key={c}>{String(r[c] ?? "")}</td>)}
              {actions && <td onClick={e => e.stopPropagation()}>{actions(r)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ActionButton({ label, onClick, disabled }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  return (
    <div style={{display: 'inline-block', marginRight: '5px'}}>
      <button disabled={disabled || loading} onClick={async (e) => {
        e.stopPropagation();
        setLoading(true); setError("");
        try { await onClick(e); } catch(ex) { setError(String(ex?.message || ex || "Action failed")); }
        setLoading(false);
      }}>{loading ? "..." : label}</button>
      {error && <span style={{color: "red", fontSize: "10px", marginLeft: "4px"}}>{error}</span>}
    </div>
  );
}

function Projects({ district, go }) {
  const dist = district || "Coimbatore";
  const { data: d, error } = useData(`/projects/?district=${encodeURIComponent(dist)}&limit=500`, 5000);
  if (error) return <Panel title={`Project Register (${dist})`}><div className="error">Unable to load projects ({error.status || "network error"}): {error.message}</div></Panel>;
  if (!d) return <Panel title={`Project Register (${dist})`}>Loading projects...</Panel>;
  return (
    <Panel title={`Project Register · ${dist}`}>
      <Table rows={d.items || []} cols={["project_id", "project_name", "project_type", "district", "taluk", "current_stage", "project_status", "progress"]} onClick={go} />
    </Panel>
  );
}

function UnassignedParcelPool({ project, onClose }) {
  const [q, setQ] = useState("");
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [selectedOfficer, setSelectedOfficer] = useState("");
  const [assigning, setAssigning] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  
  const dist = project.district || "Coimbatore";
  const { data, error } = useData(`/land-records/?district=${encodeURIComponent(dist)}&unassigned=true&limit=200`, 0);
  const { data: officers } = useData(`/field/officers?district=${encodeURIComponent(dist)}`);
  
  const parcels = (data?.items || []).filter(p => 
    !q || `${p.survey_no} ${p.village} ${p.taluk} ${p.subdivision || ""}`.toLowerCase().includes(q.toLowerCase())
  );

  const toggleSelect = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === parcels.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(parcels.map(p => p.id)));
    }
  };

  const handleBatchAssign = async () => {
    if (selectedIds.size === 0) return;
    setAssigning(true); setErr(""); setMsg("");
    try {
      const res = await api(`/projects/${encodeURIComponent(project.project_id)}/parcels/batch-assign`, {
        method: "POST",
        body: JSON.stringify({ 
          parcel_ids: Array.from(selectedIds),
          officer_email: selectedOfficer || null
        })
      });
      setMsg(res.message || `Successfully assigned ${selectedIds.size} parcels${selectedOfficer ? ' to ' + selectedOfficer : ''}!`);
      setSelectedIds(new Set());
      EventBus.dispatch();
    } catch (e) {
      setErr(e.message || "Failed to batch-assign parcels");
    } finally {
      setAssigning(false);
    }
  };

  return (
    <div style={{ background: "#f8fafc", border: "2px solid #0056b3", borderRadius: "10px", padding: "18px", marginBottom: "20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <div>
          <h3 style={{ margin: 0, color: "#0056b3" }}>Unassigned Parcel Pool · {dist}</h3>
          <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#64748b" }}>
            Select parcels from the unassigned pool to link to <b>{project.project_id} ({project.project_name})</b> and assign to a Field Officer.
          </p>
        </div>
        <button onClick={onClose} style={{ background: "#94a3b8", color: "white" }}>Close Pool</button>
      </div>

      <div style={{ display: "flex", gap: "10px", alignItems: "center", marginBottom: "12px", flexWrap: "wrap" }}>
        <input 
          placeholder="Filter by survey number, village, taluk..." 
          value={q} 
          onChange={e => setQ(e.target.value)} 
          style={{ flex: 1, minWidth: "200px" }}
        />
        <select 
          value={selectedOfficer} 
          onChange={e => setSelectedOfficer(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "13px" }}
        >
          <option value="">Link to Project Only (No Officer)</option>
          {(officers || []).map(o => (
            <option key={o.email} value={o.email}>Assign Officer: {o.email}</option>
          ))}
        </select>
        <button type="button" onClick={selectAll} style={{ background: "#475569" }}>
          {selectedIds.size === parcels.length && parcels.length > 0 ? "Deselect All" : "Select All Visible"}
        </button>
        <button 
          type="button" 
          disabled={selectedIds.size === 0 || assigning} 
          onClick={handleBatchAssign}
          style={{ background: "#16a34a" }}
        >
          {assigning ? "Assigning..." : `Assign Selected (${selectedIds.size})`}
        </button>
      </div>

      {msg && <div className="notice" style={{ marginBottom: "10px", color: "#166534" }}>{msg}</div>}
      {err && <div className="error" style={{ marginBottom: "10px" }}>{err}</div>}

      {error && <div className="error">Failed to load unassigned parcels: {error.message}</div>}
      {!data && <p>Loading unassigned parcels for {dist}...</p>}

      {data && (
        <div className="table-wrap" style={{ maxHeight: "320px", overflowY: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: "40px" }}>Select</th>
                <th>Parcel ID</th>
                <th>Survey No</th>
                <th>Subdivision</th>
                <th>Village</th>
                <th>Taluk</th>
                <th>Area (Acres)</th>
                <th>Classification</th>
                <th>Risk Category</th>
              </tr>
            </thead>
            <tbody>
              {parcels.map(p => (
                <tr key={p.id} onClick={() => toggleSelect(p.id)} style={{ cursor: "pointer", background: selectedIds.has(p.id) ? "#e0f2fe" : "inherit" }}>
                  <td>
                    <input 
                      type="checkbox" 
                      checked={selectedIds.has(p.id)} 
                      onChange={() => toggleSelect(p.id)}
                      onClick={e => e.stopPropagation()} 
                    />
                  </td>
                  <td>{p.record_id || p.id}</td>
                  <td><b>{p.survey_no}</b></td>
                  <td>{p.subdivision || "-"}</td>
                  <td>{p.village}</td>
                  <td>{p.taluk}</td>
                  <td>{p.area}</td>
                  <td>{p.classification || "-"}</td>
                  <td>{p.risk_category || "LOW"}</td>
                </tr>
              ))}
              {parcels.length === 0 && (
                <tr>
                  <td colSpan="9" style={{ textAlign: "center", padding: "20px", color: "#94a3b8" }}>
                    No unassigned parcels found in {dist} matching your filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Workflow({ selected, go, user, district }) {
  const { data: projectDetails, error } = useData(selected ? `/projects/${selected.project_id}` : null, 5000);
  const { data: compensation, error: compensationError } = useData(selected ? `/compensation/project/${selected.project_id}` : null, 5000);
  const canExecute = ["district_authority", "authority", "admin", "acquisition_officer", "state_authority"].includes(user?.role);
  const { data: officers } = useData(canExecute && selected ? `/field/officers${district ? `?district=${encodeURIComponent(district)}` : ""}` : null);
  const [survey, setSurvey] = useState("");
  const [subdivision, setSubdivision] = useState("");
  const [village, setVillage] = useState("");
  const [taluk, setTaluk] = useState("");
  const [districtFilter, setDistrictFilter] = useState("");
  const [searchPath, setSearchPath] = useState(null);
  const [selectedParcel, setSelectedParcel] = useState(null);
  const [assigningParcel, setAssigningParcel] = useState(null);
  const [officer, setOfficer] = useState("");
  const [assignError, setAssignError] = useState("");
  const [showPool, setShowPool] = useState(false);
  const { data: searchResults, error: searchError } = useData(searchPath);

  if (!selected) return <Placeholder title="Workflow" />;
  if (error) return <Panel title="Project Details"><p className="error">Unable to load project details ({error.status || "network error"}): {error.message}</p></Panel>;
  if (!projectDetails) return <Panel title="Project Details"><p>Loading project details...</p></Panel>;
  const lifecycle = [{ internal: "Proposal", label: "Proposal" }, { internal: "SIA / Survey", label: "SIA / Survey" }, { internal: "Notification", label: "Notification" }, { internal: "Legal Dispute / Resolution", label: "Objections" }, { internal: "Approval", label: "Approval" }, { internal: "Award", label: "Award" }, { internal: "Compensation", label: "Compensation" }, { internal: "Possession", label: "Possession" }, { internal: "Rehabilitation", label: "Rehabilitation" }, { internal: "Closure / Completion", label: "Completed" }];
  const normalizedStage = { Survey: "SIA / Survey", "Rehabilitation & Resettlement": "Rehabilitation" }[projectDetails.current_stage] || projectDetails.current_stage;
  const currentIndex = lifecycle.findIndex(s => s.internal === normalizedStage);
  const nextStage = currentIndex >= 0 ? lifecycle[currentIndex + 1] : null;
  const transition = async () => {
    if (!nextStage || !window.confirm(`Move ${projectDetails.project_id} to ${nextStage.label}?`)) return;
    await api(`/projects/${encodeURIComponent(projectDetails.project_id)}/workflow/transition`, { method: "POST", body: JSON.stringify({ next_stage: nextStage.internal }) });
  };
  const search = e => {
    e.preventDefault();
    const parts = survey.trim().split("/");
    const surveyNo = parts[0] || "";
    const subdivisionValue = parts.length > 1 ? parts.slice(1).join("/") : subdivision.trim();
    const params = new URLSearchParams({ limit: "100" });
    if (surveyNo) params.set("survey_no", surveyNo);
    if (subdivisionValue) params.set("subdivision", subdivisionValue);
    if (village.trim()) params.set("village", village.trim());
    if (taluk.trim()) params.set("taluk", taluk.trim());
    if (districtFilter.trim()) params.set("district", districtFilter.trim());
    setSearchPath(`/land-records/?${params.toString()}`);
  };
  const linkSelected = async () => {
    if (!selectedParcel) return;
    await api(`/projects/${encodeURIComponent(projectDetails.project_id)}/parcels/${selectedParcel.id}`, { method: "POST" });
    setSelectedParcel(null); setSearchPath(null);
    EventBus.dispatch();
  };
  const assign = async parcel => {
    if (!officer) { setAssignError("Please select a field officer first."); return; }
    setAssignError("");
    try {
      await api("/field/assign", { method: "POST", body: JSON.stringify({ project_id: projectDetails.project_id, parcel_id: parcel.id, officer_email: officer }) });
      setAssigningParcel(null); setOfficer("");
      EventBus.dispatch();
    } catch (err) {
      setAssignError(`Assignment failed for parcel ${parcel.survey_no || parcel.id}: ${err.message}`);
    }
  };
  const unassign = async (parcel) => {
    if (!window.confirm(`Release parcel ${parcel.survey_no || parcel.id} back to the unassigned pool?`)) return;
    try {
      await api(`/projects/${encodeURIComponent(projectDetails.project_id)}/parcels/${parcel.id}/unassign`, { method: "POST" });
      EventBus.dispatch();
    } catch (err) {
      setAssignError(`Unassign failed: ${err.message}`);
    }
  };

  const parcelActions = canExecute ? p => assigningParcel === p.id ? (
    <><select value={officer} onChange={e => setOfficer(e.target.value)}><option value="">Select field officer</option>{(officers || []).map(o => <option key={o.email} value={o.email}>{o.email}</option>)}</select><ActionButton label="Assign" onClick={() => assign(p)} /></>
  ) : (
    <div style={{ display: "flex", gap: "4px" }}>
      <button type="button" onClick={() => go({ parcel_id: p.id, project_id: p.project_id })}>View Parcel</button>
      <button type="button" onClick={() => setAssigningParcel(p.id)}>Assign Officer</button>
      <button type="button" onClick={() => unassign(p)} style={{ background: "#dc2626", color: "white" }}>Unassign</button>
    </div>
  ) : undefined;

  return (
    <>
      <Panel title={`Project Details: ${projectDetails.project_id} - ${projectDetails.project_name}`}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "10px", marginBottom: "20px", padding: "15px", background: "#f8f9fa", borderRadius: "8px" }}>
          <div><b>Project ID:</b> {projectDetails.project_id}</div><div><b>Project Name:</b> {projectDetails.project_name}</div>
          <div><b>District:</b> {projectDetails.district || "N/A"}</div><div><b>Taluk:</b> {projectDetails.taluk || "N/A"}</div>
          <div><b>Village:</b> {projectDetails.village || "N/A"}</div><div><b>Stage:</b> {projectDetails.current_stage}</div>
          <div><b>Status:</b> {projectDetails.project_status || "N/A"}</div><div><b>Progress:</b> {projectDetails.progress ?? 0}%</div>
          <div><b>Linked Land Area:</b> {(projectDetails.linked_land_area ?? 0).toFixed(2)} acres</div><div><b>Target Date:</b> {projectDetails.planned_completion_date || "N/A"}</div>
          <div><b>Risk:</b> {projectDetails.project_risk || "N/A"}</div>
          <div><b>Linked Parcels:</b> {projectDetails.linked_parcel_count ?? 0}</div><div><b>Verified / Pending:</b> {projectDetails.verified_parcel_count ?? 0} / {projectDetails.pending_verification_count ?? 0}</div>
        </div>
        <h4>Acquisition Workflow</h4>
        <div className="timeline">{lifecycle.map((stage, index) => { const milestone=projectDetails.workflow?.find(m => m.stage===stage.internal); const status=index<currentIndex ? "Completed" : index===currentIndex ? "Current" : "Pending"; return <div className="stage" key={stage.internal}><b>{stage.label}</b><span>{status}</span><small>{milestone?.actual_date ? `Completed: ${milestone.actual_date}` : milestone?.planned_date ? `Started: ${milestone.planned_date}` : "No date recorded"}{milestone?.responsible_officer ? ` · ${milestone.responsible_officer}` : ""}</small></div>; })}</div>
        {projectDetails.pending_verification_count > 0 && <div className="notice">{projectDetails.pending_verification_count} linked parcel(s) are still pending field verification.</div>}
        <div style={{ display: "flex", gap: "10px", marginTop: "15px" }}>
          {canExecute && nextStage && <ActionButton label={`Move to ${nextStage.label}`} onClick={transition} />}
          {canExecute && <button type="button" onClick={() => setShowPool(!showPool)} style={{ background: "#0284c7", color: "white" }}>{showPool ? "Hide Parcel Pool" : "+ Add Land Parcels (Batch Pool)"}</button>}
        </div>
      </Panel>

      {showPool && canExecute && <UnassignedParcelPool project={projectDetails} onClose={() => setShowPool(false)} />}

      {canExecute && <Panel title="Link Single Parcel by Search">
        <form className="toolbar" onSubmit={search}><input placeholder="Survey / Survey-Subdivision (e.g. 00029/4A)" value={survey} onChange={e => setSurvey(e.target.value)} /><input placeholder="Subdivision" value={subdivision} onChange={e => setSubdivision(e.target.value)} /><input placeholder="Village" value={village} onChange={e => setVillage(e.target.value)} /><input placeholder="Taluk" value={taluk} onChange={e => setTaluk(e.target.value)} /><input placeholder="District" value={districtFilter} onChange={e => setDistrictFilter(e.target.value)} /><button type="submit">Search Parcels</button></form>
        {searchError && <div className="error">Unable to search parcels: {searchError.message}</div>}
        {searchResults && <><Table rows={searchResults.items || []} cols={["id", "survey_no", "subdivision", "village", "taluk", "district", "area", "acquisition_status", "risk_category", "risk_score"]} onClick={setSelectedParcel} /><div>{selectedParcel && <><span>Selected: Parcel {selectedParcel.id} · {selectedParcel.survey_no}</span> <button type="button" onClick={linkSelected}>Link Selected Parcel</button></>}</div></>}
        {searchResults && !(searchResults.items || []).length && <div className="empty">No parcels found for this search.</div>}
      </Panel>}

      <Panel title={`Linked Parcels (${projectDetails.parcels?.length || 0})`}>
        {assignError && <div className="error" style={{ marginBottom: "10px" }}>{assignError}</div>}
        <Table rows={projectDetails.parcels || []} cols={["id", "survey_no", "subdivision", "village", "taluk", "area", "risk_category", "acquisition_status", "assignment_status"]} onClick={p => go({ parcel_id: p.id, project_id: p.project_id })} actions={parcelActions} />
      </Panel>
      <Panel title="Pending Compensation">
        {compensationError && <div className="error">Unable to load compensation ({compensationError.status || "network error"}): {compensationError.message}</div>}
        {!compensationError && !compensation && <p>Loading compensation...</p>}
        {compensation && <Table rows={compensation} cols={["parcel_id", "survey_no", "village", "eligible_amount", "paid_amount", "pending_amount", "status"]} actions={r => <ActionButton label="Pay" onClick={() => api(`/compensation/project/${projectDetails.project_id}/parcel/${r.parcel_id}/pay`, { method: "POST" })} />} />}
        {compensation && !compensation.length && <div className="empty">No pending compensation records.</div>}
      </Panel>
    </>
  );
}

function Parcels({ district, onSelectParcel, go }) {
  const [q, setQ] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [stageFilter, setStageFilter] = useState("");
  const [gpsFilter, setGpsFilter] = useState("all");
  const dist = district || "Coimbatore";

  const queryParams = new URLSearchParams({
    limit: "250",
    district: dist
  });
  if (q.trim()) queryParams.append("q", q.trim());
  if (riskFilter) queryParams.append("risk_category", riskFilter);
  if (stageFilter) queryParams.append("acquisition_status", stageFilter);

  const { data: rows, error } = useData(`/land-records/?${queryParams.toString()}`);

  const allItems = rows?.items || [];
  const filtered = allItems.filter(p => {
    const hasGps = p.latitude != null && p.longitude != null && String(p.latitude).trim() !== "" && String(p.longitude).trim() !== "";
    if (gpsFilter === "with_gps") return hasGps;
    if (gpsFilter === "without_gps") return !hasGps;
    return true;
  });

  const highRiskCount = filtered.filter(p => ["HIGH", "CRITICAL"].includes((p.risk_category || "").toUpperCase())).length;
  const gpsCount = filtered.filter(p => p.latitude != null && p.longitude != null && String(p.latitude).trim() !== "").length;

  const handleSelect = (p) => {
    const target = { ...p, parcel_id: p.id, id: p.id };
    if (onSelectParcel) onSelectParcel(target);
    else if (go) go(target);
  };

  return (
    <Panel title={`Parcel Register · ${dist}`}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", marginBottom: "16px" }}>
        <div style={{ background: "#ffffff", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>Total Parcels</div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: "#0f172a" }}>{rows?.total ?? filtered.length}</div>
          <div style={{ fontSize: "11px", color: "#94a3b8" }}>Showing {filtered.length} in view</div>
        </div>
        <div style={{ background: "#ffffff", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>High / Critical Risk</div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: highRiskCount > 0 ? "#dc2626" : "#16a34a" }}>{highRiskCount}</div>
          <div style={{ fontSize: "11px", color: "#94a3b8" }}>Requires officer priority</div>
        </div>
        <div style={{ background: "#ffffff", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>GPS Tagged</div>
          <div style={{ fontSize: "20px", fontWeight: 800, color: "#0284c7" }}>{gpsCount}</div>
          <div style={{ fontSize: "11px", color: "#94a3b8" }}>Maps & coordinates active</div>
        </div>
        <div style={{ background: "#ffffff", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>District Scope</div>
          <div style={{ fontSize: "16px", fontWeight: 700, color: "#0f6c70", marginTop: "3px" }}>{dist}</div>
          <div style={{ fontSize: "11px", color: "#94a3b8" }}>Revenue Jurisdiction</div>
        </div>
      </div>

      <div style={{ background: "#ffffff", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0", marginBottom: "16px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr auto", gap: "10px", alignItems: "end" }}>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "4px" }}>Search Parcels</label>
            <input
              placeholder="Search Survey No, Village, Taluk, Record ID, Owner..."
              value={q}
              onChange={e => setQ(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            />
          </div>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "4px" }}>Risk Level</label>
            <select
              value={riskFilter}
              onChange={e => setRiskFilter(e.target.value)}
              style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            >
              <option value="">All Risk Levels</option>
              <option value="CRITICAL">Critical Risk</option>
              <option value="HIGH">High Risk</option>
              <option value="MEDIUM">Medium Risk</option>
              <option value="LOW">Low Risk</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "4px" }}>Acquisition Stage</label>
            <select
              value={stageFilter}
              onChange={e => setStageFilter(e.target.value)}
              style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            >
              <option value="">All Stages</option>
              <option value="Proposal">Proposal</option>
              <option value="Section 4(1)">Section 4(1) / Section 11</option>
              <option value="Section 6">Section 6 / Section 19</option>
              <option value="Award">Award Determination</option>
              <option value="Compensation">Compensation</option>
              <option value="Possession">Possession</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "4px" }}>GPS Coordinates</label>
            <select
              value={gpsFilter}
              onChange={e => setGpsFilter(e.target.value)}
              style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            >
              <option value="all">All Status</option>
              <option value="with_gps">📍 Coordinates Available</option>
              <option value="without_gps">⚠️ Missing Coordinates</option>
            </select>
          </div>
          <div>
            <button
              type="button"
              onClick={() => { setQ(""); setRiskFilter(""); setStageFilter(""); setGpsFilter("all"); }}
              style={{ padding: "8px 12px", background: "#f1f5f9", color: "#475569", border: "1px solid #cbd5e1", borderRadius: "6px", cursor: "pointer", fontWeight: 600, fontSize: "12px" }}
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error" style={{ marginBottom: "12px" }}>Failed to load land parcels: {error.message}</div>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Record ID</th>
              <th>Survey / Sub</th>
              <th>Village & Taluk</th>
              <th>Area</th>
              <th>Classification</th>
              <th>Project ID</th>
              <th>Stage</th>
              <th>AI Risk</th>
              <th>GPS Status</th>
              <th style={{ textAlign: "center" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(p => {
              const hasGps = p.latitude != null && p.longitude != null && String(p.latitude).trim() !== "";
              const risk = (p.risk_category || "LOW").toUpperCase();
              const riskColor = risk === "CRITICAL" ? "#991b1b" : risk === "HIGH" ? "#b91c1c" : risk === "MEDIUM" ? "#b45309" : "#15803d";
              const riskBg = risk === "CRITICAL" ? "#fee2e2" : risk === "HIGH" ? "#fef2f2" : risk === "MEDIUM" ? "#fef3c7" : "#dcfce7";
              return (
                <tr key={p.id || p.record_id} style={{ cursor: "pointer" }} onClick={() => handleSelect(p)}>
                  <td>
                    <span style={{ fontFamily: "monospace", fontWeight: 700, color: "#0f6c70", background: "#f0fdfa", padding: "2px 6px", borderRadius: "4px", fontSize: "11px" }}>
                      {p.record_id || `PCL-${p.id}`}
                    </span>
                  </td>
                  <td><b>{p.survey_no}</b>{p.subdivision ? `/${p.subdivision}` : ""}</td>
                  <td>{p.village}, <span style={{ color: "#64748b" }}>{p.taluk}</span></td>
                  <td>{p.area} {p.area_unit || "Acres"}</td>
                  <td><span style={{ fontSize: "11px", color: "#475569" }}>{p.classification || "Patta"}</span></td>
                  <td>
                    {p.project_id ? (
                      <span style={{ color: "#0284c7", fontWeight: 600, fontSize: "11px" }}>{p.project_id}</span>
                    ) : (
                      <span style={{ color: "#94a3b8", fontStyle: "italic", fontSize: "11px" }}>Unassigned</span>
                    )}
                  </td>
                  <td>
                    <span style={{ background: "#f1f5f9", color: "#334155", padding: "2px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 600 }}>
                      {p.acquisition_status || "Proposal"}
                    </span>
                  </td>
                  <td>
                    <span style={{ background: riskBg, color: riskColor, padding: "2px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 700 }}>
                      {risk} ({p.risk_score ?? 0})
                    </span>
                  </td>
                  <td>
                    {hasGps ? (
                      <span style={{ color: "#16a34a", fontSize: "11px", fontWeight: 600 }}>📍 Tagged</span>
                    ) : (
                      <span style={{ color: "#d97706", fontSize: "11px" }}>⚠️ No GPS</span>
                    )}
                  </td>
                  <td style={{ textAlign: "center" }} onClick={e => e.stopPropagation()}>
                    <div style={{ display: "inline-flex", gap: "6px", alignItems: "center" }}>
                      <button
                        type="button"
                        onClick={() => handleSelect(p)}
                        style={{
                          background: "#0f6c70",
                          color: "#ffffff",
                          border: "none",
                          padding: "4px 10px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: 700,
                          cursor: "pointer"
                        }}
                      >
                        View Intelligence ↗
                      </button>
                      {hasGps && (
                        <a
                          href={`https://www.google.com/maps/search/?api=1&query=${p.latitude},${p.longitude}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          title="Open coordinates in Google Maps"
                          style={{
                            background: "#0284c7",
                            color: "#ffffff",
                            padding: "4px 8px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            textDecoration: "none",
                            fontWeight: 700
                          }}
                        >
                          🗺️
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={10} style={{ textAlign: "center", padding: "24px", color: "#64748b" }}>
                  No parcels found matching your search and filter criteria in {dist}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function GIS({ district, user, onNavigateParcel, selectedParcel }) {
  const isLocked = Boolean(user?.district_scope || user?.role === "district_authority" || user?.role === "field_officer");
  const defaultDist = isLocked 
    ? (user?.district_scope || district || "Coimbatore") 
    : (user?.role === "state_authority" ? (district || "all") : (district || "Coimbatore"));
  const [activeDist, setActiveDist] = useState(defaultDist);
  const [selectedTaluk, setSelectedTaluk] = useState("all");
  const [selectedRisk, setSelectedRisk] = useState("ALL");
  const [q, setQ] = useState("");
  const [usePins, setUsePins] = useState(false);

  useEffect(() => {
    if (district && district !== activeDist) {
      setActiveDist(district);
      setSelectedTaluk("all");
    }
  }, [district]);

  // When selectedParcel is passed from dossier/details, ensure activeDist accommodates it
  useEffect(() => {
    if (selectedParcel?.district && !isLocked) {
      if (activeDist !== "all" && activeDist.toLowerCase() !== selectedParcel.district.toLowerCase()) {
        setActiveDist(selectedParcel.district);
      }
    }
  }, [selectedParcel]);

  const queryDist = activeDist;
  const { data: g, loading } = useData(
    `/gis/parcels?district=${encodeURIComponent(queryDist)}&taluk=${encodeURIComponent(selectedTaluk === 'all' ? '' : selectedTaluk)}&risk_category=${encodeURIComponent(selectedRisk === 'ALL' ? '' : selectedRisk)}&limit=5000`
  );

  const availableTaluks = g?.available_taluks || [];
  const availableDistricts = g?.available_districts || [];
  const allFeatures = g?.features || [];
  const stats = g?.stats || {};
  
  const filtered = allFeatures.filter(f => {
    if (!q) return true;
    const term = q.toLowerCase();
    const p = f.properties || {};
    return (
      String(p.survey_no || "").toLowerCase().includes(term) ||
      String(p.village || "").toLowerCase().includes(term) ||
      String(p.taluk || "").toLowerCase().includes(term) ||
      String(p.district || "").toLowerCase().includes(term) ||
      String(p.project_id || "").toLowerCase().includes(term) ||
      String(p.record_id || "").toLowerCase().includes(term) ||
      String(p.owner_reference || "").toLowerCase().includes(term)
    );
  });

  const isAll = activeDist.toLowerCase() === "all" || activeDist === "All Districts";
  const stateLabel = user?.state_scope || g?.state || "State";
  
  let center = [11.0168, 76.9558];
  let zoom = 11;
  if (selectedParcel?.latitude && selectedParcel?.longitude) {
    center = [Number(selectedParcel.latitude), Number(selectedParcel.longitude)];
    zoom = 15;
  } else if (selectedTaluk !== "all" && TALUK_CENTROIDS[selectedTaluk]) {
    center = TALUK_CENTROIDS[selectedTaluk];
    zoom = 13;
  } else if (isAll) {
    if (user?.state_scope === "Kerala" || g?.state === "Kerala") {
      center = [10.15, 76.50];
      zoom = 8;
    } else {
      center = [11.1271, 77.8500];
      zoom = 8;
    }
  } else if (DISTRICT_CENTROIDS[activeDist]) {
    center = DISTRICT_CENTROIDS[activeDist];
    zoom = 11;
  }

  const getRiskStyle = (cat) => {
    const c = String(cat || "").toUpperCase();
    if (c === "CRITICAL") return { fill: "#ef4444", color: "#991b1b" };
    if (c === "HIGH") return { fill: "#f97316", color: "#c2410c" };
    if (c === "MEDIUM") return { fill: "#f59e0b", color: "#b45309" };
    return { fill: "#10b981", color: "#047857" };
  };

  const criticalCount = filtered.filter(f => f.properties?.risk_category === "CRITICAL").length;
  const highCount = filtered.filter(f => f.properties?.risk_category === "HIGH").length;
  const mediumCount = filtered.filter(f => f.properties?.risk_category === "MEDIUM").length;
  const lowCount = filtered.filter(f => !["CRITICAL", "HIGH", "MEDIUM"].includes(f.properties?.risk_category)).length;

  const totalEligible = stats.total_eligible_parcels !== undefined ? stats.total_eligible_parcels : allFeatures.length;
  const totalGisLinked = stats.total_gis_linked !== undefined ? stats.total_gis_linked : allFeatures.length;
  const totalUnlinked = stats.total_gis_unlinked !== undefined ? stats.total_gis_unlinked : 0;

  return (
    <Panel title={`GIS Cadastral Intelligence · ${isAll ? (user?.state_scope ? `All ${user.state_scope} Districts` : "National Scope (All Districts)") : `${activeDist} District`}`}>
      <div className="notice" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
        <div>
          <b>Cadastral Spatial Intelligence:</b> Demonstration GIS geometry for {isAll ? (user?.state_scope ? `All ${user.state_scope} Districts` : "All Authorized Districts") : activeDist}.
          <span style={{ display: "block", fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
            Authoritative revenue cadastral boundary maps require certified integration with Tamil Nadu TNGIS / DILRMP.
          </span>
        </div>
        <a 
          href="https://tngis.tn.gov.in/apps.html" 
          target="_blank" 
          rel="noreferrer"
          style={{ fontSize: "12px", color: "#0f766e", fontWeight: 700, textDecoration: "none", background: "#f0fdf4", padding: "4px 10px", borderRadius: "6px", border: "1px solid #bbf7d0" }}
        >
          Open TNGIS Portal ↗
        </a>
      </div>

      {/* Honest Database-Backed KPI Summary */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "10px", margin: "14px 0" }}>
        <div style={{ background: "#f8fafc", padding: "10px 14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>DATABASE PARCELS</span>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0f172a" }}>{totalEligible.toLocaleString()}</div>
          <small style={{ color: "#64748b", fontSize: "10px" }}>Total in jurisdiction</small>
        </div>
        <div style={{ background: "#f0fdfa", padding: "10px 14px", borderRadius: "8px", border: "1px solid #ccfbf1" }}>
          <span style={{ fontSize: "11px", color: "#0f766e", fontWeight: 600 }}>GIS-LINKED</span>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0f766e" }}>{totalGisLinked.toLocaleString()}</div>
          <small style={{ color: "#0f766e", fontSize: "10px" }}>With GPS coordinates</small>
        </div>
        <div style={{ background: "#f8fafc", padding: "10px 14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>UNLINKED (LEGACY)</span>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#64748b" }}>{totalUnlinked.toLocaleString()}</div>
          <small style={{ color: "#64748b", fontSize: "10px" }}>Pending spatial capture</small>
        </div>
        <div style={{ background: "#f8fafc", padding: "10px 14px", borderRadius: "8px", border: "1px solid #cbd5e1" }}>
          <span style={{ fontSize: "11px", color: "#334155", fontWeight: 600 }}>CURRENT VISIBLE</span>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0f172a" }}>{filtered.length.toLocaleString()}</div>
          <small style={{ color: "#64748b", fontSize: "10px" }}>On map display</small>
        </div>
        <div style={{ background: "#fef2f2", padding: "10px 14px", borderRadius: "8px", border: "1px solid #fecaca" }}>
          <span style={{ fontSize: "11px", color: "#991b1b", fontWeight: 600 }}>CRITICAL RISK</span>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#b91c1c" }}>{criticalCount}</div>
          <small style={{ color: "#991b1b", fontSize: "10px" }}>Urgent intervention</small>
        </div>
        <div style={{ background: "#fff7ed", padding: "10px 14px", borderRadius: "8px", border: "1px solid #fed7aa" }}>
          <span style={{ fontSize: "11px", color: "#9a3412", fontWeight: 600 }}>HIGH RISK</span>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#c2410c" }}>{highCount}</div>
          <small style={{ color: "#9a3412", fontSize: "10px" }}>Acquisition watch</small>
        </div>
        <div style={{ background: "#fefce8", padding: "10px 14px", borderRadius: "8px", border: "1px solid #fef08a" }}>
          <span style={{ fontSize: "11px", color: "#854d0e", fontWeight: 600 }}>MEDIUM RISK</span>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#a16207" }}>{mediumCount}</div>
          <small style={{ color: "#854d0e", fontSize: "10px" }}>In progress</small>
        </div>
        <div style={{ background: "#f0fdf4", padding: "10px 14px", borderRadius: "8px", border: "1px solid #bbf7d0" }}>
          <span style={{ fontSize: "11px", color: "#166534", fontWeight: 600 }}>LOW RISK</span>
          <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#15803d" }}>{lowCount}</div>
          <small style={{ color: "#166534", fontSize: "10px" }}>Clear titles</small>
        </div>
      </div>

      {/* District-wise breakdown & Quick Switch Bar */}
      {availableDistricts.length > 0 && !isLocked && (
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginBottom: "14px", background: "#f8fafc", padding: "10px 14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <span style={{ fontSize: "11px", fontWeight: 800, color: "#475569", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Jurisdiction Breakdown:
          </span>
          <button
            type="button"
            onClick={() => { setActiveDist("all"); setSelectedTaluk("all"); }}
            style={{
              padding: "4px 12px",
              borderRadius: "16px",
              fontSize: "11px",
              fontWeight: 700,
              border: "1px solid",
              borderColor: isAll ? "#0f766e" : "#cbd5e1",
              background: isAll ? "#0f766e" : "#ffffff",
              color: isAll ? "#ffffff" : "#334155",
              cursor: "pointer",
              boxShadow: isAll ? "0 2px 6px rgba(15,118,110,0.25)" : "none"
            }}
          >
            🌐 All {stateLabel} ({totalGisLinked.toLocaleString()})
          </button>
          {availableDistricts.map(d => {
            const b = stats?.district_breakdown?.[d];
            const isSel = activeDist.toLowerCase() === d.toLowerCase();
            return (
              <button
                key={d}
                type="button"
                onClick={() => { setActiveDist(d); setSelectedTaluk("all"); }}
                style={{
                  padding: "4px 12px",
                  borderRadius: "16px",
                  fontSize: "11px",
                  fontWeight: isSel ? 700 : 500,
                  border: "1px solid",
                  borderColor: isSel ? "#0f766e" : "#cbd5e1",
                  background: isSel ? "#0f766e" : "#ffffff",
                  color: isSel ? "#ffffff" : "#334155",
                  cursor: "pointer",
                  boxShadow: isSel ? "0 2px 6px rgba(15,118,110,0.25)" : "none"
                }}
              >
                {d}: <b>{b ? b.gis_linked?.toLocaleString() : "0"}</b> <span style={{ opacity: 0.7, fontSize: "10px" }}>/ {b ? b.total?.toLocaleString() : "0"}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Filter and Search Controls */}
      <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap", marginBottom: "12px", background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
        {!isLocked && (
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569" }}>DISTRICT SCOPE</label>
            <select
              value={activeDist}
              onChange={e => { setActiveDist(e.target.value); setSelectedTaluk("all"); }}
              style={{ padding: "7px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", fontWeight: 600, background: "#fff" }}
            >
              <option value="all">
                🌐 All {user?.state_scope ? `${user.state_scope} Districts (Statewide)` : "Districts Nationwide"} ({totalGisLinked.toLocaleString()} parcels)
              </option>
              {(availableDistricts.length > 0 ? availableDistricts : DISTRICTS).map(d => {
                const b = stats?.district_breakdown?.[d];
                return (
                  <option key={d} value={d}>
                    {d} {b ? `(${b.gis_linked?.toLocaleString()} parcels)` : ""}
                  </option>
                );
              })}
            </select>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569" }}>TALUK FILTER</label>
          <select
            value={selectedTaluk}
            onChange={e => setSelectedTaluk(e.target.value)}
            style={{ padding: "7px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", background: "#fff", minWidth: "150px" }}
          >
            <option value="all">All Taluks ({availableTaluks.length || "All"})</option>
            {availableTaluks.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569" }}>RISK FILTER</label>
          <select
            value={selectedRisk}
            onChange={e => setSelectedRisk(e.target.value)}
            style={{ padding: "7px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", background: "#fff" }}
          >
            <option value="ALL">All Risk Levels</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="LOW">Low Risk</option>
          </select>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px", flex: 1, minWidth: "180px" }}>
          <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569" }}>SEARCH SURVEY / VILLAGE</label>
          <input
            placeholder="Search Survey No, Village, Project ID..."
            value={q}
            onChange={e => setQ(e.target.value)}
            style={{ padding: "7px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", background: "#fff" }}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569" }}>DISPLAY MODE</label>
          <div style={{ display: "flex", gap: "4px" }}>
            <button
              type="button"
              onClick={() => setUsePins(false)}
              style={{
                padding: "6px 10px",
                fontSize: "11px",
                fontWeight: 600,
                borderRadius: "6px",
                border: "1px solid #cbd5e1",
                background: !usePins ? "#0f766e" : "#fff",
                color: !usePins ? "#fff" : "#334155",
                cursor: "pointer"
              }}
            >
              ● Cadastral Dots
            </button>
            <button
              type="button"
              onClick={() => setUsePins(true)}
              style={{
                padding: "6px 10px",
                fontSize: "11px",
                fontWeight: 600,
                borderRadius: "6px",
                border: "1px solid #cbd5e1",
                background: usePins ? "#0f766e" : "#fff",
                color: usePins ? "#fff" : "#334155",
                cursor: "pointer"
              }}
            >
              📍 Pins
            </button>
          </div>
        </div>
      </div>

      {/* Empty State Alert */}
      {!loading && filtered.length === 0 && (
        <div style={{
          background: "#fffbeb",
          border: "1px solid #fef3c7",
          color: "#92400e",
          padding: "16px 20px",
          borderRadius: "8px",
          marginBottom: "12px",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          fontWeight: 600,
          fontSize: "13px"
        }}>
          <span style={{ fontSize: "20px" }}>⚠️</span>
          <div>
            No GIS-linked parcels available for {activeDist === "all" ? "this jurisdiction" : `${activeDist} district`}.
            {stats?.district_breakdown?.[activeDist]?.total ? (
              <span style={{ display: "block", fontSize: "11px", fontWeight: 400, color: "#b45309", marginTop: "2px" }}>
                ({stats.district_breakdown[activeDist].total.toLocaleString()} total land records exist in the database for {activeDist}, but all are currently unlinked / pending GPS spatial capture).
              </span>
            ) : null}
          </div>
        </div>
      )}

      {/* Focused Parcel Banner */}
      {selectedParcel?.latitude && (
        <div style={{
          background: "#f0fdf4",
          border: "1px solid #bbf7d0",
          color: "#166534",
          padding: "8px 14px",
          borderRadius: "8px",
          marginBottom: "10px",
          fontSize: "12px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}>
          <span>🎯 Focused on Survey No. <b>{selectedParcel.survey_no}</b> ({selectedParcel.village || "Village"}, {selectedParcel.district || activeDist})</span>
          <span style={{ fontSize: "11px", opacity: 0.8 }}>Zoom: 15x</span>
        </div>
      )}

      <div className="map" style={{ height: "550px", position: "relative", borderRadius: "10px", overflow: "hidden", border: "1px solid #cbd5e1" }}>
        {loading && (
          <div style={{ position: "absolute", top: 10, right: 10, zIndex: 1000, background: "rgba(255,255,255,0.9)", padding: "6px 12px", borderRadius: "6px", fontWeight: 600, fontSize: "12px", boxShadow: "0 2px 6px rgba(0,0,0,0.15)" }}>
            Loading GIS Parcels...
          </div>
        )}
        <MapContainer key={`${activeDist}-${selectedTaluk}-${usePins}-${selectedParcel?.latitude || 'none'}`} center={center} zoom={zoom} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
          <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {filtered.map((f, i) => {
            const coords = f.geometry?.coordinates || [center[1], center[0]];
            const p = f.properties || {};
            const style = getRiskStyle(p.risk_category);
            const pos = [coords[1], coords[0]];
            const isSelected = selectedParcel && (
              String(p.survey_no) === String(selectedParcel.survey_no) ||
              String(p.record_id) === String(selectedParcel.record_id) ||
              String(p.parcel_id) === String(selectedParcel.id || selectedParcel.parcel_id)
            );

            const popupContent = (
              <Popup>
                <div style={{ minWidth: "220px", fontSize: "12px", lineHeight: "1.5" }}>
                  <div style={{ fontWeight: 800, fontSize: "14px", color: "#0f172a", marginBottom: "4px" }}>
                    Survey {p.survey_no}{p.subdivision ? `/${p.subdivision}` : ""}
                  </div>
                  <div><b>Village:</b> {p.village || "N/A"}</div>
                  <div><b>Taluk:</b> {p.taluk || "N/A"} | <b>District:</b> {p.district || activeDist}</div>
                  <div><b>Area:</b> {p.area ? `${p.area} acres` : "N/A"}</div>
                  <div style={{ marginTop: "4px" }}>
                    <b>Risk:</b>{" "}
                    <span style={{ background: style.fill, color: "#fff", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 700 }}>
                      {p.risk_category || "LOW"} ({p.risk_score || 0}/100)
                    </span>
                  </div>
                  <div style={{ marginTop: "4px" }}><b>Project:</b> {p.project_id || "Unassigned Land Pool"}</div>
                  <div style={{ marginTop: "4px" }}><b>Status:</b> {p.acquisition_status || "Proposal"}</div>
                  {onNavigateParcel && (
                    <button
                      type="button"
                      onClick={() => onNavigateParcel(p)}
                      style={{
                        marginTop: "8px",
                        width: "100%",
                        padding: "6px 10px",
                        background: "#0f766e",
                        color: "#fff",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer",
                        fontWeight: 600,
                        fontSize: "11px"
                      }}
                    >
                      View Full Land Record Dossier →
                    </button>
                  )}
                </div>
              </Popup>
            );

            if (usePins) {
              return (
                <Marker key={i} position={pos}>
                  {popupContent}
                </Marker>
              );
            }

            return (
              <CircleMarker
                key={i}
                center={pos}
                radius={isSelected ? 10 : (p.risk_category === "CRITICAL" ? 7 : p.risk_category === "HIGH" ? 6 : 5)}
                pathOptions={{
                  fillColor: isSelected ? "#2563eb" : style.fill,
                  fillOpacity: isSelected ? 1.0 : 0.85,
                  color: isSelected ? "#1d4ed8" : style.color,
                  weight: isSelected ? 3 : 1.5
                }}
              >
                {popupContent}
              </CircleMarker>
            );
          })}
        </MapContainer>

        <div style={{
          position: "absolute",
          bottom: "16px",
          left: "16px",
          zIndex: 1000,
          background: "rgba(255, 255, 255, 0.95)",
          padding: "8px 12px",
          borderRadius: "8px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
          fontSize: "11px",
          display: "flex",
          gap: "12px",
          alignItems: "center",
          backdropFilter: "blur(4px)"
        }}>
          <span style={{ fontWeight: 800, color: "#334155" }}>RISK LEGEND:</span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444", display: "inline-block" }}></span> Critical
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#f97316", display: "inline-block" }}></span> High
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#f59e0b", display: "inline-block" }}></span> Medium
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#10b981", display: "inline-block" }}></span> Low
          </span>
        </div>
      </div>
      <div style={{ marginTop: "8px", display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#64748b" }}>
        <span>Showing {filtered.length.toLocaleString()} cadastral demonstration points across {isAll ? (user?.state_scope ? `All ${user.state_scope} Districts` : "All Districts Nationwide") : `${activeDist} District`}</span>
        <span>Click any point or pin on the map to inspect survey intelligence and open dossier</span>
      </div>
    </Panel>
  );
}

function ML() {
  const { data: dashboardData, error } = useData("/ml/dashboard");
  const { data: v } = useData("/ml/versions");
  
  if (error) {
    return (
      <Panel title="ML Monitoring">
        <div className="error" style={{ padding: "16px", borderRadius: "8px", background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b" }}>
          <p style={{ margin: "0 0 8px 0", fontWeight: 700 }}>⚠️ ML Service Unavailable</p>
          <p style={{ margin: 0, fontSize: "13px" }}>
            {error.message || "Unable to reach the ML service. Please verify VITE_API_URL."}
          </p>
        </div>
      </Panel>
    );
  }
  if (!dashboardData) return <Panel title="ML Monitoring">Loading...</Panel>;
  
  return (
    <>
      <Panel title="ML Model Overview">
        <div className="cards">
          <div className="metric"><span>Model Version</span><b>{dashboardData.model_version}</b></div>
          <div className="metric"><span>Status</span><b>{dashboardData.model_status}</b></div>
          <div className="metric"><span>Accuracy</span><b>{dashboardData.accuracy}%</b></div>
          <div className="metric"><span>Predictions Today</span><b>{dashboardData.predictions_today}</b></div>
          <div className="metric"><span>Avg Confidence</span><b>{dashboardData.average_confidence}%</b></div>
          <div className="metric"><span>Data Drift</span><b>{dashboardData.data_drift}</b></div>
        </div>
      </Panel>
      <div className="grid2">
        <Panel title="Recent Risk Predictions">
          <Table rows={dashboardData.recent_predictions || []} cols={["project_id", "survey_no", "risk", "confidence"]} />
        </Panel>
        <Panel title="AI Alerts">
          {dashboardData.alerts?.map((a, i) => <div className="notice" key={i}><b>{a.type}</b>: {a.message} <span style={{float:'right', color: 'red'}}>{a.severity}</span></div>)}
        </Panel>
      </div>
      <Panel title="Model Version History">
        <Table rows={v || []} cols={["version", "accuracy", "status", "created_at"]} />
      </Panel>
    </>
  );
}

function SLA({ selected }) {
  const { data: d } = useData("/sla/timeline/" + (selected?.project_id || "none"), 5000);
  if (!selected?.project_id) return <Placeholder title="SLA & Timeline" />;
  return (
    <Panel title={`SLA & Timeline · ${selected.project_id}`}>
      <div className="timeline">
        {(d || []).map(m => (
          <div className="stage" key={m.stage}>
            <b>{m.stage}</b><span>{m.status}</span>
            <small>Started: {m.planned_date || 'N/A'} · Actual: {m.actual_date || 'N/A'}<br />Delay: {m.delay_days || 0} days</small>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function AlertTable({ rows, columns, onOpen, emptyMessage, actionLabel = "View Details" }) {
  if (!rows.length) return <div className="empty">{emptyMessage}</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}<th>Action</th></tr></thead>
        <tbody>{rows.map((row, index) => (
          <tr key={row.parcel_id || row.project_id || index}>
            {columns.map(c => <td key={c.key}>{c.render ? c.render(row) : String(row[c.key] ?? "N/A")}</td>)}
            <td><button type="button" onClick={() => onOpen(row)}>{actionLabel}</button></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function RefreshButton() {
  return <button type="button" onClick={() => EventBus.dispatch()}>Refresh</button>;
}

function DataPanel({ title, data, error, children, empty = false }) {
  if (error) return <Panel title={title}><div className="error">Unable to load {title} ({error.status || "network error"}): {error.message} <RefreshButton /></div></Panel>;
  if (!data) return <Panel title={title}><p>Loading {title.toLowerCase()}...</p></Panel>;
  if (empty) return <Panel title={title}><div className="empty">No {title.toLowerCase()} found.</div><RefreshButton /></Panel>;
  return children;
}

function RiskIntelligence({ district, go }) {
  const dist = district || "Coimbatore";
  const { data, error } = useData(`/analytics/operations?district=${encodeURIComponent(dist)}`, 5000);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("ALL");
  const [explanationParcel, setExplanationParcel] = useState(null);
  const { data: explanation, error: explanationError } = useData(explanationParcel ? `/ml/parcels/${explanationParcel.parcel_id}/explanation` : null);
  if (error || !data) return <DataPanel title={`Risk Intelligence (${dist})`} data={data} error={error} />;
  const risk = data.risk;
  const matches = row => `${row.parcel_id || ""} ${row.survey_no || ""} ${row.project_id || ""} ${row.project_name || ""} ${row.village || ""} ${row.taluk || ""} ${row.district || ""}`.toLowerCase().includes(query.toLowerCase());
  const rows = risk.top_parcels.filter(r => (category === "ALL" || r.risk_category === category) && matches(r));
  const open = row => go({ project_id: row.project_id, parcel_id: row.parcel_id, record_id: row.record_id, survey_no: row.survey_no });
  return (
    <>
      <Panel title={`Risk Intelligence · ${dist}`}>
        <div className="toolbar"><input aria-label="Search risk records" placeholder="Search parcel, survey, project, village..." value={query} onChange={e => setQuery(e.target.value)} /><select value={category} onChange={e => setCategory(e.target.value)}><option value="ALL">All categories</option><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option><option value="CRITICAL">Critical</option></select><RefreshButton /></div>
        {risk.prediction_count === 0 && <div className="notice">No risk predictions available for {dist}.</div>}
        {risk.synthetic_note && <div className="notice">{risk.synthetic_note}</div>}
        <div className="cards">
          <div className="metric"><span>Total Risk Parcels</span><b>{risk.total}</b></div>
          {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map(level => <div className="metric" key={level}><span>{level} RISK</span><b>{data.parcels.risk_distribution.find(x => x.category === level)?.count || 0}</b></div>)}
          <div className="metric"><span>Average Risk Score</span><b>{risk.average_score ?? "N/A"}</b></div>
        </div>
      </Panel>
      <div className="grid2">
        <Panel title="Risk Distribution">{risk.prediction_count ? <Table rows={risk.prediction_distribution} cols={["category", "count"]} /> : <div className="empty">No risk predictions available.</div>}</Panel>
        <Panel title="Project-wise Risk"><Table rows={risk.project_wise.slice(0, 20)} cols={["project_id", "project_name", "parcels", "high_risk", "average_risk_score"]} onClick={r => go({ project_id: r.project_id })} /></Panel>
      </div>
      <Panel title="Village-wise Risk"><Table rows={risk.village_wise.slice(0, 30)} cols={["village", "taluk", "district", "parcels", "high_risk", "average_risk_score"]} /></Panel>
      <Panel title="Top High-risk Parcels">
        <AlertTable rows={rows} columns={[{key:"parcel_id",label:"Parcel ID"},{key:"survey_no",label:"Survey Number"},{key:"project_id",label:"Project"},{key:"project_name",label:"Project Name"},{key:"village",label:"Village"},{key:"taluk",label:"Taluk"},{key:"district",label:"District"},{key:"risk_category",label:"Risk Category"},{key:"risk_score",label:"Risk Score",render:r=>r.risk_score ?? "N/A"},{key:"assessed_at",label:"Assessed"}]} onOpen={row => setExplanationParcel(row)} actionLabel="View Explanation" emptyMessage="No risk records available." />
      </Panel>
      {explanationParcel && <RiskExplanation parcel={explanationParcel} explanation={explanation} error={explanationError} onClose={() => setExplanationParcel(null)} />}
    </>
  );
}

function RiskExplanation({ parcel, explanation, error, onClose }) {
  return <Panel title="PARCEL RISK EXPLANATION">
    <button type="button" onClick={onClose}>Close Explanation</button>
    <div className="status-card"><p><b>Survey Number:</b> {parcel.survey_no}</p><p><b>Village / Taluk:</b> {parcel.village} / {parcel.taluk}</p><p><b>Project:</b> {parcel.project_name || parcel.project_id}</p>{error ? <div className="error">Unable to load risk explanation ({error.status || "network error"}): {error.message}</div> : !explanation ? <p>Loading risk explanation...</p> : <><p><b>Model Risk Score:</b> {explanation.risk_score}</p><p><b>Model Risk Category:</b> {explanation.risk_category}</p><p><b>Stored Parcel Classification:</b> {explanation.stored_risk_category || "N/A"}</p><p><b>Model Confidence:</b> {(explanation.confidence * 100).toFixed(2)}%</p><p><b>Explainer:</b> {explanation.explanation_method} ({explanation.output_space})</p><p><b>Base Prediction:</b> {explanation.base_value} <b>Final Prediction:</b> {explanation.final_value}</p><h3>WHY DOES THE MODEL CLASSIFY THIS PARCEL THIS WAY?</h3><div>{explanation.features.slice(0,8).map(f => <div key={f.name + f.display_name} style={{display:"grid",gridTemplateColumns:"2fr 1fr 2fr",gap:"8px",alignItems:"center",margin:"6px 0"}}><span>{f.display_name}</span><span>{String(f.value ?? "N/A")}</span><span style={{color:f.shap_value >= 0 ? "#b42318" : "#16704a"}}>{f.shap_value >= 0 ? "+" : ""}{f.shap_value}</span><i style={{height:"8px",width:`${Math.min(100,Math.abs(f.shap_value)*400)}%`,background:f.shap_value >= 0 ? "#d92d20" : "#12b76a",display:"block"}} /></div>)}</div><h3>Recommended operational action based on risk factors</h3><ul>{explanation.recommended_actions.map(action => <li key={action}>{action}</li>)}</ul></>}</div>
  </Panel>;
}

function AlertsPage({ district, go }) {
  const dist = district || "Coimbatore";
  const { data, error } = useData(`/alerts/operations?district=${encodeURIComponent(dist)}`, 5000);
  const [filter, setFilter] = useState("All");
  const [query, setQuery] = useState("");
  if (error || !data) return <DataPanel title={`Alerts (${dist})`} data={data} error={error} />;
  const visible = data.filter(a => (filter === "All" || (filter === "Unread" ? a.read_status === "Unread" : a.category === filter)) && `${a.type} ${a.message} ${a.project_id || ""} ${a.survey_no || ""} ${a.district || ""}`.toLowerCase().includes(query.toLowerCase()));
  const open = row => { if (row.parcel_id) go({ project_id: row.project_id, parcel_id: row.parcel_id, record_id: row.record_id, survey_no: row.survey_no }); else if (row.project_id) go({ project_id: row.project_id }); };
  return <Panel title={`Operational Alerts · ${dist}`}>
    <div className="toolbar"><input aria-label="Search alerts" placeholder="Search alert, project, parcel, district..." value={query} onChange={e => setQuery(e.target.value)} /><select value={filter} onChange={e => setFilter(e.target.value)}>{["All", "Unread", "Risk", "SLA", "Project", "Grievance", "Verification"].map(x => <option key={x}>{x}</option>)}</select><RefreshButton /></div>
    <AlertTable rows={visible} columns={[{key:"type",label:"Alert Type"},{key:"category",label:"Category"},{key:"message",label:"Message"},{key:"project_id",label:"Project"},{key:"survey_no",label:"Parcel / Survey",render:r=>r.parcel_id ? `${r.parcel_id} / ${r.survey_no || "N/A"}` : "N/A"},{key:"district",label:"District"},{key:"created_at",label:"Created"},{key:"severity",label:"Severity"},{key:"read_status",label:"Read Status"},{key:"assigned_to",label:"Relevant User / Role"}]} onOpen={open} emptyMessage="No alerts found." />
    {visible.filter(a => a.status === "Open").map(a => <ActionButton key={a.alert_id} label={`Acknowledge ${a.alert_id}`} onClick={() => api(`/alerts/${a.alert_id}`, { method: "PATCH", body: JSON.stringify({ status: "Acknowledged" }) }).then(() => EventBus.dispatch())} />)}
  </Panel>;
}

function AnalyticsPage({ district, go }) {
  const dist = district || "Coimbatore";
  const { data, error } = useData(`/analytics/operations?district=${encodeURIComponent(dist)}`, 5000);
  if (error || !data) return <DataPanel title={`Analytics (${dist})`} data={data} error={error} />;
  const kpis = [["Total Projects", data.projects.total], ["Active Projects", data.projects.active], ["Delayed Projects", data.projects.delayed], ["Completed Projects", data.projects.completed], ["Total Parcels", data.parcels.total], ["Affected Parcels", data.parcels.affected], ["Verified Parcels", data.parcels.verified], ["Pending Verification", data.parcels.pending_verification], ["SLA Due Soon", data.sla.due_soon], ["SLA Breached", data.sla.breached], ["Compensation Pending", data.acquisition.compensation_pending], ["Open Grievances", (data.grievances.by_status.find(x => x.status === "Open") || {}).count || 0]];
  return <>
    <Panel title={`Operational Analytics · ${dist}`}><div className="toolbar"><RefreshButton /></div><div className="cards">{kpis.map(k => <div className="metric" key={k[0]}><span>{k[0]}</span><b>{k[1]}</b></div>)}</div></Panel>
    <div className="grid2"><Panel title="Projects by Stage"><Table rows={data.projects.by_stage} cols={["stage", "count"]} /></Panel><Panel title="Projects by District"><Table rows={data.projects.by_district} cols={["district", "count"]} /></Panel></div>
    <Panel title="Project Risk Detail"><AlertTable rows={data.risk.project_wise.slice(0, 30)} columns={[{key:"project_id",label:"Project ID"},{key:"project_name",label:"Project Name"},{key:"parcels",label:"Parcels"},{key:"high_risk",label:"High / Critical"},{key:"average_risk_score",label:"Average Risk Score"}]} onOpen={r => go({ project_id: r.project_id })} emptyMessage="No project analytics available." /></Panel>
    <div className="grid2"><Panel title="Parcel Risk Distribution"><Table rows={data.parcels.risk_distribution} cols={["category", "count", "average_score"]} /></Panel><Panel title="Acquisition Stage Distribution"><Table rows={data.acquisition.by_stage} cols={["stage", "count"]} /></Panel></div>
    <div className="grid2"><Panel title="Compensation / Possession"><Table rows={[{status:"Pending",count:data.acquisition.compensation_pending},{status:"Paid",count:data.acquisition.compensation_completed},...(data.acquisition.possession || [])]} cols={["status", "count"]} /></Panel><Panel title="Rehabilitation / R&R"><Table rows={data.acquisition.rehabilitation} cols={["status", "count"]} /></Panel></div>
    <div className="grid2"><Panel title="SLA Analytics"><Table rows={[{status:"Due Soon",count:data.sla.due_soon},{status:"Breached",count:data.sla.breached},{status:"Average Delay",count:data.sla.average_delay},{status:"Bottlenecks",count:data.sla.bottlenecks}]} cols={["status", "count"]} /></Panel><Panel title="Grievances"><Table rows={data.grievances.by_status.length ? data.grievances.by_status : [{status:"Total",count:data.grievances.total}]} cols={["status", "count"]} /></Panel></div>
  </>;
}

function Bottlenecks({ district, go }) {
  const dist = district || "Coimbatore";
  const { data, error } = useData(`/sla/operations?district=${encodeURIComponent(dist)}`, 5000);
  const [query, setQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");

  if (error) return <Panel title={`Operational Bottlenecks (${dist})`}><div className="error">Unable to load bottleneck operations ({error.status || "network error"}): {error.message}</div></Panel>;
  if (!data) return <Panel title={`Operational Bottlenecks (${dist})`}><p>Loading operational records...</p></Panel>;

  const matches = row => {
    const text = `${row.project_id || ""} ${row.project_name || ""} ${row.district || ""} ${row.stage || row.current_stage || ""} ${row.survey_no || ""} ${row.village || ""}`.toLowerCase();
    return text.includes(query.toLowerCase());
  };
  const bottlenecks = data.process_bottlenecks.filter(matches);
  const dueSoon = data.sla_due_soon.filter(matches);
  const breached = data.sla_breached.filter(matches);
  const risks = data.risk_alerts.filter(r => (riskFilter === "ALL" || r.risk_category === riskFilter) && matches(r));
  const openProject = row => go({ project_id: row.project_id, parcel_id: row.parcel_id, record_id: row.record_id, survey_no: row.survey_no });
  const projectColumns = [
    { key: "project_id", label: "Project ID" }, { key: "project_name", label: "Project Name" },
    { key: "district", label: "District" }, { key: "current_stage", label: "Current Stage" },
    { key: "progress", label: "Progress", render: r => `${r.progress ?? 0}%` },
    { key: "days_at_stage", label: "Days at Stage" }, { key: "project_status", label: "Status" },
    { key: "responsible_officer", label: "Responsible Officer" }, { key: "reason", label: "Reason" },
  ];
  const slaColumns = [
    { key: "project_id", label: "Project ID" }, { key: "project_name", label: "Project Name" },
    { key: "current_stage", label: "Current Stage" }, { key: "due_date", label: "Due Date" },
    { key: "days_remaining", label: "Days Remaining", render: r => r.sla_status === "SLA Breached" ? "-" : r.days_remaining },
    { key: "days_overdue", label: "Days Overdue", render: r => r.sla_status === "SLA Breached" ? r.days_overdue || r.delay_days : "-" },
    { key: "responsible_officer", label: "Responsible Officer" }, { key: "reason", label: "Reason" },
  ];
  const riskColumns = [
    { key: "parcel_id", label: "Parcel ID" }, { key: "survey_no", label: "Survey Number" },
    { key: "village", label: "Village" }, { key: "project_id", label: "Project" },
    { key: "risk_category", label: "Risk Category" }, { key: "risk_score", label: "Risk Score", render: r => r.risk_score ?? "N/A" },
    { key: "current_stage", label: "Current Stage" }, { key: "responsible_officer", label: "Responsible Officer" },
  ];

  return (
    <>
      <Panel title={`Bottleneck Operations · ${dist}`}>
        <div className="toolbar">
          <input aria-label="Filter operational alerts" placeholder="Filter project, district, stage, survey..." value={query} onChange={e => setQuery(e.target.value)} />
          <select aria-label="Filter risk alerts" value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
            <option value="ALL">All risk alerts</option><option value="HIGH">High risk</option><option value="CRITICAL">Critical risk</option>
          </select>
        </div>
        <div className="cards">
          <div className="metric"><span>EPO / PROCESS BOTTLENECKS</span><b>{bottlenecks.length}</b></div>
          <div className="metric"><span>SLA DUE SOON</span><b>{dueSoon.length}</b></div>
          <div className="metric"><span>SLA BREACHED</span><b>{breached.length}</b></div>
          <div className="metric"><span>HIGH RISK</span><b>{risks.filter(r => r.risk_category === "HIGH").length}</b></div>
          <div className="metric"><span>CRITICAL RISK</span><b>{risks.filter(r => r.risk_category === "CRITICAL").length}</b></div>
        </div>
      </Panel>
      <Panel title="EPO / PROCESS BOTTLENECKS">
        <AlertTable rows={bottlenecks} columns={projectColumns} onOpen={openProject} emptyMessage="No active process bottlenecks match the current filter." />
      </Panel>
      <Panel title="SLA DUE SOON">
        <AlertTable rows={dueSoon} columns={slaColumns} onOpen={openProject} emptyMessage="No active milestone is due within 7 days." />
      </Panel>
      <Panel title="SLA BREACHED">
        <AlertTable rows={breached} columns={slaColumns} onOpen={openProject} emptyMessage="No active milestone is past its due date or has a recorded delay." />
      </Panel>
      <Panel title="HIGH RISK / CRITICAL RISK">
        <div className="notice">{data.risk_data_note}</div>
        <AlertTable rows={risks} columns={riskColumns} onOpen={openProject} emptyMessage="No stored high or critical parcel risk alerts match the current filter." />
      </Panel>
    </>
  );
}

function Reports({ district, user }) {
  const dist = district || "Coimbatore";
  const { data: d, error: reportErr } = useData(`/reports/?district=${encodeURIComponent(dist)}`);
  
  // Use the new /reports/project-list endpoint instead of the projects endpoint, which is faster.
  const { data: pl } = useData(`/reports/project-list?district=${encodeURIComponent(dist)}`);
  
  const [selectedProject, setSelectedProject] = useState("");

  const downloadPDF = async (url, filename) => {
    const token = localStorage.getItem("survi_token");
    const fullUrl = url.startsWith("http://") || url.startsWith("https://") ? url : `${API}${url}`;
    const res = await fetch(fullUrl, {
      headers: { ...(token && token !== "null" && token !== "undefined" ? { "Authorization": `Bearer ${token}` } : {}) }
    });
    if (!res.ok) {
      if (res.status === 401) {
        throw new Error("Session expired. Please log in again.");
      } else if (res.status === 403) {
        throw new Error("You do not have permission to download this report.");
      }
      const text = await res.text();
      throw new Error(`Failed to download PDF: ${res.status} - ${text}`);
    }
    const blob = await res.blob();
    const objUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(objUrl);
  };

  if (reportErr) {
    return (
      <Panel title={`MIS Reports (${dist})`}>
        <div className="error" style={{ padding: "16px", borderRadius: "8px", background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b" }}>
          <p style={{ margin: "0 0 8px 0", fontWeight: 700 }}>⚠️ Reports Unavailable</p>
          <p style={{ margin: 0, fontSize: "13px" }}>
            {reportErr.message || "Unable to reach the reports service. Please verify VITE_API_URL."}
          </p>
        </div>
      </Panel>
    );
  }
  if (!d) return <Panel title={`MIS Reports (${dist})`}>Loading...</Panel>;
  
  const isCitizen = user?.role === "citizen";
  const isStateAuth = user?.role === "state_authority" || user?.role === "admin" || user?.role === "authority";

  return (
    <>
      <Cards d={{ total_projects: d.summary.total_projects, active_projects: d.summary.active_projects, completed_projects: d.summary.completed_projects, delayed_projects: d.summary.delayed_cases, pending_compensation: d.summary.total_pending_compensation }} />
      
      {!isCitizen && (
        <Panel title={`PDF Reports & Downloads · ${dist}`}>
          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '20px' }}>
            <div style={{ flex: '1', minWidth: '300px', padding: '15px', border: '1px solid #cbd5e1', borderRadius: '6px' }}>
              <h4 style={{ marginTop: 0, color: '#0f6c70', marginBottom: '5px' }}>Project Reports</h4>
              <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '15px', marginTop: 0 }}>Select a project to generate a detailed or bottleneck report.</p>
              
              <select 
                value={selectedProject} 
                onChange={e => setSelectedProject(e.target.value)}
                style={{ width: '100%', padding: '8px', marginBottom: '15px', borderRadius: '4px', border: '1px solid #ccc' }}
              >
                <option value="">-- Select Project --</option>
                {pl && pl.map(p => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.project_id} - {p.project_name}
                  </option>
                ))}
              </select>
              
              <div style={{ display: 'flex', gap: '10px' }}>
                <ActionButton 
                  label="📄 Project Detailed PDF" 
                  disabled={!selectedProject}
                  onClick={() => downloadPDF(`/reports/project/${selectedProject}/pdf`, `Project_${selectedProject}.pdf`)} 
                />
                <ActionButton 
                  label="⚠️ Bottleneck PDF" 
                  disabled={!selectedProject}
                  onClick={() => downloadPDF(`/reports/project/${selectedProject}/bottlenecks/pdf`, `Bottlenecks_${selectedProject}.pdf`)} 
                />
              </div>
            </div>
            
            <div style={{ flex: '1', minWidth: '300px', padding: '15px', border: '1px solid #cbd5e1', borderRadius: '6px' }}>
              <h4 style={{ marginTop: 0, color: '#0f6c70', marginBottom: '5px' }}>District & State Reports</h4>
              <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '15px', marginTop: 0 }}>Generate aggregate reports for the selected district or entire state.</p>
              
              <div style={{ display: 'flex', gap: '10px', flexDirection: 'column', alignItems: 'flex-start' }}>
                <ActionButton 
                  label={`📊 Download ${dist} District Report`} 
                  onClick={() => downloadPDF(`/reports/district/${encodeURIComponent(dist)}/pdf`, `District_${dist.replace(' ', '_')}.pdf`)} 
                />
                
                {isStateAuth && (
                  <ActionButton 
                    label="🏢 Download State-wide Comparison Report" 
                    onClick={() => downloadPDF(`/reports/state/pdf`, `State_Report.pdf`)} 
                  />
                )}
              </div>
            </div>
          </div>
        </Panel>
      )}

      <Panel title={`Project Progress Summary · ${dist}`}>
        <Table rows={d.project_wise || []} cols={["project_id", "project_name", "current_stage", "progress"]} />
      </Panel>
    </>
  );
}

function FieldVerification({ district, user, go, onNavigateRR }) {
  const dist = user?.district_scope || district || "Coimbatore";
  const { data: d, error } = useData(`/field/assigned?district=${encodeURIComponent(dist)}`, 3000);
  const { data: dssPriority } = useData(`/dss/priority-parcels?district=${encodeURIComponent(dist)}&limit=10`, 10000);
  const [activeDssParcel, setActiveDssParcel] = useState(null);
  const [askAiOpen, setAskAiOpen] = useState(false);
  const [inspectingParcel, setInspectingParcel] = useState(null);
  const [groundForm, setGroundForm] = useState({ condition: "Pucca residential dwelling / Clear demarcation", gps_lat: "11.0168", gps_lon: "76.9558", remarks: "Site visit conducted. Boundary pillars verified. Physical structures matched with land records." });
  const [savingGround, setSavingGround] = useState(false);

  if (error) return <Panel title={`Field Verification Worklist (${dist})`}><div className="error">Unable to load field assignments ({error.status || "network error"}): {error.message} <RefreshButton /></div></Panel>;
  if (!d) return <Panel title={`Field Verification Worklist (${dist})`}><p>Loading field assignments...</p></Panel>;

  const handleSaveGroundInspection = async (parcelId) => {
    setSavingGround(true);
    try {
      await api(`/field/${parcelId}/verify`, {
        method: "POST",
        body: JSON.stringify({
          remarks: groundForm.remarks,
          gps_lat: parseFloat(groundForm.gps_lat) || null,
          gps_lon: parseFloat(groundForm.gps_lon) || null,
          house_condition: groundForm.condition
        })
      });
      EventBus.dispatch();
      setInspectingParcel(null);
    } catch (err) {
      alert("Failed to submit ground verification: " + err.message);
    } finally {
      setSavingGround(false);
    }
  };

  const pendingAssignments = d.filter(r => (r.assignment_status || "").toLowerCase().includes("pending"));

  return (
    <>
      {/* ── AI Priority Verification Queue (DSS) ── */}
      {dssPriority?.items && dssPriority.items.length > 0 && (
        <Panel title={`🤖 AI Priority Verification Queue · ${dist} (${dssPriority.items.length} prioritized parcels)`}>
          <div style={{ background: "#e8f0fe", padding: "10px 14px", borderRadius: "8px", border: "1px solid #c2e7ff", marginBottom: "14px", fontSize: "12px", color: "#1967d2" }}>
            <b>Field Officer Decision Support:</b> High & critical risk parcels requiring ground verification, boundary check, or evidence collection are ranked by composite priority score.
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Parcel ID</th>
                  <th>Project</th>
                  <th>Priority Score</th>
                  <th>Risk Level</th>
                  <th>Data Quality</th>
                  <th>AI Recommendation</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {dssPriority.items.map((p, idx) => (
                  <tr key={p.parcel_id} style={{ background: idx === 0 ? "#fffbf0" : "inherit" }}>
                    <td><b>#{idx + 1}</b></td>
                    <td><span style={{ fontWeight: 700, color: "#0f6c70" }}>{p.record_id || `P-${p.parcel_id}`}</span></td>
                    <td>{p.project_id || "Unassigned"}</td>
                    <td><b style={{ color: p.priority_score > 70 ? "#b42318" : "#202124" }}>{p.priority_score}/100</b></td>
                    <td><DSSBadge level={p.risk_level} /></td>
                    <td>{p.components?.data_quality?.label}</td>
                    <td style={{ maxWidth: "320px", fontSize: "12px", fontWeight: 500 }}>{p.recommendation}</td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      <button
                        type="button"
                        onClick={() => setActiveDssParcel(activeDssParcel?.parcel_id === p.parcel_id ? null : p)}
                        style={{ padding: "4px 8px", background: activeDssParcel?.parcel_id === p.parcel_id ? "#334155" : "#1a73e8", color: "#fff", border: "none", borderRadius: "4px", fontSize: "11px", fontWeight: 600, cursor: "pointer", marginRight: "6px" }}
                      >
                        {activeDssParcel?.parcel_id === p.parcel_id ? "Hide DSS" : "Review AI Decision"}
                      </button>
                      <button
                        type="button"
                        onClick={() => go({ parcel_id: p.parcel_id, id: p.parcel_id })}
                        style={{ padding: "4px 8px", background: "#0f6c70", color: "#fff", border: "none", borderRadius: "4px", fontSize: "11px", fontWeight: 600, cursor: "pointer" }}
                      >
                        Open Dossier →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Expanded Inline DSS Decision Card */}
          {activeDssParcel && (
            <div style={{ marginTop: "14px" }}>
              <DSSCard
                title={`AI Decision Support — Parcel ${activeDssParcel.record_id || activeDssParcel.parcel_id}`}
                assessment={activeDssParcel}
                recommendation={{ recommendation: activeDssParcel.recommendation, suggested_actions: activeDssParcel.suggested_actions }}
                userRole={user?.role}
                onAction={async (action, notes) => {
                  const res = await api("/dss/decision", {
                    method: "POST",
                    body: JSON.stringify({
                      recommendation_id: activeDssParcel.recommendation_id,
                      entity_type: "parcel",
                      entity_id: String(activeDssParcel.parcel_id),
                      action: action,
                      modified_notes: notes
                    })
                  });
                  EventBus.dispatch();
                  return res;
                }}
                onAskAi={() => setAskAiOpen(true)}
              />
            </div>
          )}
        </Panel>
      )}

      {/* Ask AI Modal for Field Officer */}
      {activeDssParcel && (
        <AskAiModal
          isOpen={askAiOpen}
          onClose={() => setAskAiOpen(false)}
          entityType="parcel"
          entityId={String(activeDssParcel.parcel_id)}
          onAsk={async (entityType, entityId, question) => {
            return await api("/dss/ask", {
              method: "POST",
              body: JSON.stringify({ entity_type: entityType, entity_id: entityId, question: question })
            });
          }}
        />
      )}

      <div data-tutorial="field-queue">
        <Panel title={`Field Verification · Ground & Parcel Inspection · ${dist} District`}>
        {pendingAssignments.length > 0 && (
          <div className="notice" style={{ marginBottom: "16px", borderLeft: "4px solid #f59e0b", background: "#fffbeb", padding: "12px 16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <b style={{ color: "#b45309" }}>⚡ Active Field Assignment ({pendingAssignments.length} Pending)</b>
              <small style={{ color: "#78350f", fontWeight: 700 }}>Real-time Database Sync</small>
            </div>
            <div style={{ fontSize: "12px", marginTop: "6px", display: "flex", flexDirection: "column", gap: "4px" }}>
              {pendingAssignments.slice(0, 3).map(p => (
                <div key={p.parcel_id} style={{ color: "#92400e" }}>
                  • <b>New Assignment</b> → Project: <b>{p.project_id}</b> | Survey No: <b>{p.survey_no}</b> | Parcel ID: <b>{p.parcel_id}</b> | District: <b>{p.district || dist}</b> | Status: <span style={{ background: "#fef3c7", padding: "1px 6px", borderRadius: "4px", fontWeight: 700 }}>{p.assignment_status || "Pending Verification"}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ marginBottom: "14px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
          <div>
            <p style={{ margin: 0, fontSize: "13px", color: "#334155", fontWeight: 600 }}>
              Ground-level physical parcel verification, boundary inspection, GPS tagging, and site evidence capture.
            </p>
            <span style={{ fontSize: "11px", color: "#64748b" }}>
              Complete R&R verification and affected family entitlements are managed in the <b>R&R Workflow</b> workspace.
            </span>
          </div>
          <span style={{ fontSize: "12px", fontWeight: 700, color: "#0f6c70", background: "#f0fdfa", padding: "4px 12px", borderRadius: "12px", border: "1px solid #99f6e4" }}>
            Assigned Parcels: {d.length}
          </span>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Parcel ID</th>
                <th>Survey No</th>
                <th>Project</th>
                <th>Village / Taluk</th>
                <th>Landowner</th>
                <th>Physical / Site Visit</th>
                <th>R&R Overview</th>
                <th>Assignment Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {d.map(r => {
                const readiness = r.readiness_percentage !== undefined && r.readiness_percentage !== null ? r.readiness_percentage : 0;
                const badgeColor = readiness >= 90 ? "#16704a" : (readiness >= 75 ? "#0f6c70" : (readiness >= 50 ? "#d97706" : "#dc2626"));
                const badgeBg = readiness >= 90 ? "#e6f4ea" : (readiness >= 75 ? "#e0f2f1" : (readiness >= 50 ? "#fef3c7" : "#fee2e2"));
                const isVerified = (r.verification_status || r.assignment_status) === "Verified";

                return (
                  <tr key={r.assignment_id || r.parcel_id}>
                    <td><b>{r.parcel_id}</b></td>
                    <td><b>{r.survey_no}</b></td>
                    <td><span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>{r.project_id}</span></td>
                    <td>{r.village} / {r.taluk}</td>
                    <td><b>{r.landowner || r.family_head || "Landowner"}</b></td>
                    <td>
                      <span style={{
                        background: isVerified ? "#e6f4ea" : "#f1f5f9",
                        color: isVerified ? "#16704a" : "#475569",
                        padding: "2px 8px", borderRadius: "10px", fontSize: "11px", fontWeight: 700
                      }}>
                        {isVerified ? "✓ Site Inspected" : "Pending Inspection"}
                      </span>
                      {r.verified_at && <div style={{ fontSize: "10px", color: "#64748b", marginTop: "2px" }}>Date: {r.verified_at.split("T")[0]}</div>}
                    </td>
                    <td>
                      <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <span style={{ background: badgeBg, color: badgeColor, padding: "1px 6px", borderRadius: "8px", fontSize: "10px", fontWeight: 700 }}>
                            {r.rr_status || "Pending"}
                          </span>
                          <span style={{ fontSize: "11px", fontWeight: 700 }}>{readiness}%</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            if (onNavigateRR) {
                              onNavigateRR({
                                family_id: r.family_id,
                                parcel_id: r.parcel_id,
                                project_id: r.project_id,
                                district: r.district || dist
                              });
                            }
                          }}
                          style={{
                            background: "none", border: "none", color: "#0f6c70",
                            fontSize: "11px", fontWeight: 700, padding: 0, textAlign: "left",
                            cursor: "pointer", textDecoration: "underline"
                          }}
                        >
                          → Open R&R Workflow
                        </button>
                      </div>
                    </td>
                    <td>
                      <span style={{
                        background: isVerified ? "#e6f4ea" : "#fef3c7",
                        color: isVerified ? "#16704a" : "#b45309",
                        padding: "2px 8px", borderRadius: "10px", fontSize: "11px", fontWeight: 700
                      }}>
                        {r.assignment_status || (isVerified ? "Verified" : "Assigned")}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button
                          type="button"
                          onClick={() => setInspectingParcel(r)}
                          style={{
                            background: "#0f6c70", color: "#ffffff", border: "none",
                            padding: "5px 9px", borderRadius: "5px", fontSize: "11px", fontWeight: 700,
                            cursor: "pointer"
                          }}
                        >
                          🔍 Ground Inspection
                        </button>
                        <button
                          type="button"
                          onClick={() => go({ project_id: r.project_id, parcel_id: r.parcel_id })}
                          style={{
                            background: "#475569", color: "#ffffff", border: "none",
                            padding: "5px 8px", borderRadius: "5px", fontSize: "11px", cursor: "pointer"
                          }}
                        >
                          Photos / OCR
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {d.length === 0 && (
                <tr>
                  <td colSpan={9} style={{ textAlign: "center", padding: "20px", color: "#64748b" }}>
                    No field assignments found for {dist} District.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
      </div>

      {/* General Ground / Physical Inspection Quick Modal */}
      {inspectingParcel && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(3px)",
          display: "flex", justifyContent: "center", alignItems: "center", zIndex: 10000, padding: "16px"
        }}>
          <div style={{
            background: "#ffffff", borderRadius: "10px", width: "100%", maxWidth: "560px",
            padding: "20px", boxShadow: "0 20px 45px rgba(0,0,0,0.3)", border: "1px solid #cbd5e1"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", paddingBottom: "10px", marginBottom: "14px" }}>
              <div>
                <b style={{ fontSize: "11px", color: "#0f6c70", textTransform: "uppercase" }}>Ground Inspection Log</b>
                <h3 style={{ margin: "2px 0 0", color: "#0f172a" }}>Parcel {inspectingParcel.parcel_id} · Survey {inspectingParcel.survey_no}</h3>
              </div>
              <button onClick={() => setInspectingParcel(null)} style={{ background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "4px", padding: "3px 8px", cursor: "pointer" }}>✕</button>
            </div>

            <div style={{ display: "grid", gap: "10px", fontSize: "12px" }}>
              <label>
                <b>House / Land Physical Condition:</b>
                <input
                  style={{ width: "100%", padding: "7px", border: "1px solid #cbd5e1", borderRadius: "5px", marginTop: "3px" }}
                  value={groundForm.condition} onChange={e => setGroundForm({ ...groundForm, condition: e.target.value })}
                />
              </label>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <label>
                  <b>GPS Latitude:</b>
                  <input
                    style={{ width: "100%", padding: "7px", border: "1px solid #cbd5e1", borderRadius: "5px", marginTop: "3px" }}
                    value={groundForm.gps_lat} onChange={e => setGroundForm({ ...groundForm, gps_lat: e.target.value })}
                  />
                </label>
                <label>
                  <b>GPS Longitude:</b>
                  <input
                    style={{ width: "100%", padding: "7px", border: "1px solid #cbd5e1", borderRadius: "5px", marginTop: "3px" }}
                    value={groundForm.gps_lon} onChange={e => setGroundForm({ ...groundForm, gps_lon: e.target.value })}
                  />
                </label>
              </div>

              <label>
                <b>Field Inspection Remarks:</b>
                <textarea
                  rows={3}
                  style={{ width: "100%", padding: "7px", border: "1px solid #cbd5e1", borderRadius: "5px", marginTop: "3px", font: "inherit" }}
                  value={groundForm.remarks} onChange={e => setGroundForm({ ...groundForm, remarks: e.target.value })}
                />
              </label>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "16px", paddingTop: "12px", borderTop: "1px solid #e2e8f0" }}>
              <button
                type="button"
                onClick={() => {
                  const p = inspectingParcel;
                  setInspectingParcel(null);
                  if (onNavigateRR) onNavigateRR({ family_id: p.family_id, parcel_id: p.parcel_id, project_id: p.project_id });
                }}
                style={{ background: "none", border: "none", color: "#0f6c70", fontWeight: 700, fontSize: "11px", cursor: "pointer", textDecoration: "underline" }}
              >
                Go to Complete R&R Workflow →
              </button>

              <div style={{ display: "flex", gap: "8px" }}>
                <button type="button" onClick={() => setInspectingParcel(null)} style={{ background: "#f1f5f9", border: "1px solid #cbd5e1", padding: "6px 12px", borderRadius: "5px" }}>Cancel</button>
                <button
                  type="button"
                  disabled={savingGround}
                  onClick={() => handleSaveGroundInspection(inspectingParcel.parcel_id)}
                  style={{ background: "#16704a", color: "#fff", border: "none", padding: "6px 14px", borderRadius: "5px", fontWeight: 700, cursor: "pointer" }}
                >
                  {savingGround ? "Saving..." : "✓ Submit Ground Check"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Grievances({ district, user }) {
  const dist = district || "Coimbatore";
  const { data: all_grievances } = useData(`/grievances/all?district=${encodeURIComponent(dist)}`);
  const [form, setForm] = useState({ parcel_id: "", project_id: "", type: "Compensation", description: "" });
  
  return (
    <>
      {user.role === "citizen" && (
        <Panel title="Submit Grievance">
          <div className="form">
            <label>Parcel ID <input value={form.parcel_id} onChange={e => setForm({...form, parcel_id: e.target.value})} /></label>
            <label>Project ID <input value={form.project_id} onChange={e => setForm({...form, project_id: e.target.value})} /></label>
            <label>Type 
              <select value={form.type} onChange={e => setForm({...form, type: e.target.value})}>
                <option>Compensation</option><option>Ownership</option><option>Boundary</option><option>Survey</option>
              </select>
            </label>
            <label>Description <input value={form.description} onChange={e => setForm({...form, description: e.target.value})} /></label>
          </div>
          <ActionButton label="Submit Grievance" onClick={() => {
            if (!form.parcel_id || !form.project_id) throw Error("Fill required fields");
            return api("/grievances/", { method: "POST", body: JSON.stringify({...form, submitted_by: user.email}) })
          }} />
        </Panel>
      )}
      
      <Panel title={`Grievance Management · ${dist}`}>
        <Table rows={all_grievances || []} cols={["id", "parcel_id", "project_id", "submitted_by", "type", "status", "created_at"]} actions={(r) => (
          (user.role === "district_authority" && r.status !== "Resolved") ? 
          <ActionButton label="Resolve" onClick={() => api(`/grievances/${r.id}/resolve`, { method: "POST", body: JSON.stringify({ resolution: "Resolved by officer" }) })} /> 
          : null
        )}/>
      </Panel>
    </>
  );
}

function CitizenDash({ lang, user }) {
  const t = (en, ta) => lang === "ta" ? ta : en;

  // 1. Fetch authenticated citizen's personal land records
  const { data: myParcelsData, error: parcelsError } = useData("/land-records/mine", 5000);
  const myParcels = myParcelsData?.items || [];
  const [activeParcelIndex, setActiveParcelIndex] = useState(0);
  const currentParcel = myParcels[activeParcelIndex] || null;

  // 2. Fetch authenticated citizen's compensation records
  const { data: compensation, error: compensationError } = useData("/compensation/mine", 5000);

  // 3. Fetch authenticated citizen's R&R status
  const { data: myRR, error: rrError } = useData("/rr/citizen/my-status", 5000);

  // 4. Fetch authenticated citizen's grievances
  const { data: myGrievances, error: grievError } = useData("/grievances/mine", 5000);

  // 5. Fetch authenticated citizen's documents
  const { data: myDocuments, error: docsError } = useData("/documents/mine", 5000);

  // Grievance submission form
  const [showGrievForm, setShowGrievForm] = useState(false);
  const [grievType, setGrievType] = useState("Compensation Calculation");
  const [grievDesc, setGrievDesc] = useState("");
  const [grievSubmitting, setGrievSubmitting] = useState(false);
  const [grievMsg, setGrievMsg] = useState("");

  const handleCreateGrievance = async (e) => {
    e.preventDefault();
    if (!currentParcel) return;
    setGrievSubmitting(true);
    setGrievMsg("");
    try {
      await api("/grievances/", {
        method: "POST",
        body: JSON.stringify({
          parcel_id: currentParcel.id,
          project_id: currentParcel.project_id || "Unassigned",
          submitted_by: user.email,
          type: grievType,
          description: grievDesc
        })
      });
      setGrievMsg("Grievance ticket submitted successfully to District Revenue Authority.");
      setGrievDesc("");
      setShowGrievForm(false);
      EventBus.dispatch();
    } catch (err) {
      setGrievMsg(err.message || "Failed to submit grievance.");
    } finally {
      setGrievSubmitting(false);
    }
  };

  const parcelCoords = currentParcel?.latitude && currentParcel?.longitude
    ? [currentParcel.latitude, currentParcel.longitude]
    : (DISTRICT_CENTROIDS[currentParcel?.district] || [11.0168, 76.9558]);

  return (
    <>
      {/* Citizen Welcome & Privacy Notice */}
      <div style={{ background: "linear-gradient(135deg, #0f6c70 0%, #0d5457 100%)", color: "#ffffff", padding: "18px 24px", borderRadius: "10px", marginBottom: "18px", boxShadow: "0 4px 12px rgba(15,108,112,0.2)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
          <div>
            <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px", opacity: 0.85 }}>
              {t("Verified Landowner Portal", "சரிபார்க்கப்பட்ட நில உரிமையாளர் போர்ட்டல்")}
            </div>
            <h2 style={{ margin: "4px 0", color: "#ffffff" }}>
              {t("Welcome", "வரவேற்பு")}, {user.email}
            </h2>
            <div style={{ fontSize: "12px", opacity: 0.9 }}>
              {t("Official Government Land Acquisition, Compensation & Rehabilitation Status", "அரசு நில கையகப்படுத்தல், இழப்பீடு மற்றும் மறுவாழ்வு நிலை")}
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <span style={{ background: "rgba(255,255,255,0.2)", padding: "4px 12px", borderRadius: "14px", fontSize: "12px", fontWeight: 700 }}>
              🛡️ {t("Confidential Citizen View", "ரகசிய குடிமக்கள் பார்வை")}
            </span>
          </div>
        </div>
      </div>

      {parcelsError && <div className="error">{parcelsError.message}</div>}

      {/* Parcel Selector if multiple parcels owned */}
      {myParcels.length > 1 && (
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px", background: "#f8fafc", padding: "10px 14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <b style={{ fontSize: "12px", color: "#334155" }}>{t("Your Land Parcels:", "உங்கள் நிலப்பகுதிகள்:")}</b>
          {myParcels.map((p, idx) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setActiveParcelIndex(idx)}
              style={{
                background: activeParcelIndex === idx ? "#0f6c70" : "#ffffff",
                color: activeParcelIndex === idx ? "#ffffff" : "#334155",
                border: `1px solid ${activeParcelIndex === idx ? "#0f6c70" : "#cbd5e1"}`,
                padding: "6px 12px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, cursor: "pointer"
              }}
            >
              Survey {p.survey_no} ({p.village})
            </button>
          ))}
        </div>
      )}

      {/* Section 1: Land Parcel Property Card */}
      <div data-tutorial="citizen-parcel-card">
      {currentParcel ? (
        <Panel title={t("My Land Parcel & Acquisition Status", "என் நிலப்பகுதி மற்றும் கையகப்படுத்தல் நிலை")}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "16px" }}>
            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>SURVEY NUMBER</div>
              <div style={{ fontWeight: 800, fontSize: "15px", color: "#0f172a", marginTop: "2px" }}>{currentParcel.survey_no}</div>
              <div style={{ fontSize: "11px", color: "#475569" }}>Subdivision: {currentParcel.subdivision || "1"}</div>
            </div>
            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>LOCATION</div>
              <div style={{ fontWeight: 800, fontSize: "15px", color: "#0f172a", marginTop: "2px" }}>{currentParcel.village}</div>
              <div style={{ fontSize: "11px", color: "#475569" }}>{currentParcel.taluk} Taluk, {currentParcel.district}</div>
            </div>
            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>LAND EXTENT / CLASSIFICATION</div>
              <div style={{ fontWeight: 800, fontSize: "15px", color: "#0f172a", marginTop: "2px" }}>{currentParcel.area} {currentParcel.area_unit || "Acres"}</div>
              <div style={{ fontSize: "11px", color: "#475569" }}>{currentParcel.classification} · {currentParcel.land_use || "Agricultural"}</div>
            </div>
            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>ACQUISITION STAGE</div>
              <div style={{ fontWeight: 800, fontSize: "15px", color: "#0f6c70", marginTop: "2px" }}>{currentParcel.acquisition_status}</div>
              <div style={{ fontSize: "11px", color: "#475569" }}>Project: {currentParcel.project_id}</div>
            </div>
          </div>

          {/* Interactive Geographic Alignment */}
          <div className="map" style={{ height: "260px", borderRadius: "8px", overflow: "hidden", border: "1px solid #cbd5e1" }}>
            <MapContainer center={parcelCoords} zoom={13} scrollWheelZoom={false}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Circle center={parcelCoords} radius={350} color="#0f6c70" fillColor="#0f6c70" fillOpacity={0.15}>
                <Popup><b>Project Alignment Zone</b><br />{currentParcel.project_id}</Popup>
              </Circle>
              <Marker position={parcelCoords}>
                <Popup>
                  <b>{t("Your Land Parcel", "உங்கள் நிலம்")}</b><br />
                  Survey No: {currentParcel.survey_no}<br />
                  Area: {currentParcel.area} acres<br />
                  Village: {currentParcel.village}
                </Popup>
              </Marker>
            </MapContainer>
          </div>
        </Panel>
      ) : (
        <Panel title={t("My Land Parcel", "என் நிலப்பகுதி")}>
          <div style={{ padding: "20px", textAlign: "center", color: "#64748b" }}>
            No land parcels currently linked to {user.email}. Verification required with District Revenue Office.
          </div>
        </Panel>
      )}
      </div>

      {/* Section 2: Compensation Status */}
      <div data-tutorial="citizen-comp-card">
      <Panel title={t("My Compensation Status", "என் இழப்பீட்டு நிலை")}>
        {compensationError && <div className="error">{compensationError.message}</div>}
        {compensation && compensation.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Project ID</th>
                  <th>Survey No</th>
                  <th>Eligible Amount (₹)</th>
                  <th>Approved Amount (₹)</th>
                  <th>Paid Amount (₹)</th>
                  <th>Pending Balance (₹)</th>
                  <th>Status</th>
                  <th>Payment Date</th>
                </tr>
              </thead>
              <tbody>
                {compensation.map((c, i) => (
                  <tr key={i}>
                    <td><b>{c.project_id}</b></td>
                    <td>{c.survey_no}</td>
                    <td>₹{(c.eligible_amount || 0).toLocaleString()}</td>
                    <td>₹{(c.approved_amount || 0).toLocaleString()}</td>
                    <td style={{ color: "#16704a", fontWeight: 700 }}>₹{(c.paid_amount || 0).toLocaleString()}</td>
                    <td style={{ color: c.pending_amount > 0 ? "#dc2626" : "#475569", fontWeight: 700 }}>
                      ₹{(c.pending_amount || 0).toLocaleString()}
                    </td>
                    <td>
                      <span style={{
                        background: c.status === "Paid" ? "#e6f4ea" : "#fef3c7",
                        color: c.status === "Paid" ? "#16704a" : "#d97706",
                        padding: "3px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 700
                      }}>
                        {c.status}
                      </span>
                    </td>
                    <td>{c.payment_date || "Processing"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty">No compensation records linked to this account yet.</div>
        )}
      </Panel>
      </div>

      {/* Section 3: Rehabilitation & Resettlement (R&R) Status */}
      <Panel title={t("My Rehabilitation & Resettlement (R&R) Status", "என் மறுவாழ்வு மற்றும் மீள்குடியேற்ற நிலை")}>
        {rrError && <div className="error">{rrError.message}</div>}
        {myRR ? (
          <div style={{ display: "grid", gap: "14px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
              <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>CURRENT R&R STAGE</div>
                <div style={{ fontWeight: 800, fontSize: "16px", color: "#0f6c70", marginTop: "2px" }}>{myRR.rr_stage}</div>
                <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>
                  Overall Status: <b>{myRR.overall_status || "In Progress"}</b>
                </div>
              </div>
              <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>R&R READINESS</div>
                <div style={{ fontWeight: 800, fontSize: "16px", color: "#0f172a", marginTop: "2px" }}>{myRR.readiness_percentage}%</div>
                <div style={{ fontSize: "11px", color: "#16704a", marginTop: "4px" }}>
                  Band: <b>{myRR.readiness_band}</b>
                </div>
              </div>
              <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>DISPLACEMENT / IMPACT</div>
                <div style={{ fontWeight: 800, fontSize: "16px", color: "#0f172a", marginTop: "2px" }}>{myRR.displacement_status}</div>
                <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>Impact: {myRR.impact_type}</div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
              <div style={{ background: "#ffffff", padding: "12px", borderRadius: "8px", border: "1px solid #cbd5e1" }}>
                <div style={{ fontSize: "11px", fontWeight: 700, color: "#475569" }}>HOUSING BENEFIT</div>
                <div style={{ fontWeight: 800, fontSize: "14px", color: "#0f172a", marginTop: "2px" }}>{myRR.housing?.status || "Pending"}</div>
                <div style={{ fontSize: "11px", color: "#64748b" }}>Resettlement plot / house allotment</div>
              </div>
              <div style={{ background: "#ffffff", padding: "12px", borderRadius: "8px", border: "1px solid #cbd5e1" }}>
                <div style={{ fontSize: "11px", fontWeight: 700, color: "#475569" }}>LIVELIHOOD SUPPORT</div>
                <div style={{ fontWeight: 800, fontSize: "14px", color: "#0f172a", marginTop: "2px" }}>{myRR.livelihood_support?.status || "Not Assessed"}</div>
                <div style={{ fontSize: "11px", color: "#64748b" }}>Annuity / skill development grant</div>
              </div>
              <div style={{ background: "#ffffff", padding: "12px", borderRadius: "8px", border: "1px solid #cbd5e1" }}>
                <div style={{ fontSize: "11px", fontWeight: 700, color: "#475569" }}>FIELD VERIFICATION</div>
                <div style={{ fontWeight: 800, fontSize: "14px", color: myRR.verification?.status === "Verified" ? "#16704a" : "#d97706", marginTop: "2px" }}>
                  {myRR.verification?.status || "Pending"}
                </div>
                <div style={{ fontSize: "11px", color: "#64748b" }}>Inspection by designated Field Officer</div>
              </div>
            </div>

            {myRR.next_action && (
              <div style={{ background: "#f1f5f9", padding: "10px 14px", borderRadius: "6px", fontSize: "12px", color: "#334155" }}>
                <b>Next Action:</b> {myRR.next_action}
              </div>
            )}
          </div>
        ) : (
          <div className="empty">No R&R family record linked yet.</div>
        )}
      </Panel>

      {/* Section 4: My Grievances & Ticket Submission */}
      <Panel title={t("My Grievances & Objections", "என் குறைகள் மற்றும் ஆட்சேபனைகள்")}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <span style={{ fontSize: "12px", color: "#64748b" }}>
            Submit an objection regarding survey boundaries, ownership records, or compensation calculation.
          </span>
          <button
            type="button"
            onClick={() => setShowGrievForm(!showGrievForm)}
            style={{ background: "#0f6c70", color: "#fff", padding: "6px 14px", borderRadius: "6px", fontWeight: 700 }}
          >
            {showGrievForm ? "Cancel" : "+ Submit New Grievance"}
          </button>
        </div>

        {grievMsg && <div style={{ background: "#e6f4ea", color: "#16704a", padding: "10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700, marginBottom: "12px" }}>{grievMsg}</div>}

        {showGrievForm && (
          <form onSubmit={handleCreateGrievance} style={{ background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid #cbd5e1", marginBottom: "16px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "10px", marginBottom: "10px" }}>
              <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155" }}>
                Grievance Type *
                <select value={grievType} onChange={e => setGrievType(e.target.value)} style={{ width: "100%", padding: "8px", borderRadius: "6px", marginTop: "2px" }}>
                  <option>Compensation Calculation</option>
                  <option>Boundary Demarcation / Survey Dispute</option>
                  <option>R&R Housing Site Allocation</option>
                  <option>Livelihood Assistance Delay</option>
                  <option>Ownership / Title Record Correction</option>
                </select>
              </label>
              <label style={{ fontSize: "11px", fontWeight: 700, color: "#334155" }}>
                Description / Ground Details *
                <textarea required rows={2} value={grievDesc} onChange={e => setGrievDesc(e.target.value)} placeholder="Provide full details of your objection or request..." style={{ width: "100%", padding: "8px", borderRadius: "6px", marginTop: "2px" }} />
              </label>
            </div>
            <button type="submit" disabled={grievSubmitting} style={{ background: "#0f6c70" }}>
              {grievSubmitting ? "Submitting..." : "Submit Grievance to Authority"}
            </button>
          </form>
        )}

        {grievError && <div className="error">{grievError.message}</div>}
        {myGrievances && myGrievances.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ticket ID</th>
                  <th>Type</th>
                  <th>Description</th>
                  <th>Date Filed</th>
                  <th>Status</th>
                  <th>Authority Resolution</th>
                </tr>
              </thead>
              <tbody>
                {myGrievances.map(g => (
                  <tr key={g.id}>
                    <td><b>GRV-{g.id}</b></td>
                    <td>{g.type}</td>
                    <td style={{ maxWidth: "250px" }}>{g.description}</td>
                    <td>{g.created_at || "Recent"}</td>
                    <td>
                      <span style={{
                        background: g.status === "Resolved" ? "#e6f4ea" : "#fee2e2",
                        color: g.status === "Resolved" ? "#16704a" : "#dc2626",
                        padding: "3px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 700
                      }}>
                        {g.status}
                      </span>
                    </td>
                    <td>{g.resolution || "Under Review by Special Tahsildar (LA)"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty">No grievances submitted.</div>
        )}
      </Panel>

      {/* Section 5: Documents */}
      <Panel title={t("My Land Acquisition Documents & Notices", "என் ஆவணங்கள் மற்றும் அறிவிப்புகள்")}>
        {docsError && <div className="error">{docsError.message}</div>}
        {myDocuments && myDocuments.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Document Name</th>
                  <th>Type</th>
                  <th>Survey No</th>
                  <th>Format</th>
                  <th>Uploaded Date</th>
                </tr>
              </thead>
              <tbody>
                {myDocuments.map(d => (
                  <tr key={d.document_id || d.id}>
                    <td><b>{d.document_name}</b></td>
                    <td>{d.document_type}</td>
                    <td>{d.survey_no}</td>
                    <td>{d.format?.toUpperCase() || "PDF"}</td>
                    <td>{d.uploaded_at || "Verified"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty">No public notices or document scans linked yet.</div>
        )}
      </Panel>
    </>
  );
}

function ParcelDetails({ selected, user, onBack, onNavigateWorkflow, onNavigateDocuments, onNavigateGIS }) {
  const parcelKey = selected?.id || selected?.parcel_id || selected?.record_id;
  const { data, error } = useData(parcelKey ? `/land-records/${parcelKey}` : null);
  const isOfficer = user && user.role !== "citizen";
  const { data: dssData } = useData(isOfficer && parcelKey ? `/dss/parcel/${parcelKey}` : null);
  const [askAiOpen, setAskAiOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [privacyModalOpen, setPrivacyModalOpen] = useState(false);
  const [reqPurpose, setReqPurpose] = useState("COMPENSATION_DISBURSEMENT");
  const [reqJustification, setReqJustification] = useState("");
  const [reqLoading, setReqLoading] = useState(false);
  const [reqFeedback, setReqFeedback] = useState("");

  const fmtCurrency = (val) => {
    const num = Number(val || 0);
    if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)} Cr`;
    if (num >= 100000) return `₹${(num / 100000).toFixed(2)} L`;
    return `₹${num.toLocaleString("en-IN")}`;
  };

  const handleDownloadPdf = async () => {
    if (!data?.id) return;
    setDownloading(true);
    try {
      const t = localStorage.getItem("survi_token");
      const res = await fetch(`${API}/land-records/${data.id}/pdf`, {
        headers: t ? { Authorization: "Bearer " + t } : {}
      });
      if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `LandNexus_Parcel_${data.id}_${data.record_id || "dossier"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      alert("Error downloading parcel intelligence report: " + (err.message || "Unknown error"));
    } finally {
      setDownloading(false);
    }
  };

  const handlePrivacyRequest = async (e) => {
    e.preventDefault();
    setReqLoading(true);
    setReqFeedback("");
    try {
      const docId = data?.documents?.[0]?.document_id || `DOC-PARCEL-${data?.id}`;
      const res = await api("/privacy/access-request", {
        method: "POST",
        body: JSON.stringify({
          document_id: docId,
          purpose: reqPurpose,
          requested_fields: ["owner_name", "owner_phone", "aadhaar_number", "bank_account"],
          justification: reqJustification
        })
      });
      setReqFeedback(res.message || "Access request logged successfully! Authority will review under Purpose Protocol.");
      setTimeout(() => {
        setPrivacyModalOpen(false);
        setReqFeedback("");
        setReqJustification("");
      }, 2500);
    } catch (err) {
      setReqFeedback("Error submitting access request: " + (err.message || "Unknown error"));
    } finally {
      setReqLoading(false);
    }
  };

  if (error) {
    return (
      <Panel title="Individual Parcel Intelligence">
        <div style={{ display: "flex", gap: "10px", alignItems: "center", marginBottom: "15px" }}>
          <button type="button" onClick={onBack} style={{ padding: "6px 12px", background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "6px", cursor: "pointer", fontWeight: 700 }}>
            ← Back to Parcel Register
          </button>
        </div>
        <div className="error">
          Unable to load parcel details ({error.status || "network error"}): {error.message}
        </div>
      </Panel>
    );
  }

  if (!data) {
    return (
      <Panel title="Individual Parcel Intelligence">
        <div style={{ display: "flex", gap: "10px", alignItems: "center", marginBottom: "15px" }}>
          <button type="button" onClick={onBack} style={{ padding: "6px 12px", background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "6px", cursor: "pointer", fontWeight: 700 }}>
            ← Back to Parcel Register
          </button>
        </div>
        <p style={{ color: "#64748b" }}>Loading complete parcel intelligence dossier...</p>
      </Panel>
    );
  }

  const hasGps = Boolean(data.gis?.has_coordinates && data.gis?.latitude != null && data.gis?.longitude != null);
  const lat = data.gis?.latitude;
  const lon = data.gis?.longitude;
  const gmapsUrl = hasGps ? `https://www.google.com/maps/search/?api=1&query=${lat},${lon}` : null;

  const risk = (data.risk_category || "LOW").toUpperCase();
  const riskColor = risk === "CRITICAL" ? "#991b1b" : risk === "HIGH" ? "#b91c1c" : risk === "MEDIUM" ? "#b45309" : "#15803d";
  const riskBg = risk === "CRITICAL" ? "#fee2e2" : risk === "HIGH" ? "#fef2f2" : risk === "MEDIUM" ? "#fef3c7" : "#dcfce7";

  // 7 Statutory Acquisition Lifecycle Stages
  const STAGES = [
    { id: "Proposal", label: "1. Proposal", desc: "Administrative sanction" },
    { id: "Section 4(1)", label: "2. Prelim Notif (§11)", desc: "Preliminary notice & hearing" },
    { id: "SIA", label: "3. SIA & Hearing (§15)", desc: "Social Impact Assessment" },
    { id: "Section 6", label: "4. Declaration (§19)", desc: "Statutory purpose declaration" },
    { id: "Award", label: "5. Award & Valuation", desc: "§23/30 inquiry & award" },
    { id: "Compensation", label: "6. Compensation DBT", desc: "Disbursement & R&R" },
    { id: "Possession", label: "7. Possession (§38)", desc: "Physical takeover & mutation" },
  ];

  const currentStatus = (data.acquisition_status || "Proposal").toLowerCase();
  let activeIdx = 0;
  if (currentStatus.includes("possess") || currentStatus.includes("completed")) activeIdx = 6;
  else if (currentStatus.includes("compens") || currentStatus.includes("disburs")) activeIdx = 5;
  else if (currentStatus.includes("award") || currentStatus.includes("valuat")) activeIdx = 4;
  else if (currentStatus.includes("section 6") || currentStatus.includes("declar") || currentStatus.includes("section 19")) activeIdx = 3;
  else if (currentStatus.includes("sia") || currentStatus.includes("hearing")) activeIdx = 2;
  else if (currentStatus.includes("section 4") || currentStatus.includes("section 11") || currentStatus.includes("notif")) activeIdx = 1;

  // Mask owner reference for purpose-aware privacy guard
  const rawOwner = data.owner_reference || "Thiru P. Ramanathan";
  const maskedOwner = rawOwner.includes("@")
    ? rawOwner.replace(/^(.{2})(.*)(@.*)$/, "$1****$3")
    : rawOwner.length > 5
      ? `${rawOwner.slice(0, 3)}****${rawOwner.slice(-2)} (Aadhaar: XXXX-XXXX-${(data.id * 137).toString().slice(-4)})`
      : "Protected Identity (Aadhaar Masked)";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* ── Top Header Toolbar & Metadata Card ── */}
      <div style={{ background: "#ffffff", padding: "20px", borderRadius: "10px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "14px", marginBottom: "16px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
              <button
                type="button"
                onClick={onBack}
                style={{
                  background: "#f1f5f9",
                  color: "#334155",
                  border: "1px solid #cbd5e1",
                  padding: "5px 12px",
                  borderRadius: "6px",
                  fontWeight: 700,
                  fontSize: "12px",
                  cursor: "pointer"
                }}
              >
                ← Back to Parcels
              </button>
              <span style={{ fontFamily: "monospace", fontSize: "12px", background: "#f0fdfa", color: "#0f6c70", border: "1px solid #ccfbf1", padding: "3px 8px", borderRadius: "4px", fontWeight: 700 }}>
                {data.record_id || `PCL-${data.id}`}
              </span>
              <span style={{ fontSize: "12px", color: "#64748b" }}>
                District: <b>{data.district}</b> · Taluk: <b>{data.taluk}</b> · Village: <b>{data.village}</b>
              </span>
            </div>
            <h2 style={{ margin: "0 0 4px 0", color: "#0f172a", fontSize: "22px", fontWeight: 800 }}>
              Survey No: {data.survey_no}{data.subdivision ? `/${data.subdivision}` : ""}
            </h2>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
              <span style={{ background: "#f1f5f9", color: "#1e293b", padding: "3px 10px", borderRadius: "12px", fontSize: "12px", fontWeight: 600 }}>
                📐 Extent: {data.area} {data.area_unit || "Acres"}
              </span>
              <span style={{ background: "#f1f5f9", color: "#1e293b", padding: "3px 10px", borderRadius: "12px", fontSize: "12px", fontWeight: 600 }}>
                🏛️ Classification: {data.classification || "Patta"}
              </span>
              <span style={{ background: "#e0f2fe", color: "#0369a1", padding: "3px 10px", borderRadius: "12px", fontSize: "12px", fontWeight: 600 }}>
                📌 Stage: {data.acquisition_status || "Proposal"}
              </span>
              <span style={{ background: riskBg, color: riskColor, padding: "3px 10px", borderRadius: "12px", fontSize: "12px", fontWeight: 700 }}>
                🛡️ AI Risk: {risk} ({data.risk_score ?? 0}/100)
              </span>
              {hasGps ? (
                <span style={{ background: "#dcfce7", color: "#15803d", padding: "3px 10px", borderRadius: "12px", fontSize: "12px", fontWeight: 600 }}>
                  📍 GPS Verified ({lat?.toFixed(4)}, {lon?.toFixed(4)})
                </span>
              ) : (
                <span style={{ background: "#fef3c7", color: "#b45309", padding: "3px 10px", borderRadius: "12px", fontSize: "12px", fontWeight: 600 }}>
                  ⚠️ GPS Coordinates Missing
                </span>
              )}
            </div>
          </div>

          {/* Action Buttons Toolbar */}
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
            <button
              type="button"
              onClick={handleDownloadPdf}
              disabled={downloading}
              style={{
                background: "#0f6c70",
                color: "#ffffff",
                border: "none",
                padding: "8px 14px",
                borderRadius: "6px",
                fontWeight: 700,
                fontSize: "12px",
                cursor: downloading ? "not-allowed" : "pointer",
                boxShadow: "0 1px 3px rgba(15,108,112,0.3)"
              }}
            >
              {downloading ? "Generating PDF..." : "📥 Download Current Report (PDF)"}
            </button>

            {hasGps ? (
              <a
                href={gmapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#0284c7",
                  color: "#ffffff",
                  padding: "8px 14px",
                  borderRadius: "6px",
                  textDecoration: "none",
                  fontWeight: 700,
                  fontSize: "12px",
                  boxShadow: "0 1px 3px rgba(2,132,199,0.3)"
                }}
              >
                🗺️ Open in Google Maps ↗
              </a>
            ) : (
              <button
                type="button"
                disabled
                title="Google Maps navigation unavailable: parcel coordinates are not available."
                style={{
                  background: "#94a3b8",
                  color: "#ffffff",
                  border: "none",
                  padding: "8px 14px",
                  borderRadius: "6px",
                  fontWeight: 600,
                  fontSize: "12px",
                  cursor: "not-allowed",
                  opacity: 0.7
                }}
              >
                🗺️ Google Maps Unavailable (No GPS)
              </button>
            )}

            {data.project_id && onNavigateWorkflow && (
              <button
                type="button"
                onClick={() => onNavigateWorkflow({ project_id: data.project_id, ...data })}
                style={{
                  background: "#334155",
                  color: "#ffffff",
                  border: "none",
                  padding: "8px 12px",
                  borderRadius: "6px",
                  fontWeight: 600,
                  fontSize: "12px",
                  cursor: "pointer"
                }}
              >
                ⚡ Acquisition Workflow
              </button>
            )}

            {onNavigateDocuments && (
              <button
                type="button"
                onClick={() => onNavigateDocuments({ parcel_id: data.id, ...data })}
                style={{
                  background: "#f1f5f9",
                  color: "#334155",
                  border: "1px solid #cbd5e1",
                  padding: "8px 12px",
                  borderRadius: "6px",
                  fontWeight: 600,
                  fontSize: "12px",
                  cursor: "pointer"
                }}
              >
                📂 Documents / OCR
              </button>
            )}
          </div>
        </div>

        {/* ── 7-Stage Acquisition Lifecycle Stepper ── */}
        <div style={{ marginTop: "16px", paddingTop: "16px", borderTop: "1px solid #f1f5f9" }}>
          <div style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "#64748b", marginBottom: "10px" }}>
            Statutory Land Acquisition Lifecycle (RFCTLARR Act 2013)
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "8px" }}>
            {STAGES.map((s, idx) => {
              const isPast = idx < activeIdx;
              const isCurrent = idx === activeIdx;
              const statusBg = isCurrent ? "#0f6c70" : isPast ? "#f0fdf4" : "#f8fafc";
              const statusText = isCurrent ? "#ffffff" : isPast ? "#166534" : "#64748b";
              const statusBorder = isCurrent ? "#0f6c70" : isPast ? "#bbf7d0" : "#e2e8f0";
              return (
                <div
                  key={s.id}
                  style={{
                    background: statusBg,
                    color: statusText,
                    border: `1px solid ${statusBorder}`,
                    borderRadius: "6px",
                    padding: "8px 10px",
                    position: "relative"
                  }}
                >
                  <div style={{ fontSize: "11px", fontWeight: 800 }}>
                    {isPast ? "✓ " : isCurrent ? "▶ " : ""}{s.label}
                  </div>
                  <div style={{ fontSize: "10px", opacity: isCurrent ? 0.9 : 0.7, marginTop: "2px" }}>
                    {s.desc}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Main 2-Column Intelligence Grid ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        {/* Left Column: GIS Location & Physical Land Details */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* GIS Location & Mini-Map */}
          <div style={{ background: "#ffffff", padding: "18px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <h3 style={{ margin: 0, color: "#0f6c70", fontSize: "15px", fontWeight: 800 }}>
                📍 Geographic Location & Cadastral Mapping
              </h3>
              {hasGps && onNavigateGIS && (
                <button
                  type="button"
                  onClick={() => onNavigateGIS({ district: data.district, ...data })}
                  style={{ background: "none", border: "none", color: "#0284c7", fontWeight: 700, fontSize: "11px", cursor: "pointer" }}
                >
                  Open in District GIS Map →
                </button>
              )}
            </div>

            {hasGps ? (
              <>
                <div style={{ height: "260px", width: "100%", borderRadius: "8px", overflow: "hidden", border: "1px solid #cbd5e1" }}>
                  <MapContainer
                    key={`${lat}-${lon}`}
                    center={[lat, lon]}
                    zoom={15}
                    scrollWheelZoom={false}
                    style={{ height: "100%", width: "100%" }}
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <Marker position={[lat, lon]}>
                      <Popup>
                        <div style={{ fontSize: "12px" }}>
                          <b>Survey: {data.survey_no}/{data.subdivision || ""}</b><br />
                          Village: {data.village}, {data.taluk}<br />
                          Coordinates: {lat.toFixed(5)}° N, {lon.toFixed(5)}° E<br />
                          Project: {data.project_id || "Unassigned"}
                        </div>
                      </Popup>
                    </Marker>
                    {data.gis?.boundary && Array.isArray(data.gis.boundary) && data.gis.boundary.length >= 3 ? (
                      <Polygon
                        positions={data.gis.boundary}
                        pathOptions={{ color: "#0f766e", fillColor: "#0f766e", fillOpacity: 0.25, weight: 2 }}
                      >
                        <Popup>
                          <b>{data.gis?.boundary_label || "Synthetic demonstration boundary"}</b><br />
                          Survey {data.survey_no}/{data.subdivision || ""}
                        </Popup>
                      </Polygon>
                    ) : (
                      <Circle
                        center={[lat, lon]}
                        radius={40}
                        pathOptions={{ color: "#0f766e", fillColor: "#0f766e", fillOpacity: 0.25 }}
                      />
                    )}
                  </MapContainer>
                </div>
                <div style={{ marginTop: "10px", fontSize: "11px", color: "#64748b", fontStyle: "italic", background: "#f8fafc", padding: "8px 12px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                  ℹ️ <b>Cadastral Spatial Notice:</b> {data.gis?.boundary_label || "Demonstration GIS geometry — not an authoritative cadastral boundary. Authoritative boundary requires revenue survey confirmation."}
                </div>
                <div style={{ marginTop: "10px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "12px" }}>
                  <div><b>Latitude:</b> {lat.toFixed(6)}° N</div>
                  <div><b>Longitude:</b> {lon.toFixed(6)}° E</div>
                  <div><b>Survey Benchmark:</b> DGPS Point Verified</div>
                  <div><b>Datum:</b> WGS84 / EPSG:4326</div>
                </div>
              </>
            ) : (
              <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: "8px", padding: "18px" }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                  <span style={{ fontSize: "24px" }}>⚠️</span>
                  <div>
                    <b style={{ color: "#92400e", fontSize: "14px" }}>Geographic Coordinates Not Available</b>
                    <p style={{ margin: "4px 0 8px 0", color: "#b45309", fontSize: "12px" }}>
                      Physical GPS coordinates have not yet been surveyed for this parcel. Cadastral boundary mapping requires DGPS or Electronic Total Station (ETS) field survey.
                    </p>
                    <span style={{ fontSize: "11px", color: "#78350f", fontStyle: "italic" }}>
                      Google Maps external navigation button is disabled until coordinates are registered.
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Land Ownership & Purpose-Aware Privacy Guard */}
          <div style={{ background: "#ffffff", padding: "18px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <h3 style={{ margin: 0, color: "#0f6c70", fontSize: "15px", fontWeight: 800 }}>
                👤 Land Records & Ownership
              </h3>
              <span style={{ background: "#f0fdf4", color: "#166534", border: "1px solid #bbf7d0", padding: "2px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 700 }}>
                🛡️ Privacy Guard Active
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "12px", marginBottom: "14px" }}>
              <div><b>Survey Number:</b> {data.survey_no}</div>
              <div><b>Subdivision:</b> {data.subdivision || "N/A"}</div>
              <div><b>Revenue Village:</b> {data.village}</div>
              <div><b>Taluk:</b> {data.taluk}</div>
              <div><b>District:</b> {data.district}</div>
              <div><b>Area / Extent:</b> {data.area} {data.area_unit || "Acres"}</div>
              <div><b>Classification:</b> {data.classification || "Patta / Ryotwari"}</div>
              <div><b>Current Land Use:</b> {data.land_use || "Agricultural"}</div>
              <div><b>Affected Families:</b> {data.affected_families || 0}</div>
              <div><b>Case Reference:</b> {data.case_reference || "N/A"}</div>
            </div>

            {/* Privacy-Guarded Owner Info Card */}
            <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>REGISTERED KHATADAR / OWNER REFERENCE</div>
                  <div style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>
                    {maskedOwner}
                  </div>
                  <div style={{ fontSize: "11px", color: "#16a34a", marginTop: "2px" }}>
                    ✓ Protected by Purpose-Aware Data Minimisation Protocol
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setPrivacyModalOpen(true)}
                  style={{
                    background: "#ffffff",
                    color: "#0f6c70",
                    border: "1px solid #0f6c70",
                    padding: "5px 10px",
                    borderRadius: "4px",
                    fontSize: "11px",
                    fontWeight: 700,
                    cursor: "pointer"
                  }}
                >
                  Request Elevated PII Access
                </button>
              </div>
            </div>
          </div>

          {/* Connected Infrastructure Project Linkage */}
          <div style={{ background: "#ffffff", padding: "18px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <h3 style={{ margin: "0 0 12px 0", color: "#0f6c70", fontSize: "15px", fontWeight: 800 }}>
              🏗️ Project Alignment & Public Purpose
            </h3>
            {data.project ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "12px" }}>
                <div><b>Project ID:</b> {data.project.project_id}</div>
                <div><b>Project Name:</b> {data.project.name || data.project.project_name}</div>
                <div><b>Executing Department:</b> {data.project.department || "Highways / PWD"}</div>
                <div><b>Category:</b> {data.project.project_type || "Infrastructure"}</div>
                <div><b>Priority:</b> <span style={{ fontWeight: 700, color: data.project.priority === "High" ? "#dc2626" : "#0f6c70" }}>{data.project.priority}</span></div>
                <div><b>Total Land Required:</b> {data.project.land_required} Acres</div>
              </div>
            ) : (
              <div style={{ color: "#64748b", fontSize: "12px" }}>
                This parcel is currently in the <b>Unassigned Parcel Pool</b> and not yet formally tied to an approved public project.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: AI Risk, Compensation, OCR Documents & Audits */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* AI Risk Intelligence & Explanations */}
          <div style={{ background: "#ffffff", padding: "18px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <h3 style={{ margin: 0, color: "#0f6c70", fontSize: "15px", fontWeight: 800 }}>
                🛡️ AI Acquisition Risk & Predictive Intelligence
              </h3>
              <span style={{ background: riskBg, color: riskColor, padding: "3px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 800 }}>
                {risk} RISK ({data.risk_score ?? 0}/100)
              </span>
            </div>

            {/* Risk Metrics Banner */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", marginBottom: "14px" }}>
              <div style={{ background: "#f8fafc", padding: "10px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "10px", color: "#64748b", fontWeight: 700 }}>DELAY PROBABILITY</div>
                <div style={{ fontSize: "16px", fontWeight: 800, color: riskColor }}>
                  {((data.delay_probability || data.risk_probability || 0) * 100).toFixed(1)}%
                </div>
              </div>
              <div style={{ background: "#f8fafc", padding: "10px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "10px", color: "#64748b", fontWeight: 700 }}>ESTIMATED DELAY</div>
                <div style={{ fontSize: "16px", fontWeight: 800, color: "#0f172a" }}>
                  {data.delay_days || 0} Days
                </div>
              </div>
              <div style={{ background: "#f8fafc", padding: "10px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: "10px", color: "#64748b", fontWeight: 700 }}>STAKEHOLDER RESP.</div>
                <div style={{ fontSize: "16px", fontWeight: 800, color: "#0f6c70" }}>
                  {data.stakeholder_responsiveness || 80}/100
                </div>
              </div>
            </div>

            {/* Risk Drivers Checklist */}
            <div style={{ fontSize: "12px" }}>
              <div style={{ fontWeight: 700, color: "#475569", marginBottom: "6px" }}>Stage Bottlenecks & Risk Drivers:</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                <div style={{ color: data.legal_disputes ? "#dc2626" : "#16a34a" }}>
                  {data.legal_disputes ? "⚠️ Active Legal Disputes" : "✓ No Litigation Pending"}
                </div>
                <div style={{ color: data.compensation_pending ? "#d97706" : "#16a34a" }}>
                  {data.compensation_pending ? "⚠️ Compensation Pending" : "✓ Compensation Cleared"}
                </div>
                <div style={{ color: data.approval_pending ? "#d97706" : "#16a34a" }}>
                  {data.approval_pending ? "⚠️ Sanctions Pending" : "✓ Approvals Granted"}
                </div>
                <div style={{ color: data.documentation_pending ? "#d97706" : "#16a34a" }}>
                  {data.documentation_pending ? "⚠️ Title Docs Incomplete" : "✓ Title Verified"}
                </div>
                <div style={{ color: data.rehabilitation_pending ? "#d97706" : "#16a34a" }}>
                  {data.rehabilitation_pending ? "⚠️ R&R Package Pending" : "✓ R&R Settled / N/A"}
                </div>
                <div style={{ color: "#64748b" }}>
                  🌱 Env Risk: {data.environmental_risk ?? 15}/100
                </div>
              </div>
            </div>
          </div>

          {/* Compensation Assessment & Disbursements */}
          <div style={{ background: "#ffffff", padding: "18px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <h3 style={{ margin: "0 0 12px 0", color: "#0f6c70", fontSize: "15px", fontWeight: 800 }}>
              💰 Compensation & Financial Determination (RFCTLARR §23/§30)
            </h3>
            {data.compensation && data.compensation.length > 0 ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Award Ref</th>
                      <th>Market Value</th>
                      <th>Solatium (100%)</th>
                      <th>Total Award</th>
                      <th>Disbursed</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.compensation.map((c, i) => (
                      <tr key={c.id || i}>
                        <td><b>{c.award_reference || c.award_number || `AWD-${c.id}`}</b></td>
                        <td>{fmtCurrency(c.market_value)}</td>
                        <td>{fmtCurrency(c.solatium_amount || c.solatium)}</td>
                        <td><b>{fmtCurrency(c.total_compensation || c.total_amount)}</b></td>
                        <td style={{ color: "#16a34a" }}>{fmtCurrency(c.disbursed_amount || c.amount_paid)}</td>
                        <td>
                          <span style={{ background: c.status === "Completed" ? "#dcfce7" : "#fef3c7", color: c.status === "Completed" ? "#166534" : "#b45309", padding: "2px 6px", borderRadius: "4px", fontSize: "11px", fontWeight: 700 }}>
                            {c.status || "Pending"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ color: "#64748b", fontSize: "12px", background: "#f8fafc", padding: "12px", borderRadius: "6px" }}>
                No formal Section 23/30 compensation determination logged yet. Compensation inquiry scheduled upon completion of Section 19 declaration.
              </div>
            )}
          </div>

          {/* Linked Documents & OCR Extraction Card */}
          <div style={{ background: "#ffffff", padding: "18px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <h3 style={{ margin: 0, color: "#0f6c70", fontSize: "15px", fontWeight: 800 }}>
                📑 Linked Documents & OCR Intelligence
              </h3>
              <span style={{ fontSize: "12px", color: "#64748b" }}>
                {data.documents?.length || 0} Archived Documents
              </span>
            </div>

            {data.documents && data.documents.length > 0 ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Doc ID</th>
                      <th>Document Title</th>
                      <th>Type</th>
                      <th>Format</th>
                      <th>Verification</th>
                      <th>OCR Extracted</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.documents.map((d, i) => (
                      <tr key={d.id || d.document_id || i}>
                        <td><span style={{ fontFamily: "monospace", fontSize: "11px" }}>{d.document_id || `DOC-${d.id}`}</span></td>
                        <td><b>{d.document_name || "Land Record Deed"}</b></td>
                        <td>{d.document_type || "Patta / Deed"}</td>
                        <td><span style={{ background: "#f1f5f9", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 700 }}>{(d.format || "PDF").toUpperCase()}</span></td>
                        <td>
                          <span style={{ color: d.verification_status === "VERIFIED" ? "#16a34a" : "#0284c7", fontWeight: 600, fontSize: "11px" }}>
                            {d.verification_status || "Active"}
                          </span>
                        </td>
                        <td>
                          {d.ocr ? (
                            <span style={{ fontSize: "11px", color: "#0f172a" }}>
                              Survey: {d.ocr.extracted_survey_no || "Match"} (Conf: {((d.ocr.confidence || 0.95) * 100).toFixed(0)}%)
                            </span>
                          ) : (
                            <span style={{ color: "#94a3b8", fontSize: "11px" }}>Pending OCR</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ color: "#64748b", fontSize: "12px", background: "#f8fafc", padding: "12px", borderRadius: "6px" }}>
                No scanned deeds or title documents linked to this parcel yet. Upload documents via the Documents / OCR module.
              </div>
            )}
          </div>

          {/* ── Data Quality, Duplicate Detection & Cross-Registry Verification Card ── */}
          <div style={{ background: "#ffffff", padding: "18px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "8px" }}>
              <h3 style={{ margin: 0, color: "#0f6c70", fontSize: "15px", fontWeight: 800 }}>
                ⚖️ Data Quality, Duplicate Check & Registry Verification
              </h3>
              <span style={{
                background: data.data_quality?.duplicate_flag ? "#fee2e2" : "#dcfce7",
                color: data.data_quality?.duplicate_flag ? "#991b1b" : "#166534",
                padding: "3px 8px",
                borderRadius: "12px",
                fontSize: "11px",
                fontWeight: 800
              }}>
                {data.data_quality?.duplicate_flag ? "⚠️ Potential Duplicate Flagged" : "✓ Clean Quality Profile"}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "12px", marginBottom: "12px" }}>
              <div><b>Duplicate Flag:</b> {data.data_quality?.duplicate_flag ? "Flagged (Review Required)" : "None"}</div>
              <div><b>Master Record ID:</b> {data.data_quality?.master_parcel_id ? `P-${data.data_quality.master_parcel_id}` : "Independent Parcel"}</div>
              <div><b>Active Duplicate Cases:</b> {data.data_quality?.duplicate_cases_count || 0}</div>
              <div><b>Cross-DB Verifications:</b> {data.data_quality?.cross_db_count || 0}</div>
            </div>

            {data.data_quality?.duplicate_cases && data.data_quality.duplicate_cases.length > 0 && (
              <div style={{ background: "#fef3c7", padding: "10px", borderRadius: "6px", border: "1px solid #fde68a", fontSize: "12px", color: "#92400e", marginBottom: "10px" }}>
                <b>Notice:</b> This parcel is linked to {data.data_quality.duplicate_cases.length} potential duplicate case(s). Review side-by-side comparisons in Data Quality & Verification module.
              </div>
            )}
          </div>

          {/* ── AI Role-Based Decision Support Assessment ── */}
          {isOfficer && dssData && (
            <div style={{ background: "#ffffff", padding: "6px", borderRadius: "10px" }}>
              <DSSCard
                title="AI Role-Based Decision Support Dossier"
                assessment={dssData.assessment}
                recommendation={dssData.recommendation}
                userRole={user?.role}
                onAction={async (action, notes) => {
                  return await api("/dss/decision", {
                    method: "POST",
                    body: JSON.stringify({
                      recommendation_id: dssData.recommendation_id,
                      entity_type: "parcel",
                      entity_id: String(data.id),
                      action: action,
                      modified_notes: notes
                    })
                  });
                }}
                onAskAi={() => setAskAiOpen(true)}
              />
            </div>
          )}
        </div>
      </div>

      {/* Ask AI Modal */}
      {isOfficer && (
        <AskAiModal
          isOpen={askAiOpen}
          onClose={() => setAskAiOpen(false)}
          entityType="parcel"
          entityId={String(data.id)}
          onAsk={async (entityType, entityId, question) => {
            return await api("/dss/ask", {
              method: "POST",
              body: JSON.stringify({ entity_type: entityType, entity_id: entityId, question: question })
            });
          }}
        />
      )}

      {/* ── Lower Full-Width Grid: Field Verification, Grievances, Alerts, Audit Ledger ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        {/* Field Verification History */}
        <div style={{ background: "#ffffff", padding: "18px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
          <h3 style={{ margin: "0 0 12px 0", color: "#0f6c70", fontSize: "15px", fontWeight: 800 }}>
            📋 Field Verification & Ground Truth History
          </h3>
          {data.field_verifications && data.field_verifications.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Task ID</th>
                    <th>Officer</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Boundary</th>
                    <th>Remarks</th>
                  </tr>
                </thead>
                <tbody>
                  {data.field_verifications.map((fv, i) => (
                    <tr key={fv.id || i}>
                      <td><span style={{ fontFamily: "monospace", fontSize: "11px" }}>{fv.task_id || `TSK-${fv.id}`}</span></td>
                      <td>{fv.verified_by || fv.officer_email || "Field Officer"}</td>
                      <td>{(fv.verification_date || fv.created_at || "N/A").slice(0, 10)}</td>
                      <td><span style={{ color: "#16a34a", fontWeight: 700, fontSize: "11px" }}>{fv.status || "Completed"}</span></td>
                      <td>{fv.boundary_matched ? "✓ Matched" : "⚠️ Discrepancy"}</td>
                      <td style={{ fontSize: "11px", color: "#64748b" }}>{fv.remarks || "Survey conducted"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ color: "#64748b", fontSize: "12px", background: "#f8fafc", padding: "12px", borderRadius: "6px" }}>
              No ground field inspection logged yet for this parcel.
            </div>
          )}
        </div>

        {/* Citizen Grievances & Objections */}
        <div style={{ background: "#ffffff", padding: "18px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
          <h3 style={{ margin: "0 0 12px 0", color: "#0f6c70", fontSize: "15px", fontWeight: 800 }}>
            ⚖️ Citizen Grievances & Public Objections
          </h3>
          {data.grievances && data.grievances.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Grievance ID</th>
                    <th>Category</th>
                    <th>Filing Date</th>
                    <th>Status</th>
                    <th>Resolution SLA</th>
                  </tr>
                </thead>
                <tbody>
                  {data.grievances.map((g, i) => (
                    <tr key={g.id || i}>
                      <td><span style={{ fontFamily: "monospace", fontSize: "11px" }}>{g.grievance_id || `GRV-${g.id}`}</span></td>
                      <td><b>{g.category || "Compensation Mismatch"}</b></td>
                      <td>{(g.filed_date || g.created_at || "N/A").slice(0, 10)}</td>
                      <td>
                        <span style={{ background: g.status === "Resolved" ? "#dcfce7" : "#fee2e2", color: g.status === "Resolved" ? "#166534" : "#991b1b", padding: "2px 6px", borderRadius: "4px", fontSize: "11px", fontWeight: 700 }}>
                          {g.status || "Submitted"}
                        </span>
                      </td>
                      <td style={{ fontSize: "11px" }}>{g.sla_status || "Within Statutory SLA"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ color: "#64748b", fontSize: "12px", background: "#f8fafc", padding: "12px", borderRadius: "6px" }}>
              No citizen grievances or statutory objections registered for this parcel.
            </div>
          )}
        </div>
      </div>

      {/* ── Official Audit Ledger & Chain of Custody ── */}
      <div style={{ background: "#ffffff", padding: "18px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
        <h3 style={{ margin: "0 0 12px 0", color: "#0f6c70", fontSize: "15px", fontWeight: 800 }}>
          🔒 Official Audit Trail & Chain of Custody
        </h3>
        {data.audit && data.audit.length > 0 ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp (UTC)</th>
                  <th>Actor / Officer</th>
                  <th>Action</th>
                  <th>Entity</th>
                  <th>Ledger Details</th>
                </tr>
              </thead>
              <tbody>
                {data.audit.slice(0, 8).map((a, i) => (
                  <tr key={a.id || i}>
                    <td style={{ fontSize: "11px", color: "#64748b" }}>{a.timestamp?.slice(0, 19)}</td>
                    <td><b>{a.user_email || "system"}</b></td>
                    <td>
                      <span style={{ background: "#f1f5f9", color: "#0f6c70", padding: "2px 6px", borderRadius: "4px", fontSize: "11px", fontWeight: 700, fontFamily: "monospace" }}>
                        {a.action}
                      </span>
                    </td>
                    <td style={{ fontSize: "11px" }}>{a.entity_type} #{a.entity_id}</td>
                    <td style={{ fontSize: "11px", color: "#334155" }}>{a.new_value || a.details || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ color: "#64748b", fontSize: "12px", background: "#f8fafc", padding: "12px", borderRadius: "6px" }}>
            No audit trail records found for this parcel.
          </div>
        )}
      </div>

      {/* ── Privacy Access Request Modal ── */}
      {privacyModalOpen && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(15, 23, 42, 0.6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000,
          padding: "20px"
        }}>
          <div style={{
            background: "#ffffff",
            borderRadius: "12px",
            maxWidth: "500px",
            width: "100%",
            padding: "24px",
            boxShadow: "0 20px 25px -5px rgba(0,0,0,0.2)"
          }}>
            <h3 style={{ margin: "0 0 8px 0", color: "#0f6c70", fontSize: "18px", fontWeight: 800 }}>
              Request Elevated PII Access
            </h3>
            <p style={{ margin: "0 0 16px 0", fontSize: "12px", color: "#64748b" }}>
              In compliance with the Purpose-Aware Privacy Guard protocol, unmasking citizen identity or banking details requires a justified statutory operational purpose.
            </p>

            <form onSubmit={handlePrivacyRequest} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <label style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>
                Operational Purpose *
                <select
                  value={reqPurpose}
                  onChange={e => setReqPurpose(e.target.value)}
                  style={{ width: "100%", marginTop: "4px", padding: "8px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                >
                  <option value="COMPENSATION_DISBURSEMENT">Compensation Disbursement (Direct Bank Transfer)</option>
                  <option value="LEGAL_NOTICE_SERVICE">Legal Notice Service (§11 / §19 Gazette Notice)</option>
                  <option value="FIELD_VERIFICATION">Field Verification & Ground Truth Inspection</option>
                  <option value="GRIEVANCE_REDRESSAL">Grievance Redressal & Hearing Inquiry</option>
                  <option value="REHABILITATION_SETTLEMENT">Rehabilitation & Resettlement (R&R Package)</option>
                </select>
              </label>

              <label style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>
                Operational Justification / Case Reference *
                <textarea
                  required
                  rows={3}
                  value={reqJustification}
                  onChange={e => setReqJustification(e.target.value)}
                  placeholder="State the official statutory rationale for requiring unmasked Aadhaar, bank details, or contact info..."
                  style={{ width: "100%", marginTop: "4px", padding: "8px", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                />
              </label>

              {reqFeedback && (
                <div style={{ padding: "8px 12px", borderRadius: "6px", fontSize: "12px", background: reqFeedback.includes("Error") ? "#fee2e2" : "#f0fdf4", color: reqFeedback.includes("Error") ? "#991b1b" : "#166534" }}>
                  {reqFeedback}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setPrivacyModalOpen(false)}
                  style={{ padding: "8px 14px", background: "#f1f5f9", color: "#334155", border: "1px solid #cbd5e1", borderRadius: "6px", fontWeight: 700, cursor: "pointer", fontSize: "12px" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={reqLoading}
                  style={{ padding: "8px 16px", background: "#0f6c70", color: "#ffffff", border: "none", borderRadius: "6px", fontWeight: 700, cursor: reqLoading ? "not-allowed" : "pointer", fontSize: "12px" }}
                >
                  {reqLoading ? "Submitting..." : "Submit Access Request"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function Placeholder({ title }) { return <Panel title={title}><div className="empty">No operational records available.</div></Panel>; }

function Simulator() {
  const [out, setOut] = useState(null);
  return <section className="panel"><h2>Acquisition Flight Simulator</h2><p>Compare Route A/B/C before a decision.</p><button onClick={async() => setOut(await api('/intelligence/simulate', {method:'POST',body:JSON.stringify({})}))}>Run Simulation</button>{out && <div className="grid2" style={{marginTop: 15}}>{out.scenarios.map(s => <div className="notice" key={s.name}><h3>{s.name}{s.name === out.recommended.name ? ' ★ Recommended' : ''}</h3><div>Cost: {s.cost.toFixed(1)}</div><div>Affected parcels: {s.affected_parcels}</div><div>High-risk: {s.high_risk}</div><div>Delay: {s.delay_months} months</div><div>Decision score: <b>{s.decision_score}</b></div></div>)}</div>}</section>;
}

function Tools({ district }) {
  const [res, setRes] = useState(null);
  const [p, setP] = useState({before:0.2, after:0.5, threshold:0.15});
  return <section className="panel"><h2>Evidence Intelligence</h2><div className="toolbar" style={{display: 'flex', gap: '10px'}}><button onClick={async() => setRes(await api('/intelligence/satellite/change', {method:'POST',body:JSON.stringify(p)}))}>Check Satellite Change</button><button onClick={async() => setRes(await api('/intelligence/premortem', {method:'POST',body:JSON.stringify({legal_disputes:1,objections:1,compensation_deviation:18,satellite_change:1})}))}>Run Acquisition Pre-Mortem</button><button onClick={async() => setRes(await api(`/intelligence/conflict-graph${district ? `?district=${encodeURIComponent(district)}` : ''}`))}>Build Conflict Graph</button></div><div className="toolbar" style={{display: 'flex', gap: '10px', marginTop: '10px'}}>{Object.keys(p).map(k => <label key={k}>{k} <input type="number" step="0.01" value={p[k]} onChange={e => setP({...p, [k]: parseFloat(e.target.value)})}/></label>)}</div>{res && <pre style={{background: '#f4f4f4', padding: '10px', marginTop: '10px', overflowX: 'auto'}}>{JSON.stringify(res,null,2)}</pre>}</section>;
}

function Evidence() {
  const [parcel, setParcel] = useState('');
  const [reason, setReason] = useState('');
  const [msg, setMsg] = useState('');
  return <section className="panel"><h2>Citizen Evidence & Field Verification</h2><div style={{display: 'grid', gap: '10px', marginBottom: '10px'}}><label>Parcel ID <input value={parcel} onChange={e => setParcel(e.target.value)}/></label><label>Objection / notes <textarea value={reason} onChange={e => setReason(e.target.value)}/></label></div><div className="toolbar" style={{display: 'flex', gap: '10px'}}><button onClick={async() => {try {const x = await api('/intelligence/objection', {method:'POST',body:JSON.stringify({parcel_id:parcel,reason})}); setMsg(x.message)} catch(e) {setMsg(e.message)}}}>Submit Citizen Objection</button><button onClick={async() => {try {const x = await api('/intelligence/verify', {method:'POST',body:JSON.stringify({parcel_id:parcel,outcome:'verified',notes:reason,latitude:11.0168,longitude:76.9558})}); setMsg(x.message)} catch(e) {setMsg(e.message)}}}>Field Verify</button><button onClick={async() => setMsg(JSON.stringify(await api('/intelligence/ledger'), null, 2))}>Check Evidence Ledger</button></div>{msg && <pre style={{background: '#f4f4f4', padding: '10px', marginTop: '10px', overflowX: 'auto'}}>{msg}</pre>}</section>;
}

function Report() {
  const [id, setId] = useState('');
  const [out, setOut] = useState(null);
  return <section className="panel"><h2>Factual Evidence Report</h2><div className="toolbar"><input placeholder="Parcel database ID" value={id} onChange={e => setId(e.target.value)}/><button onClick={async() => setOut(await api('/intelligence/report/'+id))}>Generate Report</button></div>{out && <pre style={{background: '#f4f4f4', padding: '10px', marginTop: '10px', overflowX: 'auto'}}>{JSON.stringify(out,null,2)}</pre>}</section>;
}

function Advanced({ district }) {
  const [fusion, setFusion] = useState(null);
  const [cluster, setCluster] = useState(null);
  const [active, setActive] = useState(null);
  const [fb, setFb] = useState('');
  const runFusion = async() => setFusion(await api('/intelligence/fusion', {method:'POST',body:JSON.stringify({features:{project_type:'Road',land_required:2,affected_parcels:10,affected_families:3,legal_disputes:1,compensation_pending:1,approval_pending:0,documentation_pending:1,rehabilitation_pending:0,notification_pending:0,award_pending:0,possession_pending:0,stakeholder_responsiveness:2,environmental_risk:1,weather_risk:1},evidence:{satellite_observation:true,satellite_confidence:.86,document_mismatch_count:2,objection_count:2,ownership_complexity:3,data_completeness:72}})}));
  const runActive = async() => setActive(await api('/intelligence/active-learning', {method:'POST',body:JSON.stringify({parcels:[{parcel_id:'P1048',risk:76,uncertainty:28,missing_evidence:2,connected_parcels:8},{parcel_id:'P102',risk:64,uncertainty:61,missing_evidence:4,connected_parcels:6},{parcel_id:'P103',risk:77,uncertainty:35,missing_evidence:1,connected_parcels:2}]})}));
  return <section className="panel"><h2>Advanced Intelligence • Closed Loop</h2><div className="toolbar" style={{display: 'flex', gap: '10px'}}><button onClick={runFusion}>Run Multimodal Fusion</button><button onClick={async() => setCluster(await api(`/intelligence/clusters${district ? `?district=${encodeURIComponent(district)}` : ''}`))}>Detect Conflict Clusters</button><button onClick={runActive}>Prioritize Field Verification</button></div>{fusion && <div className="notice" style={{marginTop: '10px'}}><b>Fusion Risk {fusion.risk_score}/100 • {fusion.risk_category}</b><br/>Uncertainty: {fusion.uncertainty}% • Data quality: {fusion.data_quality}%<br/>{fusion.disclaimer}</div>}{cluster && <pre style={{background: '#f4f4f4', padding: '10px', marginTop: '10px', overflowX: 'auto'}}>{JSON.stringify(cluster,null,2)}</pre>}{active && <pre style={{background: '#f4f4f4', padding: '10px', marginTop: '10px', overflowX: 'auto'}}>{JSON.stringify(active,null,2)}</pre>}<div className="toolbar" style={{display: 'flex', gap: '10px', marginTop: '10px'}}><input placeholder="Predicted label" value={fb} onChange={e => setFb(e.target.value)}/><button onClick={async() => setFb(JSON.stringify(await api('/intelligence/feedback', {method:'POST',body:JSON.stringify({parcel_id:1,predicted:fb,ground_truth:'VERIFIED',notes:'Field outcome captured'})}), null, 2))}>Record Ground Truth</button><button onClick={async() => setFb(JSON.stringify(await api('/intelligence/model-health'), null, 2))}>Model Health</button></div>{fb && <pre style={{background: '#f4f4f4', padding: '10px', marginTop: '10px', overflowX: 'auto'}}>{fb}</pre>}</section>;
}


// ─── Cross-Department Conflict Engine ────────────────────────────────────────
const SEV_COLOR = { Critical: '#b42318', High: '#d97706', Medium: '#0056b3', Low: '#16704a' };
const STATUS_COLOR = { Resolved: '#16704a', 'Under Review': '#d97706', Escalated: '#b42318', Assigned: '#0056b3', Pending: '#888', Verified: '#16704a', 'Cannot Verify': '#b42318' };

function SeverityBadge({ s }) {
  return <span style={{ background: SEV_COLOR[s] || '#888', color: '#fff', borderRadius: '4px', padding: '2px 8px', fontSize: '11px', fontWeight: 700 }}>{s}</span>;
}
function StatusBadge({ s }) {
  return <span style={{ background: STATUS_COLOR[s] || '#888', color: '#fff', borderRadius: '4px', padding: '2px 8px', fontSize: '11px' }}>{s || 'Pending'}</span>;
}

function ConflictEngine({ user, district }) {
  const role = user?.role || '';
  const isState    = ['state_authority', 'authority', 'admin'].includes(role);
  const isDistrict = ['district_authority', 'authority', 'admin', 'acquisition_officer'].includes(role);
  const isField    = ['field_officer', 'officer', 'authority', 'admin'].includes(role);

  // ── shared conflict list state ────────────────────────────────────
  const [severity, setSeverity] = useState('ALL');
  const [status, setStatus]     = useState('ALL');
  const [search, setSearch]     = useState('');
  const [refresh, setRefresh]   = useState(0);
  const bump = () => setRefresh(r => r + 1);

  const params = new URLSearchParams({ severity, status, search });
  if (district) params.set('district', district);
  const { data, error } = useData(`/intelligence/conflict-engine?${params}`, 0);

  // ── assignment tracking (District view) ──────────────────────────
  const { data: allAssignments } = useData(isDistrict ? '/intelligence/conflict-engine/assignments/all' : null, 0);
  // ── my assignments (Field view) ──────────────────────────────────
  const { data: myData } = useData(isField && !isDistrict && !isState ? '/intelligence/conflict-engine/assignments/mine' : null, 0);

  // ── per-row UI state ─────────────────────────────────────────────
  const [expandedId, setExpandedId] = useState(null);
  const [assignForms, setAssignForms]     = useState({}); // {conflictId: {officer_email, priority, notes}}
  const [fieldForms, setFieldForms]       = useState({}); // {conflictId: {field_status, field_remarks, evidence_description}}
  const [resolveForms, setResolveForms]   = useState({}); // {conflictId: {resolution_status, resolution_note}}
  const [saving, setSaving]               = useState({});
  const [msgs, setMsgs]                   = useState({});

  const setMsg = (id, m) => setMsgs(p => ({ ...p, [id]: m }));
  const setSav = (id, v) => setSaving(p => ({ ...p, [id]: v }));

  // ── field officers for District assign dropdown ───────────────────
  const { data: officersData } = useData(isDistrict ? '/field/officers' : null);
  const officers = officersData || [];

  // ── summary cards ─────────────────────────────────────────────────
  const sum = data?.summary || {};

  // ── Field officer: merge my assignments with conflict list ────────
  const myAssignMap = {};
  if (myData?.assignments) {
    myData.assignments.forEach(a => { myAssignMap[a.conflict_id] = a; });
  }
  const allAssignMap = {};
  if (allAssignments?.assignments) {
    allAssignments.assignments.forEach(a => { allAssignMap[a.conflict_id] = a; });
  }

  // For field officers without District/State access, only show their assigned conflicts
  const conflicts = (() => {
    if (!data?.conflicts) return [];
    if (isField && !isDistrict && !isState) {
      // Only show conflicts that are assigned to this field officer
      return data.conflicts.filter(cf => myAssignMap[cf.conflict_id]);
    }
    return data.conflicts;
  })();

  const saveAssign = async (cf) => {
    const form = assignForms[cf.conflict_id] || {};
    if (!form.officer_email) { setMsg(cf.conflict_id, 'Select a field officer'); return; }
    setSav(cf.conflict_id, true);
    try {
      const r = await api(`/intelligence/conflict-engine/${cf.conflict_id}/assign`, {
        method: 'POST',
        body: JSON.stringify({ officer_email: form.officer_email, priority: form.priority || 'Normal', notes: form.notes || '' })
      });
      setMsg(cf.conflict_id, r.message);
      setAssignForms(p => ({ ...p, [cf.conflict_id]: {} }));
      bump();
    } catch(e) { setMsg(cf.conflict_id, e.message); }
    setSav(cf.conflict_id, false);
  };

  const saveFieldUpdate = async (cf) => {
    const form = fieldForms[cf.conflict_id] || {};
    if (!form.field_status) { setMsg(cf.conflict_id, 'Select a field status'); return; }
    setSav(cf.conflict_id, true);
    try {
      const r = await api(`/intelligence/conflict-engine/${cf.conflict_id}/field-update`, {
        method: 'PATCH',
        body: JSON.stringify({ field_status: form.field_status, field_remarks: form.field_remarks || '', evidence_description: form.evidence_description || '' })
      });
      setMsg(cf.conflict_id, r.message);
      bump();
    } catch(e) { setMsg(cf.conflict_id, e.message); }
    setSav(cf.conflict_id, false);
  };

  const saveResolve = async (cf) => {
    const form = resolveForms[cf.conflict_id] || {};
    setSav(cf.conflict_id, true);
    try {
      const r = await api(`/intelligence/conflict-engine/${cf.conflict_id}/resolve`, {
        method: 'PATCH',
        body: JSON.stringify({ resolution_status: form.resolution_status || 'Resolved', resolution_note: form.resolution_note || '' })
      });
      setMsg(cf.conflict_id, r.message);
      bump();
    } catch(e) { setMsg(cf.conflict_id, e.message); }
    setSav(cf.conflict_id, false);
  };

  if (error) return (
    <Panel title="Cross-Department Conflict Engine">
      <div className="error">Unable to load conflicts ({error.status || 'network error'}): {error.message} <RefreshButton /></div>
    </Panel>
  );
  if (!data) return <Panel title="Cross-Department Conflict Engine"><p>Loading conflict data…</p></Panel>;

  return (
    <>
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>Cross-Department Conflict Engine</h2>
        <RefreshButton />
      </div>

      {sum.demo_rows > 0 && (
        <div className="notice" style={{ background: '#fffbe6', borderLeft: '4px solid #d97706', marginBottom: 12 }}>
          ⚠ <b>DEMO DATA:</b> {sum.demo_rows} synthetic conflict row(s) are included for demonstration. Real conflicts detected from live parcel-project overlaps are labelled LIVE.
        </div>
      )}

      {/* ── Summary Cards ──────────────────────────────────────────── */}
      <div className="cards" style={{ marginBottom: 16 }}>
        {[['Total Conflicts', sum.total, '#0056b3'],
          ['Critical', sum.critical, '#b42318'],
          ['High', sum.high, '#d97706'],
          ['Resolved', sum.resolved, '#16704a'],
          ['Pending', sum.pending, '#555']
        ].map(([label, val, col]) => (
          <div className="metric" key={label} style={{ borderTop: `3px solid ${col}` }}>
            <span>{label}</span><b style={{ color: col }}>{val ?? 0}</b>
          </div>
        ))}
      </div>

      {/* ── Filters ────────────────────────────────────────────────── */}
      <div className="toolbar" style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <input placeholder="Search survey, village, type…" value={search}
          onChange={e => setSearch(e.target.value)} style={{ minWidth: 200 }} />
        <select value={severity} onChange={e => setSeverity(e.target.value)}>
          {['ALL','Critical','High','Medium','Low'].map(x => <option key={x}>{x}</option>)}
        </select>
        <select value={status} onChange={e => setStatus(e.target.value)}>
          {['ALL','Pending','Under Review','Escalated','Assigned','Verified','Resolved'].map(x => <option key={x}>{x}</option>)}
        </select>
      </div>

      {/* ── Field officer with no assignments ─────────────────────── */}
      {isField && !isDistrict && !isState && conflicts.length === 0 && (
        <div className="empty">No conflicts assigned to you yet. Your District Authority will assign conflicts for field verification.</div>
      )}

      {/* ── Conflict Cards ─────────────────────────────────────────── */}
      {conflicts.map(cf => {
        const expanded   = expandedId === cf.conflict_id;
        const assignment = allAssignMap[cf.conflict_id] || myAssignMap[cf.conflict_id] || null;
        const aForm  = assignForms[cf.conflict_id] || {};
        const fForm  = fieldForms[cf.conflict_id] || {};
        const rForm  = resolveForms[cf.conflict_id] || {};
        const isSaving = saving[cf.conflict_id];
        const msg    = msgs[cf.conflict_id];

        return (
          <div key={cf.conflict_id} style={{ background: '#fff', border: `2px solid ${SEV_COLOR[cf.severity] || '#ddd'}`, borderRadius: 8, marginBottom: 12, overflow: 'hidden' }}>

            {/* ── Card Header ────────────────────────────────────── */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 16px', background: '#f8f9fa', cursor: 'pointer' }}
                 onClick={() => setExpandedId(expanded ? null : cf.conflict_id)}>
              <div>
                <b>Survey {cf.survey_no}</b> · {cf.village}
                {cf.data_source === 'DEMO' && <span style={{ marginLeft: 8, fontSize: 10, background: '#d97706', color: '#fff', borderRadius: 3, padding: '1px 6px' }}>DEMO</span>}
                <span style={{ margin: '0 8px', color: '#666', fontSize: 12 }}>{cf.conflict_type}</span>
              </div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <SeverityBadge s={cf.severity} />
                <StatusBadge s={assignment?.field_status || cf.resolution_status} />
                <span style={{ fontSize: 18, color: '#666' }}>{expanded ? '▲' : '▼'}</span>
              </div>
            </div>

            {/* ── Expanded Body ───────────────────────────────────── */}
            {expanded && (
              <div style={{ padding: '14px 16px' }}>

                {/* Core info */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 12, background: '#f8f9fa', padding: 10, borderRadius: 6 }}>
                  <div><b>Conflict ID:</b><br /><small>{cf.conflict_id}</small></div>
                  <div><b>Overlap Area:</b><br />{cf.overlap_area_acres} acres ({cf.overlap_pct}%)</div>
                  <div><b>Resolution Status:</b><br /><StatusBadge s={cf.resolution_status} /></div>
                </div>

                {/* Departments */}
                <div style={{ marginBottom: 10 }}>
                  <b>Conflicting Departments / Projects:</b>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
                    {cf.departments.map((d, i) => (
                      <div key={i} style={{ background: '#e8f0fe', borderRadius: 6, padding: '5px 10px', fontSize: 13 }}>
                        <b>{d.department}</b><br /><small>{d.project_name}</small><br /><small style={{ color: '#666' }}>{d.project_id}</small>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Suggested resolution */}
                <div style={{ background: '#f0fff4', border: '1px solid #16704a', borderRadius: 6, padding: 10, marginBottom: 12 }}>
                  <b>💡 Suggested Resolution:</b><br />{cf.suggested_resolution}
                </div>

                {/* Assignment status if any */}
                {assignment && (
                  <div style={{ background: '#e8f0fe', borderRadius: 6, padding: 10, marginBottom: 12 }}>
                    <b>Field Assignment:</b> {assignment.assigned_to} · Priority: {assignment.priority}
                    {assignment.notes && <> · Notes: {assignment.notes}</>}<br />
                    <b>Field Status:</b> <StatusBadge s={assignment.field_status} />
                    {assignment.field_remarks && <> · Remarks: {assignment.field_remarks}</>}
                    {assignment.evidence_file && <> · Evidence: {assignment.evidence_file}</>}
                  </div>
                )}

                {msg && <div className="notice" style={{ marginBottom: 10, color: msg.includes('failed') || msg.includes('error') ? 'red' : '#16704a' }}>{msg}</div>}

                {/* ── District Officer Actions ────────────────────── */}
                {isDistrict && (
                  <details style={{ marginBottom: 10 }}>
                    <summary style={{ cursor: 'pointer', fontWeight: 600, marginBottom: 6 }}>
                      {assignment ? '↺ Re-assign Field Officer' : '+ Assign Field Officer'}
                    </summary>
                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 2fr auto', gap: 8, alignItems: 'end', marginTop: 8 }}>
                      <label>Field Officer
                        <select value={aForm.officer_email || ''} onChange={e => setAssignForms(p => ({ ...p, [cf.conflict_id]: { ...aForm, officer_email: e.target.value } }))}>
                          <option value="">Select officer…</option>
                          {officers.map(o => <option key={o.email} value={o.email}>{o.email}</option>)}
                        </select>
                      </label>
                      <label>Priority
                        <select value={aForm.priority || 'Normal'} onChange={e => setAssignForms(p => ({ ...p, [cf.conflict_id]: { ...aForm, priority: e.target.value } }))}>
                          {['Normal','High','Urgent'].map(x => <option key={x}>{x}</option>)}
                        </select>
                      </label>
                      <label>Notes
                        <input placeholder="Instructions for officer…" value={aForm.notes || ''}
                          onChange={e => setAssignForms(p => ({ ...p, [cf.conflict_id]: { ...aForm, notes: e.target.value } }))} />
                      </label>
                      <button onClick={() => saveAssign(cf)} disabled={isSaving} style={{ background: '#0056b3', color: '#fff' }}>
                        {isSaving ? 'Saving…' : 'Assign'}
                      </button>
                    </div>
                  </details>
                )}

                {isDistrict && (
                  <details style={{ marginBottom: 10 }}>
                    <summary style={{ cursor: 'pointer', fontWeight: 600, marginBottom: 6 }}>Mark as Resolved / Escalated</summary>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr auto', gap: 8, alignItems: 'end', marginTop: 8 }}>
                      <label>Status
                        <select value={rForm.resolution_status || 'Resolved'} onChange={e => setResolveForms(p => ({ ...p, [cf.conflict_id]: { ...rForm, resolution_status: e.target.value } }))}>
                          {['Resolved','Under Review','Escalated','Pending'].map(x => <option key={x}>{x}</option>)}
                        </select>
                      </label>
                      <label>Resolution Note
                        <input placeholder="Describe resolution…" value={rForm.resolution_note || ''}
                          onChange={e => setResolveForms(p => ({ ...p, [cf.conflict_id]: { ...rForm, resolution_note: e.target.value } }))} />
                      </label>
                      <button onClick={() => saveResolve(cf)} disabled={isSaving} style={{ background: '#16704a', color: '#fff' }}>
                        {isSaving ? 'Saving…' : 'Update'}
                      </button>
                    </div>
                  </details>
                )}

                {/* ── Field Officer Actions ───────────────────────── */}
                {isField && (
                  <details style={{ marginBottom: 10 }} open={isField && !isDistrict && !isState}>
                    <summary style={{ cursor: 'pointer', fontWeight: 600, marginBottom: 6 }}>📋 Submit Field Verification</summary>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 2fr auto', gap: 8, alignItems: 'end', marginTop: 8 }}>
                      <label>Field Status
                        <select value={fForm.field_status || ''} onChange={e => setFieldForms(p => ({ ...p, [cf.conflict_id]: { ...fForm, field_status: e.target.value } }))}>
                          <option value="">Select…</option>
                          {['Assigned','In Progress','Verified','Cannot Verify','Escalated'].map(x => <option key={x}>{x}</option>)}
                        </select>
                      </label>
                      <label>Field Remarks
                        <input placeholder="Ground observations…" value={fForm.field_remarks || ''}
                          onChange={e => setFieldForms(p => ({ ...p, [cf.conflict_id]: { ...fForm, field_remarks: e.target.value } }))} />
                      </label>
                      <label>Evidence Description
                        <input placeholder="Photo ref / doc ref / GPS note…" value={fForm.evidence_description || ''}
                          onChange={e => setFieldForms(p => ({ ...p, [cf.conflict_id]: { ...fForm, evidence_description: e.target.value } }))} />
                      </label>
                      <button onClick={() => saveFieldUpdate(cf)} disabled={isSaving} style={{ background: '#0056b3', color: '#fff' }}>
                        {isSaving ? 'Saving…' : 'Submit'}
                      </button>
                    </div>
                  </details>
                )}

              </div>
            )}
          </div>
        );
      })}

      {conflicts.length === 0 && data && (
        <div className="empty">No conflicts match the current filters.</div>
      )}

      {/* ── District: Assignment Tracker ───────────────────────────── */}
      {isDistrict && allAssignments?.assignments?.length > 0 && (
        <Panel title={`Field Assignment Tracker (${allAssignments.total})`}>
          <Table
            rows={allAssignments.assignments}
            cols={['conflict_id','assigned_to','assigned_by','priority','field_status','field_remarks','assigned_at','updated_at']}
          />
        </Panel>
      )}
    </>
  );
}

function RRHouseholdModal({ familyId, user, onClose, onOpenVerify }) {
  const { data, error } = useData(familyId ? `/rr/families/${encodeURIComponent(familyId)}` : null);

  if (!familyId) return null;

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      background: "rgba(15, 37, 51, 0.7)", backdropFilter: "blur(3px)",
      display: "flex", justifyContent: "center", alignItems: "center", zIndex: 9999, padding: "20px"
    }}>
      <div style={{
        background: "#ffffff", borderRadius: "12px", width: "100%", maxWidth: "880px",
        maxHeight: "92vh", overflowY: "auto", padding: "24px", boxShadow: "0 20px 45px rgba(0,0,0,0.3)",
        position: "relative", border: "1px solid #cbd5e1"
      }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid #e2e8f0", paddingBottom: "14px", marginBottom: "16px" }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: 800, color: "#0f6c70", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Affected Household & Property R&R Profile
            </div>
            <h2 style={{ margin: "4px 0", color: "#0f172a", fontSize: "22px" }}>
              {data?.family_head || "Loading..."} <span style={{ fontSize: "15px", color: "#64748b", fontWeight: 400 }}>({familyId})</span>
            </h2>
            <div style={{ fontSize: "13px", color: "#475569" }}>
              {data?.full_address || `${data?.village || ""}, ${data?.taluk || ""}, ${data?.district || ""}`}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: "#f1f5f9", color: "#475569", border: "1px solid #cbd5e1", borderRadius: "6px", padding: "6px 12px", cursor: "pointer", fontSize: "14px", fontWeight: 700 }}
          >
            ✕ Close
          </button>
        </div>

        {error && <div className="error" style={{ marginBottom: "16px" }}>Failed to load household profile: {error.message}</div>}
        {!data && !error && <div style={{ padding: "30px", textAlign: "center", color: "#64748b" }}>Loading household R&R profile...</div>}

        {data && (
          <>
            {/* Status & Readiness Banner */}
            <div style={{
              background: "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)",
              border: "1px solid #e2e8f0", borderRadius: "10px", padding: "16px", marginBottom: "20px",
              display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", alignItems: "center"
            }}>
              <div>
                <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>Current R&R Stage</span>
                <div style={{ fontWeight: 800, fontSize: "15px", color: "#0f6c70", marginTop: "2px" }}>{data.rr_stage}</div>
              </div>
              <div>
                <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>Overall Status</span>
                <div style={{ fontWeight: 800, fontSize: "15px", color: data.exceptional_state === "Completed" ? "#16704a" : "#d97706", marginTop: "2px" }}>
                  {data.exceptional_state || "Pending"}
                </div>
              </div>
              <div>
                <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>Readiness Score</span>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
                  <div style={{ flex: 1, height: "10px", background: "#e2e8f0", borderRadius: "5px", overflow: "hidden" }}>
                    <div style={{
                      width: `${Math.min(100, Math.max(0, data.readiness_percentage || 0))}%`,
                      height: "100%",
                      background: data.readiness_percentage >= 90 ? "#16704a" : (data.readiness_percentage >= 60 ? "#0f6c70" : (data.readiness_percentage >= 30 ? "#d97706" : "#dc2626")),
                      transition: "width 0.4s ease"
                    }} />
                  </div>
                  <b style={{ fontSize: "14px", color: "#0f172a", minWidth: "45px" }}>{data.readiness_percentage || 0}%</b>
                </div>
                <span style={{ fontSize: "11px", fontWeight: 600, color: "#475569" }}>Band: {data.readiness_band || "Pending"}</span>
              </div>
            </div>

            {/* Core Identification & Land Attributes */}
            <div style={{ marginBottom: "20px" }}>
              <h4 style={{ margin: "0 0 10px", fontSize: "13px", color: "#334155", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                1. Property & Family Demographics
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "14px", fontSize: "12px" }}>
                <div><b style={{ color: "#64748b" }}>Survey Number:</b> <span style={{ color: "#0f172a", fontWeight: 600 }}>{data.survey_no}</span></div>
                <div><b style={{ color: "#64748b" }}>Parcel ID:</b> <span style={{ color: "#0f172a", fontWeight: 600 }}>{data.parcel_id || "Unassigned"}</span></div>
                <div><b style={{ color: "#64748b" }}>Registered Landowner:</b> <span style={{ color: "#0f172a", fontWeight: 600 }}>{data.landowner}</span></div>
                <div><b style={{ color: "#64748b" }}>Affected Family Head:</b> <span style={{ color: "#0f172a", fontWeight: 600 }}>{data.family_head}</span></div>
                <div><b style={{ color: "#64748b" }}>Family Members:</b> <span style={{ color: "#0f172a", fontWeight: 600 }}>{data.members} persons</span></div>
                <div><b style={{ color: "#64748b" }}>Displacement Status:</b> <span style={{ color: "#0f172a", fontWeight: 600 }}>{data.displacement_status}</span></div>
                <div><b style={{ color: "#64748b" }}>Village / Taluk:</b> <span style={{ color: "#0f172a" }}>{data.village} / {data.taluk}</span></div>
                <div><b style={{ color: "#64748b" }}>District:</b> <span style={{ color: "#0f172a" }}>{data.district}</span></div>
                <div><b style={{ color: "#64748b" }}>Vulnerability:</b> <span style={{ color: data.is_vulnerable ? "#b91c1c" : "#0f172a", fontWeight: 600 }}>{data.is_vulnerable ? "Yes (Vulnerable)" : "Standard"}</span></div>
                <div style={{ gridColumn: "span 3" }}><b style={{ color: "#64748b" }}>Full Address:</b> <span style={{ color: "#0f172a" }}>{data.full_address}</span></div>
              </div>
            </div>

            {/* Component Entitlement Statuses */}
            <div style={{ marginBottom: "20px" }}>
              <h4 style={{ margin: "0 0 10px", fontSize: "13px", color: "#334155", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                2. Entitlement & Rehabilitation Status
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                  <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>COMPENSATION STATUS</div>
                  <div style={{ fontWeight: 800, fontSize: "14px", color: "#0f172a", marginTop: "4px" }}>{data.compensation_status}</div>
                  <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>
                    Entitled: ₹{(data.compensation_entitled || 0).toLocaleString()} | Paid: ₹{(data.compensation_paid || 0).toLocaleString()}
                  </div>
                </div>
                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                  <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>HOUSING STATUS</div>
                  <div style={{ fontWeight: 800, fontSize: "14px", color: "#0f172a", marginTop: "4px" }}>{data.housing_status}</div>
                  <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>Resettlement Site Allocation & Possession</div>
                </div>
                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                  <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>LIVELIHOOD STATUS</div>
                  <div style={{ fontWeight: 800, fontSize: "14px", color: "#0f172a", marginTop: "4px" }}>{data.livelihood_status}</div>
                  <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>Skill Development & Annuity Support</div>
                </div>
                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                  <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>OTHER R&R BENEFITS</div>
                  <div style={{ fontWeight: 800, fontSize: "14px", color: "#0f172a", marginTop: "4px" }}>
                    {data.other_benefits_status || (data.readiness_percentage >= 70 ? "Sanctioned" : "In Progress")}
                  </div>
                  <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>Subsistence Grant, Shifting Assistance, Cattle Shed</div>
                </div>
                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                  <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>GRIEVANCE STATUS</div>
                  <div style={{ fontWeight: 800, fontSize: "14px", color: data.grievance_status === "No Grievance" ? "#16704a" : "#dc2626", marginTop: "4px" }}>
                    {data.grievance_status}
                  </div>
                  <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>{data.grievances?.length || 0} grievance ticket(s) recorded</div>
                </div>
                <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px" }}>
                  <div style={{ fontSize: "11px", color: "#64748b", fontWeight: 700 }}>FIELD VERIFICATION</div>
                  <div style={{ fontWeight: 800, fontSize: "14px", color: data.verification_status === "Verified" ? "#16704a" : "#d97706", marginTop: "4px" }}>
                    {data.verification_status}
                  </div>
                  <div style={{ fontSize: "11px", color: "#475569", marginTop: "4px" }}>Ground Inspection & Audit Protocol</div>
                </div>
              </div>
            </div>

            {/* Field Officer Remarks & Uploaded Evidence */}
            <div style={{ marginBottom: "20px" }}>
              <h4 style={{ margin: "0 0 10px", fontSize: "13px", color: "#334155", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                3. Field Inspection, Remarks & Uploaded Evidence
              </h4>
              <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "14px", fontSize: "12px" }}>
                <div style={{ marginBottom: "10px" }}>
                  <b style={{ color: "#475569" }}>Latest Field Officer Remarks:</b>
                  <p style={{ margin: "4px 0", color: "#1e293b", background: "#f8fafc", padding: "8px 12px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                    {data.remarks || "No field observations submitted yet."}
                  </p>
                </div>
                <div>
                  <b style={{ color: "#475569" }}>Uploaded Evidence / Documentation:</b>
                  {data.field_verifications && data.field_verifications.length > 0 && data.field_verifications.some(v => v.evidence_notes) ? (
                    <div style={{ marginTop: "6px", display: "grid", gap: "6px" }}>
                      {data.field_verifications.filter(v => v.evidence_notes).map((v, i) => (
                        <div key={i} style={{ background: "#f1f5f9", padding: "8px 12px", borderRadius: "6px", border: "1px solid #cbd5e1" }}>
                          <span style={{ fontSize: "11px", fontWeight: 700, color: "#0f6c70" }}>[{v.completed_date || v.assigned_date || "Date"}] {v.officer_email || "Field Officer"}</span>
                          <div style={{ marginTop: "2px", whiteSpace: "pre-wrap", color: "#334155" }}>{v.evidence_notes}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ margin: "4px 0", color: "#64748b", fontStyle: "italic" }}>No evidence files uploaded yet.</p>
                  )}
                </div>
              </div>
            </div>

            {/* R&R Milestone Timeline */}
            <div style={{ marginBottom: "20px" }}>
              <h4 style={{ margin: "0 0 10px", fontSize: "13px", color: "#334155", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                4. R&R Stage Progression & Milestone Timeline
              </h4>
              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "14px" }}>
                <div style={{ display: "grid", gap: "8px" }}>
                  {(data.timeline || []).map((t, idx) => {
                    const isDone = t.status === "Completed";
                    const isAct = t.status === "In Progress" || t.status === "Action Required";
                    const badgeBg = isDone ? "#16704a" : (isAct ? (t.status === "Action Required" ? "#d97706" : "#0056b3") : "#94a3b8");
                    return (
                      <div key={idx} style={{
                        display: "flex", justifyContent: "space-between", alignItems: "center",
                        padding: "8px 12px", background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "6px"
                      }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <span style={{
                            width: "22px", height: "22px", borderRadius: "50%", background: badgeBg,
                            color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center",
                            fontSize: "11px", fontWeight: 800
                          }}>
                            {idx + 1}
                          </span>
                          <span style={{ fontSize: "13px", fontWeight: 600, color: "#1e293b" }}>{t.step}</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                          <span style={{ fontSize: "11px", color: "#64748b" }}>{t.date}</span>
                          <span style={{
                            background: badgeBg, color: "#fff", padding: "2px 8px", borderRadius: "12px",
                            fontSize: "10px", fontWeight: 700, letterSpacing: "0.3px"
                          }}>
                            {t.status}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", borderTop: "1px solid #e2e8f0", paddingTop: "14px" }}>
              {(user?.role === "field_officer" || user?.role === "district_authority") && onOpenVerify && (
                <button
                  type="button"
                  onClick={() => { onClose(); onOpenVerify(data); }}
                  style={{ background: "#16704a", color: "#fff", padding: "8px 18px", borderRadius: "6px", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}
                >
                  ✓ Verify R&R / Open Full Verification
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                style={{ background: "#f1f5f9", color: "#334155", border: "1px solid #cbd5e1", padding: "8px 16px", borderRadius: "6px", fontWeight: 600 }}
              >
                Close Profile
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function RRVerificationModal({ family, onClose, onSuccess }) {
  if (!family) return null;

  // 1. Parcel / House Details (Read-only reference)
  const [houseCondition, setHouseCondition] = useState(family.house_observations || "Pucca residential structure / Clear demarcation");
  const [housePresent, setHousePresent] = useState("Yes");
  const [occupancyStatus, setOccupancyStatus] = useState("Occupied by Landowner Family");

  // 2. Affected Family Details
  const [familyHead, setFamilyHead] = useState(family.family_head || family.affected_family || "");
  const [totalMembers, setTotalMembers] = useState(family.members || 4);
  const [familyMembersList, setFamilyMembersList] = useState(() => {
    try {
      if (family.family_members_json) return JSON.parse(family.family_members_json);
    } catch {}
    return [
      { name: family.family_head || "Head", age: 48, gender: "Male", relation: "Self", occupation: "Agriculture / Allied", vulnerable: "No" },
      { name: "Spouse", age: 44, gender: "Female", relation: "Spouse", occupation: "Homemaker", vulnerable: "No" },
      { name: "Dependent 1", age: 19, gender: "Female", relation: "Daughter", occupation: "Student", vulnerable: "No" },
      { name: "Dependent 2", age: 16, gender: "Male", relation: "Son", occupation: "Student", vulnerable: "No" }
    ];
  });
  const [vulnerableMembers, setVulnerableMembers] = useState(family.vulnerable_members || (family.is_vulnerable ? "Elderly head / single-earner household" : "None"));
  const [specialAssistance, setSpecialAssistance] = useState(family.special_assistance || (family.is_vulnerable ? "Priority housing resettlement & doorstep pension" : "Standard rehabilitation scheme"));
  const [familyAffectedStatus, setFamilyAffectedStatus] = useState(family.family_affected_status || "Titleholder / Primary Landowner");

  // 3. Displacement & Relocation
  const [displacementRequired, setDisplacementRequired] = useState(family.displacement_required || "Yes");
  const [currentResidenceStatus, setCurrentResidenceStatus] = useState(family.current_residence_status || "Presently residing on acquired site");
  const [familyRelocated, setFamilyRelocated] = useState(family.displacement_status === "Relocated" ? "Yes" : "No");
  const [relocationCompleted, setRelocationCompleted] = useState(family.relocation_completed || "No");
  const [newLocation, setNewLocation] = useState(family.new_location || "Designated R&R Resettlement Colony Sector-4");
  const [relocationDate, setRelocationDate] = useState(family.relocation_date || "2025-06-30");
  const [relocationType, setRelocationType] = useState(family.relocation_type || "Permanent");
  const [pendingRelocationIssues, setPendingRelocationIssues] = useState(family.pending_relocation_issues || "Awaiting final electricity & municipal water connection");

  // 4. Compensation Verification
  const [compEligible, setCompEligible] = useState(family.comp_eligible || "Yes");
  const [compSanctioned, setCompSanctioned] = useState(family.comp_sanctioned || "Yes");
  const [compPaid, setCompPaid] = useState(family.compensation_status === "Fully Paid" ? "Yes" : "No");
  const [amountReceived, setAmountReceived] = useState(family.compensation_paid || family.compensation_entitled || 1250000);
  const [paymentDate, setPaymentDate] = useState(family.comp_payment_date || "2025-03-15");
  const [pendingAmount, setPendingAmount] = useState(Math.max(0, (family.compensation_entitled || 0) - (family.compensation_paid || 0)));
  const [paymentVerified, setPaymentVerified] = useState(family.comp_payment_verified || (family.compensation_status === "Fully Paid" ? "Yes" : "No"));
  const [paymentRemarks, setPaymentRemarks] = useState(family.comp_payment_issue || "DBT bank transfer credit slip matched with Treasury scroll");

  // 5. Housing R&R
  const [housingEntitlement, setHousingEntitlement] = useState(family.housing_entitlement || "Constructed Pucca House (500 sq ft) or Cash Assistance");
  const [housingSanctioned, setHousingSanctioned] = useState(family.housing_sanctioned || "Yes");
  const [housingReceived, setHousingReceived] = useState(family.housing_status === "Handed Over" ? "Yes" : "No");
  const [constructionStatus, setConstructionStatus] = useState(family.house_construction_status || "Plinth completed, roof casting in progress");
  const [newHouseProvided, setNewHouseProvided] = useState(family.new_house_provided || "No");
  const [housingCompletionStatus, setHousingCompletionStatus] = useState(family.housing_completion_status || "80% Completed");
  const [housingRemarks, setHousingRemarks] = useState(family.housing_issue || "Site allotted; construction supervised by State Resettlement Wing");

  // 6. Livelihood Restoration (CRITICAL)
  const [existingOccupation, setExistingOccupation] = useState(family.existing_occupation || "Agricultural Farming & Cattle Rearing");
  const [livelihoodAffected, setLivelihoodAffected] = useState(family.livelihood_affected || "Yes");
  const [livelihoodEligible, setLivelihoodEligible] = useState(family.livelihood_eligible || "Yes");
  const [livelihoodSanctioned, setLivelihoodSanctioned] = useState(family.livelihood_sanctioned_bool || "Yes");
  const [livelihoodReceived, setLivelihoodReceived] = useState(family.livelihood_received_bool || (["Support Delivered", "Completed"].includes(family.livelihood_status) ? "Yes" : "No"));
  const [assistanceType, setAssistanceType] = useState(family.assistance_type || "One-time Agricultural Resettlement Grant + Skill Training");
  const [alternativeLivelihood, setAlternativeLivelihood] = useState(family.alternative_livelihood || "Dairy cooperative membership & agro-processing unit link");
  const [trainingProvided, setTrainingProvided] = useState(family.training_provided || "Yes");
  const [employmentSupport, setEmploymentSupport] = useState(family.employment_support || "Job card issued under State Employment Mission");
  const [livelihoodRestorationStatus, setLivelihoodRestorationStatus] = useState(family.livelihood_restoration_status || family.livelihood_status || "Plan Prepared");
  const [pendingLivelihoodSupport, setPendingLivelihoodSupport] = useState(family.pending_livelihood_support || "Second tranche seed capital disbursal");
  const [livelihoodRemarks, setLivelihoodRemarks] = useState(family.livelihood_issue || "Family members enrolled in TNSDC vocational program");

  // 7. Other R&R Benefits
  const [transportationAssistance, setTransportationAssistance] = useState(family.benefit_transportation || "Sanctioned");
  const [subsistenceAllowance, setSubsistenceAllowance] = useState(family.benefit_subsistence || "Paid");
  const [educationAssistance, setEducationAssistance] = useState(family.benefit_education || "Sanctioned");
  const [medicalAssistance, setMedicalAssistance] = useState(family.benefit_medical || "Covered");
  const [skillDevelopment, setSkillDevelopment] = useState(family.benefit_skill_development || "Enrolled");
  const [otherStatutory, setOtherStatutory] = useState(family.benefit_other_statutory || "Stamp duty exemption for replacement land purchase");
  const [benefitReceivedStatus, setBenefitReceivedStatus] = useState(family.benefit_received_status || "Partially Disbursed");
  const [pendingBenefits, setPendingBenefits] = useState(family.pending_benefits || "Subsistence allowance month 2 & 3 pending");
  const [benefitsRemarks, setBenefitsRemarks] = useState(family.benefits_remarks || "All first-tier statutory grants issued under RFCTLARR 2013 Second Schedule");

  // 8. Grievance Verification
  const [grievanceExists, setGrievanceExists] = useState(family.grievance_status && family.grievance_status !== "No Grievance" ? "Yes" : "No");
  const [grievanceId, setGrievanceId] = useState(family.field_grievance_id || (family.grievance_status && family.grievance_status !== "No Grievance" ? "GRV-RR-082" : ""));
  const [issueCategory, setIssueCategory] = useState(family.field_grievance_category || "Compensation / Tree Evaluation");
  const [grievanceDesc, setGrievanceDesc] = useState(family.field_grievance_description || "Request for re-survey of standing coconut trees and well valuation");
  const [grievanceStatusField, setGrievanceStatusField] = useState(family.field_grievance_status || family.grievance_status || "Under Review");
  const [officerObservation, setOfficerObservation] = useState(family.officer_observation || "Physical verification confirms 14 mature coconut trees; supplementary award recommended");
  const [resolutionRequired, setResolutionRequired] = useState(family.resolution_required || "Yes");

  // 9. Field Evidence / Site Visit
  const [siteVisitDate, setSiteVisitDate] = useState(family.site_visit_date || new Date().toISOString().split("T")[0]);
  const [gpsLocation, setGpsLocation] = useState("11.0168° N, 76.9558° E (Survey Boundary Pillar #4)");
  const [houseObservations, setHouseObservations] = useState(family.house_observations || "RCC roof, brick masonry structure inspected; occupant verified with Aadhaar");
  const [evidenceDesc, setEvidenceDesc] = useState(family.evidence_description || "Field inspection geotagged photographs and landowner joint statement");
  const [officerRemarks, setOfficerRemarks] = useState(family.officer_remarks || family.remarks || "Ground verification concluded. All affected family particulars verified with Land Records.");
  const [file, setFile] = useState(null);

  // 10. Final Status Selection
  const [finalStatus, setFinalStatus] = useState(family.verification_status === "Verified" ? "Verified" : "Verified");

  // UI state
  const [openSection, setOpenSection] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState("");
  const [error, setError] = useState("");

  // Section completion indicators
  const sec1Done = Boolean(houseCondition && housePresent);
  const sec2Done = Boolean(familyHead && familyMembersList.length > 0);
  const sec3Done = Boolean(displacementRequired && currentResidenceStatus);
  const sec4Done = Boolean(compEligible && (compPaid === "Yes" || amountReceived > 0));
  const sec5Done = Boolean(housingEntitlement && constructionStatus);
  const sec6Done = Boolean(existingOccupation && livelihoodAffected && assistanceType);
  const sec7Done = Boolean(transportationAssistance && subsistenceAllowance);
  const sec8Done = Boolean(grievanceExists === "No" || (grievanceExists === "Yes" && officerObservation));
  const sec9Done = Boolean(siteVisitDate && officerRemarks);
  const sec10Done = Boolean(finalStatus);

  const completedCount = [sec1Done, sec2Done, sec3Done, sec4Done, sec5Done, sec6Done, sec7Done, sec8Done, sec9Done, sec10Done].filter(Boolean).length;
  const liveReadiness = Math.round((completedCount / 10.0) * 100);

  const handleMemberChange = (idx, field, val) => {
    const updated = [...familyMembersList];
    updated[idx][field] = val;
    setFamilyMembersList(updated);
  };

  const addMember = () => {
    setFamilyMembersList([...familyMembersList, { name: "", age: "", gender: "Male", relation: "Dependent", occupation: "", vulnerable: "No" }]);
  };

  const removeMember = (idx) => {
    if (familyMembersList.length <= 1) return;
    setFamilyMembersList(familyMembersList.filter((_, i) => i !== idx));
  };

  const buildPayload = (targetStatus) => ({
    final_status: targetStatus,
    // 1. Parcel / House
    house_condition: houseCondition,
    house_present: housePresent,
    occupancy_status: occupancyStatus,
    // 2. Family
    family_members_json: JSON.stringify(familyMembersList),
    vulnerable_members: vulnerableMembers,
    special_assistance: specialAssistance,
    family_affected_status: familyAffectedStatus,
    // 3. Displacement
    displacement_required: displacementRequired,
    current_residence_status: currentResidenceStatus,
    family_relocated: familyRelocated === "Yes",
    relocation_completed: relocationCompleted,
    new_location: newLocation,
    relocation_date: relocationDate,
    relocation_type: relocationType,
    pending_relocation_issues: pendingRelocationIssues,
    // 4. Compensation
    comp_eligible: compEligible,
    comp_sanctioned: compSanctioned,
    comp_paid_bool: compPaid === "Yes",
    comp_amount_received: parseFloat(amountReceived) || 0,
    comp_payment_date: paymentDate,
    comp_pending_amount: parseFloat(pendingAmount) || 0,
    comp_payment_verified: paymentVerified,
    comp_payment_issue: paymentRemarks,
    // 5. Housing
    housing_entitlement: housingEntitlement,
    housing_sanctioned: housingSanctioned,
    housing_received: housingReceived === "Yes",
    house_construction_status: constructionStatus,
    new_house_provided: newHouseProvided,
    housing_completion_status: housingCompletionStatus,
    housing_issue: housingRemarks,
    // 6. Livelihood
    existing_occupation: existingOccupation,
    livelihood_affected: livelihoodAffected,
    livelihood_eligible: livelihoodEligible,
    livelihood_sanctioned_bool: livelihoodSanctioned,
    livelihood_received_bool: livelihoodReceived,
    assistance_type: assistanceType,
    alternative_livelihood: alternativeLivelihood,
    training_provided: trainingProvided,
    employment_support: employmentSupport,
    livelihood_restoration_status: livelihoodRestorationStatus,
    pending_livelihood_support: pendingLivelihoodSupport,
    livelihood_issue: livelihoodRemarks,
    // 7. Other benefits
    benefit_transportation: transportationAssistance,
    benefit_subsistence: subsistenceAllowance,
    benefit_education: educationAssistance,
    benefit_medical: medicalAssistance,
    benefit_skill_development: skillDevelopment,
    benefit_other_statutory: otherStatutory,
    benefit_received_status: benefitReceivedStatus,
    pending_benefits: pendingBenefits,
    benefits_remarks: benefitsRemarks,
    // 8. Grievance
    grievance_exists: grievanceExists === "Yes",
    field_grievance_id: grievanceId,
    field_grievance_category: issueCategory,
    field_grievance_description: grievanceDesc,
    field_grievance_status: grievanceStatusField,
    officer_observation: officerObservation,
    resolution_required: resolutionRequired,
    // 9. Evidence
    site_visit_date: siteVisitDate,
    house_observations: houseObservations,
    evidence_description: evidenceDesc,
    officer_remarks: officerRemarks,
    // Section completion flags
    sec_parcel_done: sec1Done,
    sec_family_done: sec2Done,
    sec_displacement_done: sec3Done,
    sec_compensation_done: sec4Done,
    sec_housing_done: sec5Done,
    sec_livelihood_done: sec6Done,
    sec_other_benefits_done: sec7Done,
    sec_grievance_done: sec8Done,
    sec_evidence_done: sec9Done,
    sec_final_done: sec10Done,
  });

  const handleSave = async (targetStatus, isDraft = false) => {
    setSubmitting(true);
    setError("");
    setSaveSuccess("");
    try {
      // 1. Upload evidence file if attached
      if (file) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("description", evidenceDesc || "Ground R&R photo evidence");
        await api(`/rr/families/${encodeURIComponent(family.family_id)}/evidence`, {
          method: "POST",
          body: formData
        });
      }

      // 2. Submit full verification payload
      const payload = buildPayload(targetStatus);
      const res = await api(`/rr/families/${encodeURIComponent(family.family_id)}/full-verify`, {
        method: "POST",
        body: JSON.stringify(payload)
      });

      EventBus.dispatch();
      if (isDraft) {
        setSaveSuccess(`Draft saved successfully! Sections verified: ${completedCount}/10 (${res.readiness_percentage || liveReadiness}%)`);
      } else {
        if (onSuccess) onSuccess(res);
        onClose();
      }
    } catch (err) {
      setError(err.message || "Failed to submit R&R verification");
    } finally {
      setSubmitting(false);
    }
  };

  const sectionRefs = useRef({});

  const toggleSection = (secId) => {
    const next = openSection === secId ? 0 : secId;
    setOpenSection(next);
    if (next !== 0) {
      setTimeout(() => {
        const el = sectionRefs.current[next];
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      }, 60);
    }
  };

  const renderBadge = (isDone) => (
    <span style={{
      fontSize: "11px",
      fontWeight: 800,
      padding: "3px 10px",
      borderRadius: "12px",
      background: isDone ? "#dcfce7" : "#fef3c7",
      color: isDone ? "#15803d" : "#b45309",
      border: isDone ? "1px solid #86efac" : "1px solid #fde68a",
      marginLeft: "auto",
      flexShrink: 0
    }}>
      {isDone ? "✓ Completed" : "⚠ Incomplete"}
    </span>
  );

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      background: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)",
      display: "flex", justifyContent: "center", alignItems: "center", zIndex: 10000, padding: "16px"
    }}>
      <div className="rr-modal modal" style={{
        background: "#ffffff", borderRadius: "12px", width: "min(94vw, 1250px)",
        height: "92vh", maxHeight: "92vh", minHeight: 0, display: "flex", flexDirection: "column",
        boxShadow: "0 25px 50px -12px rgba(0,0,0,0.35)", border: "1px solid #cbd5e1",
        overflow: "hidden"
      }}>
        {/* Fixed Header */}
        <div className="modal-header rr-header" style={{
          flexShrink: 0, minHeight: "56px",
          padding: "16px 20px", background: "linear-gradient(135deg, #0f6c70 0%, #0d5457 100%)",
          color: "#ffffff", display: "flex", justifyContent: "space-between", alignItems: "center",
          borderTopLeftRadius: "12px", borderTopRightRadius: "12px"
        }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.5px", color: "#99f6e4" }}>
              LANDNEXUS Field Officer Verification Protocol · 10 Sections
            </div>
            <h3 style={{ margin: "2px 0 0", fontSize: "18px", color: "#ffffff" }}>
              Ground R&R Verification: {family.family_head || family.affected_family || "Affected Family"} ({family.family_id})
            </h3>
            <div style={{ fontSize: "12px", color: "#ccfbf1", marginTop: "2px" }}>
              Project: {family.project_id || "Direct"} · Parcel ID: {family.parcel_id} · Survey No: {family.survey_no} · {family.village} Village, {family.taluk} Taluk, {family.district}
            </div>
          </div>
          <button
            onClick={onClose}
            type="button"
            style={{ background: "rgba(255,255,255,0.15)", color: "#fff", border: "none", borderRadius: "6px", width: "32px", height: "32px", cursor: "pointer", fontSize: "16px", fontWeight: 700 }}
          >
            ✕
          </button>
        </div>

        {/* Fixed Progress & Live Readiness Header */}
        <div className="modal-progress rr-progress" style={{
          flexShrink: 0,
          padding: "12px 20px", background: "#f8fafc", borderBottom: "1px solid #e2e8f0",
          display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>
              Sections Completed: <b>{completedCount} / 10</b>
            </span>
            <div style={{ width: "140px", height: "8px", background: "#e2e8f0", borderRadius: "4px", overflow: "hidden" }}>
              <div style={{ width: `${liveReadiness}%`, height: "100%", background: liveReadiness >= 80 ? "#16704a" : "#0f6c70", transition: "width 0.3s" }} />
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Live R&R Readiness:</span>
            <span style={{
              background: liveReadiness >= 80 ? "#16704a" : (liveReadiness >= 50 ? "#0f6c70" : "#d97706"),
              color: "#fff", padding: "3px 10px", borderRadius: "12px", fontWeight: 800, fontSize: "12px"
            }}>
              {liveReadiness}%
            </span>
          </div>
        </div>

        {/* Notifications */}
        {error && (
          <div style={{ flexShrink: 0, margin: "10px 20px 0", padding: "10px 14px", background: "#fee2e2", border: "1px solid #f87171", borderRadius: "6px", color: "#b91c1c", fontSize: "12px" }}>
            {error}
          </div>
        )}
        {saveSuccess && (
          <div style={{ flexShrink: 0, margin: "10px 20px 0", padding: "10px 14px", background: "#ecfdf5", border: "1px solid #6ee7b7", borderRadius: "6px", color: "#065f46", fontSize: "12px" }}>
            {saveSuccess}
          </div>
        )}

        {/* Scrollable R&R Content Area */}
        <div className="modal-content rr-scroll-area" style={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          overflowX: "hidden",
          padding: "18px 20px 48px 20px",
          display: "flex",
          flexDirection: "column",
          gap: "14px"
        }}>

          {/* ──────────────── 1. PARCEL / HOUSE DETAILS ──────────────── */}
          <div
            ref={el => sectionRefs.current[1] = el}
            style={{
              border: openSection === 1 ? "2px solid #0f6c70" : "1px solid #e2e8f0",
              borderRadius: "8px", overflow: "visible", height: "auto", background: "#ffffff",
              transition: "border-color 0.2s, box-shadow 0.2s",
              boxShadow: openSection === 1 ? "0 4px 12px rgba(15, 108, 112, 0.08)" : "none"
            }}
          >
            <div
              onClick={() => toggleSection(1)}
              style={{
                minHeight: "52px", padding: "12px 18px", background: openSection === 1 ? "#f0fdfa" : "#ffffff",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
                gap: "12px", fontWeight: 700, color: openSection === 1 ? "#0f6c70" : "#0f172a", fontSize: "13.5px", userSelect: "none"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: "12px", color: openSection === 1 ? "#0f6c70" : "#64748b", fontWeight: 800 }}>{openSection === 1 ? "▼" : "▶"}</span>
                <span style={{ wordBreak: "break-word" }}>1. PARCEL & HOUSE GROUND DETAILS</span>
              </div>
              {renderBadge(sec1Done)}
            </div>
            {openSection === 1 && (
              <div style={{ height: "auto", maxHeight: "none", minHeight: 0, overflow: "visible", padding: "20px", background: "#fafafa", borderTop: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: "16px", rowGap: "18px", fontSize: "12.5px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", background: "#ffffff", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                  <div><span style={{ color: "#64748b" }}>Project ID:</span> <b style={{ display: "block", color: "#0f172a" }}>{family.project_id || "N/A"}</b></div>
                  <div><span style={{ color: "#64748b" }}>Parcel ID:</span> <b style={{ display: "block", color: "#0f172a" }}>{family.parcel_id}</b></div>
                  <div><span style={{ color: "#64748b" }}>Survey No:</span> <b style={{ display: "block", color: "#0f172a" }}>{family.survey_no}</b></div>
                  <div><span style={{ color: "#64748b" }}>Village / Taluk:</span> <b style={{ display: "block", color: "#0f172a" }}>{family.village} / {family.taluk}</b></div>
                  <div><span style={{ color: "#64748b" }}>District:</span> <b style={{ display: "block", color: "#0f172a" }}>{family.district}</b></div>
                  <div><span style={{ color: "#64748b" }}>Registered Landowner:</span> <b style={{ display: "block", color: "#0f172a" }}>{family.landowner || family.family_head || "Registered Owner"}</b></div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>House / Property Present on Site?</b>
                    <select
                      value={housePresent} onChange={e => setHousePresent(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Yes">Yes (Dwelling Structure Present)</option>
                      <option value="No">No (Vacant Agricultural Land)</option>
                      <option value="Partially Demolished">Partially Demolished</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Current Occupancy Status:</b>
                    <select
                      value={occupancyStatus} onChange={e => setOccupancyStatus(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Occupied by Landowner Family">Occupied by Landowner Family</option>
                      <option value="Occupied by Tenants / Sharecroppers">Occupied by Tenants / Sharecroppers</option>
                      <option value="Vacated / Relocated to R&R Site">Vacated / Relocated to R&R Site</option>
                      <option value="Unoccupied / Locked">Unoccupied / Locked</option>
                    </select>
                  </label>
                </div>
                <label style={{ display: "block" }}>
                  <b style={{ color: "#334155" }}>House / Property Structural Condition:</b>
                  <input
                    value={houseCondition} onChange={e => setHouseCondition(e.target.value)}
                    placeholder="e.g., Pucca single-story RCC construction, roof intact, habitable"
                    style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                  />
                </label>
              </div>
            )}
          </div>

          {/* ──────────────── 2. AFFECTED FAMILY DETAILS ──────────────── */}
          <div
            ref={el => sectionRefs.current[2] = el}
            style={{
              border: openSection === 2 ? "2px solid #0f6c70" : "1px solid #e2e8f0",
              borderRadius: "8px", overflow: "visible", height: "auto", background: "#ffffff",
              transition: "border-color 0.2s, box-shadow 0.2s",
              boxShadow: openSection === 2 ? "0 4px 12px rgba(15, 108, 112, 0.08)" : "none"
            }}
          >
            <div
              onClick={() => toggleSection(2)}
              style={{
                minHeight: "52px", padding: "12px 18px", background: openSection === 2 ? "#f0fdfa" : "#ffffff",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
                gap: "12px", fontWeight: 700, color: openSection === 2 ? "#0f6c70" : "#0f172a", fontSize: "13.5px", userSelect: "none"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: "12px", color: openSection === 2 ? "#0f6c70" : "#64748b", fontWeight: 800 }}>{openSection === 2 ? "▼" : "▶"}</span>
                <span style={{ wordBreak: "break-word" }}>2. AFFECTED FAMILY DETAILS & MEMBERS</span>
              </div>
              {renderBadge(sec2Done)}
            </div>
            {openSection === 2 && (
              <div style={{ height: "auto", maxHeight: "none", minHeight: 0, overflow: "visible", padding: "20px", background: "#fafafa", borderTop: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: "16px", rowGap: "18px", fontSize: "12.5px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Family Head:</b>
                    <input
                      value={familyHead} onChange={e => setFamilyHead(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Total Members:</b>
                    <input
                      type="number" value={totalMembers} onChange={e => setTotalMembers(parseInt(e.target.value) || 1)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Displaced Status:</b>
                    <select
                      value={familyAffectedStatus} onChange={e => setFamilyAffectedStatus(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Displaced Family (Titleholder)">Displaced Family (Titleholder)</option>
                      <option value="Affected Family (Non-Displaced)">Affected Family (Non-Displaced)</option>
                      <option value="Agricultural Labourer / Tenant">Agricultural Labourer / Tenant</option>
                      <option value="Homeless / Squatter Family">Homeless / Squatter Family</option>
                    </select>
                  </label>
                </div>

                {/* Member Sub-Table */}
                <div style={{ background: "#ffffff", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <b style={{ color: "#0f6c70", fontSize: "13px" }}>Individual Family Members ({familyMembersList.length}):</b>
                    <button
                      type="button" onClick={addMember}
                      style={{ background: "#0f6c70", color: "#fff", border: "none", borderRadius: "6px", padding: "5px 12px", fontSize: "12px", cursor: "pointer", fontWeight: 700 }}
                    >
                      + Add Member
                    </button>
                  </div>
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "#f1f5f9", textAlign: "left", color: "#475569" }}>
                          <th style={{ padding: "8px" }}>Name</th>
                          <th style={{ padding: "8px" }}>Age</th>
                          <th style={{ padding: "8px" }}>Gender</th>
                          <th style={{ padding: "8px" }}>Relationship</th>
                          <th style={{ padding: "8px" }}>Occupation</th>
                          <th style={{ padding: "8px" }}>Vulnerable?</th>
                          <th style={{ padding: "8px", textAlign: "center" }}>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {familyMembersList.map((m, idx) => (
                          <tr key={idx} style={{ borderBottom: "1px solid #e2e8f0" }}>
                            <td style={{ padding: "6px" }}>
                              <input value={m.name} onChange={e => handleMemberChange(idx, "name", e.target.value)} style={{ width: "100%", boxSizing: "border-box", padding: "6px", border: "1px solid #cbd5e1", borderRadius: "4px" }} />
                            </td>
                            <td style={{ padding: "6px" }}>
                              <input type="number" value={m.age} onChange={e => handleMemberChange(idx, "age", e.target.value)} style={{ width: "50px", boxSizing: "border-box", padding: "6px", border: "1px solid #cbd5e1", borderRadius: "4px" }} />
                            </td>
                            <td style={{ padding: "6px" }}>
                              <select value={m.gender} onChange={e => handleMemberChange(idx, "gender", e.target.value)} style={{ boxSizing: "border-box", padding: "6px", border: "1px solid #cbd5e1", borderRadius: "4px" }}>
                                <option>Male</option><option>Female</option><option>Other</option>
                              </select>
                            </td>
                            <td style={{ padding: "6px" }}>
                              <input value={m.relation} onChange={e => handleMemberChange(idx, "relation", e.target.value)} style={{ width: "90px", boxSizing: "border-box", padding: "6px", border: "1px solid #cbd5e1", borderRadius: "4px" }} />
                            </td>
                            <td style={{ padding: "6px" }}>
                              <input value={m.occupation} onChange={e => handleMemberChange(idx, "occupation", e.target.value)} style={{ width: "100%", boxSizing: "border-box", padding: "6px", border: "1px solid #cbd5e1", borderRadius: "4px" }} />
                            </td>
                            <td style={{ padding: "6px" }}>
                              <select value={m.vulnerable} onChange={e => handleMemberChange(idx, "vulnerable", e.target.value)} style={{ boxSizing: "border-box", padding: "6px", border: "1px solid #cbd5e1", borderRadius: "4px" }}>
                                <option>No</option><option>Yes (Elderly/Disabled/Widow)</option>
                              </select>
                            </td>
                            <td style={{ padding: "6px", textAlign: "center" }}>
                              <button type="button" onClick={() => removeMember(idx)} style={{ color: "#dc2626", background: "none", border: "none", cursor: "pointer", fontWeight: 800, fontSize: "14px" }}>✕</button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Vulnerable Family Members Identified:</b>
                    <input
                      value={vulnerableMembers} onChange={e => setVulnerableMembers(e.target.value)}
                      placeholder="e.g., Disabled elder, female-headed, destitute"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Special Assistance Required:</b>
                    <input
                      value={specialAssistance} onChange={e => setSpecialAssistance(e.target.value)}
                      placeholder="e.g., Ground-floor housing unit, medical transport"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* ──────────────── 3. DISPLACEMENT & RELOCATION ──────────────── */}
          <div
            ref={el => sectionRefs.current[3] = el}
            style={{
              border: openSection === 3 ? "2px solid #0f6c70" : "1px solid #e2e8f0",
              borderRadius: "8px", overflow: "visible", height: "auto", background: "#ffffff",
              transition: "border-color 0.2s, box-shadow 0.2s",
              boxShadow: openSection === 3 ? "0 4px 12px rgba(15, 108, 112, 0.08)" : "none"
            }}
          >
            <div
              onClick={() => toggleSection(3)}
              style={{
                minHeight: "52px", padding: "12px 18px", background: openSection === 3 ? "#f0fdfa" : "#ffffff",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
                gap: "12px", fontWeight: 700, color: openSection === 3 ? "#0f6c70" : "#0f172a", fontSize: "13.5px", userSelect: "none"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: "12px", color: openSection === 3 ? "#0f6c70" : "#64748b", fontWeight: 800 }}>{openSection === 3 ? "▼" : "▶"}</span>
                <span style={{ wordBreak: "break-word" }}>3. DISPLACEMENT & RELOCATION VERIFICATION</span>
              </div>
              {renderBadge(sec3Done)}
            </div>
            {openSection === 3 && (
              <div style={{ height: "auto", maxHeight: "none", minHeight: 0, overflow: "visible", padding: "20px", background: "#fafafa", borderTop: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: "16px", rowGap: "18px", fontSize: "12.5px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Displacement Required?</b>
                    <select
                      value={displacementRequired} onChange={e => setDisplacementRequired(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Yes">Yes (Physical Relocation Necessary)</option>
                      <option value="No">No (In-situ Rehabilitation / Land Only)</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Family Relocated?</b>
                    <select
                      value={familyRelocated} onChange={e => setFamilyRelocated(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="No">No (Still Living on Parcel)</option>
                      <option value="Yes">Yes (Moved Out)</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Relocation Completed?</b>
                    <select
                      value={relocationCompleted} onChange={e => setRelocationCompleted(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="No">No (In Transition / Pending Handover)</option>
                      <option value="Yes">Yes (Settled in R&R Site)</option>
                    </select>
                  </label>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>New Relocation Address / Site:</b>
                    <input
                      value={newLocation} onChange={e => setNewLocation(e.target.value)}
                      placeholder="Resettlement Colony Plot #, Taluk, Village"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Relocation Date:</b>
                    <input
                      type="date" value={relocationDate} onChange={e => setRelocationDate(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Type of Relocation:</b>
                    <select
                      value={relocationType} onChange={e => setRelocationType(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Permanent">Permanent</option>
                      <option value="Temporary Transit">Temporary Transit</option>
                      <option value="Self-Relocation">Self-Relocation</option>
                    </select>
                  </label>
                </div>

                <label style={{ display: "block" }}>
                  <b style={{ color: "#334155" }}>Pending Relocation Issues / Demands:</b>
                  <input
                    value={pendingRelocationIssues} onChange={e => setPendingRelocationIssues(e.target.value)}
                    placeholder="e.g., Transit shed maintenance, cattle shed space, school bus connectivity"
                    style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                  />
                </label>
              </div>
            )}
          </div>

          {/* ──────────────── 4. COMPENSATION VERIFICATION ──────────────── */}
          <div
            ref={el => sectionRefs.current[4] = el}
            style={{
              border: openSection === 4 ? "2px solid #0f6c70" : "1px solid #e2e8f0",
              borderRadius: "8px", overflow: "visible", height: "auto", background: "#ffffff",
              transition: "border-color 0.2s, box-shadow 0.2s",
              boxShadow: openSection === 4 ? "0 4px 12px rgba(15, 108, 112, 0.08)" : "none"
            }}
          >
            <div
              onClick={() => toggleSection(4)}
              style={{
                minHeight: "52px", padding: "12px 18px", background: openSection === 4 ? "#f0fdfa" : "#ffffff",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
                gap: "12px", fontWeight: 700, color: openSection === 4 ? "#0f6c70" : "#0f172a", fontSize: "13.5px", userSelect: "none"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: "12px", color: openSection === 4 ? "#0f6c70" : "#64748b", fontWeight: 800 }}>{openSection === 4 ? "▼" : "▶"}</span>
                <span style={{ wordBreak: "break-word" }}>4. COMPENSATION PAYMENT VERIFICATION</span>
              </div>
              {renderBadge(sec4Done)}
            </div>
            {openSection === 4 && (
              <div style={{ height: "auto", maxHeight: "none", minHeight: 0, overflow: "visible", padding: "20px", background: "#fafafa", borderTop: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: "16px", rowGap: "18px", fontSize: "12.5px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Compensation Eligible?</b>
                    <select
                      value={compEligible} onChange={e => setCompEligible(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Yes">Yes (Eligible Awardee)</option>
                      <option value="No">No (Disputed / Excluded)</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Award Sanctioned?</b>
                    <select
                      value={compSanctioned} onChange={e => setCompSanctioned(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Yes">Yes (Award Passed)</option>
                      <option value="No">No (Pending Section 23/30)</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Compensation Paid?</b>
                    <select
                      value={compPaid} onChange={e => setCompPaid(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Yes">Yes (Fully Disbursed)</option>
                      <option value="No">No (Pending / Partial)</option>
                    </select>
                  </label>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Amount Received (₹):</b>
                    <input
                      type="number" value={amountReceived} onChange={e => setAmountReceived(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Payment Date:</b>
                    <input
                      type="date" value={paymentDate} onChange={e => setPaymentDate(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Pending Amount (₹):</b>
                    <input
                      type="number" value={pendingAmount} onChange={e => setPendingAmount(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Payment Verified on Ground?</b>
                    <select
                      value={paymentVerified} onChange={e => setPaymentVerified(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Yes">Yes (Verified with Passbook/DBT)</option>
                      <option value="No">No (Discrepancy Reported)</option>
                    </select>
                  </label>
                </div>

                <label style={{ display: "block" }}>
                  <b style={{ color: "#334155" }}>Payment Verification Remarks:</b>
                  <input
                    value={paymentRemarks} onChange={e => setPaymentRemarks(e.target.value)}
                    placeholder="e.g., Bank passbook verified. Payment credited via RTGS Treasury ref 20250315-9921"
                    style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                  />
                </label>
              </div>
            )}
          </div>

          {/* ──────────────── 5. HOUSING R&R ──────────────── */}
          <div
            ref={el => sectionRefs.current[5] = el}
            style={{
              border: openSection === 5 ? "2px solid #0f6c70" : "1px solid #e2e8f0",
              borderRadius: "8px", overflow: "visible", height: "auto", background: "#ffffff",
              transition: "border-color 0.2s, box-shadow 0.2s",
              boxShadow: openSection === 5 ? "0 4px 12px rgba(15, 108, 112, 0.08)" : "none"
            }}
          >
            <div
              onClick={() => toggleSection(5)}
              style={{
                minHeight: "52px", padding: "12px 18px", background: openSection === 5 ? "#f0fdfa" : "#ffffff",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
                gap: "12px", fontWeight: 700, color: openSection === 5 ? "#0f6c70" : "#0f172a", fontSize: "13.5px", userSelect: "none"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: "12px", color: openSection === 5 ? "#0f6c70" : "#64748b", fontWeight: 800 }}>{openSection === 5 ? "▼" : "▶"}</span>
                <span style={{ wordBreak: "break-word" }}>5. HOUSING REHABILITATION & RESETTLEMENT</span>
              </div>
              {renderBadge(sec5Done)}
            </div>
            {openSection === 5 && (
              <div style={{ height: "auto", maxHeight: "none", minHeight: 0, overflow: "visible", padding: "20px", background: "#fafafa", borderTop: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: "16px", rowGap: "18px", fontSize: "12.5px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Housing Entitlement:</b>
                    <input
                      value={housingEntitlement} onChange={e => setHousingEntitlement(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Housing Sanctioned?</b>
                    <select
                      value={housingSanctioned} onChange={e => setHousingSanctioned(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Yes">Yes</option><option value="No">No</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Housing Received / Handed Over?</b>
                    <select
                      value={housingReceived} onChange={e => setHousingReceived(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="No">No (In Progress)</option>
                      <option value="Yes">Yes (Keys Handed Over)</option>
                    </select>
                  </label>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Construction Status:</b>
                    <select
                      value={constructionStatus} onChange={e => setConstructionStatus(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Not Started">Not Started</option>
                      <option value="Foundation Complete">Foundation Complete</option>
                      <option value="Superstructure Ready">Superstructure Ready</option>
                      <option value="Finishing in Progress">Finishing in Progress</option>
                      <option value="Ready for Handover">Ready for Handover</option>
                      <option value="Handed Over & Occupied">Handed Over & Occupied</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>New House Provided?</b>
                    <select
                      value={newHouseProvided} onChange={e => setNewHouseProvided(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="No">No</option><option value="Yes">Yes</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Completion Percentage:</b>
                    <input
                      value={housingCompletionStatus} onChange={e => setHousingCompletionStatus(e.target.value)}
                      placeholder="e.g., 75% Completed"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                </div>

                <label style={{ display: "block" }}>
                  <b style={{ color: "#334155" }}>Housing Remarks / Snags:</b>
                  <input
                    value={housingRemarks} onChange={e => setHousingRemarks(e.target.value)}
                    placeholder="e.g., Painting and plumbing works pending; expected occupancy next month"
                    style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                  />
                </label>
              </div>
            )}
          </div>

          {/* ──────────────── 6. LIVELIHOOD RESTORATION (CRITICAL & FULL CAPTURE) ──────────────── */}
          <div
            ref={el => sectionRefs.current[6] = el}
            style={{
              border: openSection === 6 ? "2px solid #0f6c70" : "1px solid #0f6c70",
              borderRadius: "8px", overflow: "visible", height: "auto", background: "#ffffff",
              transition: "border-color 0.2s, box-shadow 0.2s",
              boxShadow: openSection === 6 ? "0 4px 12px rgba(15, 108, 112, 0.12)" : "none"
            }}
          >
            <div
              onClick={() => toggleSection(6)}
              style={{
                minHeight: "52px", padding: "12px 18px", background: openSection === 6 ? "#e0f2f1" : "#f0fdfa",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
                gap: "12px", fontWeight: 800, color: "#0f6c70", fontSize: "13.5px", userSelect: "none"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: "12px", color: "#0f6c70", fontWeight: 800 }}>{openSection === 6 ? "▼" : "▶"}</span>
                <span style={{ wordBreak: "break-word" }}>6. LIVELIHOOD RESTORATION (CRITICAL & FULL CAPTURE)</span>
              </div>
              {renderBadge(sec6Done)}
            </div>
            {openSection === 6 && (
              <div style={{ height: "auto", maxHeight: "none", minHeight: 0, overflow: "visible", padding: "20px", background: "#f8fafc", borderTop: "1px solid #0f6c70", display: "flex", flexDirection: "column", gap: "16px", rowGap: "18px", fontSize: "12.5px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Existing Primary Occupation / Livelihood:</b>
                    <input
                      value={existingOccupation} onChange={e => setExistingOccupation(e.target.value)}
                      placeholder="e.g., Cultivator, tenant farmer, artisan, shopkeeper"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Livelihood Affected?</b>
                    <select
                      value={livelihoodAffected} onChange={e => setLivelihoodAffected(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Yes">Yes (Direct Income Loss)</option>
                      <option value="Partially">Partially (Supplementary Loss)</option>
                      <option value="No">No (Unaffected)</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Livelihood Assistance Eligible?</b>
                    <select
                      value={livelihoodEligible} onChange={e => setLivelihoodEligible(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Yes">Yes (RFCTLARR Schedule II)</option>
                      <option value="No">No</option>
                    </select>
                  </label>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Assistance Sanctioned?</b>
                    <select
                      value={livelihoodSanctioned} onChange={e => setLivelihoodSanctioned(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Yes">Yes</option><option value="No">No</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Assistance Received?</b>
                    <select
                      value={livelihoodReceived} onChange={e => setLivelihoodReceived(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="No">No (Pending)</option>
                      <option value="Yes">Yes (Delivered)</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Assistance Scheme / Type:</b>
                    <input
                      value={assistanceType} onChange={e => setAssistanceType(e.target.value)}
                      placeholder="e.g., Agricultural grant ₹5,00,000, dairy kit, artisan kiosk"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Alternative Livelihood Provided:</b>
                    <input
                      value={alternativeLivelihood} onChange={e => setAlternativeLivelihood(e.target.value)}
                      placeholder="e.g., Commercial vendor stall allotted at transit hub"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Training Provided:</b>
                    <select
                      value={trainingProvided} onChange={e => setTrainingProvided(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Yes">Yes (Skill Training Completed)</option>
                      <option value="In Progress">In Progress</option>
                      <option value="No">No (Pending Course Batch)</option>
                    </select>
                  </label>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Employment Support:</b>
                    <input
                      value={employmentSupport} onChange={e => setEmploymentSupport(e.target.value)}
                      placeholder="e.g., Guaranteed job in project concessionaire / Self-help credit"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Restoration Status:</b>
                    <select
                      value={livelihoodRestorationStatus} onChange={e => setLivelihoodRestorationStatus(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="Not Assessed">Not Assessed</option>
                      <option value="Assessment Pending">Assessment Pending</option>
                      <option value="Eligible">Eligible</option>
                      <option value="Plan Prepared">Plan Prepared</option>
                      <option value="Sanctioned">Sanctioned</option>
                      <option value="Training Pending">Training Pending</option>
                      <option value="Support Delivered">Support Delivered</option>
                      <option value="Monitoring">Monitoring</option>
                      <option value="Completed">Completed</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Pending Livelihood Support:</b>
                    <input
                      value={pendingLivelihoodSupport} onChange={e => setPendingLivelihoodSupport(e.target.value)}
                      placeholder="e.g., Equipment loan clearance"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                </div>

                <label style={{ display: "block" }}>
                  <b style={{ color: "#334155" }}>Livelihood Remarks / Observations:</b>
                  <input
                    value={livelihoodRemarks} onChange={e => setLivelihoodRemarks(e.target.value)}
                    placeholder="Ground verification of breadwinner employment transition and monthly income..."
                    style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                  />
                </label>
              </div>
            )}
          </div>

          {/* ──────────────── 7. OTHER R&R BENEFITS ──────────────── */}
          <div
            ref={el => sectionRefs.current[7] = el}
            style={{
              border: openSection === 7 ? "2px solid #0f6c70" : "1px solid #e2e8f0",
              borderRadius: "8px", overflow: "visible", height: "auto", background: "#ffffff",
              transition: "border-color 0.2s, box-shadow 0.2s",
              boxShadow: openSection === 7 ? "0 4px 12px rgba(15, 108, 112, 0.08)" : "none"
            }}
          >
            <div
              onClick={() => toggleSection(7)}
              style={{
                minHeight: "52px", padding: "12px 18px", background: openSection === 7 ? "#f0fdfa" : "#ffffff",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
                gap: "12px", fontWeight: 700, color: openSection === 7 ? "#0f6c70" : "#0f172a", fontSize: "13.5px", userSelect: "none"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: "12px", color: openSection === 7 ? "#0f6c70" : "#64748b", fontWeight: 800 }}>{openSection === 7 ? "▼" : "▶"}</span>
                <span style={{ wordBreak: "break-word" }}>7. OTHER STATUTORY R&R BENEFITS</span>
              </div>
              {renderBadge(sec7Done)}
            </div>
            {openSection === 7 && (
              <div style={{ height: "auto", maxHeight: "none", minHeight: 0, overflow: "visible", padding: "20px", background: "#fafafa", borderTop: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: "16px", rowGap: "18px", fontSize: "12.5px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "14px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Transportation:</b>
                    <select
                      value={transportationAssistance} onChange={e => setTransportationAssistance(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option>Paid</option><option>Sanctioned</option><option>Pending</option><option>Not Applicable</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Subsistence Grant:</b>
                    <select
                      value={subsistenceAllowance} onChange={e => setSubsistenceAllowance(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option>Paid</option><option>Sanctioned</option><option>Pending</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Education Aid:</b>
                    <select
                      value={educationAssistance} onChange={e => setEducationAssistance(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option>Sanctioned</option><option>Paid</option><option>Pending</option><option>Not Applicable</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Medical Aid:</b>
                    <select
                      value={medicalAssistance} onChange={e => setMedicalAssistance(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option>Covered</option><option>Sanctioned</option><option>Pending</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Skill Dev:</b>
                    <select
                      value={skillDevelopment} onChange={e => setSkillDevelopment(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option>Enrolled</option><option>Completed</option><option>Pending</option>
                    </select>
                  </label>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Other Statutory Benefits:</b>
                    <input
                      value={otherStatutory} onChange={e => setOtherStatutory(e.target.value)}
                      placeholder="e.g., Cattle shed allowance, stamp duty exemption"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Benefit Received Status:</b>
                    <select
                      value={benefitReceivedStatus} onChange={e => setBenefitReceivedStatus(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option>All Disbursed</option><option>Partially Disbursed</option><option>Pending Approval</option>
                    </select>
                  </label>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Pending Benefits:</b>
                    <input
                      value={pendingBenefits} onChange={e => setPendingBenefits(e.target.value)}
                      placeholder="e.g., Remaining 2 months subsistence grant"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Benefits Remarks:</b>
                    <input
                      value={benefitsRemarks} onChange={e => setBenefitsRemarks(e.target.value)}
                      placeholder="Notes on statutory entitlements release"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* ──────────────── 8. GRIEVANCE VERIFICATION ──────────────── */}
          <div
            ref={el => sectionRefs.current[8] = el}
            style={{
              border: openSection === 8 ? "2px solid #0f6c70" : "1px solid #e2e8f0",
              borderRadius: "8px", overflow: "visible", height: "auto", background: "#ffffff",
              transition: "border-color 0.2s, box-shadow 0.2s",
              boxShadow: openSection === 8 ? "0 4px 12px rgba(15, 108, 112, 0.08)" : "none"
            }}
          >
            <div
              onClick={() => toggleSection(8)}
              style={{
                minHeight: "52px", padding: "12px 18px", background: openSection === 8 ? "#f0fdfa" : "#ffffff",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
                gap: "12px", fontWeight: 700, color: openSection === 8 ? "#0f6c70" : "#0f172a", fontSize: "13.5px", userSelect: "none"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: "12px", color: openSection === 8 ? "#0f6c70" : "#64748b", fontWeight: 800 }}>{openSection === 8 ? "▼" : "▶"}</span>
                <span style={{ wordBreak: "break-word" }}>8. GRIEVANCE & DISPUTE VERIFICATION</span>
              </div>
              {renderBadge(sec8Done)}
            </div>
            {openSection === 8 && (
              <div style={{ height: "auto", maxHeight: "none", minHeight: 0, overflow: "visible", padding: "20px", background: "#fafafa", borderTop: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: "16px", rowGap: "18px", fontSize: "12.5px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Grievance Exists?</b>
                    <select
                      value={grievanceExists} onChange={e => setGrievanceExists(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="No">No (No Grievances Raised)</option>
                      <option value="Yes">Yes (Active Grievance / Dispute)</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Grievance ID (if available):</b>
                    <input
                      value={grievanceId} onChange={e => setGrievanceId(e.target.value)}
                      placeholder="e.g., GRV-RR-2025-01"
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Issue Category:</b>
                    <select
                      value={issueCategory} onChange={e => setIssueCategory(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option>Compensation / Tree Evaluation</option>
                      <option>Boundary & Survey Area Mismatch</option>
                      <option>Housing Allotment Location</option>
                      <option>Livelihood Grant Delay</option>
                      <option>Family Member Inclusion</option>
                    </select>
                  </label>
                </div>

                <label style={{ display: "block" }}>
                  <b style={{ color: "#334155" }}>Grievance Description:</b>
                  <input
                    value={grievanceDesc} onChange={e => setGrievanceDesc(e.target.value)}
                    placeholder="Nature of grievance recorded by citizen/landowner"
                    style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                  />
                </label>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Current Grievance Status:</b>
                    <select
                      value={grievanceStatusField} onChange={e => setGrievanceStatusField(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option>No Grievance</option><option>Open</option><option>Under Review</option>
                      <option>Field Investigation</option><option>Resolved</option>
                    </select>
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Administrative Resolution Required?</b>
                    <select
                      value={resolutionRequired} onChange={e => setResolutionRequired(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    >
                      <option value="No">No (Resolved / Standard Procedure)</option>
                      <option value="Yes">Yes (District Authority Action Needed)</option>
                    </select>
                  </label>
                </div>

                <label style={{ display: "block" }}>
                  <b style={{ color: "#334155" }}>Field Officer Ground Observation on Grievance:</b>
                  <input
                    value={officerObservation} onChange={e => setOfficerObservation(e.target.value)}
                    placeholder="Officer's factual findings on the dispute..."
                    style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                  />
                </label>
              </div>
            )}
          </div>

          {/* ──────────────── 9. EVIDENCE CAPTURE & SITE VISIT ──────────────── */}
          <div
            ref={el => sectionRefs.current[9] = el}
            style={{
              border: openSection === 9 ? "2px solid #0f6c70" : "1px solid #e2e8f0",
              borderRadius: "8px", overflow: "visible", height: "auto", background: "#ffffff",
              transition: "border-color 0.2s, box-shadow 0.2s",
              boxShadow: openSection === 9 ? "0 4px 12px rgba(15, 108, 112, 0.08)" : "none"
            }}
          >
            <div
              onClick={() => toggleSection(9)}
              style={{
                minHeight: "52px", padding: "12px 18px", background: openSection === 9 ? "#f0fdfa" : "#ffffff",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
                gap: "12px", fontWeight: 700, color: openSection === 9 ? "#0f6c70" : "#0f172a", fontSize: "13.5px", userSelect: "none"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: "12px", color: openSection === 9 ? "#0f6c70" : "#64748b", fontWeight: 800 }}>{openSection === 9 ? "▼" : "▶"}</span>
                <span style={{ wordBreak: "break-word" }}>9. FIELD EVIDENCE & SITE VISIT LOG</span>
              </div>
              {renderBadge(sec9Done)}
            </div>
            {openSection === 9 && (
              <div style={{ height: "auto", maxHeight: "none", minHeight: 0, overflow: "visible", padding: "20px", background: "#fafafa", borderTop: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: "16px", rowGap: "18px", fontSize: "12.5px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>Site Visit Date:</b>
                    <input
                      type="date" value={siteVisitDate} onChange={e => setSiteVisitDate(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                  <label style={{ display: "block" }}>
                    <b style={{ color: "#334155" }}>GPS Coordinates / Pillar Demarcation:</b>
                    <input
                      value={gpsLocation} onChange={e => setGpsLocation(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", fontSize: "12.5px" }}
                    />
                  </label>
                </div>

                <label style={{ display: "block" }}>
                  <b style={{ color: "#334155" }}>House / Property Ground Observations:</b>
                  <textarea
                    rows={3} value={houseObservations} onChange={e => setHouseObservations(e.target.value)}
                    style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", font: "inherit", fontSize: "12.5px" }}
                  />
                </label>

                {/* Evidence Upload */}
                <div style={{ background: "#ffffff", border: "1.5px dashed #0f6c70", borderRadius: "8px", padding: "14px" }}>
                  <b style={{ color: "#0f6c70", display: "block", marginBottom: "8px", fontSize: "13px" }}>📸 Upload Field Photo / Inspection Certificate:</b>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "12px", alignItems: "center" }}>
                    <input
                      type="file" accept="image/*,.pdf" onChange={e => setFile(e.target.files?.[0] || null)}
                      style={{ fontSize: "12px" }}
                    />
                    <input
                      placeholder="Evidence note (e.g., Geotagged site photo with landowner)"
                      value={evidenceDesc} onChange={e => setEvidenceDesc(e.target.value)}
                      style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", fontSize: "12.5px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                    />
                  </div>
                </div>

                <label style={{ display: "block" }}>
                  <b style={{ color: "#334155" }}>Final Field Officer Remarks:</b>
                  <textarea
                    rows={3} value={officerRemarks} onChange={e => setOfficerRemarks(e.target.value)}
                    placeholder="Comprehensive observations, verification findings and formal recommendation..."
                    style={{ boxSizing: "border-box", width: "100%", padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", marginTop: "5px", font: "inherit", fontSize: "12.5px" }}
                  />
                </label>
              </div>
            )}
          </div>

          {/* ──────────────── 10. FINAL VERIFICATION, AUDIT & SUBMISSION ──────────────── */}
          <div
            ref={el => sectionRefs.current[10] = el}
            style={{
              border: openSection === 10 ? "2px solid #0f172a" : "1.5px solid #0f172a",
              borderRadius: "8px", overflow: "visible", height: "auto", background: "#f8fafc",
              transition: "border-color 0.2s, box-shadow 0.2s",
              boxShadow: openSection === 10 ? "0 4px 12px rgba(15, 23, 42, 0.12)" : "none"
            }}
          >
            <div
              onClick={() => toggleSection(10)}
              style={{
                minHeight: "52px", padding: "12px 18px", background: "#0f172a", color: "#ffffff",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between",
                gap: "12px", fontWeight: 800, fontSize: "13.5px", userSelect: "none"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: "12px", color: "#99f6e4", fontWeight: 800 }}>{openSection === 10 ? "▼" : "▶"}</span>
                <span style={{ wordBreak: "break-word" }}>10. FINAL VERIFICATION, AUDIT & SUBMISSION</span>
              </div>
              {renderBadge(sec10Done)}
            </div>
            {openSection === 10 && (
              <div style={{ height: "auto", maxHeight: "none", minHeight: 0, overflow: "visible", padding: "20px", display: "flex", flexDirection: "column", gap: "16px", rowGap: "18px", fontSize: "12.5px" }}>
                {/* 10 Sections Check-off Grid */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "10px" }}>
                  <div style={{ padding: "8px 12px", background: sec1Done ? "#dcfce7" : "#fee2e2", border: sec1Done ? "1px solid #86efac" : "1px solid #fca5a5", borderRadius: "6px", fontWeight: 600, color: sec1Done ? "#166534" : "#991b1b" }}>
                    {sec1Done ? "✓" : "✗"} 1. Parcel Verified
                  </div>
                  <div style={{ padding: "8px 12px", background: sec2Done ? "#dcfce7" : "#fee2e2", border: sec2Done ? "1px solid #86efac" : "1px solid #fca5a5", borderRadius: "6px", fontWeight: 600, color: sec2Done ? "#166534" : "#991b1b" }}>
                    {sec2Done ? "✓" : "✗"} 2. Family Verified
                  </div>
                  <div style={{ padding: "8px 12px", background: sec3Done ? "#dcfce7" : "#fee2e2", border: sec3Done ? "1px solid #86efac" : "1px solid #fca5a5", borderRadius: "6px", fontWeight: 600, color: sec3Done ? "#166534" : "#991b1b" }}>
                    {sec3Done ? "✓" : "✗"} 3. Displacement Verified
                  </div>
                  <div style={{ padding: "8px 12px", background: sec4Done ? "#dcfce7" : "#fee2e2", border: sec4Done ? "1px solid #86efac" : "1px solid #fca5a5", borderRadius: "6px", fontWeight: 600, color: sec4Done ? "#166534" : "#991b1b" }}>
                    {sec4Done ? "✓" : "✗"} 4. Compensation Verified
                  </div>
                  <div style={{ padding: "8px 12px", background: sec5Done ? "#dcfce7" : "#fee2e2", border: sec5Done ? "1px solid #86efac" : "1px solid #fca5a5", borderRadius: "6px", fontWeight: 600, color: sec5Done ? "#166534" : "#991b1b" }}>
                    {sec5Done ? "✓" : "✗"} 5. Housing Verified
                  </div>
                  <div style={{ padding: "8px 12px", background: sec6Done ? "#dcfce7" : "#fee2e2", border: sec6Done ? "1px solid #86efac" : "1px solid #fca5a5", borderRadius: "6px", fontWeight: 600, color: sec6Done ? "#166534" : "#991b1b" }}>
                    {sec6Done ? "✓" : "✗"} 6. Livelihood Verified
                  </div>
                  <div style={{ padding: "8px 12px", background: sec7Done ? "#dcfce7" : "#fee2e2", border: sec7Done ? "1px solid #86efac" : "1px solid #fca5a5", borderRadius: "6px", fontWeight: 600, color: sec7Done ? "#166534" : "#991b1b" }}>
                    {sec7Done ? "✓" : "✗"} 7. Other Benefits Verified
                  </div>
                  <div style={{ padding: "8px 12px", background: sec8Done ? "#dcfce7" : "#fee2e2", border: sec8Done ? "1px solid #86efac" : "1px solid #fca5a5", borderRadius: "6px", fontWeight: 600, color: sec8Done ? "#166534" : "#991b1b" }}>
                    {sec8Done ? "✓" : "✗"} 8. Grievance Checked
                  </div>
                  <div style={{ padding: "8px 12px", background: sec9Done ? "#dcfce7" : "#fee2e2", border: sec9Done ? "1px solid #86efac" : "1px solid #fca5a5", borderRadius: "6px", fontWeight: 600, color: sec9Done ? "#166534" : "#991b1b" }}>
                    {sec9Done ? "✓" : "✗"} 9. Evidence Captured
                  </div>
                  <div style={{ padding: "8px 12px", background: sec10Done ? "#dcfce7" : "#fee2e2", border: sec10Done ? "1px solid #86efac" : "1px solid #fca5a5", borderRadius: "6px", fontWeight: 600, color: sec10Done ? "#166534" : "#991b1b" }}>
                    {sec10Done ? "✓" : "✗"} 10. Final Verification Selected
                  </div>
                </div>

                <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #cbd5e1" }}>
                  <b style={{ color: "#0f172a", display: "block", marginBottom: "10px", fontSize: "13px" }}>Select Final Ground Verification Outcome:</b>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
                    {[
                      { val: "Verified", label: "✓ Verified (All OK)", color: "#16704a", desc: "All 10 sections confirmed on site" },
                      { val: "Partially Verified", label: "⏳ Partially Verified", color: "#0f6c70", desc: "Some documentation in progress" },
                      { val: "Re-verification Required", label: "⚠️ Re-verification Req", color: "#d97706", desc: "Discrepancy needs field revisit" },
                      { val: "Blocked", label: "🛑 Blocked / Stayed", color: "#dc2626", desc: "Active litigation / serious dispute" }
                    ].map(opt => (
                      <label
                        key={opt.val}
                        style={{
                          display: "flex", flexDirection: "column", gap: "4px", padding: "10px 12px", borderRadius: "6px", cursor: "pointer",
                          border: finalStatus === opt.val ? `2px solid ${opt.color}` : "1px solid #cbd5e1",
                          background: finalStatus === opt.val ? "#f0fdfa" : "#fff",
                          boxShadow: finalStatus === opt.val ? "0 2px 8px rgba(0,0,0,0.06)" : "none"
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <input
                            type="radio" name="finalStatusOpt" value={opt.val}
                            checked={finalStatus === opt.val} onChange={() => setFinalStatus(opt.val)}
                          />
                          <b style={{ color: opt.color, fontSize: "13px" }}>{opt.label}</b>
                        </div>
                        <span style={{ fontSize: "11px", color: "#64748b", marginLeft: "22px" }}>{opt.desc}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

        </div>

        {/* Fixed Footer Actions (Sticky) */}
        <div className="rr-footer" style={{
          flexShrink: 0,
          padding: "14px 20px", background: "#f8fafc", borderTop: "1px solid #e2e8f0",
          display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px",
          borderBottomLeftRadius: "12px", borderBottomRightRadius: "12px"
        }}>
          <button
            type="button" onClick={onClose} disabled={submitting}
            style={{ background: "#ffffff", color: "#475569", border: "1px solid #cbd5e1", padding: "8px 16px", borderRadius: "6px", fontWeight: 600, cursor: "pointer" }}
          >
            Cancel / Close
          </button>

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              type="button" disabled={submitting}
              onClick={() => handleSave("Partially Verified", true)}
              style={{
                background: "#0f6c70", color: "#ffffff", border: "none", padding: "8px 16px",
                borderRadius: "6px", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: "6px"
              }}
            >
              💾 Save Draft
            </button>
            <button
              type="button" disabled={submitting}
              onClick={() => handleSave(finalStatus, false)}
              style={{
                background: finalStatus === "Verified" ? "#16704a" : (finalStatus === "Blocked" ? "#dc2626" : "#d97706"),
                color: "#ffffff", border: "none", padding: "8px 20px", borderRadius: "6px",
                fontWeight: 800, cursor: "pointer", boxShadow: "0 2px 6px rgba(0,0,0,0.15)"
              }}
            >
              {submitting ? "Saving to Database..." : `✓ Submit Verification (${finalStatus})`}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

function RRPage({ district, user, selected, onSelectCase }) {
  const dist = district || user?.district_scope || "Coimbatore";
  const isField = user?.role === "field_officer";
  const [activeTab, setActiveTab] = useState(isField ? "field_verifications" : "projects");
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [selectedFamilyId, setSelectedFamilyId] = useState(null);
  const [verifyFamily, setVerifyFamily] = useState(null);

  // Filter States
  const [fProject, setFProject] = useState("");
  const [fTaluk, setFTaluk] = useState("");
  const [fVillage, setFVillage] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fStage, setFStage] = useState("");
  const [fPriority, setFPriority] = useState("");
  const [fReadiness, setFReadiness] = useState("");
  const [fReverification, setFReverification] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  // Auto-handle selected case passed from Field Verification or parent nav
  useEffect(() => {
    if (selected?.family_id) {
      setSelectedFamilyId(selected.family_id);
    }
    if (selected?.project_id) {
      setSelectedProjectId(selected.project_id);
    }
  }, [selected]);

  // Fetch district dashboard summary
  const { data: d, error: dashErr } = useData(`/rr/district-dashboard?district=${encodeURIComponent(dist)}`, 5000);

  // Fetch projects for this district
  const { data: projData, error: projErr } = useData(`/projects/?district=${encodeURIComponent(dist)}&limit=500`, 5000);
  const projects = projData?.items || (Array.isArray(projData) ? projData : []);

  // Set default selected project when loaded
  useEffect(() => {
    if (!selectedProjectId && projects.length > 0) {
      setSelectedProjectId(selected?.project_id || projects[0].project_id);
    }
  }, [projects, selectedProjectId, selected]);

  // Fetch parcels for selected project
  const { data: projectParcels, error: parcelsErr } = useData(
    selectedProjectId ? `/rr/projects/${encodeURIComponent(selectedProjectId)}/parcels` : null, 5000
  );

  // Fetch field assignments for field officer
  const { data: assignmentsData, error: assignErr } = useData(
    isField || activeTab === "field_verifications" ? `/rr/field-assignments?district=${encodeURIComponent(dist)}` : null, 5000
  );
  const assignments = assignmentsData?.assignments || [];

  // DSS Priority Queue Data
  const { data: dssPriorityData } = useData(`/dss/priority-parcels?district=${encodeURIComponent(dist)}&limit=50`, 10000);
  const dssParcels = dssPriorityData?.items || [];

  if (dashErr) return <Panel title={`R&R Rehabilitation & Resettlement (${dist})`}><div className="error">Unable to load R&R data: {dashErr.message}</div></Panel>;

  const sum = d?.summary || {};
  const cards = [
    ["Total Affected Families", sum.total_families || 0],
    ["Avg Readiness", `${sum.avg_readiness || sum.overall_readiness_percentage || 0}%`],
    ["Completed", sum.completed || sum.completed_rehabilitation || 0],
    ["In Progress", sum.in_progress || 0],
    ["Delayed / Critical", (sum.delayed || 0) + (sum.critical || 0)],
    ["Open Grievances", sum.open_grievances || 0],
    ["Pending Verification", sum.pending_verification || sum.awaiting_verification || 0],
    ["Vulnerable Families", sum.at_risk || sum.vulnerable_families || 0],
  ];

  const currentProject = projects.find(p => p.project_id === selectedProjectId);

  // Helper filter function across case items
  const filterCase = (item) => {
    if (fProject && (item.project_id !== fProject && item.project_display !== fProject)) return false;
    if (fTaluk && item.taluk?.toLowerCase() !== fTaluk.toLowerCase()) return false;
    if (fVillage && item.village?.toLowerCase() !== fVillage.toLowerCase()) return false;
    if (fStatus) {
      const curStat = (item.exceptional_state || item.verification_status || "").toLowerCase();
      if (!curStat.includes(fStatus.toLowerCase())) return false;
    }
    if (fStage && item.rr_stage?.toLowerCase() !== fStage.toLowerCase()) return false;
    if (fPriority && item.priority?.toLowerCase() !== fPriority.toLowerCase()) return false;
    if (fReadiness) {
      const r = item.readiness_percentage || 0;
      if (fReadiness === "<50" && r >= 50) return false;
      if (fReadiness === "50-74" && (r < 50 || r >= 75)) return false;
      if (fReadiness === "75-89" && (r < 75 || r >= 90)) return false;
      if (fReadiness === ">=90" && r < 90) return false;
    }
    if (fReverification) {
      const curStat = (item.exceptional_state || item.verification_status || "").toLowerCase();
      if (!curStat.includes("re-verification")) return false;
    }
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const match = (
        (item.rr_id || "").toLowerCase().includes(q) ||
        (item.family_id || "").toLowerCase().includes(q) ||
        (item.parcel_id || "").toLowerCase().includes(q) ||
        (item.survey_no || "").toLowerCase().includes(q) ||
        (item.landowner || "").toLowerCase().includes(q) ||
        (item.family_head || "").toLowerCase().includes(q) ||
        (item.affected_family || "").toLowerCase().includes(q) ||
        (item.village || "").toLowerCase().includes(q) ||
        (item.taluk || "").toLowerCase().includes(q)
      );
      if (!match) return false;
    }
    return true;
  };

  // Build unique lists for filter dropdowns
  const allCasesPool = [...assignments, ...(projectParcels?.parcels || [])];
  const uniqueTaluks = Array.from(new Set(allCasesPool.map(c => c.taluk).filter(Boolean)));
  const uniqueVillages = Array.from(new Set(allCasesPool.map(c => c.village).filter(Boolean)));
  const uniqueStages = [
    "Impact Assessment",
    "Eligibility Determination",
    "Compensation Disbursement",
    "Housing Resettlement",
    "Livelihood Support",
    "Verification",
    "Completed"
  ];

  const filteredAssignments = assignments.filter(filterCase);
  const rawParcels = projectParcels?.parcels || [];
  const filteredParcels = rawParcels.filter(filterCase);

  return (
    <>
      <Panel title={`Rehabilitation & Resettlement (R&R) Workspace · ${dist} District`}>
        <div className="cards">
          {cards.map(c => <div className="metric" key={c[0]}><span>{c[0]}</span><b>{c[1]}</b></div>)}
        </div>
      </Panel>

      {/* Tabs / Switcher */}
      <div style={{ display: "flex", gap: "10px", marginBottom: "16px" }}>
        <button
          type="button"
          onClick={() => setActiveTab("dss_priority")}
          style={{
            background: activeTab === "dss_priority" ? "#1a73e8" : "#ffffff",
            color: activeTab === "dss_priority" ? "#ffffff" : "#1a73e8",
            border: `1px solid ${activeTab === "dss_priority" ? "#1a73e8" : "#90caf9"}`,
            padding: "8px 18px", borderRadius: "8px", fontWeight: 700, cursor: "pointer",
            boxShadow: activeTab === "dss_priority" ? "0 2px 4px rgba(26,115,232,0.3)" : "none",
            display: "inline-flex", alignItems: "center", gap: "6px"
          }}
        >
          <span>🤖</span> AI Priority Verification Queue ({dssParcels.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("field_verifications")}
          style={{
            background: activeTab === "field_verifications" ? "#0f6c70" : "#ffffff",
            color: activeTab === "field_verifications" ? "#ffffff" : "#334155",
            border: `1px solid ${activeTab === "field_verifications" ? "#0f6c70" : "#cbd5e1"}`,
            padding: "8px 18px", borderRadius: "8px", fontWeight: 700, cursor: "pointer",
            boxShadow: activeTab === "field_verifications" ? "0 2px 4px rgba(15,108,112,0.2)" : "none"
          }}
        >
          📋 Field Officer R&R Queue ({assignments.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("projects")}
          style={{
            background: activeTab === "projects" ? "#0f6c70" : "#ffffff",
            color: activeTab === "projects" ? "#ffffff" : "#334155",
            border: `1px solid ${activeTab === "projects" ? "#0f6c70" : "#cbd5e1"}`,
            padding: "8px 18px", borderRadius: "8px", fontWeight: 700, cursor: "pointer",
            boxShadow: activeTab === "projects" ? "0 2px 4px rgba(15,108,112,0.2)" : "none"
          }}
        >
          📁 Project-Linked R&R Parcels
        </button>
      </div>

      {/* Comprehensive Filter Controls */}
      <Panel title="R&R Case Queue Filters & Quick Search">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "10px", alignItems: "center" }}>
          {/* Quick Search */}
          <div style={{ gridColumn: "span 2" }}>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "3px" }}>Search Case:</label>
            <input
              type="text"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="Search R&R ID, Family, Survey No, Landowner..."
              style={{ width: "100%", padding: "7px 10px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "12px" }}
            />
          </div>

          {/* Project Filter */}
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "3px" }}>Project:</label>
            <select
              value={fProject}
              onChange={e => setFProject(e.target.value)}
              style={{ width: "100%", padding: "7px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "12px" }}
            >
              <option value="">All Projects</option>
              {projects.map(p => (
                <option key={p.project_id} value={p.project_id}>{p.project_id} - {p.project_name}</option>
              ))}
            </select>
          </div>

          {/* Taluk Filter */}
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "3px" }}>Taluk:</label>
            <select
              value={fTaluk}
              onChange={e => setFTaluk(e.target.value)}
              style={{ width: "100%", padding: "7px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "12px" }}
            >
              <option value="">All Taluks</option>
              {uniqueTaluks.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          {/* Village Filter */}
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "3px" }}>Village:</label>
            <select
              value={fVillage}
              onChange={e => setFVillage(e.target.value)}
              style={{ width: "100%", padding: "7px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "12px" }}
            >
              <option value="">All Villages</option>
              {uniqueVillages.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>

          {/* R&R Status Filter */}
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "3px" }}>R&R Status:</label>
            <select
              value={fStatus}
              onChange={e => setFStatus(e.target.value)}
              style={{ width: "100%", padding: "7px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "12px" }}
            >
              <option value="">All Statuses</option>
              <option value="Pending">Pending</option>
              <option value="Verified">Verified</option>
              <option value="Partially Verified">Partially Verified</option>
              <option value="Re-verification Required">Re-verification Required</option>
              <option value="Blocked">Blocked</option>
            </select>
          </div>

          {/* R&R Stage Filter */}
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "3px" }}>R&R Stage:</label>
            <select
              value={fStage}
              onChange={e => setFStage(e.target.value)}
              style={{ width: "100%", padding: "7px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "12px" }}
            >
              <option value="">All Stages</option>
              {uniqueStages.map(st => <option key={st} value={st}>{st}</option>)}
            </select>
          </div>

          {/* Priority Filter */}
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "3px" }}>Priority:</label>
            <select
              value={fPriority}
              onChange={e => setFPriority(e.target.value)}
              style={{ width: "100%", padding: "7px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "12px" }}
            >
              <option value="">All Priorities</option>
              <option value="High">High</option>
              <option value="Normal">Normal</option>
            </select>
          </div>

          {/* Readiness Filter */}
          <div>
            <label style={{ fontSize: "11px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "3px" }}>Readiness %:</label>
            <select
              value={fReadiness}
              onChange={e => setFReadiness(e.target.value)}
              style={{ width: "100%", padding: "7px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "12px" }}
            >
              <option value="">All Readiness</option>
              <option value="<50">&lt; 50% (Critical)</option>
              <option value="50-74">50% - 74% (Moderate)</option>
              <option value="75-89">75% - 89% (Substantial)</option>
              <option value=">=90">&gt;= 90% (Ready)</option>
            </select>
          </div>

          {/* Re-verification Toggle & Reset */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "16px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", fontWeight: 700, color: "#d97706", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={fReverification}
                onChange={e => setFReverification(e.target.checked)}
              />
              Re-verification Only
            </label>
            <button
              type="button"
              onClick={() => {
                setFProject("");
                setFTaluk("");
                setFVillage("");
                setFStatus("");
                setFStage("");
                setFPriority("");
                setFReadiness("");
                setFReverification(false);
                setSearchTerm("");
              }}
              style={{ background: "#f1f5f9", color: "#475569", border: "1px solid #cbd5e1", borderRadius: "4px", padding: "4px 8px", fontSize: "11px", cursor: "pointer" }}
            >
              Reset Filters
            </button>
          </div>
        </div>
      </Panel>

      {/* ── Tab: AI Priority Verification Queue (DSS) ─────────────── */}
      {activeTab === "dss_priority" && (
        <Panel title={`🤖 AI Priority Verification Queue · ${dist} District (${dssParcels.length} ranked parcels)`}>
          <div style={{ background: "#e8f0fe", padding: "10px 14px", borderRadius: "8px", border: "1px solid #c2e7ff", marginBottom: "14px", fontSize: "12px", color: "#1967d2" }}>
            <b>Automated Risk Ranking:</b> Parcels are dynamically sorted by the Decision Support System using 6 multi-criteria risk vectors: Data Completeness, Boundary Geometry, Statutory SLA, Prior History, and Verification Delays.
          </div>
          <div className="table-wrap" style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Priority Rank</th>
                  <th>Parcel ID</th>
                  <th>Project ID</th>
                  <th>Risk Level</th>
                  <th>Priority Score</th>
                  <th>Data Quality</th>
                  <th>GIS Risk</th>
                  <th>SLA Risk</th>
                  <th>AI Recommendation</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {dssParcels.map((p, idx) => (
                  <tr key={p.parcel_id} style={{ background: idx === 0 ? "#fffbf0" : "inherit" }}>
                    <td><b>#{idx + 1}</b></td>
                    <td>
                      <span style={{ fontWeight: 700, color: "#0f6c70" }}>{p.record_id || `P-${p.parcel_id}`}</span>
                    </td>
                    <td>{p.project_id || "Unassigned"}</td>
                    <td><DSSBadge level={p.risk_level} /></td>
                    <td><b style={{ color: p.priority_score > 70 ? "#b42318" : "#202124" }}>{p.priority_score}/100</b></td>
                    <td>{p.components?.data_quality?.label || "Good"} ({p.components?.data_quality?.score}%)</td>
                    <td>{p.components?.gis_risk?.score}/100</td>
                    <td>{p.components?.sla_risk?.score}/100</td>
                    <td style={{ maxWidth: "300px", fontSize: "12px", fontWeight: 500 }}>
                      {p.recommendation}
                    </td>
                    <td>
                      <button
                        type="button"
                        onClick={() => {
                          if (onSelectCase) onSelectCase({ id: p.parcel_id, parcel_id: p.parcel_id, record_id: p.record_id });
                        }}
                        style={{
                          background: "#0f6c70",
                          color: "#ffffff",
                          border: "none",
                          padding: "6px 12px",
                          borderRadius: "4px",
                          fontWeight: 700,
                          fontSize: "11px",
                          cursor: "pointer"
                        }}
                      >
                        Inspect Dossier →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* ── Tab 1: Field Verification Queue ─────────────────────── */}
      {activeTab === "field_verifications" && (
        <Panel title={`Field Officer Assigned R&R Cases (${filteredAssignments.length} of ${assignments.length})`}>
          {assignErr && <div className="error">{assignErr.message}</div>}
          <div className="table-wrap" style={{ overflowX: "auto" }}>
            <table style={{ minWidth: "1650px" }}>
              <thead>
                <tr>
                  <th style={{ position: "sticky", left: 0, background: "#f8fafc", zIndex: 2 }}>R&R ID</th>
                  <th>Project</th>
                  <th>Parcel ID</th>
                  <th>Survey No</th>
                  <th>Landowner</th>
                  <th>Family ID / Head</th>
                  <th>Location (Vlg/Tlk/Dist)</th>
                  <th>R&R Status</th>
                  <th>R&R Stage</th>
                  <th>Readiness %</th>
                  <th>Priority</th>
                  <th>Displacement</th>
                  <th>Compensation</th>
                  <th>Housing</th>
                  <th>Livelihood</th>
                  <th>Grievance</th>
                  <th>Last Verified</th>
                  <th style={{ position: "sticky", right: 0, background: "#f8fafc", zIndex: 2 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAssignments.map(a => {
                  const readiness = a.readiness_percentage || 0;
                  const readinessColor = readiness >= 90 ? "#16704a" : (readiness >= 75 ? "#0f6c70" : (readiness >= 50 ? "#d97706" : "#dc2626"));
                  const readinessBg = readiness >= 90 ? "#e6f4ea" : (readiness >= 75 ? "#e0f2f1" : (readiness >= 50 ? "#fef3c7" : "#fee2e2"));

                  const curStatus = a.exceptional_state || a.verification_status || "Pending";
                  const statusBg = curStatus.includes("Verified") && !curStatus.includes("Partially") ? "#e6f4ea" :
                    (curStatus.includes("Partially") ? "#e0f2f1" :
                    (curStatus.includes("Re-verification") ? "#fef3c7" :
                    (curStatus.includes("Blocked") ? "#fee2e2" : "#f1f5f9")));
                  const statusColor = curStatus.includes("Verified") && !curStatus.includes("Partially") ? "#16704a" :
                    (curStatus.includes("Partially") ? "#0f6c70" :
                    (curStatus.includes("Re-verification") ? "#d97706" :
                    (curStatus.includes("Blocked") ? "#dc2626" : "#475569")));

                  return (
                    <tr key={a.verification_id || a.family_id}>
                      <td style={{ position: "sticky", left: 0, background: "#ffffff", zIndex: 1 }}>
                        <b style={{ color: "#0f6c70", fontFamily: "monospace" }}>{a.rr_id || `RR-${a.family_id}`}</b>
                      </td>
                      <td>
                        <span style={{ fontSize: "11px", fontWeight: 600, color: "#334155" }} title={a.project_name}>
                          {a.project_display || a.project_id || "Direct"}
                        </span>
                      </td>
                      <td><b>{a.parcel_id}</b></td>
                      <td><b>{a.survey_no}</b></td>
                      <td>{a.landowner || a.family_head}</td>
                      <td>
                        <div><b>{a.family_head}</b></div>
                        <div style={{ fontSize: "10px", color: "#64748b" }}>{a.family_id} ({a.members || 1} mem)</div>
                      </td>
                      <td>
                        <div style={{ fontSize: "11px" }}>{a.village}, {a.taluk}</div>
                        <div style={{ fontSize: "10px", color: "#64748b" }}>{a.district}</div>
                      </td>
                      <td>
                        <span style={{ background: statusBg, color: statusColor, padding: "3px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 700, whiteSpace: "nowrap" }}>
                          {curStatus}
                        </span>
                      </td>
                      <td>
                        <span style={{ background: "#f8fafc", border: "1px solid #cbd5e1", color: "#0f6c70", padding: "2px 6px", borderRadius: "4px", fontSize: "11px", fontWeight: 600, whiteSpace: "nowrap" }}>
                          {a.rr_stage || "Impact Assessment"}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <div style={{ width: "50px", height: "6px", background: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
                            <div style={{ width: `${readiness}%`, height: "100%", background: readinessColor }} />
                          </div>
                          <b style={{ fontSize: "11px", color: readinessColor }}>{readiness}%</b>
                        </div>
                      </td>
                      <td>
                        <span style={{
                          background: a.priority === "High" ? "#fee2e2" : "#f1f5f9",
                          color: a.priority === "High" ? "#dc2626" : "#475569",
                          padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 700
                        }}>
                          {a.priority || "Normal"}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: "11px", color: a.displacement_status === "Displaced" ? "#dc2626" : "#16704a", fontWeight: 600 }}>
                          {a.displacement_status || "Not Displaced"}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: "11px", color: a.compensation_status === "Paid" ? "#16704a" : "#d97706", fontWeight: 600 }}>
                          {a.compensation_status || "Pending"}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: "11px", color: a.housing_status === "Allotted" ? "#16704a" : "#475569" }}>
                          {a.housing_status || "Pending"}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: "11px", color: a.livelihood_status === "Restored" ? "#16704a" : "#475569" }}>
                          {a.livelihood_status || "Pending"}
                        </span>
                      </td>
                      <td>
                        <span style={{
                          background: (a.grievance_status === "Open" || a.grievance_status === "Escalated") ? "#fee2e2" : "#f1f5f9",
                          color: (a.grievance_status === "Open" || a.grievance_status === "Escalated") ? "#dc2626" : "#64748b",
                          padding: "2px 6px", borderRadius: "4px", fontSize: "11px", fontWeight: 600
                        }}>
                          {a.grievance_status || "None"}
                        </span>
                      </td>
                      <td style={{ fontSize: "11px", color: "#64748b", whiteSpace: "nowrap" }}>
                        {a.verified_at ? a.verified_at.split("T")[0] : (a.completed_date ? a.completed_date.split("T")[0] : "Not Verified")}
                      </td>
                      <td style={{ position: "sticky", right: 0, background: "#ffffff", zIndex: 1 }}>
                        <div style={{ display: "flex", gap: "6px" }}>
                          <button
                            type="button"
                            onClick={() => setSelectedFamilyId(a.family_id)}
                            style={{ background: "#0f6c70", color: "#fff", padding: "4px 9px", borderRadius: "5px", fontSize: "11px", fontWeight: 700, cursor: "pointer", border: "none" }}
                          >
                            View R&R
                          </button>
                          <button
                            type="button"
                            onClick={() => setVerifyFamily(a)}
                            style={{ background: "#16704a", color: "#fff", padding: "4px 10px", borderRadius: "5px", fontSize: "11px", fontWeight: 700, cursor: "pointer", border: "none" }}
                          >
                            Verify R&R
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filteredAssignments.length === 0 && (
                  <tr>
                    <td colSpan={18} style={{ textAlign: "center", padding: "28px", color: "#64748b" }}>
                      No R&R cases matching the selected filters in this queue.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* ── Tab 2: Project → Parcel Flow ───────────────────────── */}
      {activeTab === "projects" && (
        <>
          <Panel title="R&R-Enabled Projects Selection">
            <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap", marginBottom: "10px" }}>
              <label style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Select Project:</label>
              <select
                style={{ flex: 1, maxWidth: "500px", padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: "8px", fontWeight: 600 }}
                value={selectedProjectId || ""}
                onChange={e => setSelectedProjectId(e.target.value)}
              >
                {projects.map(p => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.project_id} · {p.project_name} ({p.taluk || dist})
                  </option>
                ))}
              </select>
            </div>

            {currentProject && (
              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: "12px 16px", borderRadius: "8px", display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "10px" }}>
                <div>
                  <b style={{ color: "#0f6c70", fontSize: "14px" }}>{currentProject.project_name}</b>
                  <div style={{ fontSize: "12px", color: "#64748b", marginTop: "2px" }}>
                    ID: {currentProject.project_id} · Type: {currentProject.project_type || "Infrastructure"} · Taluk: {currentProject.taluk || "District-Wide"} · Status: {currentProject.project_status || "Active"}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>Linked Parcels</span>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: "#0f172a" }}>{projectParcels?.total_parcels || 0}</div>
                </div>
              </div>
            )}
          </Panel>

          {/* Parcels Linked Table */}
          <Panel title={`Parcels Linked to Project · ${selectedProjectId || "Select Project"} (${filteredParcels.length} of ${rawParcels.length})`}>
            {parcelsErr && <div className="error">{parcelsErr.message}</div>}
            {!projectParcels && !parcelsErr && <p>Loading parcels linked to {selectedProjectId}...</p>}

            {projectParcels && (
              <div className="table-wrap" style={{ overflowX: "auto" }}>
                <table style={{ minWidth: "1650px" }}>
                  <thead>
                    <tr>
                      <th style={{ position: "sticky", left: 0, background: "#f8fafc", zIndex: 2 }}>R&R ID</th>
                      <th>Project</th>
                      <th>Parcel ID</th>
                      <th>Survey No</th>
                      <th>Landowner</th>
                      <th>Family ID / Head</th>
                      <th>Location (Vlg/Tlk/Dist)</th>
                      <th>R&R Status</th>
                      <th>R&R Stage</th>
                      <th>Readiness %</th>
                      <th>Priority</th>
                      <th>Displacement</th>
                      <th>Compensation</th>
                      <th>Housing</th>
                      <th>Livelihood</th>
                      <th>Grievance</th>
                      <th>Last Verified</th>
                      <th style={{ position: "sticky", right: 0, background: "#f8fafc", zIndex: 2 }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredParcels.map((p) => {
                      const readiness = p.readiness_percentage || 0;
                      const badgeColor = readiness >= 90 ? "#16704a" : (readiness >= 75 ? "#0f6c70" : (readiness >= 50 ? "#d97706" : "#dc2626"));
                      const badgeBg = readiness >= 90 ? "#e6f4ea" : (readiness >= 75 ? "#e0f2f1" : (readiness >= 50 ? "#fef3c7" : "#fee2e2"));

                      const curStatus = p.exceptional_state || p.verification_status || "Pending";
                      const statusBg = curStatus.includes("Verified") && !curStatus.includes("Partially") ? "#e6f4ea" :
                        (curStatus.includes("Partially") ? "#e0f2f1" :
                        (curStatus.includes("Re-verification") ? "#fef3c7" :
                        (curStatus.includes("Blocked") ? "#fee2e2" : "#f1f5f9")));
                      const statusColor = curStatus.includes("Verified") && !curStatus.includes("Partially") ? "#16704a" :
                        (curStatus.includes("Partially") ? "#0f6c70" :
                        (curStatus.includes("Re-verification") ? "#d97706" :
                        (curStatus.includes("Blocked") ? "#dc2626" : "#475569")));

                      return (
                        <tr key={p.parcel_id}>
                          <td style={{ position: "sticky", left: 0, background: "#ffffff", zIndex: 1 }}>
                            <b style={{ color: "#0f6c70", fontFamily: "monospace" }}>{p.rr_id || `RR-${p.family_id || p.parcel_id}`}</b>
                          </td>
                          <td>
                            <span style={{ fontSize: "11px", fontWeight: 600, color: "#334155" }} title={p.project_name}>
                              {p.project_display || p.project_id || selectedProjectId}
                            </span>
                          </td>
                          <td><b>{p.parcel_id}</b></td>
                          <td><b>{p.survey_no}</b></td>
                          <td>{p.landowner}</td>
                          <td>
                            <div><b>{p.affected_family}</b></div>
                            <div style={{ fontSize: "10px", color: "#64748b" }}>{p.family_id || "N/A"}</div>
                          </td>
                          <td>
                            <div style={{ fontSize: "11px" }}>{p.village}, {p.taluk}</div>
                            <div style={{ fontSize: "10px", color: "#64748b" }}>{p.district}</div>
                          </td>
                          <td>
                            <span style={{ background: statusBg, color: statusColor, padding: "3px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 700, whiteSpace: "nowrap" }}>
                              {curStatus}
                            </span>
                          </td>
                          <td>
                            <span style={{ background: "#f8fafc", border: "1px solid #cbd5e1", color: "#0f6c70", padding: "2px 6px", borderRadius: "4px", fontSize: "11px", fontWeight: 600, whiteSpace: "nowrap" }}>
                              {p.rr_stage || "Impact Assessment"}
                            </span>
                          </td>
                          <td>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                              <div style={{ width: "50px", height: "6px", background: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
                                <div style={{ width: `${readiness}%`, height: "100%", background: badgeColor }} />
                              </div>
                              <b style={{ fontSize: "11px", color: badgeColor }}>{readiness}%</b>
                            </div>
                          </td>
                          <td>
                            <span style={{
                              background: p.priority === "High" ? "#fee2e2" : "#f1f5f9",
                              color: p.priority === "High" ? "#dc2626" : "#475569",
                              padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 700
                            }}>
                              {p.priority || "Normal"}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontSize: "11px", color: p.displacement_status === "Displaced" ? "#dc2626" : "#16704a", fontWeight: 600 }}>
                              {p.displacement_status || "Not Displaced"}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontSize: "11px", color: p.compensation_status === "Paid" ? "#16704a" : "#d97706", fontWeight: 600 }}>
                              {p.compensation_status || "Pending"}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontSize: "11px", color: p.housing_status === "Allotted" ? "#16704a" : "#475569" }}>
                              {p.housing_status || "Pending"}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontSize: "11px", color: p.livelihood_status === "Restored" ? "#16704a" : "#475569" }}>
                              {p.livelihood_status || "Pending"}
                            </span>
                          </td>
                          <td>
                            <span style={{
                              background: (p.grievance_status === "Open" || p.grievance_status === "Escalated") ? "#fee2e2" : "#f1f5f9",
                              color: (p.grievance_status === "Open" || p.grievance_status === "Escalated") ? "#dc2626" : "#64748b",
                              padding: "2px 6px", borderRadius: "4px", fontSize: "11px", fontWeight: 600
                            }}>
                              {p.grievance_status || "None"}
                            </span>
                          </td>
                          <td style={{ fontSize: "11px", color: "#64748b", whiteSpace: "nowrap" }}>
                            {p.verified_at ? p.verified_at.split("T")[0] : "Not Verified"}
                          </td>
                          <td style={{ position: "sticky", right: 0, background: "#ffffff", zIndex: 1 }}>
                            <div style={{ display: "flex", gap: "6px" }}>
                              <button
                                type="button"
                                onClick={() => setSelectedFamilyId(p.family_id || `RNR-${dist.slice(0,3).toUpperCase()}-${p.parcel_id}`)}
                                style={{ background: "#0f6c70", color: "#fff", padding: "4px 9px", borderRadius: "5px", fontSize: "11px", fontWeight: 700, cursor: "pointer", border: "none" }}
                              >
                                View R&R
                              </button>
                              {isField && (
                                <button
                                  type="button"
                                  onClick={() => setVerifyFamily(p)}
                                  style={{ background: "#16704a", color: "#fff", padding: "4px 10px", borderRadius: "5px", fontSize: "11px", fontWeight: 700, cursor: "pointer", border: "none" }}
                                >
                                  Verify R&R
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {filteredParcels.length === 0 && (
                      <tr>
                        <td colSpan={18} style={{ textAlign: "center", padding: "28px", color: "#64748b" }}>
                          No land parcels match the selected filters for this project.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </>
      )}

      {/* R&R Stage Breakdown & Taluk Overview from Backend Data */}
      <div className="grid2" style={{ marginTop: "16px" }}>
        <Panel title={`R&R Stage Breakdown · ${dist}`}>
          {d?.stage_breakdown && d.stage_breakdown.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>R&R Stage</th>
                    <th>Affected Families</th>
                    <th>Share</th>
                  </tr>
                </thead>
                <tbody>
                  {d.stage_breakdown.map((s, idx) => {
                    const total = sum.total_families || 1;
                    const pct = Math.round((s.cnt / total) * 100);
                    return (
                      <tr key={idx}>
                        <td><b>{s.rr_stage}</b></td>
                        <td>{s.cnt}</td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <div style={{ width: "60px", height: "6px", background: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
                              <div style={{ width: `${pct}%`, height: "100%", background: "#0f6c70" }} />
                            </div>
                            <span style={{ fontSize: "11px", color: "#64748b" }}>{pct}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty">No stage breakdown records available.</div>
          )}
        </Panel>

        <Panel title={`Taluk-wise R&R Performance · ${dist}`}>
          {d?.taluk_overview && d.taluk_overview.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Taluk</th>
                    <th>Families</th>
                    <th>Avg Readiness</th>
                    <th>Completed</th>
                    <th>At Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {d.taluk_overview.map((t, idx) => (
                    <tr key={idx}>
                      <td><b>{t.taluk}</b></td>
                      <td>{t.families}</td>
                      <td><b>{t.avg_readiness}%</b></td>
                      <td style={{ color: "#16704a", fontWeight: 700 }}>{t.completed}</td>
                      <td style={{ color: t.at_risk > 0 ? "#dc2626" : "#475569" }}>{t.at_risk}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty">No taluk overview records available.</div>
          )}
        </Panel>
      </div>

      {/* Household Profile Modal */}
      {selectedFamilyId && (
        <RRHouseholdModal
          familyId={selectedFamilyId}
          user={user}
          onClose={() => setSelectedFamilyId(null)}
          onOpenVerify={fam => setVerifyFamily(fam)}
        />
      )}

      {/* Field Officer Verification Modal */}
      {verifyFamily && (
        <RRVerificationModal
          family={verifyFamily}
          onClose={() => setVerifyFamily(null)}
          onSuccess={() => {
            setSelectedFamilyId(null);
          }}
        />
      )}
    </>
  );
}

function IntelligenceDashboard({ district, user }) {
  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}>
        <h2 style={{ margin: 0 }}>Advanced Intelligence · {district}</h2>
      </div>
      <ConflictEngine user={user} district={district} />
      <Simulator />
      <Tools district={district} />
      <Advanced district={district} />
      <Evidence />
      <Report />
    </>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// 📱 MULTI-DISTRICT SMPP SMS NOTIFICATION CENTRE (GOVERNMENT NOTIFICATION PORTAL)
// ═══════════════════════════════════════════════════════════════════════════════
function SMSNotificationCentre({ district, user, go }) {
  const dist = user?.district_scope || district || "Coimbatore";
  const isStateOrAdmin = ["state_authority", "authority", "admin", "national_authority"].includes(user?.role);

  const [tab, setTab] = useState("compose"); // "compose" | "history" | "state_view"
  const [subMode, setSubMode] = useState("bulk"); // "bulk" | "single"

  // Live Gateway health
  const { data: health } = useData("/api/sms/health", 10000);

  // Scoped District stats (auto-refreshes every 5s or upon event bus dispatch)
  const { data: stats } = useData(`/api/sms/stats?district=${encodeURIComponent(dist)}`, 5000);

  // State-wide aggregated stats (for State Authority / Admin)
  const { data: stateStats } = useData(isStateOrAdmin ? "/api/sms/state-stats" : null, 10000);

  // Official statutory SMS templates
  const { data: tplData } = useData("/api/sms/templates");
  const templates = tplData?.templates || [];

  // District project list
  const { data: projectData } = useData(`/projects/?district=${encodeURIComponent(dist)}&limit=500`);
  const projectList = projectData?.items || [];

  // Bulk Compose Form Filters
  const [filterProject, setFilterProject] = useState("");
  const [filterTaluk, setFilterTaluk] = useState("");
  const [filterVillage, setFilterVillage] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [messageText, setMessageText] = useState("");

  // Recipient query response & state
  const [recipientData, setRecipientData] = useState(null);
  const [recipientLoading, setRecipientLoading] = useState(false);
  const [showRecipientList, setShowRecipientList] = useState(false);

  // Confirmation & Preview Modals
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [confirmAgreed, setConfirmAgreed] = useState(false);
  const [bulkSending, setBulkSending] = useState(false);
  const [sendResult, setSendResult] = useState(null);

  // Single SMS Form State
  const [singlePhone, setSinglePhone] = useState("");
  const [singleName, setSingleName] = useState("");
  const [singleSurveyNo, setSingleSurveyNo] = useState("");
  const [singleProject, setSingleProject] = useState("");
  const [singleMessage, setSingleMessage] = useState("");
  const [singleSending, setSingleSending] = useState(false);
  const [singleResult, setSingleResult] = useState(null);

  // History Tab state
  const [historySearch, setHistorySearch] = useState("");
  const [historyProject, setHistoryProject] = useState("");
  const [historyStatus, setHistoryStatus] = useState("");
  const [historyType, setHistoryType] = useState("");
  const [historyData, setHistoryData] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [selectedLogMessage, setSelectedLogMessage] = useState(null);

  // Query recipients dynamically whenever filters change
  useEffect(() => {
    let active = true;
    setRecipientLoading(true);
    const q = new URLSearchParams({
      district: dist,
      project_id: filterProject,
      taluk: filterTaluk,
      village: filterVillage,
      status: filterStatus
    }).toString();

    api(`/api/sms/recipients?${q}`)
      .then(res => {
        if (active) {
          setRecipientData(res);
          setRecipientLoading(false);
        }
      })
      .catch(() => {
        if (active) setRecipientLoading(false);
      });

    return () => { active = false; };
  }, [dist, filterProject, filterTaluk, filterVillage, filterStatus]);

  // Load history whenever history tab is active or filters change
  const loadHistory = () => {
    setHistoryLoading(true);
    const q = new URLSearchParams({
      district: dist,
      project_id: historyProject,
      status: historyStatus,
      message_type: historyType,
      search: historySearch,
      limit: "200"
    }).toString();

    api(`/api/sms/history?${q}`)
      .then(res => {
        setHistoryData(res);
        setHistoryLoading(false);
      })
      .catch(() => {
        setHistoryLoading(false);
      });
  };

  useEffect(() => {
    if (tab === "history") {
      loadHistory();
    }
  }, [tab, dist, historyProject, historyStatus, historyType, historySearch]);

  // Handle template selection
  const handleSelectTemplate = (id) => {
    setSelectedTemplateId(id);
    if (!id) return;
    const found = templates.find(t => t.id === id);
    if (found) {
      const today = new Date();
      const nextWeek = new Date(today.getTime() + 5 * 86400000);
      const formattedDate = nextWeek.toLocaleDateString("en-IN", { day: '2-digit', month: 'short', year: 'numeric' });
      let txt = found.template
        .replaceAll("{district}", dist)
        .replaceAll("{project_id}", filterProject || (projectList[0]?.project_id || "PRJ-TN-01"))
        .replaceAll("{date}", formattedDate)
        .replaceAll("{amount}", "{{amount}}")
        .replaceAll("{survey_no}", "{{survey_no}}")
        .replaceAll("{village}", filterVillage || "{{village}}")
        .replaceAll("{owner_name}", "{{owner_name}}")
        .replaceAll("{ref_no}", `TN-${dist.slice(0, 3).toUpperCase()}-2026`);
      setMessageText(txt);
    }
  };

  const insertPlaceholder = (tag) => {
    setMessageText(prev => prev ? `${prev} ${tag} ` : `${tag} `);
  };

  const getSampleRenderedMessage = (rawText) => {
    const sampleRecipient = recipientData?.recipients?.[0] || {
      owner_name: "M. Ramaswamy",
      survey_no: "142/3B",
      village: filterVillage || "Perur",
      project_id: filterProject || "PRJ-TN-CBE-001"
    };
    return (rawText || "")
      .replaceAll("{{owner_name}}", sampleRecipient.owner_name || "M. Ramaswamy")
      .replaceAll("{{survey_no}}", sampleRecipient.survey_no || "142/3B")
      .replaceAll("{{village}}", sampleRecipient.village || filterVillage || "Perur")
      .replaceAll("{{project_id}}", sampleRecipient.project_id || filterProject || "PRJ-TN-CBE-001")
      .replaceAll("{{amount}}", "Rs. 18,50,000")
      .replaceAll("{{date}}", new Date(Date.now() + 5 * 86400000).toLocaleDateString("en-IN"))
      .replaceAll("{{ref_no}}", `TN-${dist.slice(0, 3).toUpperCase()}-2026-AWD`);
  };

  // Bulk SMS Transmission Trigger
  const handleTransmitBulkSMS = async () => {
    setBulkSending(true);
    setSendResult(null);
    try {
      const selectedTpl = templates.find(t => t.id === selectedTemplateId);
      const payload = {
        district: dist,
        project_id: filterProject,
        taluk: filterTaluk,
        village: filterVillage,
        status: filterStatus,
        template_name: selectedTpl ? selectedTpl.title : "Custom Broadcast",
        message_text: messageText
      };
      const res = await api("/api/sms/bulk-send", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      setSendResult({
        success: true,
        message: res.message,
        summary: res.summary
      });
      setShowConfirmModal(false);
      setConfirmAgreed(false);
      EventBus.dispatch();
      if (tab === "history") loadHistory();
    } catch (err) {
      setSendResult({
        success: false,
        message: err.message || "Failed to execute bulk SMS transmission."
      });
      setShowConfirmModal(false);
    } finally {
      setBulkSending(false);
    }
  };

  // Single SMS Send Trigger
  const handleSendSingle = async (e) => {
    e.preventDefault();
    if (!/^[6-9]\d{9}$/.test(singlePhone.trim())) {
      setSingleResult({ success: false, message: "Please enter a valid 10-digit Indian mobile number (starts with 6, 7, 8, or 9)." });
      return;
    }
    setSingleSending(true);
    setSingleResult(null);
    try {
      const payload = {
        district: dist,
        recipient_phone: singlePhone.trim(),
        recipient_name: singleName.trim() || "Landowner",
        project_id: singleProject.trim() || undefined,
        message: singleMessage.trim(),
        template: "Direct Landowner Notice"
      };
      const res = await api("/api/sms/send", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      setSingleResult({
        success: true,
        message: `SMS successfully transmitted to +91 ${singlePhone} (Gateway Status: ${res.status}, Gateway Ref: ${res.gateway_ref || res.sms_id})`
      });
      setSinglePhone("");
      setSingleName("");
      setSingleSurveyNo("");
      setSingleMessage("");
      EventBus.dispatch();
      if (tab === "history") loadHistory();
    } catch (err) {
      setSingleResult({
        success: false,
        message: err.message || "Failed to send single SMS."
      });
    } finally {
      setSingleSending(false);
    }
  };

  const charCount = messageText.length;
  const smsSegments = Math.ceil(charCount / 160) || 1;
  const charsRemaining = 160 * smsSegments - charCount;

  return (
    <>
      {/* ── Top Header with District Badge & SMPP Gateway Status ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: "10px", fontSize: "1.45rem", color: "#0f172a" }}>
            <span>📱 SMPP SMS Notification Centre</span>
          </h2>
          <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>
            Official Statutory Communication Gateway for Affected Landowners & Beneficiaries
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {/* Active District Scope Badge */}
          <div style={{
            background: "#0f2f44",
            color: "#66d2c8",
            border: "1px solid #1e4963",
            padding: "6px 14px",
            borderRadius: "20px",
            fontSize: "12.5px",
            fontWeight: 700,
            display: "inline-flex",
            alignItems: "center",
            gap: "6px"
          }}>
            <span>🏛️ {dist} District Scope Active</span>
            <span style={{ fontSize: "10px", background: "#1b5264", color: "#ffffff", padding: "2px 6px", borderRadius: "10px" }}>Secured</span>
          </div>

          {/* SMPP Gateway Status Badge */}
          {health?.gateway_mode === "SMPP_LIVE" ? (
            <div style={{
              background: "#dcfce7",
              color: "#166534",
              border: "1px solid #86efac",
              padding: "6px 12px",
              borderRadius: "20px",
              fontSize: "12.5px",
              fontWeight: 700,
              display: "inline-flex",
              alignItems: "center",
              gap: "6px"
            }}>
              <span>🟢 SMPP Gateway: LIVE v3.4</span>
              <span style={{ fontSize: "10.5px", color: "#15803d" }}>({health?.smpp_host || "Connected"})</span>
            </div>
          ) : (
            <div style={{
              background: "#e0f2fe",
              color: "#0369a1",
              border: "1px solid #7dd3fc",
              padding: "6px 12px",
              borderRadius: "20px",
              fontSize: "12.5px",
              fontWeight: 700,
              display: "inline-flex",
              alignItems: "center",
              gap: "6px"
            }}>
              <span>🔵 SMS Gateway: DEMO MODE</span>
              <span style={{ fontSize: "10.5px", color: "#0284c7" }}>(Safe Simulation)</span>
            </div>
          )}
        </div>
      </div>

      {/* ── 6 Overview KPI Cards ── */}
      <Panel title={`SMS Communications Performance Overview · ${dist}`}>
        <div className="cards">
          <div className="metric">
            <span>📱 Total Sent</span>
            <b>{stats?.total_sent ?? 0}</b>
          </div>
          <div className="metric">
            <span>📅 Sent Today</span>
            <b style={{ color: "#0369a1" }}>{stats?.sent_today ?? 0}</b>
          </div>
          <div className="metric" style={{ borderLeft: "4px solid #10b981" }}>
            <span>📨 Delivered</span>
            <b style={{ color: "#10b981" }}>{stats?.delivered ?? 0}</b>
          </div>
          <div className="metric" style={{ borderLeft: "4px solid #f59e0b" }}>
            <span>⏳ Pending / In-Flight</span>
            <b style={{ color: "#f59e0b" }}>{stats?.pending ?? 0}</b>
          </div>
          <div className="metric" style={{ borderLeft: "4px solid #ef4444" }}>
            <span>❌ Failed</span>
            <b style={{ color: "#ef4444" }}>{stats?.failed ?? 0}</b>
          </div>
          <div className="metric" style={{ borderLeft: "4px solid #0f766e" }}>
            <span>📊 Delivery Rate</span>
            <b style={{ color: "#0f766e" }}>{stats?.delivery_rate ?? "0%"}</b>
          </div>
          <div className="metric">
            <span>👥 District Landowners</span>
            <b>{stats?.total_district_parcels ?? 0}</b>
          </div>
        </div>
      </Panel>

      {/* ── Notification / Result Banner ── */}
      {sendResult && (
        <div style={{
          padding: "14px 18px",
          marginBottom: "18px",
          borderRadius: "8px",
          background: sendResult.success ? "#dcfce7" : "#fee2e2",
          border: sendResult.success ? "1px solid #86efac" : "1px solid #fca5a5",
          color: sendResult.success ? "#166534" : "#991b1b",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}>
          <div>
            <b>{sendResult.success ? "✓ Transmission Successful: " : "✗ Transmission Failed: "}</b>
            {sendResult.message}
            {sendResult.summary && (
              <span style={{ display: "block", fontSize: "12px", marginTop: "4px", color: "#14532d" }}>
                Total Target: {sendResult.summary.total_recipients} | Transmitted: {sendResult.summary.sent_count} | Skipped (Invalid/No Phone): {sendResult.summary.skipped_count}
              </span>
            )}
          </div>
          <button
            style={{ background: "transparent", border: "none", cursor: "pointer", fontWeight: 700, fontSize: "16px", color: "inherit" }}
            onClick={() => setSendResult(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Navigation Tabs ── */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "2px solid #e2e8f0", marginBottom: "20px" }}>
        <button
          style={{
            padding: "10px 20px",
            border: "none",
            borderBottom: tab === "compose" ? "3px solid #0f766e" : "3px solid transparent",
            background: tab === "compose" ? "#f0fdfa" : "transparent",
            color: tab === "compose" ? "#0f766e" : "#64748b",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
            borderRadius: "6px 6px 0 0"
          }}
          onClick={() => setTab("compose")}
        >
          📤 Compose & Bulk SMS
        </button>
        <button
          style={{
            padding: "10px 20px",
            border: "none",
            borderBottom: tab === "history" ? "3px solid #0f766e" : "3px solid transparent",
            background: tab === "history" ? "#f0fdfa" : "transparent",
            color: tab === "history" ? "#0f766e" : "#64748b",
            fontWeight: 700,
            fontSize: "14px",
            cursor: "pointer",
            borderRadius: "6px 6px 0 0"
          }}
          onClick={() => setTab("history")}
        >
          📜 SMS Delivery History & Audit Trail
        </button>
        {isStateOrAdmin && (
          <button
            style={{
              padding: "10px 20px",
              border: "none",
              borderBottom: tab === "state_view" ? "3px solid #0f766e" : "3px solid transparent",
              background: tab === "state_view" ? "#f0fdfa" : "transparent",
              color: tab === "state_view" ? "#0f766e" : "#64748b",
              fontWeight: 700,
              fontSize: "14px",
              cursor: "pointer",
              borderRadius: "6px 6px 0 0"
            }}
            onClick={() => setTab("state_view")}
          >
            🌐 State-Wide SMS Comparison (5 Districts)
          </button>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {/* TAB 1: COMPOSE & BULK TRANSMISSION                                     */}
      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {tab === "compose" && (
        <>
          {/* Sub-mode selector */}
          <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
            <button
              style={{
                padding: "8px 16px",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: 600,
                border: subMode === "bulk" ? "2px solid #0f766e" : "1px solid #cbd5e1",
                background: subMode === "bulk" ? "#0f766e" : "#ffffff",
                color: subMode === "bulk" ? "#ffffff" : "#334155",
                cursor: "pointer"
              }}
              onClick={() => setSubMode("bulk")}
            >
              📢 Broadcast / Bulk SMS by Project & Filters
            </button>
            <button
              style={{
                padding: "8px 16px",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: 600,
                border: subMode === "single" ? "2px solid #0f766e" : "1px solid #cbd5e1",
                background: subMode === "single" ? "#0f766e" : "#ffffff",
                color: subMode === "single" ? "#ffffff" : "#334155",
                cursor: "pointer"
              }}
              onClick={() => setSubMode("single")}
            >
              👤 Individual Landowner SMS Notice
            </button>
          </div>

          {subMode === "bulk" ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "20px" }}>
              {/* Recipient Filter Box */}
              <Panel title={`1. Define Target Landowners in ${dist}`}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "15px", marginBottom: "16px" }}>
                  <label style={{ display: "block" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Project</span>
                    <select
                      value={filterProject}
                      onChange={e => setFilterProject(e.target.value)}
                      style={{ width: "100%", padding: "8px 10px", marginTop: "4px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                    >
                      <option value="">-- All Projects in {dist} --</option>
                      {projectList.map(p => (
                        <option key={p.project_id} value={p.project_id}>
                          {p.project_id} - {p.project_name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label style={{ display: "block" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Taluk</span>
                    <input
                      placeholder="e.g. Coimbatore South (Optional)"
                      value={filterTaluk}
                      onChange={e => setFilterTaluk(e.target.value)}
                      style={{ width: "100%", padding: "8px 10px", marginTop: "4px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                    />
                  </label>

                  <label style={{ display: "block" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Village</span>
                    <input
                      placeholder="e.g. Perur (Optional)"
                      value={filterVillage}
                      onChange={e => setFilterVillage(e.target.value)}
                      style={{ width: "100%", padding: "8px 10px", marginTop: "4px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                    />
                  </label>

                  <label style={{ display: "block" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Acquisition Stage / Status</span>
                    <select
                      value={filterStatus}
                      onChange={e => setFilterStatus(e.target.value)}
                      style={{ width: "100%", padding: "8px 10px", marginTop: "4px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                    >
                      <option value="">-- All Stages / Statuses --</option>
                      <option value="Preliminary Notification">Preliminary Notification (Sec 11)</option>
                      <option value="Joint Measurement Completed">Joint Measurement Completed</option>
                      <option value="Declaration">Declaration (Sec 19)</option>
                      <option value="Award Enquiry Scheduled">Award Enquiry Scheduled</option>
                      <option value="Award Passed">Award Passed</option>
                      <option value="Compensation Pending">Compensation Pending</option>
                      <option value="Compensation Disbursed">Compensation Disbursed</option>
                      <option value="Possession Taken">Possession Taken</option>
                    </select>
                  </label>
                </div>

                {/* Live Recipient Metrics Banner */}
                <div style={{
                  padding: "14px 18px",
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "12px"
                }}>
                  <div style={{ display: "flex", gap: "20px", flexWrap: "wrap" }}>
                    <div>
                      <span style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>Total Matching Parcels</span>
                      <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#0f172a" }}>
                        {recipientLoading ? "..." : (recipientData?.total_parcels ?? 0)}
                      </div>
                    </div>
                    <div style={{ borderLeft: "2px solid #cbd5e1", paddingLeft: "15px" }}>
                      <span style={{ fontSize: "11px", color: "#166534", textTransform: "uppercase", fontWeight: 700 }}>Valid Mobile (Recipients)</span>
                      <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#166534" }}>
                        {recipientLoading ? "..." : (recipientData?.valid_mobile_count ?? 0)}
                      </div>
                    </div>
                    <div style={{ borderLeft: "2px solid #cbd5e1", paddingLeft: "15px" }}>
                      <span style={{ fontSize: "11px", color: "#991b1b", textTransform: "uppercase", fontWeight: 700 }}>Missing Mobile</span>
                      <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#991b1b" }}>
                        {recipientLoading ? "..." : (recipientData?.missing_mobile_count ?? 0)}
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    style={{
                      background: "#ffffff",
                      border: "1px solid #cbd5e1",
                      borderRadius: "6px",
                      padding: "6px 12px",
                      fontSize: "12.5px",
                      fontWeight: 600,
                      color: "#334155",
                      cursor: "pointer"
                    }}
                    onClick={() => setShowRecipientList(!showRecipientList)}
                  >
                    {showRecipientList ? "▲ Hide Landowner List" : `▼ Inspect Landowner List (${recipientData?.recipients?.length || 0})`}
                  </button>
                </div>

                {recipientData?.missing_mobile_count > 0 && (
                  <div style={{ fontSize: "12px", color: "#b45309", marginTop: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>⚠️</span>
                    <span>Note: {recipientData.missing_mobile_count} parcel(s) have no registered phone number and will be automatically bypassed to protect delivery integrity.</span>
                  </div>
                )}

                {/* Inspect Recipient Drawer */}
                {showRecipientList && recipientData?.recipients && (
                  <div style={{ marginTop: "15px", maxHeight: "260px", overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: "6px" }}>
                    <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse" }}>
                      <thead style={{ background: "#f1f5f9", position: "sticky", top: 0 }}>
                        <tr>
                          <th style={{ padding: "8px 10px", textAlign: "left" }}>Landowner</th>
                          <th style={{ padding: "8px 10px", textAlign: "left" }}>Survey No</th>
                          <th style={{ padding: "8px 10px", textAlign: "left" }}>Village</th>
                          <th style={{ padding: "8px 10px", textAlign: "left" }}>Taluk</th>
                          <th style={{ padding: "8px 10px", textAlign: "left" }}>Mobile</th>
                          <th style={{ padding: "8px 10px", textAlign: "left" }}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {recipientData.recipients.slice(0, 30).map((r, idx) => (
                          <tr key={idx} style={{ borderBottom: "1px solid #f1f5f9" }}>
                            <td style={{ padding: "6px 10px", fontWeight: 600 }}>{r.owner_name || r.owner_reference}</td>
                            <td style={{ padding: "6px 10px" }}>{r.survey_no}</td>
                            <td style={{ padding: "6px 10px" }}>{r.village}</td>
                            <td style={{ padding: "6px 10px" }}>{r.taluk}</td>
                            <td style={{ padding: "6px 10px", color: "#166534", fontWeight: 700 }}>
                              +91 {r.mobile_number ? `${r.mobile_number.slice(0, 2)}****${r.mobile_number.slice(-4)}` : "None"}
                            </td>
                            <td style={{ padding: "6px 10px" }}>{r.acquisition_status || "Active"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Panel>

              {/* Message Composer Box */}
              <Panel title="2. Select Template & Compose Message">
                <div style={{ marginBottom: "15px" }}>
                  <label style={{ display: "block" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>
                      Government Standard Template (10 Official Pre-Approved Notices)
                    </span>
                    <select
                      value={selectedTemplateId}
                      onChange={e => handleSelectTemplate(e.target.value)}
                      style={{ width: "100%", padding: "9px 12px", marginTop: "4px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "13px" }}
                    >
                      <option value="">-- Custom Notice or Select Pre-Approved Template --</option>
                      {templates.map(t => (
                        <option key={t.id} value={t.id}>
                          [{t.id}] {t.title} ({t.category})
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                {/* Helper chips for dynamic placeholders */}
                <div style={{ marginBottom: "10px" }}>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
                    Click to Insert Dynamic Landowner Tags:
                  </span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {[
                      ["{{owner_name}}", "Landowner Name"],
                      ["{{survey_no}}", "Survey Number"],
                      ["{{village}}", "Village"],
                      ["{{project_id}}", "Project ID"],
                      ["{{amount}}", "Compensation Amount"],
                      ["{{date}}", "Notice Date"],
                      ["{{ref_no}}", "Statutory Ref No"]
                    ].map(([tag, label]) => (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => insertPlaceholder(tag)}
                        style={{
                          background: "#e2e8f0",
                          border: "none",
                          borderRadius: "14px",
                          padding: "4px 10px",
                          fontSize: "11.5px",
                          fontWeight: 600,
                          color: "#1e293b",
                          cursor: "pointer"
                        }}
                      >
                        + {label} ({tag})
                      </button>
                    ))}
                  </div>
                </div>

                {/* Textarea */}
                <textarea
                  rows={5}
                  value={messageText}
                  onChange={e => setMessageText(e.target.value)}
                  placeholder="Enter official SMS message content to broadcast to affected citizens..."
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    padding: "12px",
                    border: "1px solid #cbd5e1",
                    borderRadius: "6px",
                    fontSize: "13.5px",
                    fontFamily: "inherit",
                    lineHeight: "1.5"
                  }}
                />

                {/* Character & Segment Counter */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "6px", fontSize: "12px", color: "#64748b" }}>
                  <div>
                    <b>{charCount}</b> characters | <b>{smsSegments}</b> SMS segment(s)
                    {charCount > 0 && <span> ({charsRemaining} chars remaining in current segment)</span>}
                  </div>
                  <div>
                    <span style={{ color: "#0f766e", fontWeight: 600 }}>Standard SMPP GSM 7-bit Encoding</span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "18px" }}>
                  <button
                    type="button"
                    style={{
                      padding: "9px 16px",
                      background: "#ffffff",
                      border: "1px solid #cbd5e1",
                      borderRadius: "6px",
                      fontSize: "13px",
                      fontWeight: 600,
                      cursor: "pointer",
                      color: "#334155"
                    }}
                    onClick={() => setShowPreviewModal(true)}
                    disabled={!messageText.trim()}
                  >
                    📱 Preview Mobile View
                  </button>

                  <button
                    type="button"
                    className="primary"
                    style={{
                      padding: "9px 20px",
                      borderRadius: "6px",
                      fontSize: "13px",
                      fontWeight: 700,
                      cursor: "pointer",
                      background: "#0f766e",
                      color: "#ffffff",
                      border: "none",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px"
                    }}
                    disabled={!messageText.trim() || (recipientData?.valid_mobile_count || 0) === 0}
                    onClick={() => {
                      setConfirmAgreed(false);
                      setShowConfirmModal(true);
                    }}
                  >
                    <span>📤 Transmit Bulk SMS</span>
                    <span>({recipientData?.valid_mobile_count || 0} Citizens)</span>
                  </button>
                </div>
              </Panel>
            </div>
          ) : (
            /* Individual Landowner SMS Form */
            <Panel title={`Single Citizen Direct SMS Notification · ${dist}`}>
              <form onSubmit={handleSendSingle} style={{ maxWidth: "680px" }}>
                {singleResult && (
                  <div style={{
                    padding: "10px 14px",
                    marginBottom: "14px",
                    borderRadius: "6px",
                    background: singleResult.success ? "#dcfce7" : "#fee2e2",
                    color: singleResult.success ? "#166534" : "#991b1b",
                    fontSize: "13px",
                    fontWeight: 600
                  }}>
                    {singleResult.message}
                  </div>
                )}

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", marginBottom: "14px" }}>
                  <label style={{ display: "block" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Landowner Mobile Number* (10 Digits)</span>
                    <input
                      required
                      placeholder="e.g. 9876543210"
                      value={singlePhone}
                      onChange={e => setSinglePhone(e.target.value)}
                      style={{ width: "100%", padding: "8px 10px", marginTop: "4px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                    />
                  </label>

                  <label style={{ display: "block" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Landowner Name</span>
                    <input
                      placeholder="e.g. M. Ramaswamy"
                      value={singleName}
                      onChange={e => setSingleName(e.target.value)}
                      style={{ width: "100%", padding: "8px 10px", marginTop: "4px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                    />
                  </label>

                  <label style={{ display: "block" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Survey Number (Optional)</span>
                    <input
                      placeholder="e.g. 142/3B"
                      value={singleSurveyNo}
                      onChange={e => setSingleSurveyNo(e.target.value)}
                      style={{ width: "100%", padding: "8px 10px", marginTop: "4px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                    />
                  </label>

                  <label style={{ display: "block" }}>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Project ID (Optional)</span>
                    <input
                      placeholder="e.g. PRJ-TN-CBE-001"
                      value={singleProject}
                      onChange={e => setSingleProject(e.target.value)}
                      style={{ width: "100%", padding: "8px 10px", marginTop: "4px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                    />
                  </label>
                </div>

                <label style={{ display: "block", marginBottom: "14px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569" }}>Message Content*</span>
                  <textarea
                    required
                    rows={4}
                    value={singleMessage}
                    onChange={e => setSingleMessage(e.target.value)}
                    placeholder="Enter statutory notice text for this specific citizen..."
                    style={{ width: "100%", boxSizing: "border-box", padding: "10px", marginTop: "4px", border: "1px solid #cbd5e1", borderRadius: "6px", fontFamily: "inherit" }}
                  />
                  <div style={{ fontSize: "11.5px", color: "#64748b", marginTop: "4px" }}>
                    {singleMessage.length} characters ({Math.ceil(singleMessage.length / 160) || 1} segment)
                  </div>
                </label>

                <button
                  type="submit"
                  disabled={singleSending}
                  style={{
                    padding: "9px 20px",
                    background: "#0f766e",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: "6px",
                    fontWeight: 700,
                    cursor: "pointer",
                    fontSize: "13px"
                  }}
                >
                  {singleSending ? "Transmitting..." : "Send Individual SMS"}
                </button>
              </form>
            </Panel>
          )}
        </>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {/* TAB 2: SMS HISTORY & DELIVERY AUDIT                                    */}
      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {tab === "history" && (
        <Panel title={`SMS Delivery Log & Statutory Audit Register · ${dist}`}>
          {/* Filters Bar */}
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginBottom: "16px", alignItems: "center" }}>
            <input
              placeholder="Search by phone, name, survey no..."
              value={historySearch}
              onChange={e => setHistorySearch(e.target.value)}
              style={{ padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "13px", minWidth: "220px", flex: "1" }}
            />

            <select
              value={historyStatus}
              onChange={e => setHistoryStatus(e.target.value)}
              style={{ padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "13px" }}
            >
              <option value="">All Delivery Statuses</option>
              <option value="Delivered">Delivered</option>
              <option value="Sent">Sent / In Flight</option>
              <option value="Pending">Pending</option>
              <option value="Failed">Failed</option>
            </select>

            <select
              value={historyType}
              onChange={e => setHistoryType(e.target.value)}
              style={{ padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "13px" }}
            >
              <option value="">All Notification Types</option>
              <option value="Bulk Broadcast">Bulk Broadcast</option>
              <option value="Individual">Individual</option>
              <option value="Workflow Trigger">Workflow Trigger</option>
            </select>

            <button
              style={{ padding: "8px 14px", background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "13px", fontWeight: 600, cursor: "pointer" }}
              onClick={loadHistory}
            >
              🔄 Refresh
            </button>
          </div>

          {/* Table */}
          {historyLoading ? (
            <p>Loading delivery history records...</p>
          ) : !historyData?.logs?.length ? (
            <p style={{ color: "#64748b", padding: "20px 0", textAlign: "center" }}>No SMS records found matching the filter criteria.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date & Time</th>
                    <th>Recipient</th>
                    <th>Survey No / Village</th>
                    <th>Project</th>
                    <th>Type</th>
                    <th>Message</th>
                    <th>Gateway Status</th>
                    <th>Operator</th>
                    <th>Ref ID</th>
                  </tr>
                </thead>
                <tbody>
                  {historyData.logs.map(log => {
                    let statusBadge;
                    if (log.status === "Delivered") {
                      statusBadge = <span style={{ background: "#dcfce7", color: "#166534", padding: "3px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 700 }}>✓ Delivered</span>;
                    } else if (log.status === "Sent" || log.status === "Submitted") {
                      statusBadge = <span style={{ background: "#e0f2fe", color: "#0369a1", padding: "3px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 700 }}>↗ Submitted</span>;
                    } else if (log.status === "Pending") {
                      statusBadge = <span style={{ background: "#fef3c7", color: "#b45309", padding: "3px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 700 }}>⏳ Pending</span>;
                    } else {
                      statusBadge = <span style={{ background: "#fee2e2", color: "#991b1b", padding: "3px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 700 }}>✗ Failed</span>;
                    }

                    return (
                      <tr key={log.id}>
                        <td style={{ whiteSpace: "nowrap", fontSize: "12px" }}>
                          {log.created_at ? new Date(log.created_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" }) : "-"}
                        </td>
                        <td>
                          <b>{log.recipient_name || "Citizen"}</b>
                          <div style={{ fontSize: "11.5px", color: "#0f766e", fontWeight: 600 }}>
                            +91 {log.recipient_phone}
                          </div>
                        </td>
                        <td style={{ fontSize: "12px" }}>
                          {log.survey_no ? `Survey ${log.survey_no}` : "-"}
                          {log.village && <span style={{ display: "block", color: "#64748b" }}>{log.village}</span>}
                        </td>
                        <td style={{ fontSize: "12px" }}>{log.project_id || "District-Wide"}</td>
                        <td style={{ fontSize: "12px" }}>{log.message_type || log.template || "General"}</td>
                        <td style={{ maxWidth: "240px" }}>
                          <div style={{ fontSize: "12px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {log.message}
                          </div>
                          <button
                            type="button"
                            onClick={() => setSelectedLogMessage(log)}
                            style={{ background: "transparent", border: "none", color: "#0284c7", fontSize: "11px", cursor: "pointer", padding: 0, textDecoration: "underline" }}
                          >
                            View Full
                          </button>
                        </td>
                        <td>{statusBadge}</td>
                        <td style={{ fontSize: "11.5px", color: "#64748b" }}>{log.created_by || "system"}</td>
                        <td style={{ fontSize: "11px", color: "#94a3b8", fontFamily: "monospace" }}>
                          {log.gateway_ref ? log.gateway_ref.slice(0, 10) + "..." : log.id}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {/* TAB 3: STATE-WIDE AGGREGATED COMPARISON (FOR STATE / ADMIN)            */}
      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {tab === "state_view" && isStateOrAdmin && (
        <Panel title="🌐 State-Wide SMS Notification Center Summary (All 5 Districts)">
          <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "16px" }}>
            Aggregated multi-district communication pipeline across Coimbatore, Tiruppur, Namakkal, Erode, and Salem.
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>District</th>
                  <th>Total SMS Sent</th>
                  <th>Delivered</th>
                  <th>Pending</th>
                  <th>Failed</th>
                  <th>Delivery Rate</th>
                  <th>Total Landowners</th>
                  <th>Covered with Mobile</th>
                </tr>
              </thead>
              <tbody>
                {(stateStats?.districts || []).map(ds => (
                  <tr key={ds.district}>
                    <td style={{ fontWeight: 700, color: "#0f766e" }}>{ds.district}</td>
                    <td><b>{ds.total_sent}</b></td>
                    <td style={{ color: "#166534", fontWeight: 700 }}>{ds.delivered}</td>
                    <td style={{ color: "#b45309" }}>{ds.pending}</td>
                    <td style={{ color: "#991b1b" }}>{ds.failed}</td>
                    <td><b>{ds.delivery_rate}</b></td>
                    <td>{ds.total_parcels}</td>
                    <td style={{ color: "#0f766e", fontWeight: 600 }}>{ds.valid_mobile_parcels}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {/* ── Realistic Mobile Preview Modal ── */}
      {showPreviewModal && (
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
            borderRadius: "24px",
            width: "360px",
            boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
            overflow: "hidden",
            border: "8px solid #1e293b"
          }}>
            {/* Phone Top Notch Bar */}
            <div style={{ background: "#0f172a", color: "#ffffff", padding: "10px 18px", fontSize: "11px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>9:41 AM</span>
              <span style={{ fontSize: "10px", background: "#334155", padding: "2px 8px", borderRadius: "8px" }}>TNSURVI-GOV</span>
              <span>📶 5G 100%</span>
            </div>
            
            {/* Chat header */}
            <div style={{ padding: "12px 16px", background: "#f8fafc", borderBottom: "1px solid #e2e8f0", display: "flex", alignItems: "center", gap: "10px" }}>
              <div style={{ width: "36px", height: "36px", borderRadius: "50%", background: "#0f766e", color: "#ffffff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: "14px" }}>
                TN
              </div>
              <div>
                <b style={{ fontSize: "13px", color: "#0f172a" }}>Govt of Tamil Nadu</b>
                <div style={{ fontSize: "10.5px", color: "#64748b" }}>Land Acquisition Notice (SMPP)</div>
              </div>
            </div>

            {/* Bubble Area */}
            <div style={{ padding: "20px 16px", minHeight: "260px", background: "#e2e8f0" }}>
              <div style={{
                background: "#ffffff",
                padding: "14px",
                borderRadius: "14px 14px 14px 2px",
                boxShadow: "0 2px 6px rgba(0,0,0,0.08)",
                fontSize: "13px",
                lineHeight: "1.5",
                color: "#1e293b"
              }}>
                {getSampleRenderedMessage(messageText)}
                <div style={{ fontSize: "10px", color: "#94a3b8", textAlign: "right", marginTop: "6px" }}>
                  Just now · Delivered
                </div>
              </div>
            </div>

            {/* Footer */}
            <div style={{ padding: "12px 16px", background: "#ffffff", textAlign: "center", borderTop: "1px solid #e2e8f0" }}>
              <button
                type="button"
                style={{ padding: "8px 24px", background: "#0f766e", color: "#ffffff", border: "none", borderRadius: "6px", fontWeight: 600, fontSize: "13px", cursor: "pointer" }}
                onClick={() => setShowPreviewModal(false)}
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Bulk Send Statutory Confirmation Modal ── */}
      {showConfirmModal && (
        <div style={{
          position: "fixed",
          top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(15, 23, 42, 0.8)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 9999,
          padding: "20px"
        }}>
          <div style={{
            background: "#ffffff",
            borderRadius: "12px",
            maxWidth: "560px",
            width: "100%",
            boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.3)",
            overflow: "hidden"
          }}>
            {/* Modal Header */}
            <div style={{ background: "#0f2f44", color: "#ffffff", padding: "16px 20px", display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "20px" }}>⚠️</span>
              <div>
                <b style={{ fontSize: "15px", display: "block" }}>Confirm Statutory SMS Broadcast Transmission</b>
                <span style={{ fontSize: "12px", color: "#66d2c8" }}>{dist} District Administration</span>
              </div>
            </div>

            {/* Modal Content */}
            <div style={{ padding: "20px" }}>
              <div style={{ background: "#f8fafc", padding: "12px 16px", borderRadius: "8px", border: "1px solid #e2e8f0", marginBottom: "16px", fontSize: "13px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "130px 1fr", gap: "8px" }}>
                  <span style={{ color: "#64748b" }}>District Scope:</span>
                  <b>{dist}</b>
                  <span style={{ color: "#64748b" }}>Target Landowners:</span>
                  <b style={{ color: "#166534" }}>{recipientData?.valid_mobile_count || 0} Registered Mobile Numbers</b>
                  <span style={{ color: "#64748b" }}>Target Project:</span>
                  <b>{filterProject || "All Projects in District"}</b>
                  <span style={{ color: "#64748b" }}>Bypassed Parcels:</span>
                  <span style={{ color: "#991b1b" }}>{recipientData?.missing_mobile_count || 0} (No registered phone)</span>
                </div>
              </div>

              <div style={{ marginBottom: "16px" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "#475569", display: "block", marginBottom: "4px" }}>
                  Message Sample Preview (Landowner View):
                </span>
                <div style={{ background: "#f1f5f9", padding: "10px 12px", borderRadius: "6px", fontSize: "12.5px", lineHeight: "1.4", color: "#334155" }}>
                  {getSampleRenderedMessage(messageText)}
                </div>
              </div>

              <label style={{ display: "flex", alignItems: "flex-start", gap: "10px", cursor: "pointer", fontSize: "12.5px", color: "#1e293b", userSelect: "none" }}>
                <input
                  type="checkbox"
                  checked={confirmAgreed}
                  onChange={e => setConfirmAgreed(e.target.checked)}
                  style={{ marginTop: "3px" }}
                />
                <span>
                  I certify that this official notification transmission is authorized under the Tamil Nadu Land Acquisition Act and has been verified for delivery by the District Authority.
                </span>
              </label>
            </div>

            {/* Modal Actions */}
            <div style={{ padding: "14px 20px", background: "#f8fafc", borderTop: "1px solid #e2e8f0", display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button
                type="button"
                style={{ padding: "8px 16px", background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "13px", fontWeight: 600, cursor: "pointer" }}
                onClick={() => setShowConfirmModal(false)}
                disabled={bulkSending}
              >
                Cancel
              </button>
              <button
                type="button"
                style={{
                  padding: "8px 20px",
                  background: confirmAgreed && !bulkSending ? "#0f766e" : "#94a3b8",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: 700,
                  cursor: confirmAgreed && !bulkSending ? "pointer" : "not-allowed"
                }}
                disabled={!confirmAgreed || bulkSending}
                onClick={handleTransmitBulkSMS}
              >
                {bulkSending ? "Transmitting SMS via SMPP..." : `Confirm & Transmit (${recipientData?.valid_mobile_count || 0} SMS)`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── View Full Message Modal ── */}
      {selectedLogMessage && (
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
          <div style={{ background: "#fff", borderRadius: "12px", maxWidth: "500px", width: "100%", padding: "20px", boxShadow: "0 20px 25px -5px rgba(0,0,0,0.3)" }}>
            <h3 style={{ margin: "0 0 12px 0", fontSize: "1.1rem" }}>SMS Delivery Details</h3>
            <div style={{ fontSize: "13px", marginBottom: "14px", lineHeight: "1.6" }}>
              <div><b>Recipient:</b> {selectedLogMessage.recipient_name} (+91 {selectedLogMessage.recipient_phone})</div>
              <div><b>Survey No:</b> {selectedLogMessage.survey_no || "N/A"} | <b>Village:</b> {selectedLogMessage.village || "N/A"}</div>
              <div><b>Project:</b> {selectedLogMessage.project_id || "District-Wide"}</div>
              <div><b>Status:</b> {selectedLogMessage.status}</div>
              <div><b>Gateway Ref:</b> <code style={{ fontSize: "11px" }}>{selectedLogMessage.gateway_ref || "None"}</code></div>
              <div><b>Operator:</b> {selectedLogMessage.created_by}</div>
              <div style={{ marginTop: "10px" }}>
                <b>Full Message:</b>
                <div style={{ background: "#f8fafc", padding: "10px", borderRadius: "6px", border: "1px solid #e2e8f0", marginTop: "4px" }}>
                  {selectedLogMessage.message}
                </div>
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <button
                type="button"
                style={{ padding: "7px 16px", background: "#0f766e", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontWeight: 600 }}
                onClick={() => setSelectedLogMessage(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

const ROUTE_PAGE_MAP = {
  "": "dashboard",
  "dashboard": "dashboard",
  "state-dashboard": "state_dashboard",
  "state_dashboard": "state_dashboard",
  "district-dashboard": "district_dashboard",
  "district_dashboard": "district_dashboard",
  "projects": "projects",
  "parcels": "parcels",
  "parcel-details": "parcel_details",
  "parcel_details": "parcel_details",
  "data-quality": "data_quality",
  "data_quality": "data_quality",
  "gis": "gis",
  "workflow": "workflow",
  "sla": "sla",
  "bottlenecks": "bottlenecks",
  "field": "field",
  "documents": "documents",
  "risk": "risk",
  "alerts": "alerts",
  "sms-centre": "sms_centre",
  "sms_centre": "sms_centre",
  "sms": "sms_centre",
  "analytics": "analytics",
  "intelligence": "intelligence",
  "reports": "reports",
  "grievances": "grievances",
  "rr": "rr",
  "ml": "ml",
  "users": "users",
  "audit": "audit",
  "citizen": "citizen_dash",
  "citizen_dash": "citizen_dash"
};

function getPageFromLocation() {
  if (typeof window === "undefined") return "dashboard";
  const path = window.location.pathname.replace(/^\/+|\/+$/g, "").toLowerCase();
  return ROUTE_PAGE_MAP[path] || null;
}

function getPathForPage(p) {
  const reverseMap = {
    dashboard: "/dashboard",
    state_dashboard: "/state-dashboard",
    district_dashboard: "/district-dashboard",
    projects: "/projects",
    parcels: "/parcels",
    parcel_details: "/parcel-details",
    data_quality: "/data-quality",
    gis: "/gis",
    workflow: "/workflow",
    sla: "/sla",
    bottlenecks: "/bottlenecks",
    field: "/field",
    documents: "/documents",
    risk: "/risk",
    alerts: "/alerts",
    sms_centre: "/sms-centre",
    analytics: "/analytics",
    intelligence: "/intelligence",
    reports: "/reports",
    grievances: "/grievances",
    rr: "/rr",
    ml: "/ml",
    users: "/users",
    audit: "/audit",
    citizen_dash: "/citizen"
  };
  return reverseMap[p] || `/${p}`;
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    console.warn("Application Section Notice:", error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <section className="panel">
          <div className="panel-head"><h2>⚠️ Section Display Notice</h2></div>
          <div style={{ padding: "16px", color: "#64748b" }}>
            <p>This section encountered a temporary issue. You can select another tab or try again.</p>
            <button className="btn" type="button" onClick={() => this.setState({ hasError: false, error: null })}>
              Try Again
            </button>
          </div>
        </section>
      );
    }
    return this.props.children;
  }
}

function App() {
  const [user, setUser] = useState(null);
  const initialPage = (typeof window !== "undefined" ? getPageFromLocation() : null) || "dashboard";
  const [page, setPageState] = useState(initialPage);
  const [lang, setLang] = useState("en");
  const [selected, setSelected] = useState(null);
  const [selectedDistrict, setSelectedDistrict] = useState("Coimbatore");
  const [tutorialOpen, setTutorialOpen] = useState(false);
  const [showWelcomePrompt, setShowWelcomePrompt] = useState(false);

  const setPage = (newPage, updateHistory = true) => {
    setPageState(newPage);
    if (updateHistory && typeof window !== "undefined") {
      const targetPath = getPathForPage(newPage);
      if (window.location.pathname !== targetPath) {
        window.history.pushState({ page: newPage }, "", targetPath);
      }
    }
  };

  useEffect(() => {
    const handlePopState = (e) => {
      const pageFromUrl = getPageFromLocation();
      if (pageFromUrl) {
        setPageState(pageFromUrl);
      } else if (e.state && e.state.page) {
        setPageState(e.state.page);
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const applyUserLogin = (u) => {
    setUser(u);
    if (u.district_scope) setSelectedDistrict(u.district_scope);
    else if (u.role === 'national_authority') setSelectedDistrict('all');
    else if (u.role === 'state_authority') setSelectedDistrict('all');
    else if (u.state_scope === 'Kerala') setSelectedDistrict('Palakkad');
    else setSelectedDistrict('Coimbatore');

    const urlPage = getPageFromLocation();
    if (urlPage) {
      setPage(urlPage);
    } else if (u.role === 'citizen') {
      setPage('citizen_dash');
    } else if (u.role === 'state_authority') {
      setPage('state_dashboard');
    } else if (u.role === 'district_authority') {
      setPage('district_dashboard');
    } else if (u.role === 'field_officer') {
      setPage('field');
    } else if (u.role === 'acquisition_officer') {
      setPage('projects');
    } else {
      setPage('dashboard');
    }
  };

  useEffect(() => {
    if (user) {
      const done = localStorage.getItem("landnexus_tour_completed");
      if (!done) {
        const timer = setTimeout(() => setShowWelcomePrompt(true), 800);
        return () => clearTimeout(timer);
      }
    }
  }, [user]);

  useEffect(() => {
    const token = localStorage.getItem("survi_token");
    if (token && token !== "undefined" && token !== "null") {
      api(AUTH_ME_PATH).then(u => {
        if (!u || !u.role) {
          localStorage.removeItem("survi_token");
          return;
        }
        applyUserLogin(u);
      }).catch(() => localStorage.removeItem("survi_token"));
    } else {
      localStorage.removeItem("survi_token");
    }
  }, []);

  if (!user) return <Login onLogin={applyUserLogin} />;

  let content = <Placeholder title={nav.find(x => x[0] === page)?.[1] || page} />;
  if (page === "dashboard") content = <Dashboard district={selectedDistrict} user={user} />;
  else if (page === "state_dashboard") content = <StateDashboard user={user} district={selectedDistrict} onSelectDistrict={setSelectedDistrict} />;
  else if (page === "district_dashboard") content = <DistrictDashboard district={selectedDistrict} user={user} go={x => { setSelected(x); setPage("workflow"); }} onOpenSMS={() => setPage("sms_centre")} />;
  else if (page === "projects") content = <Projects district={selectedDistrict} go={x => { setSelected(x); setPage("workflow"); }} />;
  else if (page === "parcels") content = (
    <Parcels 
      district={selectedDistrict} 
      onSelectParcel={p => { setSelected({ parcel_id: p.id, id: p.id, ...p }); setPage("parcel_details"); }} 
      go={x => { setSelected({ parcel_id: x.id || x.parcel_id, id: x.id || x.parcel_id, ...x }); setPage("parcel_details"); }} 
    />
  );
  else if (page === "gis") content = (
    <GIS 
      district={selectedDistrict} 
      user={user} 
      selectedParcel={selected}
      onNavigateParcel={p => { setSelected({ parcel_id: p.id || p.parcel_id, id: p.id || p.parcel_id, ...p }); setPage("parcel_details"); }} 
    />
  );
  else if (page === "ml") content = <ML />;
  else if (page === "citizen_dash") content = <CitizenDash lang={lang} user={user} />;
  else if (page === "workflow") content = <Workflow selected={selected} user={user} district={selectedDistrict} go={x => { setSelected(x); setPage(x.parcel_id ? "parcel_details" : "workflow"); }} />;
  else if (page === "parcel_details") content = (
    <ParcelDetails 
      selected={selected} 
      user={user} 
      onBack={() => setPage("parcels")} 
      onNavigateWorkflow={p => { setSelected(p); setPage("workflow"); }} 
      onNavigateDocuments={p => { setSelected(p); setPage("documents"); }} 
      onNavigateGIS={p => { setSelected(p); setPage("gis"); }} 
    />
  );
  else if (page === "sla") content = <SLA selected={selected} />;
  else if (page === "bottlenecks") content = <Bottlenecks district={selectedDistrict} go={x => { setSelected(x); setPage("workflow"); }} />;
  else if (page === "risk") content = <RiskIntelligence district={selectedDistrict} go={x => { setSelected(x); setPage(x.parcel_id ? "parcel_details" : "workflow"); }} />;
  else if (page === "alerts") content = <AlertsPage district={selectedDistrict} go={x => { setSelected(x); setPage(x.parcel_id ? "parcel_details" : "workflow"); }} />;
  else if (page === "analytics") content = <AnalyticsPage district={selectedDistrict} go={x => { setSelected(x); setPage("workflow"); }} />;
  else if (page === "reports") content = <Reports district={selectedDistrict} user={user} />;
  else if (page === "field") content = <FieldVerification user={user} district={selectedDistrict} go={x => { setSelected(x); setPage("documents"); }} onNavigateRR={x => { setSelected(x); if (x.district && (!user?.district_scope || user.district_scope.toLowerCase() === x.district.toLowerCase())) { setSelectedDistrict(x.district); } setPage("rr"); }} />;
  else if (page === "grievances") content = <Grievances district={selectedDistrict} user={user} />;
  else if (page === "rr") content = <RRPage district={selectedDistrict} user={user} selected={selected} onSelectCase={setSelected} />;
  else if (page === "documents") content = <DocumentsPage user={user} selected={selected} district={selectedDistrict} />;
  else if (page === "intelligence") content = <IntelligenceDashboard district={selectedDistrict} user={user} />;
  else if (page === "sms_centre") content = <SMSNotificationCentre district={selectedDistrict} user={user} go={x => { setSelected(x); setPage("workflow"); }} />;
  else if (page === "data_quality") content = <DataQualityPage district={selectedDistrict} user={user} onSelectParcel={p => { setSelected({ parcel_id: p.id, id: p.id, ...p }); setPage("parcel_details"); }} />;


  const allowedNav = nav.filter(n => {
    if (!user || !user.role) return true;
    if (user.role === "citizen") return ["citizen_dash", "grievances"].includes(n[0]);
    if (user.role === "state_authority") return !["citizen_dash", "users", "audit", "field"].includes(n[0]);
    if (user.role === "district_authority") return !["state_dashboard", "citizen_dash", "users", "audit", "ml", "intelligence"].includes(n[0]);
    if (user.role === "field_officer") return ["field", "rr", "parcels", "gis", "documents"].includes(n[0]);
    return n[0] !== "citizen_dash";
  });

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-header side-header" data-tutorial="sidebar-logo">
          <div className="logo">LAND<span>NEXUS</span></div>
          <div className="tag">SIH 26016 CORE</div>
        </div>
        <nav className="sidebar-nav nav-menu">
          {allowedNav.map(n => (
            <button 
              className={page === n[0] ? "nav active" : "nav"} 
              key={n[0]} 
              data-tutorial={`nav-${n[0]}`}
              onClick={() => setPage(n[0])}
            >
              {lang === "ta" ? tamil[n[1]] || n[1] : n[1]}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer side-bottom" data-tutorial="sidebar-footer">
          <button 
            className="nav" 
            style={{ 
              background: "rgba(6, 182, 212, 0.15)", 
              color: "#38bdf8", 
              border: "1px solid rgba(56, 189, 248, 0.35)",
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              marginBottom: "6px"
            }}
            onClick={() => setTutorialOpen(true)}
          >
            <span>🎮</span>
            <span>Guided Tour</span>
          </button>
          <button className="nav" onClick={() => setLang(lang === "en" ? "ta" : "en")}>English / தமிழ்</button>
          <button className="nav logout" onClick={() => { localStorage.removeItem("survi_token"); setUser(null); }}>Logout</button>
        </div>
      </aside>
      <main className="content main-content">
        <header>
          <div>
            <div className="eyebrow">
              {user?.role === "state_authority" 
                ? `${(user.state_scope || "STATE").toUpperCase()} LAND ACQUISITION & MONITORING AUTHORITY` 
                : user?.role === "citizen" 
                  ? "LANDNEXUS CITIZEN ACCESS PORTAL · TRANSPARENT LAND ACQUISITION"
                  : "TAMIL NADU DISTRICT LAND ACQUISITION & MONITORING AUTHORITY · 5-DISTRICT SCOPE"}
            </div>
            <h1>{lang === "ta" ? (tamil[nav.find(x => x[0] === page)?.[1]] || page) : (nav.find(x => x[0] === page)?.[1] || page)}</h1>
            <p>From land records to acquisition decisions — monitor, predict, explain and act.</p>
            
            {/* District / State Scope Bar */}
            {user.role !== "citizen" && (
              <div data-tutorial="scope-badge" style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "12px", flexWrap: "wrap" }}>
                {user.role === "state_authority" ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                    <div style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      background: "linear-gradient(135deg, #0f6c70 0%, #0d5457 100%)",
                      color: "#ffffff",
                      padding: "6px 14px",
                      borderRadius: "20px",
                      fontSize: "12px",
                      fontWeight: 700,
                      boxShadow: "0 2px 8px rgba(15,108,112,0.3)"
                    }}>
                      <span>🏛️</span>
                      <span>{user.state_scope || "Tamil Nadu"} State Authority</span>
                    </div>
                    <span style={{ fontSize: "11px", fontWeight: 800, textTransform: "uppercase", color: "#64748b", letterSpacing: "0.5px" }}>
                      Selected District:
                    </span>
                    <button
                      type="button"
                      onClick={() => setSelectedDistrict("all")}
                      style={{
                        background: selectedDistrict === "all" ? "#0f6c70" : "#ffffff",
                        color: selectedDistrict === "all" ? "#ffffff" : "#334155",
                        border: `1px solid ${selectedDistrict === "all" ? "#0f6c70" : "#cbd5e1"}`,
                        padding: "5px 12px",
                        borderRadius: "20px",
                        fontSize: "12px",
                        fontWeight: selectedDistrict === "all" ? 700 : 500,
                        cursor: "pointer",
                        transition: "all 0.15s ease-in-out",
                        boxShadow: selectedDistrict === "all" ? "0 2px 6px rgba(15,108,112,0.25)" : "none"
                      }}
                    >
                      🌐 All {user.state_scope || "State"} Districts
                    </button>
                    {((user.state_scope === "Kerala")
                      ? ["Palakkad", "Ernakulam", "Thrissur", "Thiruvananthapuram"]
                      : DISTRICTS
                    ).map(d => {
                      const isActive = selectedDistrict === d;
                      return (
                        <button
                          key={d}
                          type="button"
                          onClick={() => setSelectedDistrict(d)}
                          style={{
                            background: isActive ? "#0f6c70" : "#ffffff",
                            color: isActive ? "#ffffff" : "#334155",
                            border: `1px solid ${isActive ? "#0f6c70" : "#cbd5e1"}`,
                            padding: "5px 12px",
                            borderRadius: "20px",
                            fontSize: "12px",
                            fontWeight: isActive ? 700 : 500,
                            cursor: "pointer",
                            transition: "all 0.15s ease-in-out",
                            boxShadow: isActive ? "0 2px 6px rgba(15,108,112,0.25)" : "none"
                          }}
                        >
                          {d} {d === "Coimbatore" ? "★" : ""}
                        </button>
                      );
                    })}
                  </div>
                ) : user.district_scope || user.role === "district_authority" || user.role === "field_officer" ? (
                  <div style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    background: "linear-gradient(135deg, #0f6c70 0%, #0d5457 100%)",
                    color: "#ffffff",
                    padding: "6px 14px",
                    borderRadius: "20px",
                    fontSize: "12px",
                    fontWeight: 700,
                    letterSpacing: "0.3px",
                    boxShadow: "0 2px 8px rgba(15,108,112,0.3)"
                  }}>
                    <span>🔒</span>
                    <span>{user.district_scope || selectedDistrict} District (Locked Scope)</span>
                  </div>
                ) : (
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                    <div style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      background: "linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%)",
                      color: "#ffffff",
                      padding: "6px 14px",
                      borderRadius: "20px",
                      fontSize: "12px",
                      fontWeight: 700,
                      boxShadow: "0 2px 8px rgba(30,58,138,0.3)"
                    }}>
                      <span>🇮🇳</span>
                      <span>{user.role === "national_authority" ? "National Authority" : "Central Authority"}</span>
                    </div>
                    <span style={{ fontSize: "11px", fontWeight: 800, textTransform: "uppercase", color: "#64748b", letterSpacing: "0.5px" }}>
                      Scope:
                    </span>
                    {["All Districts", ...DISTRICTS, "Palakkad", "Ernakulam"].map(d => {
                      const val = d === "All Districts" ? "all" : d;
                      const isActive = selectedDistrict === val || (val === "all" && (selectedDistrict === "all" || selectedDistrict === "All Districts"));
                      return (
                        <button
                          key={d}
                          type="button"
                          onClick={() => setSelectedDistrict(val)}
                          style={{
                            background: isActive ? (val === "all" ? "#1e3a8a" : "#0f6c70") : "#ffffff",
                            color: isActive ? "#ffffff" : "#334155",
                            border: `1px solid ${isActive ? (val === "all" ? "#1e3a8a" : "#0f6c70") : "#cbd5e1"}`,
                            padding: "5px 12px",
                            borderRadius: "20px",
                            fontSize: "12px",
                            fontWeight: isActive ? 700 : 500,
                            cursor: "pointer",
                            transition: "all 0.15s ease-in-out",
                            boxShadow: isActive ? "0 2px 6px rgba(15,108,112,0.25)" : "none"
                          }}
                        >
                          {d === "All Districts" ? "🌐 Entire (National)" : d} {d === "Coimbatore" ? "★" : ""}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
          <div className="user-pill">{(user?.role || "user").replaceAll("_", " ")}<br /><small>{user?.email || ""}</small></div>
        </header>
        {selected && <div className="context-strip">Selected Context: {selected.project_id || selected.record_id || selected.survey_no} <button onClick={() => setSelected(null)}>×</button></div>}
        <ErrorBoundary>
          {content}
        </ErrorBoundary>
      </main>

      {/* ── First-Time Guided Tour Invitation Modal ── */}
      {showWelcomePrompt && (
        <div style={{
          position: "fixed",
          top: 0, left: 0, width: "100vw", height: "100vh",
          background: "rgba(15, 23, 42, 0.75)",
          backdropFilter: "blur(6px)",
          display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 99997, padding: "20px"
        }}>
          <div style={{
            background: "linear-gradient(145deg, #0f172a 0%, #1e293b 100%)",
            border: "1px solid #06b6d4",
            borderRadius: "16px",
            boxShadow: "0 20px 50px rgba(0,0,0,0.6), 0 0 30px rgba(6, 182, 212, 0.3)",
            maxWidth: "460px", width: "100%",
            padding: "28px 24px", color: "#f8fafc", textAlign: "center"
          }}>
            <div style={{ fontSize: "40px", marginBottom: "12px" }}>🎮</div>
            <div style={{ fontSize: "11px", fontWeight: 800, color: "#38bdf8", letterSpacing: "1px", textTransform: "uppercase" }}>
              INTERACTIVE ONBOARDING TOUR
            </div>
            <h2 style={{ margin: "8px 0 10px 0", fontSize: "22px", color: "#ffffff" }}>
              Welcome to LandNexus!
            </h2>
            <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: 1.6, margin: "0 0 20px 0" }}>
              Take a quick 60-second interactive guided tour customized for your role as <b>{(user.role || "Official").replace("_", " ")}</b> to master the interface and key decision tools.
            </p>
            <div style={{ display: "flex", gap: "10px" }}>
              <button
                type="button"
                onClick={() => {
                  setShowWelcomePrompt(false);
                  localStorage.setItem("landnexus_tour_completed", "true");
                }}
                style={{
                  flex: 1, padding: "10px",
                  background: "rgba(255,255,255,0.08)", color: "#cbd5e1",
                  border: "1px solid rgba(255,255,255,0.15)", borderRadius: "8px",
                  fontSize: "13px", fontWeight: 600, cursor: "pointer"
                }}
              >
                Skip for Now
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowWelcomePrompt(false);
                  setTutorialOpen(true);
                }}
                style={{
                  flex: 1.4, padding: "10px",
                  background: "linear-gradient(135deg, #06b6d4 0%, #0284c7 100%)", color: "#ffffff",
                  border: "none", borderRadius: "8px",
                  fontSize: "13px", fontWeight: 700, cursor: "pointer",
                  boxShadow: "0 4px 14px rgba(6, 182, 212, 0.4)",
                  display: "flex", alignItems: "center", justifyContent: "center", gap: "6px"
                }}
              >
                <span>Start Tour</span>
                <span>🚀</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Interactive Game-Style Tutorial Engine ── */}
      <TutorialEngine
        user={user}
        currentPage={page}
        onNavigate={p => setPage(p)}
        isOpen={tutorialOpen}
        onClose={() => setTutorialOpen(false)}
      />
    </div>
  );
}

export default App;
export { api, API, useData, Panel, Table, ActionButton, EventBus, DataPanel, RefreshButton, AlertTable };
