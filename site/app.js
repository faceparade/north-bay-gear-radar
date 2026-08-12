const STORAGE_KEY = "northBayGearRadar.saved.v1";

const state = {
  data: null,
  visible: 40,
  search: "",
  type: "active",
  sources: new Set(),
  categories: new Set(),
  min: null,
  max: null,
  newOnly: false,
  scoredOnly: false,
  savedOnly: false,
  sort: "score-desc",
  saved: loadSaved(),
};

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const titleCase = value => value.split("-").map(word => word[0].toUpperCase() + word.slice(1)).join(" ");
const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const keyFor = row => `${row.source}:${row.listing_id}`;
const escapeHtml = value => String(value ?? "").replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);

function safeExternalUrl(value) {
  try {
    const url = new URL(String(value || ""), window.location.href);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
  } catch { return "#"; }
}

function loadSaved() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch { return {}; }
}

function persistSaved() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.saved));
}

function listingPrice(row) {
  return row.listing_type === "sold" ? row.sold_price : row.asking_price;
}

function listingTime(row) {
  if (row.posted_at) return localDate(row.posted_at);
  if (row.listing_age_text) return `${row.listing_age_text} (source-reported)`;
  return "Not available from source";
}

function activePricePresentation(row) {
  if (row.asking_price != null) {
    const kinds = {
      verified_detail: "verified detail price",
      verified_description: "verified description price",
      verified_detail_free: "confirmed free listing",
    };
    return {
      value: currency.format(row.asking_price),
      kind: kinds[row.price_status] || "headline asking price",
    };
  }
  const labels = {
    multiple_prices: "Multiple prices",
    make_offer: "Make offer",
    unclear_arrangement: "Trade / unclear price",
    placeholder_unverified: "Price unknown",
    missing: "Price unknown",
  };
  return { value: labels[row.price_status] || "Price unknown", kind: "headline is a placeholder" };
}

function localDate(value) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function renderStats() {
  const s = state.data.stats;
  const items = [[s.active, "Active finds"], [s.sold, "Sold comps"], [s.new_discoveries, "New discoveries"], [s.scored, "Fit-scored"], [Object.keys(state.data.categories).length, "Categories"]];
  $("#stats").innerHTML = items.map(([value, label]) => `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`).join("");
  $("#updatedAt").textContent = localDate(state.data.generated_at);
  $("#sourceFreshness").textContent = `Marketplace observed ${localDate(state.data.source_as_of.facebook)}`;
  const active = state.data.listings.filter(row => row.listing_type === "active");
  const scored = active.filter(row => row.score != null).length;
  const reviewed = active.filter(row => row.recommendation).length;
  const photos = active.filter(row => row.thumbnail_url).length;
  $("#coverageNote").textContent = `${active.length} active records widen discovery, but only ${scored} are fit-scored and ${reviewed} have manual listing-level recommendations. ${photos} currently have locally cached low-resolution photos.`;
}

function checkboxMarkup(name, entries) {
  return entries.map(([key, count]) => `<label><input type="checkbox" name="${escapeHtml(name)}" value="${escapeHtml(key)}"><span>${escapeHtml(titleCase(key))}</span><span class="count">${escapeHtml(count)}</span></label>`).join("");
}

function renderFilters() {
  $("#sourceFilters").innerHTML = checkboxMarkup("source", Object.entries(state.data.sources));
  $("#categoryFilters").innerHTML = checkboxMarkup("category", Object.entries(state.data.categories));
  $$('input[name="source"]').forEach(el => el.addEventListener("change", () => { el.checked ? state.sources.add(el.value) : state.sources.delete(el.value); resetPageAndRender(); }));
  $$('input[name="category"]').forEach(el => el.addEventListener("change", () => { el.checked ? state.categories.add(el.value) : state.categories.delete(el.value); resetPageAndRender(); }));
}

function matches(row) {
  if (state.type !== "all" && row.listing_type !== state.type) return false;
  if (state.sources.size && !state.sources.has(row.source)) return false;
  if (state.categories.size && !state.categories.has(row.category)) return false;
  if (state.newOnly && !row.new_discovery) return false;
  if (state.scoredOnly && row.score == null) return false;
  if (state.savedOnly && !state.saved[keyFor(row)]) return false;
  const price = listingPrice(row);
  if (state.min != null && (price == null || price < state.min)) return false;
  if (state.max != null && (price == null || price > state.max)) return false;
  if (state.search) {
    const haystack = [row.title, row.model, row.location_text, row.description, row.category, row.source].filter(Boolean).join(" ").toLowerCase();
    if (!haystack.includes(state.search)) return false;
  }
  return true;
}

