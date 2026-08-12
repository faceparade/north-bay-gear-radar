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
  sort: "score-desc",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const titleCase = (value) => value.split("-").map(word => word[0].toUpperCase() + word.slice(1)).join(" ");
const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });

function listingPrice(row) {
  return row.listing_type === "sold" ? row.sold_price : row.asking_price;
}

function localDate(value) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function renderStats() {
  const s = state.data.stats;
  const items = [
    [s.active, "Active finds"],
    [s.sold, "Sold comps"],
    [s.new_discoveries, "New discoveries"],
    [s.scored, "Fit-scored"],
    [Object.keys(state.data.categories).length, "Categories"],
  ];
  $("#stats").innerHTML = items.map(([value, label]) => `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`).join("");
  $("#updatedAt").textContent = localDate(state.data.generated_at);
  $("#sourceFreshness").textContent = `Marketplace observed ${localDate(state.data.source_as_of.facebook)}`;
}

function checkboxMarkup(name, entries) {
  return entries.map(([key, count]) => `
    <label><input type="checkbox" name="${name}" value="${key}"><span>${titleCase(key)}</span><span class="count">${count}</span></label>
  `).join("");
}

function renderFilters() {
  $("#sourceFilters").innerHTML = checkboxMarkup("source", Object.entries(state.data.sources));
  $("#categoryFilters").innerHTML = checkboxMarkup("category", Object.entries(state.data.categories));
  $$('input[name="source"]').forEach(el => el.addEventListener("change", () => {
    el.checked ? state.sources.add(el.value) : state.sources.delete(el.value);
    resetPageAndRender();
  }));
  $$('input[name="category"]').forEach(el => el.addEventListener("change", () => {
    el.checked ? state.categories.add(el.value) : state.categories.delete(el.value);
    resetPageAndRender();
  }));
}

function matches(row) {
  if (state.type !== "all" && row.listing_type !== state.type) return false;
  if (state.sources.size && !state.sources.has(row.source)) return false;
  if (state.categories.size && !state.categories.has(row.category)) return false;
  if (state.newOnly && !row.new_discovery) return false;
  if (state.scoredOnly && row.score == null) return false;
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
  return `<div><dt>${term}</dt><dd>${value}</dd></div>`;
}

function renderCard(row) {
  const fragment = $("#listingTemplate").content.cloneNode(true);
  const article = fragment.querySelector("article");
  const badge = fragment.querySelector(".source-badge");
  badge.textContent = row.source;
  badge.classList.add(row.source);
  fragment.querySelector(".category-label").textContent = titleCase(row.category);
  fragment.querySelector("h3").textContent = row.title;
  fragment.querySelector(".model-line").textContent = row.model && row.model !== row.title ? row.model : "";
  const price = listingPrice(row);
  fragment.querySelector(".price").textContent = price == null ? "Ask seller" : currency.format(price);
  fragment.querySelector(".price-kind").textContent = row.listing_type === "sold" ? "sold price" : "asking price";
  if (row.score != null) {
    const scoreBlock = fragment.querySelector(".score-block");
    scoreBlock.hidden = false;
    fragment.querySelector(".score").textContent = row.score.toFixed(1);
  }
  const market = row.market || {};
  fragment.querySelector(".facts").innerHTML = [
    fact("Location", row.location_text),
    fact("Distance", row.distance_miles != null ? `${row.distance_miles.toFixed(1)} mi` : null),
    fact("Market", market.used_low != null ? `${currency.format(market.used_low)}–${currency.format(market.used_high)}` : null),
    fact("Evidence", market.sample_size ? `${market.sample_size} sold comps` : null),
    fact("Rank", row.rank ? `#${row.rank}` : null),
  ].join("");
  const notes = fragment.querySelector(".notes");
  notes.textContent = row.research_notes || row.description || "";
  notes.hidden = !notes.textContent;
  fragment.querySelector(".risk-flags").innerHTML = (row.risk_flags || []).map(flag => `<span class="risk">${flag.replaceAll("_", " ")}</span>`).join("");
  const link = fragment.querySelector(".listing-link");
  link.href = row.url;
  link.setAttribute("aria-label", `Open original listing for ${row.title}`);
  article.dataset.id = row.listing_id;
  return fragment;
}

function renderChips() {
  const chips = [];
  if (state.type !== "all") chips.push(state.type);
  state.sources.forEach(value => chips.push(value));
  state.categories.forEach(value => chips.push(titleCase(value)));
  if (state.search) chips.push(`“${state.search}”`);
  if (state.min != null) chips.push(`from $${state.min}`);
  if (state.max != null) chips.push(`up to $${state.max}`);
  if (state.newOnly) chips.push("new discovery");
  if (state.scoredOnly) chips.push("scored");
  $("#activeFilterChips").innerHTML = chips.map(value => `<span class="chip">${value}</span>`).join("");
}

function render() {
  const rows = sortedRows();
  $("#resultCount").textContent = rows.length;
  const grid = $("#listingGrid");
  grid.replaceChildren(...rows.slice(0, state.visible).map(renderCard));
  $("#showMore").hidden = state.visible >= rows.length;
  $("#emptyState").hidden = rows.length !== 0;
  renderChips();
}

function resetPageAndRender() { state.visible = 40; render(); }

function wireControls() {
  $("#searchInput").addEventListener("input", event => { state.search = event.target.value.trim().toLowerCase(); resetPageAndRender(); });
  $$('input[name="listingType"]').forEach(el => el.addEventListener("change", event => { state.type = event.target.value; resetPageAndRender(); }));
  $("#minPrice").addEventListener("input", event => { state.min = event.target.value === "" ? null : Number(event.target.value); resetPageAndRender(); });
  $("#maxPrice").addEventListener("input", event => { state.max = event.target.value === "" ? null : Number(event.target.value); resetPageAndRender(); });
  $("#newOnly").addEventListener("change", event => { state.newOnly = event.target.checked; resetPageAndRender(); });
  $("#scoredOnly").addEventListener("change", event => { state.scoredOnly = event.target.checked; resetPageAndRender(); });
  $("#sortSelect").addEventListener("change", event => { state.sort = event.target.value; resetPageAndRender(); });
  $("#showMore").addEventListener("click", () => { state.visible += 40; render(); });
  $("#resetFilters").addEventListener("click", () => {
    Object.assign(state, { visible: 40, search: "", type: "active", sources: new Set(), categories: new Set(), min: null, max: null, newOnly: false, scoredOnly: false, sort: "score-desc" });
    $("#searchInput").value = "";
    $("#minPrice").value = "";
    $("#maxPrice").value = "";
    $("#newOnly").checked = false;
    $("#scoredOnly").checked = false;
    $("#sortSelect").value = "score-desc";
    $('input[name="listingType"][value="active"]').checked = true;
    $$('input[name="source"], input[name="category"]').forEach(el => { el.checked = false; });
    render();
  });
}

async function boot() {
  try {
    const response = await fetch("data/listings.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Data request failed: ${response.status}`);
    state.data = await response.json();
    renderStats();
    renderFilters();
    wireControls();
    render();
  } catch (error) {
    $("#listingGrid").innerHTML = `<div class="empty"><strong>Could not load listing data.</strong><p>${error.message}</p></div>`;
  }
}

document.addEventListener("DOMContentLoaded", boot);
