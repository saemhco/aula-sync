(() => {
  "use strict";

  const SESSION_KEY = "aula_sync_session";
  const SIDEBAR_KEY = "aula_sync_sidebar";
  const TAB_TITLES = {
    users: "Migración de usuarios",
    courses: "Migración de cursos",
    categories: "Migración de categorías",
    settings: "Ajustes",
    cycle: "Cerrar ciclo académico",
  };
  const PANEL_TABS = ["users", "courses", "categories", "cycle", "settings"];

  let session = null;
  let appSettings = null;
  let activeTab = "users";
  let routeSyncPaused = false;
  let coursesData = [];
  let categoriesData = [];
  let usersData = [];
  let modalResolve = null;
  let coursesProfeFilter = null;

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ── Routing (hash) ───────────────────────────────────────

  function parseRoute() {
    const raw = location.hash.replace(/^#\/?/, "");
    const [viewPart, queryPart = ""] = raw.split("?");
    const view = viewPart || "users";
    const params = Object.fromEntries(new URLSearchParams(queryPart));
    return { view, params };
  }

  function buildRoute(view, params = {}) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value != null && value !== "") qs.set(key, value);
    });
    const query = qs.toString();
    return `#/${view}${query ? `?${query}` : ""}`;
  }

  function setRoute(view, params = {}, { replace = false } = {}) {
    const hash = buildRoute(view, params);
    if (location.hash === hash) return;
    routeSyncPaused = true;
    if (replace) history.replaceState({ view, params }, "", hash);
    else history.pushState({ view, params }, "", hash);
    routeSyncPaused = false;
  }

  function collectTabParams(tab) {
    if (tab === "courses") {
      return {
        fac: $("#courses-filter-facultad")?.value || "",
        eap: $("#courses-filter-escuela")?.value || "",
        profe: $("#courses-filter-profe")?.value || "",
        q: $("#courses-search")?.value.trim() || "",
        loaded: coursesData.length ? "1" : "",
      };
    }
    if (tab === "users") {
      return {
        tipo: $("#users-tipo")?.value || "2",
        fac: $("#users-filter-facultad")?.value || "",
        eap: $("#users-filter-escuela")?.value || "",
        q: $("#users-search")?.value.trim() || "",
        loaded: usersData.length ? "1" : "",
      };
    }
    return {};
  }

  function syncTabRoute(replace = false) {
    if (!PANEL_TABS.includes(activeTab)) return;
    setRoute(activeTab, collectTabParams(activeTab), { replace });
  }

  async function handleRouteChange() {
    if (routeSyncPaused) return;
    const { view, params } = parseRoute();

    if (view === "login") {
      if (session?.token) return;
      showLogin({ skipRoute: true });
      return;
    }

    if (view === "config") {
      if (!session?.token) {
        setRoute("login", {}, { replace: true });
        showLogin({ skipRoute: true });
        return;
      }
      showSettingsGate({ skipRoute: true });
      return;
    }

    if (!session?.token) {
      setRoute("login", {}, { replace: true });
      showLogin({ skipRoute: true });
      return;
    }

    if (!PANEL_TABS.includes(view)) {
      setRoute(activeTab || "users", {}, { replace: true });
      return;
    }

    if ($("#panel-view").classList.contains("hidden")) {
      await showPanel({ skipRoute: true });
      return;
    }

    activeTab = view;
    switchTab(view, { fromRoute: true });
    await restoreTabState(view, params);
  }

  // ── Session ──────────────────────────────────────────────

  function loadSession() {
    try {
      const raw = sessionStorage.getItem(SESSION_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function saveSession(data) {
    session = data;
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(data));
  }

  function clearSession() {
    session = null;
    sessionStorage.removeItem(SESSION_KEY);
  }

  // ── API ──────────────────────────────────────────────────

  async function api(path, { method = "GET", body, auth = false } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth && session) {
      headers["X-Session-Token"] = session.token;
    }
    const res = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    let data;
    const text = await res.text();
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = text;
    }
    if (!res.ok) {
      const msg = typeof data === "object" && data?.detail
        ? (Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join(", ") : data.detail)
        : (typeof data === "string" ? data : `Error ${res.status}`);
      if (res.status === 401) {
        clearSession();
        showLogin();
      } else if (res.status === 412 && session?.token) {
        setRoute("config", {}, { replace: true });
        showSettingsGate({ skipRoute: true });
      }
      throw new Error(msg);
    }
    return data;
  }

  // ── UI helpers ───────────────────────────────────────────

  function showToast(msg, type = "") {
    const el = $("#toast");
    el.textContent = msg;
    el.className = `toast ${type}`;
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.add("hidden"), 4000);
  }

  function logActivity(msg, type = "") {
    const list = $("#activity-list");
    const li = document.createElement("li");
    const time = new Date().toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    li.innerHTML = `<span class="activity-time">${time}</span><span class="activity-msg ${type}">${escapeHtml(msg)}</span>`;
    list.prepend(li);
    while (list.children.length > 50) list.lastChild.remove();
  }

  function formatMigrationAt(value) {
    if (!value) return "—";
    const normalized = value.includes("T") ? value : `${value.replace(" ", "T")}Z`;
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("es-PE", { dateStyle: "short", timeStyle: "short" });
  }

  function migrationCell(value) {
    if (!value) {
      return `<td class="cell-migration cell-migration-pending">—</td>`;
    }
    const label = formatMigrationAt(value);
    return `<td class="cell-migration cell-migration-done" title="${escapeHtml(label)}">${escapeHtml(label)}</td>`;
  }

  function applyUserMigration(user, migratedAt) {
    if (!user || !migratedAt) return;
    user.ultima_migracion = migratedAt;
  }

  let bulkProgressState = null;

  function startBulkProgress(label, total) {
    bulkProgressState = { total, current: 0, ok: 0, err: 0 };
    $("#bulk-progress-label").textContent = label;
    $("#bulk-progress-detail").textContent = "";
    updateBulkProgressUI();
    $("#bulk-progress").classList.remove("hidden");
  }

  function updateBulkProgressUI() {
    if (!bulkProgressState) return;
    const { total, current, ok, err } = bulkProgressState;
    const pct = total ? Math.round((current / total) * 100) : 0;
    $("#bulk-progress-count").textContent = `${current} / ${total}`;
    $("#bulk-progress-bar").style.width = `${pct}%`;
    const stats = [];
    if (ok) stats.push(`${ok} correctos`);
    if (err) stats.push(`${err} errores`);
    if (stats.length && current > 0) {
      $("#bulk-progress-count").textContent = `${current} / ${total} · ${stats.join(", ")}`;
    }
  }

  function stepBulkProgress(detail, okDelta = 0, errDelta = 0) {
    if (!bulkProgressState) return;
    bulkProgressState.current += 1;
    bulkProgressState.ok += okDelta;
    bulkProgressState.err += errDelta;
    $("#bulk-progress-detail").textContent = detail || "";
    updateBulkProgressUI();
  }

  function finishBulkProgress() {
    $("#bulk-progress").classList.add("hidden");
    bulkProgressState = null;
  }

  function setUsersMigrationBusy(busy) {
    const migrateBtn = $("#users-migrate-selected");
    const loadBtn = $("#users-load");
    const tipoSelect = $("#users-tipo");
    const facSelect = $("#users-filter-facultad");
    const escSelect = $("#users-filter-escuela");
    if (loadBtn) loadBtn.disabled = busy;
    if (tipoSelect) tipoSelect.disabled = busy;
    if (facSelect) facSelect.disabled = busy;
    if (escSelect) escSelect.disabled = busy || !facSelect?.value;
    if (migrateBtn && !busy) {
      updateBulkButton("users");
    } else if (migrateBtn) {
      migrateBtn.disabled = true;
    }
    $$("[data-migrate-user]").forEach((btn) => { btn.disabled = busy; });
    $$(".user-check, #users-select-all").forEach((el) => { el.disabled = busy; });
  }

  function setCoursesMigrationBusy(busy) {
    const migrateBtn = $("#courses-migrate-selected");
    const loadBtn = $("#courses-load");
    if (loadBtn) loadBtn.disabled = busy;
    if (migrateBtn && !busy) {
      updateBulkButton("courses");
    } else if (migrateBtn) {
      migrateBtn.disabled = true;
    }
    $$("[data-migrate-course]").forEach((btn) => { btn.disabled = busy; });
    $$(".course-check, #courses-select-all").forEach((el) => { el.disabled = busy; });
  }

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  function confirmModal(title, body) {
    return new Promise((resolve) => {
      modalResolve = resolve;
      $("#modal-title").textContent = title;
      $("#modal-body").textContent = body;
      $("#modal").classList.remove("hidden");
    });
  }

  function closeModal(result) {
    $("#modal").classList.add("hidden");
    if (modalResolve) {
      modalResolve(result);
      modalResolve = null;
    }
  }

  function setLoading(tbody, cols, msg = "Cargando…") {
    tbody.innerHTML = `<tr class="loading-row"><td colspan="${cols}">${msg}</td></tr>`;
  }

  function filterRows(rows, query, fields) {
    if (!query) return rows;
    const q = query.toLowerCase();
    return rows.filter((r) =>
      fields.some((f) => String(r[f] ?? "").toLowerCase().includes(q))
    );
  }

  function defaultPeriod() {
    const now = new Date();
    const anio = String(now.getFullYear());
    const semestre = now.getMonth() >= 2 && now.getMonth() <= 6 ? "01" : "02";
    return { anio, semestre };
  }

  function activePeriod() {
    return {
      anio: appSettings?.active_anio || defaultPeriod().anio,
      semestre: appSettings?.active_semestre || defaultPeriod().semestre,
    };
  }

  function activePeriodLabel() {
    const { anio, semestre } = activePeriod();
    return `${anio}-${semestre}`;
  }

  function updatePeriodLabels() {
    const label = $("#cycle-period-label");
    if (label) label.textContent = activePeriodLabel();
  }

  // ── Settings ───────────────────────────────────────────

  async function loadSettingsStatus() {
    return api("/settings/status", { auth: true });
  }

  function hideAllViews() {
    $("#settings-gate-view").classList.add("hidden");
    $("#login-view").classList.add("hidden");
    $("#panel-view").classList.add("hidden");
  }

  function settingsSummary() {
    return configSummaryLine();
  }

  function buildConfigPreview(status, scope) {
    const originInput = document.querySelector(`input[name="${scope}-origin"]:checked`);
    const destInput = document.querySelector(`input[name="${scope}-destination"]:checked`);
    const anio = $(`#${scope}-anio`)?.value.trim();
    const semestre = $(`#${scope}-semestre`)?.value;

    const origin = (status.origins || []).find((o) => o.key === originInput?.value);
    const dest = (status.destinations || []).find((d) => String(d.id) === destInput?.value);
    const tokenInput = $(`#${scope}-dest-token`)?.value.trim();

    if (!origin || !dest || !anio || !semestre) {
      return { complete: false, text: "Completa periodo, origen y destino para continuar." };
    }
    if (!dest.has_integration_token && !tokenInput) {
      return { complete: false, text: "Indica el token de integración del destino Moodle seleccionado." };
    }
    return {
      complete: true,
      text: `Migrarás datos de ${origin.label} (${anio}-${semestre}) hacia ${dest.name}.`,
    };
  }

  function updateConfigPreview(scope, status) {
    const el = $(`#${scope}-summary`);
    if (!el) return;
    const preview = buildConfigPreview(status, scope);
    el.className = `settings-summary ${preview.complete ? "" : "empty"}`;
    el.textContent = preview.text;
  }

  function renderSettingsForm(container, status, scope) {
    const selectedOrigin = status.active_origin || "";
    const selectedDest = status.active_destination_id ? String(status.active_destination_id) : "";
    const { anio: defaultAnio, semestre: defaultSem } = defaultPeriod();
    const anio = status.active_anio || defaultAnio;
    const semestre = status.active_semestre || defaultSem;

    const originsHtml = (status.origins || []).map((o) => `
      <label class="origin-option ${selectedOrigin === o.key ? "selected" : ""}">
        <input type="radio" name="${scope}-origin" value="${escapeHtml(o.key)}" ${selectedOrigin === o.key ? "checked" : ""}>
        <div class="origin-option-content">
          <strong>${escapeHtml(o.label)}</strong>
          <span>${escapeHtml(o.faculty_name)}</span>
          <span class="origin-badge">Id_Gen ${escapeHtml(o.id_gen)} · Fac. ${escapeHtml(o.cod_fac)}</span>
        </div>
      </label>
    `).join("");

    const destinations = status.destinations || [];
    const destinationsHtml = destinations.length
      ? destinations.map((d) => `
        <label class="dest-option ${selectedDest === String(d.id) ? "selected" : ""}">
          <input type="radio" name="${scope}-destination" value="${d.id}" ${selectedDest === String(d.id) ? "checked" : ""}>
          <div class="dest-option-content">
            <strong>${escapeHtml(d.name)}</strong>
            <span>${escapeHtml(d.moodle_public_url)}</span>
            <span class="origin-badge">${d.has_integration_token ? "Token configurado" : "Sin token"}</span>
          </div>
        </label>
      `).join("")
      : `<div class="settings-empty">Aún no hay aulas virtuales. Expande «Agregar aula virtual» para registrar una.</div>`;

    container.innerHTML = `
      <div class="settings-steps">
        <section class="settings-step">
          <div class="settings-step-header">
            <div class="settings-step-num">1</div>
            <div class="settings-step-title">
              <h3>Periodo académico</h3>
              <p>Cursos, docentes y matrículas se filtran por este ciclo. Actualízalo cuando cambien asignaciones o se abran nuevas aulas.</p>
            </div>
          </div>
          <div class="settings-step-body">
            <div class="period-fields">
              <label>Año académico
                <input type="text" id="${scope}-anio" maxlength="4" inputmode="numeric" placeholder="2026" value="${escapeHtml(anio)}">
              </label>
              <label>Semestre
                <select id="${scope}-semestre">
                  <option value="00" ${semestre === "00" ? "selected" : ""}>00 — Anual</option>
                  <option value="01" ${semestre === "01" ? "selected" : ""}>01 — Primer semestre</option>
                  <option value="02" ${semestre === "02" ? "selected" : ""}>02 — Segundo semestre</option>
                </select>
              </label>
              <p class="period-hint">Tip: al inicio de ciclo revisa docentes titulares y cursos nuevos antes de migrar.</p>
            </div>
          </div>
        </section>

        <section class="settings-step">
          <div class="settings-step-header">
            <div class="settings-step-num">2</div>
            <div class="settings-step-title">
              <h3>Origen de datos</h3>
              <p>Base académica UNHEVAL de donde se leen cursos, usuarios y matrículas.</p>
            </div>
          </div>
          <div class="settings-step-body">
            <div class="origin-grid">${originsHtml}</div>
          </div>
        </section>

        <section class="settings-step">
          <div class="settings-step-header">
            <div class="settings-step-num">3</div>
            <div class="settings-step-title">
              <h3>Destino Moodle</h3>
              <p>Aula virtual donde se crearán o actualizarán los cursos migrados.</p>
            </div>
          </div>
          <div class="settings-step-body">
            <div class="dest-list">${destinationsHtml}</div>
            <div class="settings-form-grid" style="margin-top:16px">
              <label class="full">Token de integración (plugin local_aulasync)
                <input type="password" id="${scope}-dest-token" placeholder="aulasync_..." autocomplete="off" spellcheck="false">
              </label>
              <p class="period-hint full">Generado en Moodle → Plugins locales → Integración Aula Sync. Si el destino ya tiene token, déjalo vacío o escribe uno nuevo para reemplazarlo.</p>
            </div>
            <details class="settings-add-dest">
              <summary>+ Agregar aula virtual</summary>
              <div class="settings-add-inner">
                <div class="settings-form-grid">
                  <label class="full">Nombre identificador
                    <input type="text" id="${scope}-dest-name" placeholder="Ej. Moodle postgrado producción">
                  </label>
                  <label>URL API (Docker)
                    <input type="url" id="${scope}-dest-url" placeholder="http://host.docker.internal:8046">
                  </label>
                  <label>URL pública (navegador)
                    <input type="url" id="${scope}-dest-public" placeholder="http://localhost:8046">
                  </label>
                  <label class="full">Token de integración
                    <input type="password" id="${scope}-dest-new-token" placeholder="aulasync_..." autocomplete="off" spellcheck="false">
                  </label>
                </div>
                <div class="settings-actions" style="margin-top:12px">
                  <button type="button" class="btn btn-secondary btn-sm" id="${scope}-add-dest">Registrar destino</button>
                </div>
              </div>
            </details>
          </div>
        </section>
      </div>

      <div id="${scope}-summary" class="settings-summary empty">Completa periodo, origen y destino para continuar.</div>

      <div class="settings-footer">
        <p id="${scope}-settings-error" class="form-error hidden" style="margin:0"></p>
        <button type="button" class="btn btn-primary" id="${scope}-save-active">${scope === "panel" ? "Actualizar configuración" : "Guardar y continuar"}</button>
      </div>
    `;

    const onSelectionChange = () => updateConfigPreview(scope, status);

    container.querySelectorAll(".origin-option input, .dest-option input").forEach((input) => {
      input.addEventListener("change", () => {
        container.querySelectorAll(".origin-option, .dest-option").forEach((el) => el.classList.remove("selected"));
        input.closest(".origin-option, .dest-option")?.classList.add("selected");
        onSelectionChange();
      });
    });

    $(`#${scope}-anio`).addEventListener("input", onSelectionChange);
    $(`#${scope}-semestre`).addEventListener("change", onSelectionChange);
    $(`#${scope}-dest-token`)?.addEventListener("input", onSelectionChange);

    $(`#${scope}-add-dest`).addEventListener("click", () => handleAddDestination(scope));
    $(`#${scope}-save-active`).addEventListener("click", () => handleSaveActiveConfig(scope));

    updateConfigPreview(scope, status);
  }

  async function refreshSettingsViews() {
    appSettings = await loadSettingsStatus();
    renderSettingsForm($("#settings-gate-form"), appSettings, "gate");
    renderSettingsForm($("#settings-panel-form"), appSettings, "panel");
    const summary = settingsSummary();
    if ($("#login-config-info")) {
      $("#login-config-info").textContent = summary || "Configura origen y destino en Ajustes";
    }
  }

  async function handleAddDestination(scope) {
    const errEl = $(`#${scope}-settings-error`);
    errEl.classList.add("hidden");
    const name = $(`#${scope}-dest-name`).value.trim();
    const moodle_url = $(`#${scope}-dest-url`).value.trim();
    const moodle_public_url = $(`#${scope}-dest-public`).value.trim();
    const integration_token = $(`#${scope}-dest-new-token`).value.trim();
    if (!name || !moodle_url || !moodle_public_url || !integration_token) {
      errEl.textContent = "Completa nombre, URLs y token del destino Moodle";
      errEl.classList.remove("hidden");
      return;
    }
    try {
      await api("/settings/destinations", {
        method: "POST",
        auth: true,
        body: { name, moodle_url, moodle_public_url, integration_token },
      });
      showToast("Destino agregado", "success");
      await refreshSettingsViews();
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.remove("hidden");
    }
  }

  async function handleSaveActiveConfig(scope) {
    const errEl = $(`#${scope}-settings-error`);
    errEl.classList.add("hidden");
    const originInput = document.querySelector(`input[name="${scope}-origin"]:checked`);
    const destInput = document.querySelector(`input[name="${scope}-destination"]:checked`);
    const anio = $(`#${scope}-anio`).value.trim();
    const semestre = $(`#${scope}-semestre`).value;

    if (!anio || anio.length !== 4 || !/^\d{4}$/.test(anio)) {
      errEl.textContent = "Indica un año académico válido (4 dígitos)";
      errEl.classList.remove("hidden");
      return;
    }
    if (!semestre) {
      errEl.textContent = "Selecciona el semestre académico";
      errEl.classList.remove("hidden");
      return;
    }
    if (!originInput) {
      errEl.textContent = "Selecciona un origen de datos";
      errEl.classList.remove("hidden");
      return;
    }
    if (!destInput) {
      errEl.textContent = "Selecciona o agrega un destino Moodle";
      errEl.classList.remove("hidden");
      return;
    }
    const integration_token = $(`#${scope}-dest-token`)?.value.trim() || "";
    const selectedDest = (appSettings.destinations || []).find((d) => String(d.id) === destInput.value);
    if (selectedDest && !selectedDest.has_integration_token && !integration_token) {
      errEl.textContent = "Indica el token de integración del destino Moodle";
      errEl.classList.remove("hidden");
      return;
    }
    try {
      appSettings = await api("/settings/active", {
        method: "PUT",
        auth: true,
        body: {
          origin_key: originInput.value,
          destination_id: Number(destInput.value),
          anio,
          semestre,
          ...(integration_token ? { integration_token } : {}),
        },
      });
      showToast("Configuración guardada", "success");
      logActivity(`Periodo ${anio}-${semestre}: ${appSettings.origin?.label} → ${appSettings.destination?.name}`, "success");
      if (!appSettings.configured) {
        errEl.textContent = "No se pudo activar la configuración";
        errEl.classList.remove("hidden");
        return;
      }
      syncSessionFromSettings();
      updateConfigSummary();
      if (scope === "panel") {
        updatePeriodLabels();
        showToast("Configuración actualizada", "success");
        setRoute("users", {}, { replace: true });
        switchTab("users");
        await restoreTabState("users", {});
        return;
      }
      hideAllViews();
      setRoute("users", {}, { replace: true });
      await showPanel({ skipRoute: true });
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.remove("hidden");
    }
  }

  function syncSessionFromSettings() {
    if (!session || !appSettings?.configured) return;
    session.origin_label = appSettings.origin?.label || session.origin_label;
    session.destination_name = appSettings.destination?.name || session.destination_name;
    session.area = appSettings.origin?.area || session.area;
    session.moodle_url = appSettings.destination?.moodle_url || session.moodle_url;
    session.moodle_public_url = appSettings.destination?.moodle_public_url || session.moodle_public_url;
    session.server = appSettings.origin?.key || session.server;
    saveSession(session);
  }

  function configSummaryLine() {
    if (!appSettings?.configured) return "";
    const origin = appSettings.origin?.label || appSettings.active_origin || "Origen";
    const dest = appSettings.destination?.name || "Moodle";
    const period = appSettings.active_anio && appSettings.active_semestre
      ? `${appSettings.active_anio}-${appSettings.active_semestre}`
      : "";
    return period ? `Periodo ${period}: ${origin} → ${dest}` : `${origin} → ${dest}`;
  }

  function updateConfigSummary() {
    const header = $("#panel-header");
    const textEl = $("#config-summary-text");
    if (!header || !textEl) return;

    if (!appSettings?.configured) {
      header.classList.add("hidden");
      return;
    }

    const line = configSummaryLine();
    const match = line.match(/^Periodo (.+?): (.+) → (.+)$/);
    if (match) {
      textEl.innerHTML = `<span class="summary-period">Periodo ${escapeHtml(match[1])}:</span> <span class="summary-route">${escapeHtml(match[2])} → ${escapeHtml(match[3])}</span>`;
    } else {
      textEl.textContent = line;
    }
    header.classList.remove("hidden");
  }

  function openSettingsTab() {
    setSidebarCollapsed(false);
    switchTab("settings");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function isMobileLayout() {
    return window.matchMedia("(max-width: 768px)").matches;
  }

  function setSidebarCollapsed(collapsed) {
    const panel = $("#panel-view");
    const fab = $("#sidebar-expand");
    if (!panel) return;
    if (isMobileLayout()) {
      panel.classList.toggle("sidebar-mobile-open", !collapsed);
      if (fab) fab.classList.toggle("hidden", !collapsed);
      return;
    }
    panel.classList.remove("sidebar-mobile-open");
    panel.classList.toggle("sidebar-collapsed", collapsed);
    if (fab) fab.classList.toggle("hidden", !collapsed);
    sessionStorage.setItem(SIDEBAR_KEY, collapsed ? "1" : "0");
  }

  function toggleSidebar() {
    const panel = $("#panel-view");
    if (!panel) return;
    if (isMobileLayout()) {
      const open = panel.classList.contains("sidebar-mobile-open");
      setSidebarCollapsed(open);
      return;
    }
    setSidebarCollapsed(!panel.classList.contains("sidebar-collapsed"));
  }

  function initSidebar() {
    if (isMobileLayout()) {
      setSidebarCollapsed(true);
      return;
    }
    if (sessionStorage.getItem(SIDEBAR_KEY) === "1") {
      setSidebarCollapsed(true);
    }
  }

  function userInitials(username) {
    if (!username) return "?";
    const parts = username.trim().split(/[\s._-]+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return username.slice(0, 2).toUpperCase();
  }

  function updateUserHeader() {
    const username = session?.username || "Usuario";
    const initials = userInitials(username);
    const avatarEls = [$("#user-avatar"), $("#user-avatar-lg")];
    avatarEls.forEach((el) => { if (el) el.textContent = initials; });
    const nameEls = [$("#user-name"), $("#user-dropdown-name")];
    nameEls.forEach((el) => { if (el) el.textContent = username; });
  }

  function closeAccountModal() {
    $("#account-modal")?.classList.add("hidden");
    $("#account-form")?.reset();
    const err = $("#account-form-error");
    if (err) err.classList.add("hidden");
  }

  function openAccountModal() {
    closeUserDropdown();
    const usernameInput = $("#account-new-username");
    if (usernameInput) usernameInput.placeholder = session?.username || "Dejar vacío para no cambiar";
    $("#account-modal")?.classList.remove("hidden");
    $("#account-current-password")?.focus();
  }

  async function handleAccountSubmit(e) {
    e.preventDefault();
    const errEl = $("#account-form-error");
    const btn = $("#account-save-btn");
    errEl.classList.add("hidden");

    const currentPassword = $("#account-current-password").value;
    const newUsername = $("#account-new-username").value.trim();
    const newPassword = $("#account-new-password").value;
    const confirmPassword = $("#account-new-password-confirm").value;

    if (!newUsername && !newPassword) {
      errEl.textContent = "Indica un nuevo usuario o contraseña";
      errEl.classList.remove("hidden");
      return;
    }
    if (newPassword && newPassword.length < 8) {
      errEl.textContent = "La nueva contraseña debe tener al menos 8 caracteres";
      errEl.classList.remove("hidden");
      return;
    }
    if (newPassword !== confirmPassword) {
      errEl.textContent = "Las contraseñas nuevas no coinciden";
      errEl.classList.remove("hidden");
      return;
    }

    const body = { current_password: currentPassword };
    if (newUsername) body.new_username = newUsername;
    if (newPassword) body.new_password = newPassword;

    btn.disabled = true;
    btn.textContent = "Guardando…";
    try {
      const result = await api("/auth/credentials", { method: "PUT", auth: true, body });
      session.username = result.username;
      saveSession(session);
      updateUserHeader();
      closeAccountModal();
      showToast("Datos de acceso actualizados", "success");
      logActivity(`Cuenta actualizada: ${result.username}`, "success");
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.remove("hidden");
    } finally {
      btn.disabled = false;
      btn.textContent = "Guardar cambios";
    }
  }

  function closeUserDropdown() {
    const btn = $("#header-user-btn");
    const dd = $("#user-dropdown");
    if (dd) dd.classList.add("hidden");
    if (btn) {
      btn.classList.remove("open");
      btn.setAttribute("aria-expanded", "false");
    }
  }

  function toggleUserDropdown() {
    const btn = $("#header-user-btn");
    const dd = $("#user-dropdown");
    if (!btn || !dd) return;
    const willOpen = dd.classList.contains("hidden");
    if (willOpen) {
      dd.classList.remove("hidden");
      btn.classList.add("open");
      btn.setAttribute("aria-expanded", "true");
    } else {
      closeUserDropdown();
    }
  }

  function applyPeriodFromSettings() {
    updatePeriodLabels();
  }

  function showSettingsGate(opts = {}) {
    if (!session?.token) {
      showLogin(opts);
      return;
    }
    hideAllViews();
    $("#settings-gate-view").classList.remove("hidden");
    refreshSettingsViews();
    if (!opts.skipRoute) setRoute("config", {}, { replace: true });
  }

  // ── Views ────────────────────────────────────────────────

  function showLogin(opts = {}) {
    hideAllViews();
    $("#login-view").classList.remove("hidden");
    if (appSettings?.configured) {
      $("#login-config-info").textContent = settingsSummary();
    }
    checkDbStatus($("#db-status-login"));
    if (!opts.skipRoute) setRoute("login", {}, { replace: true });
  }

  async function showPanel(opts = {}) {
    hideAllViews();
    $("#panel-view").classList.remove("hidden");
    try {
      appSettings = await loadSettingsStatus();
    } catch {
      /* mantener appSettings previo si falla */
    }
    updateConfigSummary();
    initSidebar();
    updateUserHeader();
    applyPeriodFromSettings();
    checkDbStatus($("#db-status"));

    const { view, params } = parseRoute();
    const tab = PANEL_TABS.includes(view) ? view : "users";
    activeTab = tab;
    if (!opts.skipRoute && !PANEL_TABS.includes(view)) {
      setRoute(tab, params, { replace: true });
    }
    switchTab(tab, { fromRoute: true });
    await restoreTabState(tab, params);
  }

  async function restoreTabState(tab, params = {}) {
    if (tab === "courses") {
      await preloadCourseFilters();
      if (params.fac) $("#courses-filter-facultad").value = params.fac;
      await refreshCourseEscuelas();
      if (params.eap) $("#courses-filter-escuela").value = params.eap;
      await refreshCourseProfesores();
      if (params.profe) coursesProfeFilter?.setValue(params.profe);
      if (params.q) $("#courses-search").value = params.q;
      if (params.loaded === "1") await loadCourses({ skipRoute: true });
      else showCoursesEmpty();
      return;
    }
    if (tab === "users") {
      if (params.tipo) $("#users-tipo").value = params.tipo;
      await preloadUserFilters();
      if (params.fac) $("#users-filter-facultad").value = params.fac;
      await refreshUserEscuelas();
      if (params.eap) $("#users-filter-escuela").value = params.eap;
      if (params.q) $("#users-search").value = params.q;
      if (params.loaded === "1") await loadUsers({ skipRoute: true });
      else showUsersEmpty();
    }
  }

  async function checkDbStatus(el) {
    if (!el) return;
    try {
      const data = await api("/health");
      const ok = data.database === "connected";
      const detail = ok ? "" : (data.database || "Sin respuesta de la BD");
      if (el.id === "db-status-login") {
        el.className = `status-dot ${ok ? "ok" : "error"}`;
        el.textContent = ok ? "BD conectada" : "BD sin conexión";
        el.title = detail;
        return;
      }
      const btn = $("#header-db-status");
      const dot = $("#header-db-dot");
      const label = $("#db-status");
      if (btn && dot && label) {
        btn.classList.toggle("db-ok", ok);
        btn.classList.toggle("db-error", !ok);
        dot.className = `header-db-dot ${ok ? "ok" : "error"}`;
        label.textContent = ok ? "Conectada" : "Sin conexión";
        btn.title = ok ? "Base de datos conectada" : "Base de datos sin conexión";
      }
    } catch (err) {
      if (el.id === "db-status-login") {
        el.className = "status-dot error";
        el.textContent = "BD sin conexión";
        el.title = err?.message || "No se pudo contactar la API";
        return;
      }
      const btn = $("#header-db-status");
      const dot = $("#header-db-dot");
      const label = $("#db-status");
      if (btn && dot && label) {
        btn.classList.remove("db-ok");
        btn.classList.add("db-error");
        dot.className = "header-db-dot error";
        label.textContent = "Sin conexión";
        btn.title = "Base de datos sin conexión";
      }
    }
  }

  function switchTab(tab, opts = {}) {
    activeTab = tab;
    $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
    $$(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${tab}`));
    $("#page-title").textContent = TAB_TITLES[tab] || tab;
    if (tab === "settings") refreshSettingsViews();
    if (isMobileLayout()) setSidebarCollapsed(true);
    if (!opts.fromRoute && PANEL_TABS.includes(tab)) {
      if (tab === "courses") coursesData = [];
      if (tab === "users") usersData = [];
      setRoute(tab, {}, { replace: false });
      if (tab === "courses" || tab === "users") void restoreTabState(tab, {});
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    const btn = $("#login-btn");
    const errEl = $("#login-error");
    errEl.classList.add("hidden");
    btn.disabled = true;
    btn.textContent = "Conectando…";

    try {
      const result = await api("/auth/login", {
        method: "POST",
        body: {
          username: $("#login-username").value.trim(),
          password: $("#login-password").value,
        },
      });
      if (!result.status || !result.token) {
        throw new Error("Usuario o contraseña incorrectos");
      }
      saveSession({
        ...result,
        username: result.username || $("#login-username").value.trim(),
      });
      appSettings = await loadSettingsStatus();
      if (!appSettings.configured) {
        setRoute("config", {}, { replace: true });
        showSettingsGate({ skipRoute: true });
        logActivity("Sesión iniciada — completa la configuración del sistema", "success");
      } else {
        setRoute("users", {}, { replace: true });
        await showPanel({ skipRoute: true });
        logActivity(`Sesión iniciada: ${settingsSummary()}`, "success");
      }
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.remove("hidden");
    } finally {
      btn.disabled = false;
      btn.textContent = "Iniciar sesión";
    }
  }

  // ── Searchable select ────────────────────────────────────

  function createSearchSelect({ hidden, input, dropdown, placeholder, emptyLabel, onChange }) {
    let options = [];
    let enabled = false;
    let activeIndex = -1;

    function renderDropdown(filter = "") {
      const q = filter.trim().toLowerCase();
      const filtered = q
        ? options.filter(
            (option) =>
              option.label.toLowerCase().includes(q) || option.value.toLowerCase().includes(q)
          )
        : options;
      activeIndex = -1;

      if (!filtered.length) {
        dropdown.innerHTML = `<div class="search-select-empty">Sin coincidencias</div>`;
        return;
      }

      dropdown.innerHTML = [
        `<button type="button" class="search-select-option search-select-option-all" data-value="">${escapeHtml(emptyLabel)}</button>`,
        ...filtered.map(
          (option) =>
            `<button type="button" class="search-select-option" data-value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</button>`
        ),
      ].join("");
    }

    function open() {
      if (!enabled) return;
      dropdown.classList.remove("hidden");
      renderDropdown(input.value);
    }

    function close() {
      dropdown.classList.add("hidden");
      activeIndex = -1;
    }

    function syncInputLabel() {
      const value = hidden.value;
      if (!value) {
        input.placeholder = placeholder;
        if (document.activeElement !== input) input.value = "";
        return;
      }
      const match = options.find((option) => option.value === value);
      input.value = match ? match.label : value;
    }

    function select(value) {
      hidden.value = value;
      syncInputLabel();
      close();
      onChange?.();
    }

    function setOptions(items, { getValue, getLabel, enabled: isEnabled = true, preserveValue = true } = {}) {
      const previous = preserveValue ? hidden.value : "";
      options = items.map((item) => ({
        value: String(getValue(item)),
        label: String(getLabel(item)),
      }));
      enabled = isEnabled;
      input.disabled = !isEnabled;
      if (!isEnabled) {
        hidden.value = "";
        input.value = "";
        input.placeholder = placeholder;
        close();
        return;
      }
      if (previous && options.some((option) => option.value === previous)) {
        hidden.value = previous;
      } else if (previous) {
        hidden.value = "";
      }
      syncInputLabel();
    }

    function setValue(value) {
      hidden.value = value || "";
      syncInputLabel();
    }

    function clear(triggerChange = true) {
      hidden.value = "";
      input.value = "";
      input.placeholder = placeholder;
      close();
      if (triggerChange) onChange?.();
    }

    function moveActive(delta) {
      const buttons = [...dropdown.querySelectorAll(".search-select-option")];
      if (!buttons.length) return;
      activeIndex = Math.max(0, Math.min(buttons.length - 1, activeIndex + delta));
      buttons.forEach((button, index) => button.classList.toggle("active", index === activeIndex));
      buttons[activeIndex]?.scrollIntoView({ block: "nearest" });
    }

    input.addEventListener("focus", () => {
      if (!enabled) return;
      open();
    });

    input.addEventListener("input", () => {
      if (!enabled) return;
      hidden.value = "";
      open();
      renderDropdown(input.value);
    });

    input.addEventListener("blur", () => {
      setTimeout(() => {
        close();
        syncInputLabel();
      }, 120);
    });

    input.addEventListener("keydown", (e) => {
      if (!enabled) return;
      if (e.key === "Escape") {
        close();
        syncInputLabel();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (dropdown.classList.contains("hidden")) open();
        moveActive(1);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        moveActive(-1);
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        const buttons = dropdown.querySelectorAll(".search-select-option");
        const target = activeIndex >= 0 ? buttons[activeIndex] : buttons[0];
        if (target) select(target.dataset.value);
      }
    });

    dropdown.addEventListener("mousedown", (e) => {
      e.preventDefault();
    });

    dropdown.addEventListener("click", (e) => {
      const button = e.target.closest(".search-select-option");
      if (!button) return;
      select(button.dataset.value);
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".search-select")) close();
    });

    return { setOptions, setValue, clear, close, getValue: () => hidden.value };
  }

  function initCourseSearchFilters() {
    coursesProfeFilter = createSearchSelect({
      hidden: $("#courses-filter-profe"),
      input: $("#courses-filter-profe-input"),
      dropdown: $("#courses-filter-profe-dropdown"),
      placeholder: "Buscar profesor…",
      emptyLabel: "Todos los profesores",
      onChange: onCourseProfeChange,
    });
  }

  // ── Cursos ───────────────────────────────────────────────

  function fillFilterSelect(select, items, valueKey, labelKey, placeholder, { enabled = true } = {}) {
    if (!select) return;
    const current = select.value;
    select.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>${items
      .map((item) => {
        const value = String(item[valueKey] ?? "");
        const label = String(item[labelKey] ?? value);
        return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
      })
      .join("")}`;
    select.disabled = !enabled;
    if (current && items.some((item) => String(item[valueKey]) === current)) {
      select.value = current;
    }
  }

  function fillProfeSelect(items, placeholder, enabled = true, preserveValue = true) {
    if (!coursesProfeFilter) return;
    coursesProfeFilter.setOptions(items, {
      getValue: (item) => item.profe ?? item,
      getLabel: (item) => {
        const value = String(item.profe ?? item);
        return item.nombre ? `${value} - ${item.nombre}` : value;
      },
      enabled,
      preserveValue,
    });
  }

  function showCoursesEmpty(msg = "Selecciona filtros y pulsa «Cargar cursos».") {
    coursesData = [];
    const tbody = $("#courses-tbody");
    if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="empty">${escapeHtml(msg)}</td></tr>`;
    $("#courses-select-all").checked = false;
    updateBulkButton("courses");
  }

  async function preloadCourseFilters() {
    const facs = await api("/courses/filters/facultades", { auth: true });
    fillFilterSelect(
      $("#courses-filter-facultad"),
      facs,
      "cod_fac",
      "facultad",
      "Todas las facultades",
      { enabled: true }
    );
  }

  async function refreshCourseEscuelas() {
    const fac = $("#courses-filter-facultad")?.value || "";
    const escSelect = $("#courses-filter-escuela");
    if (!fac) {
      fillFilterSelect(escSelect, [], "cod_eap", "escuela", "Todas las escuelas", { enabled: false });
      return;
    }
    const qs = new URLSearchParams({ fac });
    const escuelas = await api(`/courses/filters/escuelas?${qs}`, { auth: true });
    fillFilterSelect(escSelect, escuelas, "cod_eap", "escuela", "Todas las escuelas", { enabled: true });
  }

  async function refreshCourseProfesores() {
    const fac = $("#courses-filter-facultad")?.value || "";
    const eap = $("#courses-filter-escuela")?.value || "";
    if (!fac) {
      fillProfeSelect([], "Todos los profesores", false);
      return;
    }
    const qs = new URLSearchParams();
    qs.set("fac", fac);
    if (eap) qs.set("eap", eap);
    const profesores = await api(`/courses/filters/profesores?${qs}`, { auth: true });
    fillProfeSelect(profesores, "Todos los profesores", true);
  }

  async function cascadeCourseFilters() {
    await refreshCourseEscuelas();
    await refreshCourseProfesores();
  }

  function getFilteredCourses() {
    const query = $("#courses-search").value.trim();
    return filterRows(coursesData, query, ["facultad", "escuela", "curso", "codcurso", "profe", "codicur"]);
  }

  async function onCourseFacultyChange() {
    $("#courses-filter-escuela").value = "";
    coursesProfeFilter?.clear(false);
    showCoursesEmpty();
    await cascadeCourseFilters();
    syncTabRoute(true);
  }

  async function onCourseEscuelaChange() {
    coursesProfeFilter?.clear(false);
    showCoursesEmpty();
    await refreshCourseProfesores();
    syncTabRoute(true);
  }

  function onCourseProfeChange() {
    showCoursesEmpty();
    syncTabRoute(true);
  }

  async function loadCourses(opts = {}) {
    const { anio, semestre } = activePeriod();
    const tbody = $("#courses-tbody");
    setLoading(tbody, 8);
    const qs = new URLSearchParams();
    const fac = $("#courses-filter-facultad")?.value || "";
    const eap = $("#courses-filter-escuela")?.value || "";
    const profe = $("#courses-filter-profe")?.value || "";
    if (fac) qs.set("fac", fac);
    if (eap) qs.set("eap", eap);
    if (profe) qs.set("profe", profe);
    try {
      const path = qs.toString() ? `/courses?${qs}` : "/courses";
      coursesData = await api(path, { auth: true });
      renderCourses();
      logActivity(`${coursesData.length} cursos cargados (${anio}-${semestre})`, "success");
      if (!opts.skipRoute) syncTabRoute(true);
    } catch (err) {
      coursesData = [];
      tbody.innerHTML = `<tr><td colspan="8" class="empty">${escapeHtml(err.message)}</td></tr>`;
      logActivity(`Error al cargar cursos: ${err.message}`, "error");
      if (!opts.skipRoute) syncTabRoute(true);
    }
  }

  function renderCourses() {
    const rows = getFilteredCourses();
    const tbody = $("#courses-tbody");
    $("#courses-select-all").checked = false;
    updateBulkButton("courses");

    if (!rows.length) {
      const hasSearch = $("#courses-search").value.trim();
      const emptyMsg = !coursesData.length
        ? "Sin resultados para los filtros seleccionados."
        : (hasSearch ? "Sin resultados con la búsqueda." : "Sin resultados.");
      tbody.innerHTML = `<tr><td colspan="8" class="empty">${emptyMsg}</td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map((c, i) => {
      const idx = coursesData.indexOf(c);
      return `<tr>
        <td><input type="checkbox" class="course-check" data-idx="${idx}"></td>
        <td class="cell-truncate" title="${escapeHtml(c.facultad || "")}">${escapeHtml(c.facultad || "")}</td>
        <td class="cell-truncate" title="${escapeHtml(c.escuela || "")}">${escapeHtml(c.escuela || "")}</td>
        <td class="cell-truncate" title="${escapeHtml(c.curso)}">${escapeHtml(c.curso)}</td>
        <td class="cell-mono">${escapeHtml(c.codcurso)}</td>
        <td>${escapeHtml(c.grupo)}</td>
        <td class="cell-mono">${escapeHtml(c.profe)}</td>
        <td class="col-action"><button class="btn btn-primary btn-action" data-migrate-course="${idx}">Migrar</button></td>
      </tr>`;
    }).join("");
  }

  async function migrateCourse(course) {
    const { anio, semestre } = activePeriod();
    const body = {
      codcurso: course.codcurso,
      profesor: course.profe,
      grupo: course.grupo,
      nomcurso: course.curso,
      anio,
      semestre,
      fac: course.fac,
      eap: course.eap,
      codicur: course.codicur,
      tipacta: course.tipacta || "01",
      seccion: course.seccion || "",
    };
    const result = await api("/courses/migrate", { method: "POST", auth: true, body });
    return result;
  }

  async function handleMigrateCourse(idx) {
    const course = coursesData[idx];
    if (!course) return;
    const ok = await confirmModal(
      "Migrar curso",
      `¿Migrar "${course.curso}" (${course.codcurso}) a Moodle?`
    );
    if (!ok) return;

    try {
      const result = await migrateCourse(course);
      const msg = result?.message || result?.status || JSON.stringify(result);
      logActivity(`Curso migrado: ${course.codcurso} — ${msg}`, "success");
      showToast("Curso migrado correctamente", "success");
    } catch (err) {
      logActivity(`Error migrando ${course.codcurso}: ${err.message}`, "error");
      showToast(err.message, "error");
    }
  }

  async function migrateSelectedCourses() {
    const checks = $$(".course-check:checked");
    if (!checks.length) return;
    const ok = await confirmModal(
      "Migrar cursos seleccionados",
      `Se migrarán ${checks.length} curso(s). Esta operación puede tardar varios minutos.`
    );
    if (!ok) return;

    const courses = [...checks]
      .map((chk) => coursesData[Number(chk.dataset.idx)])
      .filter(Boolean);

    startBulkProgress("Migrando cursos…", courses.length);
    setCoursesMigrationBusy(true);

    let okCount = 0;
    let errCount = 0;
    try {
      for (const course of courses) {
        $("#bulk-progress-detail").textContent = `Procesando ${course.codcurso}…`;
        try {
          await migrateCourse(course);
          okCount++;
          logActivity(`✓ ${course.codcurso}`, "success");
          stepBulkProgress(`✓ ${course.codcurso}`, 1, 0);
        } catch (err) {
          errCount++;
          logActivity(`✗ ${course.codcurso}: ${err.message}`, "error");
          stepBulkProgress(`✗ ${course.codcurso}: ${err.message}`, 0, 1);
        }
      }
    } finally {
      finishBulkProgress();
      setCoursesMigrationBusy(false);
      showToast(`${okCount} migrados, ${errCount} errores`, errCount ? "error" : "success");
      renderCourses();
    }
  }

  // ── Usuarios ─────────────────────────────────────────────

  function showUsersEmpty(msg = "Selecciona filtros y pulsa «Listar usuarios».") {
    usersData = [];
    const tbody = $("#users-tbody");
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="empty">${escapeHtml(msg)}</td></tr>`;
    $("#users-select-all").checked = false;
    updateBulkButton("users");
  }

  async function preloadUserFilters() {
    const tipo = $("#users-tipo")?.value || "2";
    const facs = await api(`/users/filters/facultades?tipo=${encodeURIComponent(tipo)}`, { auth: true });
    fillFilterSelect(
      $("#users-filter-facultad"),
      facs,
      "cod_fac",
      "facultad",
      "Todas las facultades",
      { enabled: true }
    );
  }

  async function refreshUserEscuelas() {
    const tipo = $("#users-tipo")?.value || "2";
    const fac = $("#users-filter-facultad")?.value || "";
    const escSelect = $("#users-filter-escuela");
    if (!fac) {
      fillFilterSelect(escSelect, [], "cod_eap", "escuela", "Todas las escuelas", { enabled: false });
      return;
    }
    const qs = new URLSearchParams({ tipo, fac });
    const escuelas = await api(`/users/filters/escuelas?${qs}`, { auth: true });
    fillFilterSelect(escSelect, escuelas, "cod_eap", "escuela", "Todas las escuelas", { enabled: true });
  }

  async function cascadeUserFilters() {
    await refreshUserEscuelas();
  }

  async function onUsersTipoChange() {
    $("#users-filter-facultad").value = "";
    $("#users-filter-escuela").value = "";
    showUsersEmpty();
    await preloadUserFilters();
    await cascadeUserFilters();
    syncTabRoute(true);
  }

  async function onUserFacultyChange() {
    $("#users-filter-escuela").value = "";
    showUsersEmpty();
    await cascadeUserFilters();
    syncTabRoute(true);
  }

  function onUserEscuelaChange() {
    showUsersEmpty();
    syncTabRoute(true);
  }

  async function loadUsers(opts = {}) {
    const tipo = $("#users-tipo").value;
    const { anio, semestre } = activePeriod();
    const tbody = $("#users-tbody");
    setLoading(tbody, 7);
    const qs = new URLSearchParams({ tipo });
    const fac = $("#users-filter-facultad")?.value || "";
    const eap = $("#users-filter-escuela")?.value || "";
    if (fac) qs.set("fac", fac);
    if (eap) qs.set("eap", eap);
    try {
      usersData = await api(`/users?${qs}`, { auth: true });
      renderUsers();
      const label = tipo === "1" ? "alumnos" : "docentes";
      logActivity(`${usersData.length} ${label} cargados (${anio}-${semestre})`, "success");
      if (!opts.skipRoute) syncTabRoute(true);
    } catch (err) {
      usersData = [];
      tbody.innerHTML = `<tr><td colspan="7" class="empty">${escapeHtml(err.message)}</td></tr>`;
      logActivity(`Error al cargar usuarios: ${err.message}`, "error");
      if (!opts.skipRoute) syncTabRoute(true);
    }
  }

  function renderUsers() {
    const query = $("#users-search").value.trim();
    const rows = filterRows(usersData, query, ["apellidos", "nombres", "usuario", "correo"]);
    const tbody = $("#users-tbody");
    $("#users-select-all").checked = false;
    updateBulkButton("users");

    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty">${usersData.length ? "Sin resultados." : "No hay usuarios."}</td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map((u) => {
      const idx = usersData.indexOf(u);
      return `<tr>
        <td><input type="checkbox" class="user-check" data-idx="${idx}"></td>
        <td>${escapeHtml(u.apellidos)}</td>
        <td>${escapeHtml(u.nombres)}</td>
        <td class="cell-mono">${escapeHtml(u.usuario)}</td>
        <td class="cell-truncate">${escapeHtml(u.correo)}</td>
        ${migrationCell(u.ultima_migracion)}
        <td class="col-action"><button class="btn btn-primary btn-action" data-migrate-user="${idx}">Migrar</button></td>
      </tr>`;
    }).join("");
  }

  async function migrateUser(user) {
    return api("/users/migrate", {
      method: "POST",
      auth: true,
      body: {
        usuario: user.usuario,
        nombres: user.nombres,
        apellidos: user.apellidos,
        email: user.correo,
      },
    });
  }

  async function handleMigrateUser(idx) {
    const user = usersData[idx];
    if (!user) return;
    const ok = await confirmModal(
      "Migrar usuario",
      `¿Migrar a Moodle: ${user.apellidos}, ${user.nombres} (${user.usuario})?`
    );
    if (!ok) return;

    startBulkProgress("Migrando usuario…", 1);
    setUsersMigrationBusy(true);
    try {
      $("#bulk-progress-detail").textContent = `Procesando ${user.usuario}…`;
      const result = await migrateUser(user);
      applyUserMigration(user, result?.ultima_migracion);
      stepBulkProgress(`✓ ${user.usuario}`, 1, 0);
      const msg = result?.message || result?.status || JSON.stringify(result);
      logActivity(`Usuario migrado: ${user.usuario} — ${msg}`, "success");
      showToast("Usuario migrado", "success");
      renderUsers();
    } catch (err) {
      stepBulkProgress(`✗ ${user.usuario}: ${err.message}`, 0, 1);
      logActivity(`Error migrando ${user.usuario}: ${err.message}`, "error");
      showToast(err.message, "error");
    } finally {
      finishBulkProgress();
      setUsersMigrationBusy(false);
    }
  }

  async function migrateSelectedUsers() {
    const checks = $$(".user-check:checked");
    if (!checks.length) return;
    const ok = await confirmModal(
      "Migrar usuarios seleccionados",
      `Se migrarán ${checks.length} usuario(s).`
    );
    if (!ok) return;

    const users = [...checks]
      .map((chk) => usersData[Number(chk.dataset.idx)])
      .filter(Boolean);

    startBulkProgress("Migrando usuarios…", users.length);
    setUsersMigrationBusy(true);

    let okCount = 0;
    let errCount = 0;
    try {
      for (const user of users) {
        $("#bulk-progress-detail").textContent = `Procesando ${user.usuario}…`;
        try {
          const result = await migrateUser(user);
          applyUserMigration(user, result?.ultima_migracion);
          okCount++;
          logActivity(`✓ ${user.usuario}`, "success");
          stepBulkProgress(`✓ ${user.usuario}`, 1, 0);
        } catch (err) {
          errCount++;
          logActivity(`✗ ${user.usuario}: ${err.message}`, "error");
          stepBulkProgress(`✗ ${user.usuario}: ${err.message}`, 0, 1);
        }
      }
    } finally {
      finishBulkProgress();
      setUsersMigrationBusy(false);
      showToast(`${okCount} migrados, ${errCount} errores`, errCount ? "error" : "success");
      renderUsers();
    }
  }

  // ── Categorías ───────────────────────────────────────────

  async function loadCategories() {
    const tbody = $("#categories-tbody");
    setLoading(tbody, 6);
    try {
      categoriesData = await api("/categories", { auth: true });
      renderCategories();
      logActivity(`${categoriesData.length} categorías listadas para el periodo`, "success");
    } catch (err) {
      categoriesData = [];
      tbody.innerHTML = `<tr><td colspan="6" class="empty">${escapeHtml(err.message)}</td></tr>`;
      logActivity(`Error al cargar categorías: ${err.message}`, "error");
    }
  }

  function renderCategories() {
    const tbody = $("#categories-tbody");
    if (!categoriesData.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="empty">No hay categorías para este periodo.</td></tr>`;
      return;
    }
    tbody.innerHTML = categoriesData.map((item) => `<tr>
      <td>${escapeHtml(item.level === "facultad" ? "Facultad" : "Escuela")}</td>
      <td class="cell-mono">${escapeHtml(item.idnumber)}</td>
      <td class="cell-truncate" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</td>
      <td class="cell-mono">${escapeHtml(item.cod_fac || "")}</td>
      <td class="cell-mono">${escapeHtml(item.cod_eap || "")}</td>
      <td class="cell-mono">${escapeHtml(item.parent_idnumber || "—")}</td>
    </tr>`).join("");
  }

  async function migrateCategories() {
    if (!categoriesData.length) {
      showToast("Carga las categorías primero", "error");
      return;
    }
    const ok = await confirmModal(
      "Migrar categorías a Moodle",
      `Se crearán o actualizarán ${categoriesData.length} categoría(s) en Moodle para el periodo activo.`
    );
    if (!ok) return;

    const migrateBtn = $("#categories-migrate");
    const loadBtn = $("#categories-load");
    if (migrateBtn) migrateBtn.disabled = true;
    if (loadBtn) loadBtn.disabled = true;
    try {
      const result = await api("/categories/migrate", {
        method: "POST",
        auth: true,
        body: {},
      });
      const { created = 0, updated = 0, skipped = 0, errors = 0 } = result;
      logActivity(
        `Categorías: ${created} creadas, ${updated} actualizadas, ${skipped} sin cambios, ${errors} errores`,
        errors ? "error" : "success"
      );
      showToast(
        `${created + updated + skipped} procesadas${errors ? `, ${errors} errores` : ""}`,
        errors ? "error" : "success"
      );
      if (Array.isArray(result.details)) {
        result.details.filter((item) => item.error).forEach((item) => {
          logActivity(`✗ ${item.idnumber}: ${item.error}`, "error");
        });
      }
    } catch (err) {
      logActivity(`Error migrando categorías: ${err.message}`, "error");
      showToast(err.message, "error");
    } finally {
      if (migrateBtn) migrateBtn.disabled = false;
      if (loadBtn) loadBtn.disabled = false;
    }
  }

  // ── Ciclo ────────────────────────────────────────────────

  async function handleCloseCycle() {
    const anio = activePeriod().anio;
    if (!anio || anio.length !== 4) {
      showToast("Configura un periodo académico válido en Ajustes", "error");
      return;
    }
    const ok = await confirmModal(
      "Cerrar ciclo académico",
      `¿Confirmas el cierre del ciclo ${anio} en Moodle (${session.area})?`
    );
    if (!ok) return;

    try {
      const result = await api(`/cycles/${anio}/close`, {
        method: "POST",
        auth: true,
        body: { anio },
      });
      const msg = result?.message || result?.status || JSON.stringify(result);
      logActivity(`Ciclo ${anio} cerrado — ${msg}`, "success");
      showToast("Ciclo cerrado", "success");
    } catch (err) {
      logActivity(`Error cerrando ciclo: ${err.message}`, "error");
      showToast(err.message, "error");
    }
  }

  // ── Bulk selection ───────────────────────────────────────

  function updateBulkButton(prefix) {
    const checks = $$(`.${prefix === "courses" ? "course" : "user"}-check:checked`);
    const btn = $(`#${prefix}-migrate-selected`);
    btn.disabled = checks.length === 0;
    btn.textContent = checks.length
      ? `Migrar seleccionados (${checks.length})`
      : "Migrar seleccionados";
  }

  // ── Event wiring ─────────────────────────────────────────

  async function handleLogout() {
    closeUserDropdown();
    try {
      if (session?.token) {
        await api("/auth/logout", { method: "POST", auth: true });
      }
    } catch {
      // ignore logout errors
    }
    clearSession();
    showLogin();
  }

  function bindEvents() {
    initCourseSearchFilters();
    window.addEventListener("hashchange", handleRouteChange);
    window.addEventListener("popstate", handleRouteChange);
    $("#login-form").addEventListener("submit", handleLogin);
    $("#login-password-toggle").addEventListener("click", () => {
      const input = $("#login-password");
      const btn = $("#login-password-toggle");
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.querySelector(".icon-eye").classList.toggle("hidden", show);
      btn.querySelector(".icon-eye-off").classList.toggle("hidden", !show);
      btn.setAttribute("aria-label", show ? "Ocultar contraseña" : "Mostrar contraseña");
      btn.title = show ? "Ocultar contraseña" : "Mostrar contraseña";
    });
    $("#config-strip-trigger")?.addEventListener("click", openSettingsTab);
    $("#header-user-btn")?.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleUserDropdown();
    });
    $("#user-menu-account")?.addEventListener("click", openAccountModal);
    $("#user-menu-settings")?.addEventListener("click", () => {
      closeUserDropdown();
      openSettingsTab();
    });
    $("#user-menu-logout")?.addEventListener("click", handleLogout);
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".header-user-menu")) closeUserDropdown();
    });
    $("#settings-gate-logout").addEventListener("click", handleLogout);
    $("#sidebar-toggle").addEventListener("click", toggleSidebar);
    $("#sidebar-expand").addEventListener("click", toggleSidebar);

    $$(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    $("#courses-load").addEventListener("click", () => loadCourses());
    $("#courses-filter-facultad").addEventListener("change", () => { void onCourseFacultyChange(); });
    $("#courses-filter-escuela").addEventListener("change", () => { void onCourseEscuelaChange(); });
    $("#courses-search").addEventListener("input", () => {
      renderCourses();
      syncTabRoute(true);
    });
    $("#courses-select-all").addEventListener("change", (e) => {
      $$(".course-check").forEach((c) => { c.checked = e.target.checked; });
      updateBulkButton("courses");
    });
    $("#courses-migrate-selected").addEventListener("click", migrateSelectedCourses);
    $("#courses-tbody").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-migrate-course]");
      if (btn) handleMigrateCourse(Number(btn.dataset.migrateCourse));
    });
    $("#courses-tbody").addEventListener("change", (e) => {
      if (e.target.classList.contains("course-check")) updateBulkButton("courses");
    });

    $("#users-load").addEventListener("click", () => loadUsers());
    $("#users-tipo").addEventListener("change", () => { void onUsersTipoChange(); });
    $("#users-filter-facultad").addEventListener("change", () => { void onUserFacultyChange(); });
    $("#users-filter-escuela").addEventListener("change", onUserEscuelaChange);
    $("#users-search").addEventListener("input", () => {
      renderUsers();
      syncTabRoute(true);
    });
    $("#users-select-all").addEventListener("change", (e) => {
      $$(".user-check").forEach((c) => { c.checked = e.target.checked; });
      updateBulkButton("users");
    });
    $("#users-migrate-selected").addEventListener("click", migrateSelectedUsers);
    $("#users-tbody").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-migrate-user]");
      if (btn) handleMigrateUser(Number(btn.dataset.migrateUser));
    });
    $("#users-tbody").addEventListener("change", (e) => {
      if (e.target.classList.contains("user-check")) updateBulkButton("users");
    });

    $("#cycle-close").addEventListener("click", handleCloseCycle);

    $("#categories-load").addEventListener("click", () => loadCategories());
    $("#categories-migrate").addEventListener("click", () => migrateCategories());

    $("#account-form")?.addEventListener("submit", handleAccountSubmit);
    $$("[data-close-account]").forEach((el) => {
      el.addEventListener("click", closeAccountModal);
    });
    $("#modal-cancel").addEventListener("click", () => closeModal(false));
    $("#modal-confirm").addEventListener("click", () => closeModal(true));
    $(".modal-backdrop").addEventListener("click", () => closeModal(false));

    $("#clear-log").addEventListener("click", () => {
      $("#activity-list").innerHTML = "";
    });
  }

  // ── Init ─────────────────────────────────────────────────

  async function init() {
    bindEvents();
    session = loadSession();

    if (!session?.token) {
      const { view } = parseRoute();
      if (view !== "login") setRoute("login", {}, { replace: true });
      showLogin({ skipRoute: true });
      return;
    }

    try {
      appSettings = await loadSettingsStatus();
      const { view } = parseRoute();
      if (!appSettings.configured) {
        if (view !== "config") setRoute("config", {}, { replace: true });
        showSettingsGate({ skipRoute: true });
      } else if (PANEL_TABS.includes(view)) {
        await showPanel({ skipRoute: true });
      } else if (view === "config") {
        showSettingsGate({ skipRoute: true });
      } else {
        setRoute("users", {}, { replace: true });
        await showPanel({ skipRoute: true });
      }
    } catch {
      clearSession();
      setRoute("login", {}, { replace: true });
      showLogin({ skipRoute: true });
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
