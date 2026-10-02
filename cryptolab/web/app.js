"use strict";
const $ = id => document.getElementById(id);
let token = "", example = {}, latest = null, cursor = null;
async function request(path, body) {
  const options = {headers: {"X-Session-Token": token}};
  if (body !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Request failed");
  return payload;
}
function status(message, error = false) {
  $("status").textContent = message;
  $("status").className = error ? "error" : "";
}
function element(tag, text, parent) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (parent) parent.append(node);
  return node;
}
function render(output) {
  latest = output;
  $("output").textContent = JSON.stringify(output, null, 2);
  $("export").disabled = false;
  $("summary").replaceChildren();
  $("changes").replaceChildren();
  for (const [key, value] of Object.entries(output)) {
    if (value === null || typeof value === "object") continue;
    const box = element("div", "", $("summary")); box.className = "metric";
    element("span", key.replaceAll("_", " "), box);
    element("strong", String(value), box);
  }
  if (Array.isArray(output.scenarios)) {
    for (const scenario of output.scenarios) {
      const section = element("details", "", $("changes"));
      element("summary", scenario.name + " · " + (scenario.status || "snapshot"), section);
      const table = element("table", "", section);
      if (Array.isArray(scenario.changes)) {
        const head = element("tr", "", table);
        for (const label of ["Path", "Before", "After"]) element("th", label, head);
        for (const change of scenario.changes) {
          const row = element("tr", "", table);
          element("td", change.path, row);
          element("td", JSON.stringify(change.before), row);
          element("td", JSON.stringify(change.after), row);
        }
      } else element("pre", JSON.stringify(scenario, null, 2), section);
    }
  }
}
function loadExample() {
  const mode = $("mode").value;
  $("input").value = JSON.stringify(mode === "batch" ? [example] : example, null, 2);
  $("scenario-area").hidden = mode !== "scenario";
  status("Example loaded. Edit values before running.");
}
async function history(append = false) {
  const result = await request("/api/runs" + (append && cursor ? "?before=" + cursor : ""));
  if (!append) $("history").replaceChildren();
  cursor = result.next_cursor;
  $("more").hidden = !cursor;
  for (const run of result.runs) {
    const row = element("tr", "", $("history"));
    for (const value of [run.id, run.label || "Untitled", run.mode, run.created_at]) element("td", String(value), row);
    const cell = element("td", "", row), button = element("button", "Load", cell);
    button.className = "secondary";
    button.addEventListener("click", async () => {
      try {
        const saved = await request("/api/runs/" + run.id);
        $("mode").value = saved.mode;
        $("label").value = saved.label;
        $("input").value = JSON.stringify(saved.mode === "batch" ? saved.input.documents : saved.input.input, null, 2);
        $("scenarios").value = JSON.stringify(saved.input.scenarios || [], null, 2);
        $("scenario-area").hidden = saved.mode !== "scenario";
        render(saved.output); status("Loaded run " + run.id);
      } catch (error) { status(error.message, true); }
    });
  }
}
$("run").addEventListener("click", async () => {
  $("run").disabled = true;
  status("Calculating…");
  try {
    const input = JSON.parse($("input").value), mode = $("mode").value;
    const payload = {label: $("label").value};
    let route = "/api/analyze";
    if (mode === "batch") { payload.documents = input; route = "/api/batch"; }
    else payload.input = input;
    if (mode === "scenario") { payload.scenarios = JSON.parse($("scenarios").value); route = "/api/scenarios"; }
    const result = await request(route, payload);
    render(result.output); status("Saved run " + result.run_id); await history();
  } catch (error) { status(error.message, true); }
  finally { $("run").disabled = false; }
});
$("mode").addEventListener("change", loadExample);
$("reset").addEventListener("click", loadExample);
$("refresh").addEventListener("click", () => history().catch(e => status(e.message, true)));
$("more").addEventListener("click", () => history(true).catch(e => status(e.message, true)));
$("import").addEventListener("change", async event => {
  try {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 1024 * 1024) throw new Error("File exceeds 1 MiB");
    const value = JSON.parse(await file.text());
    $("input").value = JSON.stringify(value, null, 2); status("Imported " + file.name);
  } catch (error) { status(error.message, true); }
  finally { event.target.value = ""; }
});
$("export").addEventListener("click", () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(latest, null, 2)], {type: "application/json"}));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = "crypto-analysis.json"; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
(async () => {
  try {
    const bootstrap = await request("/api/bootstrap");
    token = bootstrap.token; example = bootstrap.example;
    $("title").textContent = bootstrap.title; document.title = bootstrap.title;
    loadExample(); await history();
  } catch (error) { status(error.message, true); $("run").disabled = true; }
})();
