/**
 * LandNexus Interactive Onboarding Tutorial Steps
 * Role-tailored step journeys with target selectors, page navigation, 
 * game-style badges, actionable hints, and tooltip positioning.
 */

export const ROLE_STEPS = {
  district_authority: [
    {
      id: "dist_welcome",
      selector: '[data-tutorial="sidebar-logo"]',
      targetPage: "district_dashboard",
      title: "Welcome to LandNexus Command Center",
      badge: "MISSION BRIEFING 🏛️",
      description: "Welcome, District Collector & Land Acquisition Officer! LandNexus unifies statutory land acquisition workflows, GIS spatial verification, and AI decision intelligence into a single secure platform.",
      actionHint: "👉 Click 'Next Step →' to explore your command perimeter!",
      position: "right",
      spotlightPadding: 10
    },
    {
      id: "dist_scope",
      selector: '[data-tutorial="scope-badge"]',
      targetPage: "district_dashboard",
      title: "District Scope & Autonomous Perimeter",
      badge: "ACCESS GOVERNANCE 🔒",
      description: "Your session is locked to your jurisdiction (e.g., Coimbatore District). Real-time RBAC safeguards data integrity and cross-district boundary compliance.",
      actionHint: "👉 Notice your district lock indicator in the top header.",
      position: "bottom",
      spotlightPadding: 8
    },
    {
      id: "dist_dss",
      selector: '[data-tutorial="dss-center"]',
      targetPage: "district_dashboard",
      title: "AI Role-Based Decision Support (RB-DSS)",
      badge: "AI INTELLIGENCE 🤖",
      description: "Here is your AI Decision Support Radar. It computes deterministic risk indices (0-100), flags SLA delays, surfaces early warnings, and recommends policy interventions. Remember: AI Recommends — Authorized Officials Decide!",
      actionHint: "👉 Inspect the priority scores and early warning badges below.",
      position: "bottom",
      spotlightPadding: 12
    },
    {
      id: "dist_metrics",
      selector: '[data-tutorial="district-kpis"]',
      targetPage: "district_dashboard",
      title: "Operational KPIs & SLA Pulse",
      badge: "EXECUTIVE METRICS 📊",
      description: "Live operational metrics tracking Total Projects, Acquired Acres, Disbursed Direct Benefit Transfer (DBT) Compensation, and Pending Legal Disputes.",
      actionHint: "👉 Review real-time numbers synced with the district treasury.",
      position: "top",
      spotlightPadding: 10
    },
    {
      id: "dist_projects",
      selector: '[data-tutorial="nav-projects"]',
      targetPage: "projects",
      title: "Acquisition Project Portfolio",
      badge: "WORKFLOW ENGINE 📁",
      description: "Navigate all active district projects. Track statutory RFCTLARR Section 11 preliminary notifications, Section 19 declarations, and Section 23 compensation awards.",
      actionHint: "👉 Click 'Next' to see the projects overview or click the highlighted tab!",
      position: "right",
      spotlightPadding: 6
    },
    {
      id: "dist_gis",
      selector: '[data-tutorial="nav-gis"]',
      targetPage: "gis",
      title: "Cadastral GIS & Spatial Survey Map",
      badge: "GEOSPATIAL RADAR 🗺️",
      description: "Access high-resolution GIS cadastral boundaries, survey parcel overlays, environmental buffer zones, and drone survey imagery for spot-on ground truth verification.",
      actionHint: "👉 Explore spatial layers and boundary conflict detection.",
      position: "right",
      spotlightPadding: 6
    },
    {
      id: "dist_grievances",
      selector: '[data-tutorial="nav-grievances"]',
      targetPage: "grievances",
      title: "Citizen Grievances & Objection Redressal",
      badge: "PUBLIC TRUST & COMPLIANCE ⚖️",
      description: "Review and resolve landowner objections, title disputes, and compensation inquiries with SLA escalation tracking and transparent audit logs.",
      actionHint: "👉 Resolving citizen objections promptly minimizes legal injunctions.",
      position: "right",
      spotlightPadding: 6
    },
    {
      id: "dist_footer",
      selector: '[data-tutorial="sidebar-footer"]',
      targetPage: "district_dashboard",
      title: "Bilingual Toggle & Instant Tour Replay",
      badge: "SYSTEM CONTROLS 🌐",
      description: "Switch seamlessly between English and Tamil (தமிழ்). You can replay this interactive guided tour at any time by clicking the '🎮 Guided Tour' button right here!",
      actionHint: "👉 You are now fully certified to command the LandNexus platform!",
      position: "top",
      spotlightPadding: 8
    }
  ],

  state_authority: [
    {
      id: "state_welcome",
      selector: '[data-tutorial="sidebar-logo"]',
      targetPage: "state_dashboard",
      title: "State Command & Monitoring Center",
      badge: "STATE APEX VIEW 🏛️",
      description: "Welcome to the State Land Acquisition Authority Headquarters! From here, you monitor highway corridors, industrial corridors, and public infrastructure across all districts.",
      actionHint: "👉 Let's review statewide governance controls.",
      position: "right",
      spotlightPadding: 10
    },
    {
      id: "state_scope",
      selector: '[data-tutorial="scope-badge"]',
      targetPage: "state_dashboard",
      title: "Cross-District Filter & State Scope",
      badge: "MULTI-DISTRICT RADAR 🌐",
      description: "Filter statewide metrics with one click or isolate high-velocity districts like Coimbatore, Tiruppur, Salem, and Erode to spot regional bottlenecks.",
      actionHint: "👉 Seamlessly toggle between All Districts and specific regional hubs.",
      position: "bottom",
      spotlightPadding: 8
    },
    {
      id: "state_dss",
      selector: '[data-tutorial="state-dss-radar"]',
      targetPage: "state_dashboard",
      title: "Statewide AI Risk & Bottleneck Matrix",
      badge: "AI DECISION ENGINE 🤖",
      description: "Aggregated AI intelligence highlights cross-district risk indices, verification backlogs, and projected SLA delays before statutory deadlines lapse.",
      actionHint: "👉 AI predictive analytics helps prevent infrastructure cost overruns.",
      position: "bottom",
      spotlightPadding: 10
    },
    {
      id: "state_gis",
      selector: '[data-tutorial="nav-gis"]',
      targetPage: "gis",
      title: "Statewide Geospatial Spatial Portal",
      badge: "SPATIAL RECON 🗺️",
      description: "Inspect multi-district corridor alignments, forest conservation buffer zones, and railway corridors with interactive cadastral layering.",
      actionHint: "👉 Detect alignment conflicts and survey discrepancies in real-time.",
      position: "right",
      spotlightPadding: 6
    },
    {
      id: "state_reports",
      selector: '[data-tutorial="nav-reports"]',
      targetPage: "reports",
      title: "Executive Statutory Reports & Compliance",
      badge: "AUDIT & PARLIAMENTARY 📑",
      description: "Generate instant PDF/CSV statutory acquisition summaries, RFCTLARR 2013 compliance statements, and compensation fund audits for state review.",
      actionHint: "👉 Export audit-grade evidence packages with cryptographic audit trails.",
      position: "right",
      spotlightPadding: 6
    },
    {
      id: "state_footer",
      selector: '[data-tutorial="sidebar-footer"]',
      targetPage: "state_dashboard",
      title: "Bilingual Language & Tour Replay",
      badge: "QUICK ACCESS 🌐",
      description: "Toggle Tamil (தமிழ்) and English at will. Click '🎮 Guided Tour' in this footer whenever you want to revisit this walkthrough.",
      actionHint: "👉 State Authority mission briefing is complete!",
      position: "top",
      spotlightPadding: 8
    }
  ],

  field_officer: [
    {
      id: "field_welcome",
      selector: '[data-tutorial="sidebar-logo"]',
      targetPage: "field",
      title: "Field Verification Officer Hub",
      badge: "GROUND RECON 🌾",
      description: "Welcome, Field Officer! Your ground truth findings form the bedrock of transparent land acquisition. Perform digital inspections directly from your phone or tablet.",
      actionHint: "👉 Click 'Next Step →' to view your on-site verification queue.",
      position: "right",
      spotlightPadding: 10
    },
    {
      id: "field_queue",
      selector: '[data-tutorial="field-queue"]',
      targetPage: "field",
      title: "AI-Prioritized Field Inspection Queue",
      badge: "GROUND WORKLIST 📋",
      description: "Parcels requiring physical boundary verification, tree/structure valuation, and GPS geofencing are automatically prioritized by urgency and legal risk.",
      actionHint: "👉 Tap any parcel in the worklist to log ground verification remarks.",
      position: "bottom",
      spotlightPadding: 10
    },
    {
      id: "field_gis",
      selector: '[data-tutorial="nav-gis"]',
      targetPage: "gis",
      title: "Interactive Cadastral GIS Verification",
      badge: "GPS SURVEY 🗺️",
      description: "Cross-reference physical boundary markers with government FMB (Field Measurement Book) digital cadastral polygons to spot encroachments early.",
      actionHint: "👉 High-precision coordinates guarantee dispute-free awards.",
      position: "right",
      spotlightPadding: 6
    },
    {
      id: "field_rr",
      selector: '[data-tutorial="nav-rr"]',
      targetPage: "rr",
      title: "Rehabilitation & Resettlement (R&R) Survey",
      badge: "HUMAN WELFARE 👨‍👩‍👧‍👦",
      description: "Track project-affected families, verify dwelling structures, evaluate commercial livelihoods, and safeguard vulnerable families with empathetic diligence.",
      actionHint: "👉 Update resettlement milestones and housing allotment readiness.",
      position: "right",
      spotlightPadding: 6
    },
    {
      id: "field_docs",
      selector: '[data-tutorial="nav-documents"]',
      targetPage: "documents",
      title: "Evidentiary Document & Photo Vault",
      badge: "TAMPER-PROOF EVIDENCE 📷",
      description: "Upload geotagged on-site inspection photos, patta ownership certificates, and village revenue receipts with automated SHA-256 integrity verification.",
      actionHint: "👉 Digital evidence prevents fraudulent compensation claims.",
      position: "right",
      spotlightPadding: 6
    },
    {
      id: "field_footer",
      selector: '[data-tutorial="sidebar-footer"]',
      targetPage: "field",
      title: "Field Tools & Tutorial Replay",
      badge: "ALWAYS READY ⚡",
      description: "Available in Tamil & English. Replay this field officer tutorial anytime via '🎮 Guided Tour' in the bottom sidebar.",
      actionHint: "👉 You are ready for field deployment!",
      position: "top",
      spotlightPadding: 8
    }
  ],

  citizen: [
    {
      id: "cit_welcome",
      selector: '[data-tutorial="sidebar-logo"]',
      targetPage: "citizen_dash",
      title: "Welcome to Citizen LandNexus Portal",
      badge: "TRANSPARENCY FIRST 🤝",
      description: "Welcome! LandNexus gives you 100% transparent, direct access to your land acquisition status, compensation entitlements, and rehabilitation rights without intermediaries.",
      actionHint: "👉 Let's take a 30-second tour of your personal landowner rights.",
      position: "right",
      spotlightPadding: 10
    },
    {
      id: "cit_parcel",
      selector: '[data-tutorial="citizen-parcel-card"]',
      targetPage: "citizen_dash",
      title: "Your Verified Land Record & Survey No.",
      badge: "LAND OWNERSHIP 📜",
      description: "Here is your officially linked land record. Verify your Survey Number, Subdivision, Village, Acquired Area, and current statutory stage (e.g. Section 11/19/23).",
      actionHint: "👉 All details are directly fetched from verified government records.",
      position: "bottom",
      spotlightPadding: 10
    },
    {
      id: "cit_comp",
      selector: '[data-tutorial="citizen-comp-card"]',
      targetPage: "citizen_dash",
      title: "Transparent Compensation & DBT Tracking",
      badge: "DIRECT BENEFIT TRANSFER 💰",
      description: "View the exact breakdown of your compensation: Base Market Value + 100% Solatium + 12% Statutory Interest, alongside your bank disbursement status.",
      actionHint: "👉 Clear tracking guarantees fair and timely compensation.",
      position: "top",
      spotlightPadding: 10
    },
    {
      id: "cit_grievance",
      selector: '[data-tutorial="nav-grievances"]',
      targetPage: "grievances",
      title: "File Inquiries, Objections & Grievances",
      badge: "CITIZEN VOICE 📢",
      description: "Dispute a valuation, clarify boundary measurements, or submit inheritance documents directly to the Land Acquisition Collector with an official tracking ticket.",
      actionHint: "👉 Track the status of your petition with guaranteed SLA timelines.",
      position: "right",
      spotlightPadding: 6
    },
    {
      id: "cit_footer",
      selector: '[data-tutorial="sidebar-footer"]',
      targetPage: "citizen_dash",
      title: "Tamil / English & Guided Tour Replay",
      badge: "CITIZEN SUPPORT 🌐",
      description: "Easily switch the entire interface to Tamil (தமிழ்). Need help again? Simply click '🎮 Guided Tour' anytime to replay this walkthrough!",
      actionHint: "👉 Your citizen rights tour is complete. Explore freely!",
      position: "top",
      spotlightPadding: 8
    }
  ],

  default: [
    {
      id: "def_welcome",
      selector: '[data-tutorial="sidebar-logo"]',
      targetPage: "dashboard",
      title: "Welcome to LandNexus",
      badge: "SYSTEM OVERVIEW 🚀",
      description: "Welcome to LandNexus — the unified land acquisition intelligence platform for Smart India Hackathon 2026.",
      actionHint: "👉 Click 'Next Step →' to explore key features.",
      position: "right",
      spotlightPadding: 10
    },
    {
      id: "def_nav",
      selector: '[data-tutorial="nav-gis"]',
      targetPage: "gis",
      title: "Geospatial Cadastral System",
      badge: "GIS MAPPING 🗺️",
      description: "Explore interactive cadastral land parcels, satellite overlays, and project alignments with precision geospatial analytics.",
      actionHint: "👉 Inspect real-time spatial records.",
      position: "right",
      spotlightPadding: 6
    },
    {
      id: "def_footer",
      selector: '[data-tutorial="sidebar-footer"]',
      targetPage: "dashboard",
      title: "Bilingual Language & Guided Tour",
      badge: "ASSISTANCE 🌐",
      description: "Switch languages and replay this guided tour at any time with the buttons in this footer.",
      actionHint: "👉 Enjoy exploring LandNexus!",
      position: "top",
      spotlightPadding: 8
    }
  ]
};

/**
 * Returns the appropriate step list for a given user role.
 */
export function getStepsForRole(role) {
  if (!role) return ROLE_STEPS.default;
  if (role === "district_authority") return ROLE_STEPS.district_authority;
  if (role === "state_authority") return ROLE_STEPS.state_authority;
  if (role === "field_officer") return ROLE_STEPS.field_officer;
  if (role === "citizen") return ROLE_STEPS.citizen;
  if (role === "national_authority" || role === "admin" || role === "authority") return ROLE_STEPS.state_authority;
  return ROLE_STEPS.district_authority;
}
