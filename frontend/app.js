"use strict";

const form = document.getElementById("search-form");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const countEl = document.getElementById("count");
const cardsEl = document.getElementById("cards");
const emptyEl = document.getElementById("empty");
const choiceEl = document.getElementById("choice");
const choiceOptionsEl = document.getElementById("choice-options");

let source = null;
let searchId = null;
let leadCount = 0;

const STATUS_LABEL = {
  verified: "Verified",
  partially_verified: "Partially verified",
  unverified: "Unverified",
  rejected: "Rejected",
};

/* ---------- helpers ---------- */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text; // textContent = no HTML injection
  return node;
}

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle("error-text", isError);
}

function clearErrors() {
  document.querySelectorAll(".error").forEach((e) => (e.textContent = ""));
  document.querySelectorAll(".invalid").forEach((e) => e.classList.remove("invalid"));
}

function showFieldError(field, message) {
  const err = document.getElementById("err-" + field);
  const input = document.getElementById(field === "radius_km" ? "radius" : field);
  if (err) err.textContent = message;
  if (input) input.classList.add("invalid");
}

function formatDate(iso) {
  if (!iso) return "Not verified yet";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

/* Google Maps link from coordinates. No API key needed. */
function mapsUrl(lead) {
  if (lead.maps_url) return lead.maps_url;
  if (typeof lead.lat === "number" && typeof lead.lng === "number") {
    return "https://www.google.com/maps/search/?api=1&query=" +
      encodeURIComponent(lead.lat + "," + lead.lng);
  }
  return null;
}

/* ---------- form -> payload ---------- */

function readForm() {
  return {
    area: form.area.value.trim(),
    radius_km: Number(form.radius_km.value),
    product: form.product.value.trim(),
    category: form.category.value.trim(),
    exclusions: form.exclusions.value.split(",").map((s) => s.trim()).filter(Boolean),
  };
}

function validateLocally(data) {
  let ok = true;
  if (!data.area) { showFieldError("area", "Enter an area."); ok = false; }
  if (!data.product) { showFieldError("product", "Enter your product."); ok = false; }
  if (!data.category) { showFieldError("category", "Enter a business type."); ok = false; }
  return ok;
}

/* ---------- submit ---------- */

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearErrors();

  const data = readForm();
  if (!validateLocally(data)) return;

  submitBtn.disabled = true;
  setStatus("Starting search...");

  try {
    const res = await fetch("/api/searches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (res.status === 422) {
      const body = await res.json();
      (body.detail || []).forEach((d) => showFieldError(d.loc[d.loc.length - 1], d.msg));
      setStatus("Fix the highlighted fields and try again.", true);
      submitBtn.disabled = false;
      return;
    }
    if (!res.ok) throw new Error("Server returned " + res.status);

    const body = await res.json();
    searchId = body.search_id;
    resetResults();
    openStream(searchId);
  } catch (err) {
    setStatus("Could not reach the server: " + err.message, true);
    submitBtn.disabled = false;
  }
});

/* ---------- stream ---------- */

function resetResults() {
  if (source) source.close();
  cardsEl.replaceChildren();
  leadCount = 0;
  countEl.textContent = "0";
  emptyEl.hidden = false;
  choiceEl.hidden = true;
}

function openStream(id) {
  source = new EventSource(`/api/searches/${id}/stream`);

  source.addEventListener("status", (e) => setStatus(JSON.parse(e.data).message));
  source.addEventListener("needs_choice", (e) => showChoice(JSON.parse(e.data).options));
  source.addEventListener("lead", (e) => addLeadCard(JSON.parse(e.data)));

  source.addEventListener("complete", (e) => {
    const d = JSON.parse(e.data);
    setStatus(d.total === 0
      ? "Search complete. No leads found. Try a bigger radius or a broader category."
      : `Search complete. ${d.total} lead(s) found.`);
    finish();
  });

  source.addEventListener("error_event", (e) => {
    setStatus(JSON.parse(e.data).message, true);
    finish();
  });

  source.onerror = () => {
    if (source && source.readyState === EventSource.CLOSED) return;
    setStatus("Connection lost. Cards already shown are kept.", true);
    finish();
  };
}

