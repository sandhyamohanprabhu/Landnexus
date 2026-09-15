const COMPENSATION_STATE_KEY = "__surviCompensationState";

function getState() {
  if (!window[COMPENSATION_STATE_KEY]) {
    window[COMPENSATION_STATE_KEY] = { fixedCentRate: 0, totalLandAreaCost: 0, landAreaAcres: 0 };
  }
  return window[COMPENSATION_STATE_KEY];
}

function findLabel(form, prefix) {
  return Array.from(form.querySelectorAll("label")).find((label) =>
    label.textContent.trim().toLowerCase().startsWith(prefix.toLowerCase())
  );
}

function findInput(label) {
  return label?.querySelector("input, textarea, select") || null;
}

function numberValue(input) {
  const value = Number.parseFloat(input?.value ?? "");
  return Number.isFinite(value) && value >= 0 ? value : 0;
}

function formatINR(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value || 0);
}

function updateTotal(form, rateInput, totalInput) {
  const areaInput = findInput(findLabel(form, "Est. Land Area (Acres)"));
  const acres = numberValue(areaInput);
  const rate = numberValue(rateInput);
  const total = acres * 100 * rate;

  totalInput.value = formatINR(total);
  totalInput.dataset.rawValue = String(total);
  totalInput.title = `${acres} acres × 100 cents × ₹${rate.toLocaleString("en-IN")} per cent`;

  const state = getState();
  state.fixedCentRate = rate;
  state.totalLandAreaCost = total;
  state.landAreaAcres = acres;
}

function addCompensationFields(form) {
  if (form.dataset.compensationEnhanced === "true") return;

  const villageLabel = findLabel(form, "Village");
  const areaLabel = findLabel(form, "Est. Land Area (Acres)");
  if (!villageLabel || !areaLabel) return;

  const rateLabel = document.createElement("label");
  rateLabel.className = "survi-compensation-field";
  rateLabel.innerHTML = `Fixed Cent Rate (₹ / cent)<input type="number" min="0" step="0.01" inputmode="decimal" placeholder="Enter rate per cent" aria-label="Fixed Cent Rate in rupees per cent" />`;

  const totalLabel = document.createElement("label");
  totalLabel.className = "survi-compensation-field";
  totalLabel.innerHTML = `Total Land Area Cost (₹)<input type="text" value="₹0.00" readonly aria-readonly="true" aria-label="Total land area cost" />`;

  const rateInput = rateLabel.querySelector("input");
  const totalInput = totalLabel.querySelector("input");
  const state = getState();
  rateInput.value = state.fixedCentRate || "";

  const recalculate = () => updateTotal(form, rateInput, totalInput);
  rateInput.addEventListener("input", recalculate);
  rateInput.addEventListener("change", recalculate);

  const areaInput = findInput(areaLabel);
  areaInput?.addEventListener("input", recalculate);
  areaInput?.addEventListener("change", recalculate);

  villageLabel.insertAdjacentElement("afterend", rateLabel);
  rateLabel.insertAdjacentElement("afterend", totalLabel);

  const hint = document.createElement("div");
  hint.className = "survi-compensation-hint";
  hint.textContent = "Calculation: Land Area (acres) × 100 × Fixed Cent Rate";
  hint.style.gridColumn = "1 / -1";
  hint.style.fontSize = "12px";
  hint.style.color = "#607080";
  hint.style.marginTop = "-8px";
  totalLabel.insertAdjacentElement("afterend", hint);

  form.dataset.compensationEnhanced = "true";
  recalculate();
}

function enhanceForms() {
  const form = Array.from(document.querySelectorAll("form.form")).find((f) =>
    findLabel(f, "Village") && findLabel(f, "Est. Land Area (Acres)")
  );
  if (form) addCompensationFields(form);
}

// The normal project POST remains the single source of truth. This wrapper only
// adds the two compensation values to the existing request; the backend recalculates
// the total from authoritative project acreage before saving it.
const nativeFetch = window.fetch.bind(window);
window.fetch = async (input, init = {}) => {
  try {
    const requestUrl = typeof input === "string" ? input : input?.url || "";
    const url = new URL(requestUrl, window.location.href);
    const method = String(
      init.method || (typeof input !== "string" ? input?.method : "GET") || "GET"
    ).toUpperCase();

    if (method === "POST" && (url.pathname === "/projects" || url.pathname === "/projects/")) {
      if (typeof init.body === "string") {
        const payload = JSON.parse(init.body);
        const form = Array.from(document.querySelectorAll("form.form")).find((f) =>
          findLabel(f, "Village") && findLabel(f, "Est. Land Area (Acres)")
        );

        if (form) {
          const area = numberValue(findInput(findLabel(form, "Est. Land Area (Acres)")));
          const rate = numberValue(form.querySelector('.survi-compensation-field input[type="number"]'));
          payload.fixed_cent_rate = rate;
          payload.total_land_area_cost = area * 100 * rate;
          payload.estimated_land_cost = payload.total_land_area_cost;
        }
        init = { ...init, body: JSON.stringify(payload) };
      }
    }
  } catch (error) {
    console.warn("SURVI compensation enhancement could not prepare request:", error);
  }

  return nativeFetch(input, init);
};

const observer = new MutationObserver(() => enhanceForms());
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    enhanceForms();
    observer.observe(document.body, { childList: true, subtree: true });
  });
} else {
  enhanceForms();
  observer.observe(document.body, { childList: true, subtree: true });
}