function sortedRows() {
  const rows = state.data.listings.filter(matches);
  const price = row => listingPrice(row) ?? Number.POSITIVE_INFINITY;
  const score = row => row.score ?? -1;
  const sorters = {
    "score-desc": (a, b) => score(b) - score(a) || price(a) - price(b),
    "price-asc": (a, b) => price(a) - price(b),
    "price-desc": (a, b) => price(b) - price(a),
    "title-asc": (a, b) => a.title.localeCompare(b.title),
    "source-asc": (a, b) => a.source.localeCompare(b.source) || price(a) - price(b),
  };
  return rows.sort(sorters[state.sort]);
}

function fact(term, value) {
  if (value == null || value === "") return "";
  return `<div><dt>${escapeHtml(term)}</dt><dd>${escapeHtml(value)}</dd></div>`;
}

function toggleSaved(row) {
  const key = keyFor(row);
  if (state.saved[key]) delete state.saved[key];
  else state.saved[key] = { source: row.source, listing_id: row.listing_id, title: row.title, url: row.url, price: row.listing_type === "active" ? row.asking_price : null };
  persistSaved();
  render();
}

function reconcileSavedPrices() {
  const live = new Map(state.data.listings.map(row => [keyFor(row), row]));
  let changed = false;
  Object.entries(state.saved).forEach(([key, saved]) => {
    const row = live.get(key);
    const verifiedPrice = row?.listing_type === "active" && row.asking_price != null ? row.asking_price : null;
    if (saved.price !== verifiedPrice) {
      saved.price = verifiedPrice;
      changed = true;
    }
  });
  if (changed) persistSaved();
}

function renderCard(row) {
  const fragment = $("#listingTemplate").content.cloneNode(true);
  const article = fragment.querySelector("article");
  const badge = fragment.querySelector(".source-badge");
  badge.textContent = row.source;
  badge.classList.add(row.source);
  fragment.querySelector(".category-label").textContent = titleCase(row.category);
  const thumbLink = fragment.querySelector(".thumbnail-link");
  if (row.thumbnail_url) {
    thumbLink.hidden = false;
    thumbLink.href = safeExternalUrl(row.url);
    const image = fragment.querySelector(".listing-thumbnail");
    image.src = row.thumbnail_url;
    image.alt = `Listing photo for ${row.title}`;
  }
  fragment.querySelector("h3").textContent = row.title;
  fragment.querySelector(".model-line").textContent = row.model && row.model !== row.title ? row.model : "";
  const presentation = row.listing_type === "sold"
    ? { value: row.sold_price == null ? "Price unavailable" : currency.format(row.sold_price), kind: "sold price" }
    : activePricePresentation(row);
  fragment.querySelector(".price").textContent = presentation.value;
  fragment.querySelector(".price-kind").textContent = presentation.kind;
  if (row.score != null) {
    fragment.querySelector(".score-block").hidden = false;
    fragment.querySelector(".score").textContent = row.score.toFixed(1);
  }
  const market = row.market || {};
  fragment.querySelector(".facts").innerHTML = [
    fact("Location", row.location_text), fact("Distance", row.distance_miles != null ? `${row.distance_miles.toFixed(1)} mi` : null),
    fact(row.listing_type === "sold" ? "Observed" : "Listed", row.listing_type === "sold" ? localDate(row.observed_at) : listingTime(row)),
    fact("Updated", row.updated_at ? localDate(row.updated_at) : null),
    fact("Market", market.used_low != null ? `${currency.format(market.used_low)}–${currency.format(market.used_high)}` : null),
    fact("Evidence", market.sample_size ? `${market.sample_size} sold comps` : null), fact("Rank", row.rank ? `#${row.rank}` : null),
    fact("Verdict", row.recommendation ? titleCase(row.recommendation) : null), fact("Condition", row.condition),
  ].join("");
  const notes = fragment.querySelector(".notes");
  notes.textContent = [
    row.price_note,
    row.research_notes,
    row.description,
    row.accessories ? `Accessories: ${row.accessories}` : "",
  ].filter(Boolean).join("\n\n");
  notes.hidden = !notes.textContent;
  fragment.querySelector(".risk-flags").innerHTML = (row.risk_flags || []).map(flag => `<span class="risk">${escapeHtml(String(flag).replaceAll("_", " "))}</span>`).join("");
  const save = fragment.querySelector(".save-button");
  const isSaved = Boolean(state.saved[keyFor(row)]);
  save.textContent = isSaved ? "★ Saved" : "☆ Save";
  save.setAttribute("aria-pressed", String(isSaved));
  save.setAttribute("aria-label", `${isSaved ? "Remove" : "Save"} ${row.title} ${isSaved ? "from" : "to"} private shortlist`);
  save.addEventListener("click", () => toggleSaved(row));
  const link = fragment.querySelector(".listing-link");
  link.href = safeExternalUrl(row.url);
  link.setAttribute("aria-label", `Open original listing for ${row.title}`);
  article.dataset.id = row.listing_id;
  return fragment;
}