function finish() {
  if (source) source.close();
  source = null;
  submitBtn.disabled = false;
}

function showChoice(options) {
  choiceOptionsEl.replaceChildren();
  options.forEach((opt) => {
    const btn = el("button", "", opt.label);
    btn.type = "button";
    btn.addEventListener("click", async () => {
      choiceEl.hidden = true;
      setStatus("Continuing with: " + opt.label);
      await fetch(`/api/searches/${searchId}/area`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ choice_id: opt.id }),
      });
    });
    choiceOptionsEl.appendChild(btn);
  });
  choiceEl.hidden = false;
  setStatus("Waiting for you to pick an area.");
}

/* ---------- lead card (6 fields) ---------- */

function openLink(url, text) {
  const a = el("a", "", text);
  a.href = url;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  return a;
}

function pinIcon() {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", "14");
  svg.setAttribute("height", "14");
  svg.setAttribute("class", "pin");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", "M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z");
  const dot = document.createElementNS(ns, "circle");
  dot.setAttribute("cx", "12");
  dot.setAttribute("cy", "10");
  dot.setAttribute("r", "2.5");
  svg.append(path, dot);
  return svg;
}

/* one label + value pair; value is a node, text, or "Not found" */
function addField(dl, label, value) {
  dl.appendChild(el("dt", "", label));
  const dd = el("dd");
  if (value instanceof Node) {
    dd.appendChild(value);
  } else if (value) {
    dd.textContent = value;
  } else {
    dd.appendChild(el("span", "missing", "Not found")); // never invent data
  }
  dl.appendChild(dd);
}

function addLeadCard(lead) {
  emptyEl.hidden = true;
  leadCount += 1;
  countEl.textContent = String(leadCount);

  const status = lead.status in STATUS_LABEL ? lead.status : "unverified";
  const sources = lead.sources || [];
  const card = el("article", "lead " + status);

  // title + status
  const top = el("div", "lead-top");
  top.appendChild(el("h3", "", lead.name || "Unnamed business"));
  top.appendChild(el("span", "badge " + status, STATUS_LABEL[status]));
  card.appendChild(top);

  // six fields: Address, Phone, Email | Website, Distance, Location
  const fields = el("div", "fields");
  const left = el("dl", "fcol");
  const right = el("dl", "fcol");

  addField(left, "Address", lead.address);
  addField(left, "Phone", lead.phone);
  addField(left, "Email", lead.email);

  addField(right, "Website", lead.website
    ? openLink(lead.website, lead.website.replace(/^https?:\/\//, ""))
    : null);
  addField(right, "Distance", lead.distance_km != null ? lead.distance_km.toFixed(1) + " km" : null);

  const url = mapsUrl(lead);
  if (url) {
    const wrap = el("span");
    wrap.appendChild(pinIcon());
    wrap.appendChild(openLink(url, "View on Google Maps"));
    addField(right, "Location", wrap);
  } else {
    addField(right, "Location", null);
  }

  fields.append(left, right);
  card.appendChild(fields);

  card.appendChild(el("hr"));

  if (lead.reason) {
    const p = el("p", "reason", lead.reason + " ");
    p.appendChild(el("em", "", "(inference)"));
    card.appendChild(p);
  }

  // footer: score, sources, last verified
  const foot = el("p", "foot");
  const score = typeof lead.score === "number" ? lead.score + "%" : "n/a";
  foot.appendChild(el("strong", "", "Relevance Score: " + score));
  foot.appendChild(document.createTextNode("  |  Sources: " +
    (sources.length ? sources.map((s) => s.name).join(", ") : "none") +
    "  |  Last verified: " + formatDate(lead.last_verified)));
  card.appendChild(foot);

  cardsEl.appendChild(card); // append only: old cards stay on screen
}