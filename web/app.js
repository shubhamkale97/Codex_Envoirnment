const $ = (id) => document.getElementById(id);
let rows = [];
let currentDownload = "";
let browserCoordinates = null;
let currentCsv = "";
let currentFilename = "atlas-results.csv";

function toast(message) {
  $("toast").textContent = message;
  $("toast").classList.remove("hidden");
  setTimeout(() => $("toast").classList.add("hidden"), 5000);
}

async function request(url, options) {
  const response = await fetch(url, options);
  const text = await response.text();
  let body; try { body = JSON.parse(text); } catch { body = text; }
  if (!response.ok) throw new Error(body?.error || `Request failed (${response.status})`);
  return body;
}

async function checkHealth() {
  try {
    await request("/api/health");
    $("serviceDot").className = "dot live"; $("serviceText").textContent = "Service ready";
  } catch {
    $("serviceDot").className = "dot dead"; $("serviceText").textContent = "Service offline";
  }
}

const value = (row, ...keys) => keys.map((key) => row[key]).find((item) => item != null && item !== "") || "";
const safeUrl = (url) => /^https?:\/\//i.test(url || "") ? url : url ? `https://${url}` : "";
function escapeHtml(input) { const el = document.createElement("div"); el.textContent = String(input || ""); return el.innerHTML; }

function render(data) {
  const query = $("filter").value.toLowerCase().trim();
  const visible = data.filter((row) => Object.values(row).join(" ").toLowerCase().includes(query));
  $("resultRows").innerHTML = visible.map((row) => {
    const name = value(row, "title", "name"); const website = value(row, "website");
    const phone = value(row, "phone"); const email = value(row, "emails", "email");
    const rating = value(row, "review_rating", "rating"); const reviews = value(row, "review_count", "reviews");
    return `<tr><td><strong>${escapeHtml(name || "Untitled business")}</strong>${website ? `<a href="${escapeHtml(safeUrl(website))}" target="_blank" rel="noopener">Visit website ↗</a>` : "No website"}</td><td>${escapeHtml(value(row, "category") || "—")}</td><td>${phone ? `<a href="tel:${escapeHtml(phone)}">${escapeHtml(phone)}</a>` : "—"}${email ? `<br><a href="mailto:${escapeHtml(email)}">${escapeHtml(email)}</a>` : ""}</td><td class="rating">${rating ? `★ ${escapeHtml(rating)}` : "—"}${reviews ? `<br><small>${escapeHtml(reviews)} reviews</small>` : ""}</td><td>${escapeHtml(value(row, "address") || "—")}</td></tr>`;
  }).join("");
  $("resultCount").textContent = data.length;
  $("emptyFilter").classList.toggle("hidden", visible.length > 0);
}

function parseCsv(text) {
  const records = []; let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted && c === '"' && text[i + 1] === '"') { field += '"'; i++; }
    else if (c === '"') quoted = !quoted;
    else if (c === ',' && !quoted) { row.push(field); field = ""; }
    else if ((c === '\n' || c === '\r') && !quoted) { if (c === '\r' && text[i + 1] === '\n') i++; row.push(field); if (row.some(Boolean)) records.push(row); row = []; field = ""; }
    else field += c;
  }
  if (field || row.length) { row.push(field); records.push(row); }
  const headers = records.shift() || [];
  return records.map((record) => Object.fromEntries(headers.map((header, i) => [header, record[i] || ""])));
}

function downloadCsv() {
  if (!currentCsv) return toast("Run a successful search before downloading.");
  const url = URL.createObjectURL(new Blob([currentCsv], {type: "text/csv;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = url; link.download = currentFilename;
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function poll(jobId) {
  for (let attempt = 1; attempt <= 120; attempt++) {
    const job = await request(`/api/jobs/${jobId}`);
    const status = String(job.Status || job.status || "working").toLowerCase();
    $("progressText").textContent = `Google Maps is processing the request · check ${attempt}`;
    if (status === "ok") return;
    if (status === "failed") throw new Error("The search failed. Try a smaller depth or wait before retrying.");
    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
  throw new Error("The search timed out after 10 minutes.");
}

$("searchForm").addEventListener("submit", async (event) => {
  event.preventDefault(); const button = $("searchButton");
  button.disabled = true; $("results").classList.add("hidden"); $("progress").classList.remove("hidden");
  $("downloadLatest").disabled = true; $("downloadStatus").textContent = "Search running—your CSV will download automatically when ready.";
  $("progressTitle").textContent = "Locating your search area…"; $("progressText").textContent = "Converting the location into map coordinates.";
  try {
    const manualLat = $("latitude").value.trim(); const manualLon = $("longitude").value.trim();
    let location;
    if (manualLat && manualLon) location = {lat: manualLat, lon: manualLon, label: `Coordinates ${manualLat}, ${manualLon}`};
    else if (browserCoordinates) location = browserCoordinates;
    else {
      try { location = await request(`/api/geocode?q=${encodeURIComponent($("location").value)}`); }
      catch { $("coordinates").classList.remove("hidden"); throw new Error("Automatic geocoding is unavailable. Use “Use my location” or enter latitude and longitude."); }
    }
    $("progressTitle").textContent = "Finding businesses…"; $("progressText").textContent = location.label;
    const job = await request("/api/jobs", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({keyword:$("keyword").value, lat:location.lat, lon:location.lon, depth:Number($("depth").value), email:$("email").checked})});
    const jobId = job.id || job.ID; if (!jobId) throw new Error("The scraper did not return a job ID.");
    await poll(jobId); currentDownload = `/api/jobs/${jobId}/download`; currentFilename = `atlas-results-${jobId.slice(0, 12)}.csv`;
    const response = await fetch(currentDownload); if (!response.ok) throw new Error("Could not download the completed results.");
    currentCsv = await response.text(); rows = parseCsv(currentCsv); render(rows);
    $("downloadLatest").disabled = false;
    $("downloadStatus").textContent = `${rows.length} rows ready. The CSV download has started; use the button to download it again.`;
    $("results").classList.remove("hidden"); $("results").scrollIntoView({behavior:"smooth", block:"start"});
    downloadCsv();
  } catch (error) { $("downloadStatus").textContent = `No file prepared: ${error.message}`; toast(error.message); }
  finally { button.disabled = false; $("progress").classList.add("hidden"); }
});

$("coordinateToggle").addEventListener("click", () => {
  const opening = $("coordinates").classList.contains("hidden");
  $("coordinates").classList.toggle("hidden");
  $("location").required = !opening && !browserCoordinates;
  if (opening) $("latitude").focus();
});
$("useLocation").addEventListener("click", () => {
  if (!navigator.geolocation) return toast("This browser does not provide location access. Enter coordinates instead.");
  $("useLocation").disabled = true; $("useLocation").textContent = "Locating…";
  navigator.geolocation.getCurrentPosition(
    ({coords}) => {
      browserCoordinates = {lat: String(coords.latitude), lon: String(coords.longitude), label: "Your current location"};
      $("location").value = "Current location"; $("location").required = false;
      $("useLocation").textContent = "Location ready"; $("useLocation").disabled = false;
    },
    () => { toast("Location permission was unavailable. Enter coordinates instead."); $("coordinates").classList.remove("hidden"); $("useLocation").textContent = "Use my location"; $("useLocation").disabled = false; },
    {enableHighAccuracy:false, timeout:10000, maximumAge:300000}
  );
});

$("filter").addEventListener("input", () => render(rows));
$("downloadButton").addEventListener("click", downloadCsv);
$("downloadLatest").addEventListener("click", downloadCsv);
checkHealth();