function renderSaved() {
  const entries = Object.values(state.saved);
  $("#savedCount").textContent = entries.length;
  $("#savedTotal").textContent = currency.format(entries.reduce((sum, row) => sum + (Number(row.price) || 0), 0));
  $("#clearSaved").disabled = entries.length === 0;
  const container = $("#savedItems");
  container.replaceChildren(...entries.map(row => {
    const link = document.createElement("a");
    link.className = "saved-item";
    link.href = safeExternalUrl(row.url);
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    const title = document.createElement("span");
    title.textContent = row.title;
    const price = document.createElement("strong");
    price.textContent = row.price == null ? "—" : currency.format(row.price);
    link.append(title, price);
    return link;
  }));
}

function renderChips() {
  const chips = [];
  if (state.type !== "all") chips.push(state.type);
  state.sources.forEach(value => chips.push(value)); state.categories.forEach(value => chips.push(titleCase(value)));
  if (state.search) chips.push(`“${state.search}”`); if (state.min != null) chips.push(`from $${state.min}`); if (state.max != null) chips.push(`up to $${state.max}`);
  if (state.newOnly) chips.push("new discovery"); if (state.scoredOnly) chips.push("scored"); if (state.savedOnly) chips.push("saved");
  $("#activeFilterChips").innerHTML = chips.map(value => `<span class="chip">${escapeHtml(value)}</span>`).join("");
}

function render() {
  const rows = sortedRows();
  $("#resultCount").textContent = rows.length;
  $("#listingGrid").replaceChildren(...rows.slice(0, state.visible).map(renderCard));
  $("#showMore").hidden = state.visible >= rows.length;
  $("#emptyState").hidden = rows.length !== 0;
  renderChips(); renderSaved();
}

function resetPageAndRender() { state.visible = 40; render(); }

function wireControls() {
  $("#searchInput").addEventListener("input", event => { state.search = event.target.value.trim().toLowerCase(); resetPageAndRender(); });
  $$('input[name="listingType"]').forEach(el => el.addEventListener("change", event => { state.type = event.target.value; resetPageAndRender(); }));
  $("#minPrice").addEventListener("input", event => { state.min = event.target.value === "" ? null : Number(event.target.value); resetPageAndRender(); });
  $("#maxPrice").addEventListener("input", event => { state.max = event.target.value === "" ? null : Number(event.target.value); resetPageAndRender(); });
  $("#newOnly").addEventListener("change", event => { state.newOnly = event.target.checked; resetPageAndRender(); });
  $("#scoredOnly").addEventListener("change", event => { state.scoredOnly = event.target.checked; resetPageAndRender(); });
  $("#savedOnly").addEventListener("change", event => { state.savedOnly = event.target.checked; resetPageAndRender(); });
  $("#sortSelect").addEventListener("change", event => { state.sort = event.target.value; resetPageAndRender(); });
  $("#showMore").addEventListener("click", () => { state.visible += 40; render(); });
  $("#clearSaved").addEventListener("click", () => { state.saved = {}; persistSaved(); render(); });
  $("#resetFilters").addEventListener("click", () => {
    Object.assign(state, { visible: 40, search: "", type: "active", sources: new Set(), categories: new Set(), min: null, max: null, newOnly: false, scoredOnly: false, savedOnly: false, sort: "score-desc" });
    $("#searchInput").value = ""; $("#minPrice").value = ""; $("#maxPrice").value = ""; $("#newOnly").checked = false; $("#scoredOnly").checked = false; $("#savedOnly").checked = false; $("#sortSelect").value = "score-desc";
    $('input[name="listingType"][value="active"]').checked = true;
    $$('input[name="source"], input[name="category"]').forEach(el => { el.checked = false; }); render();
  });
}

async function boot() {
  try {
    const response = await fetch("data/listings.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Data request failed: ${response.status}`);
    state.data = await response.json();
    reconcileSavedPrices();
    renderStats(); renderFilters(); wireControls(); render();
  } catch (error) {
    $("#listingGrid").innerHTML = `<div class="empty"><strong>Could not load listing data.</strong><p>${escapeHtml(error.message)}</p></div>`;
  }
}

document.addEventListener("DOMContentLoaded", boot);
