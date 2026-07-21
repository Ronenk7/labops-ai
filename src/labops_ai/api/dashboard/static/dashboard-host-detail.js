"use strict";

(() => {
  const REQUEST_TIMEOUT_MS = 7000;
  const REFRESH_INTERVAL_MS = 15000;

  const state = {
    hostId: null,
    overview: null,
    loadedAt: Date.now(),
    refreshTimer: null,
    requestSequence: 0
  };

  const elements = {
    page: document.body,
    apiState: document.querySelector("#host-api-state"),
    apiLabel: document.querySelector("#host-api-label"),
    refresh: document.querySelector("#host-refresh"),
    message: document.querySelector("#host-message"),
    content: document.querySelector("#host-content"),
    hostName: document.querySelector("#host-name"),
    hostId: document.querySelector("#host-id"),
    availability: document.querySelector(
      "#host-availability"
    ),
    heartbeatAge: document.querySelector(
      "#host-heartbeat-age"
    ),
    updated: document.querySelector("#host-updated"),
    latestStatus: document.querySelector(
      "#host-latest-status"
    ),
    runCount: document.querySelector("#host-run-count"),
    incidentCount: document.querySelector(
      "#host-incident-count"
    ),
    lastRun: document.querySelector("#host-last-run"),
    identityGrid: document.querySelector(
      "#host-identity-grid"
    ),
    componentGrid: document.querySelector(
      "#host-component-grid"
    ),
    runsDescription: document.querySelector(
      "#host-runs-description"
    ),
    runLimit: document.querySelector("#host-run-limit"),
    runsBody: document.querySelector("#host-runs-body"),
    runsEmpty: document.querySelector("#host-runs-empty")
  };

  function createElement(
    tagName,
    className = "",
    text = ""
  ) {
    const element = document.createElement(tagName);

    if (className) {
      element.className = className;
    }

    if (text !== "") {
      element.textContent = String(text);
    }

    return element;
  }

  function resolveHostId() {
    const segments = window.location.pathname
      .split("/")
      .filter(Boolean);

    if (segments.length < 3) {
      return null;
    }

    const rawHostId = segments[segments.length - 1];

    try {
      return decodeURIComponent(rawHostId);
    } catch {
      return rawHostId;
    }
  }

  function normalizeAvailability(value) {
    const normalized = String(
      value || "UNKNOWN"
    ).toUpperCase();

    if (
      normalized === "ONLINE"
      || normalized === "STALE"
      || normalized === "OFFLINE"
    ) {
      return normalized;
    }

    return "UNKNOWN";
  }

  function normalizeHealth(value) {
    const normalized = String(
      value || "UNKNOWN"
    ).toUpperCase();

    if (
      normalized === "HEALTHY"
      || normalized === "WARNING"
      || normalized === "CRITICAL"
    ) {
      return normalized;
    }

    return "UNKNOWN";
  }

  function formatDate(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "Unknown";
    }

    return date.toLocaleString();
  }

  function formatAge(seconds) {
    const total = Math.max(
      0,
      Math.floor(Number(seconds) || 0)
    );

    if (total < 5) {
      return "just now";
    }

    if (total < 60) {
      return `${total}s ago`;
    }

    const minutes = Math.floor(total / 60);

    if (minutes < 60) {
      return `${minutes}m ago`;
    }

    const hours = Math.floor(minutes / 60);

    if (hours < 24) {
      return `${hours}h ago`;
    }

    return `${Math.floor(hours / 24)}d ago`;
  }

  function currentHeartbeatAge() {
    if (!state.overview) {
      return 0;
    }

    const baseAge = Number(
      state.overview.host.heartbeat_age_seconds
    ) || 0;

    return (
      baseAge
      + Math.max(
        0,
        (Date.now() - state.loadedAt) / 1000
      )
    );
  }

  function setApiState(name, label) {
    elements.apiState.classList.remove(
      "fleet-api-state--online",
      "fleet-api-state--error"
    );

    if (name === "online") {
      elements.apiState.classList.add(
        "fleet-api-state--online"
      );
    }

    if (name === "error") {
      elements.apiState.classList.add(
        "fleet-api-state--error"
      );
    }

    elements.apiLabel.textContent = label;
  }

  function setLoading(loading) {
    elements.page.setAttribute(
      "aria-busy",
      String(loading)
    );
    elements.refresh.disabled = loading;
    elements.runLimit.disabled = loading;
  }

  function showMessage(message, error = false) {
    elements.message.hidden = false;
    elements.message.textContent = message;
    elements.message.classList.toggle(
      "host-detail-message--error",
      error
    );
  }

  function hideMessage() {
    elements.message.hidden = true;
    elements.message.classList.remove(
      "host-detail-message--error"
    );
  }

  function createStatusPill(status) {
    const normalized = normalizeHealth(status);

    return createElement(
      "span",
      (
        "host-status-pill "
        + `host-status-pill--${normalized.toLowerCase()}`
      ),
      normalized
    );
  }

  function createDetailItem(label, value) {
    const item = createElement(
      "div",
      "host-detail-item"
    );

    item.append(
      createElement("span", "", label),
      createElement(
        "strong",
        "",
        value || "—"
      )
    );

    return item;
  }

  function renderIdentity(host) {
    elements.identityGrid.replaceChildren();

    const values = [
      ["Host name", host.host_name],
      ["Host ID", host.host_id],
      ["Address", host.address],
      ["Operating system", host.operating_system],
      ["Architecture", host.architecture],
      ["Agent version", host.agent_version],
      ["First registered", formatDate(host.registered_at)],
      ["Last heartbeat", formatDate(host.last_seen_at)]
    ];

    const fragment = document.createDocumentFragment();

    values.forEach(
      ([label, value]) => {
        fragment.append(
          createDetailItem(label, value)
        );
      }
    );

    elements.identityGrid.append(fragment);
  }

  function renderComponents(latestRun) {
    elements.componentGrid.replaceChildren();

    const components = latestRun
      ? [
          ["System", latestRun.system_status],
          ["Network", latestRun.network_status],
          ["Services", latestRun.service_status],
          ["Processes", latestRun.process_status],
          ["Logs", latestRun.log_status],
          ["Overall", latestRun.overall_status]
        ]
      : [
          ["System", "UNKNOWN"],
          ["Network", "UNKNOWN"],
          ["Services", "UNKNOWN"],
          ["Processes", "UNKNOWN"],
          ["Logs", "UNKNOWN"],
          ["Overall", "UNKNOWN"]
        ];

    const fragment = document.createDocumentFragment();

    components.forEach(
      ([label, status]) => {
        const item = createElement(
          "div",
          "host-component-item"
        );

        item.append(
          createElement("span", "", label),
          createStatusPill(status)
        );

        fragment.append(item);
      }
    );

    elements.componentGrid.append(fragment);
  }

  function createRunCell(value) {
    const cell = document.createElement("td");
    cell.textContent = String(value);
    return cell;
  }

  function createStatusCell(status) {
    const cell = document.createElement("td");
    cell.append(createStatusPill(status));
    return cell;
  }

  function createEvidenceCell(run) {
    const cell = document.createElement("td");
    const links = createElement(
      "div",
      "host-evidence-links"
    );

    const details = createElement(
      "a",
      "host-evidence-link",
      "Details"
    );
    details.href = (
      `/dashboard/runs/${run.run_id}`
    );
const archive = createElement(
      "a",
      "host-evidence-link",
      "ZIP"
    );
    archive.href = (
      `/api/v1/runs/${run.run_id}/archive`
    );
    archive.setAttribute(
      "download",
      ""
    );

    links.append(
      details,
      archive
    );
    cell.append(links);

    return cell;
  }

  function renderRuns(runs) {
    elements.runsBody.replaceChildren();

    elements.runsDescription.textContent = (
      `${runs.length} monitoring run`
      + `${runs.length === 1 ? "" : "s"} returned`
    );

    if (runs.length === 0) {
      elements.runsEmpty.hidden = false;
      return;
    }

    elements.runsEmpty.hidden = true;

    const fragment = document.createDocumentFragment();

    runs.forEach(
      run => {
        const row = document.createElement("tr");

        const runCell = createRunCell(`#${run.run_id}`);
        runCell.className = "host-run-id";

        row.append(
          runCell,
          createRunCell(formatDate(run.generated_at)),
          createStatusCell(run.overall_status),
          createStatusCell(run.system_status),
          createStatusCell(run.network_status),
          createStatusCell(run.service_status),
          createStatusCell(run.process_status),
          createStatusCell(run.log_status),
          createRunCell(run.incident_count),
          createEvidenceCell(run)
        );

        fragment.append(row);
      }
    );

    elements.runsBody.append(fragment);
  }

  function renderOverview(overview) {
    const host = overview.host;
    const latestRun = overview.latest_run;
    const availability = normalizeAvailability(
      host.availability
    );

    document.title = (
      `LabOps AI — ${host.host_name}`
    );

    elements.hostName.textContent = host.host_name;
    elements.hostId.textContent = host.host_id;

    elements.availability.textContent = availability;
    elements.availability.className = (
      "host-availability "
      + `host-availability--${availability.toLowerCase()}`
    );

    elements.heartbeatAge.textContent = formatAge(
      currentHeartbeatAge()
    );

    elements.latestStatus.replaceChildren(
      createStatusPill(
        latestRun
          ? latestRun.overall_status
          : "UNKNOWN"
      )
    );

    elements.runCount.textContent = String(
      overview.returned_run_count
    );

    const incidentCount = overview.runs.reduce(
      (total, run) => (
        total + Number(run.incident_count || 0)
      ),
      0
    );

    elements.incidentCount.textContent = String(
      incidentCount
    );

    elements.lastRun.textContent = latestRun
      ? formatDate(latestRun.generated_at)
      : "No runs received";

    renderIdentity(host);
    renderComponents(latestRun);
    renderRuns(overview.runs);

    hideMessage();
    elements.content.hidden = false;
  }

  async function loadOverview() {
    const requestId = state.requestSequence + 1;
    state.requestSequence = requestId;

    const controller = new AbortController();
    const timeoutId = window.setTimeout(
      () => controller.abort(),
      REQUEST_TIMEOUT_MS
    );

    setLoading(true);

    try {
      const limit = Number(elements.runLimit.value);
      const encodedHostId = encodeURIComponent(
        state.hostId
      );

      const response = await fetch(
        (
          `/api/v1/hosts/${encodedHostId}/overview`
          + `?limit=${limit}`
        ),
        {
          cache: "no-store",
          headers: {
            Accept: "application/json"
          },
          signal: controller.signal
        }
      );

      if (response.status === 404) {
        throw new Error(
          `Host ${state.hostId} was not found.`
        );
      }

      if (!response.ok) {
        throw new Error(
          `Host overview returned ${response.status}.`
        );
      }

      const overview = await response.json();

      if (requestId !== state.requestSequence) {
        return;
      }

      state.overview = overview;
      state.loadedAt = Date.now();

      setApiState(
        "online",
        "Host API online"
      );

      elements.updated.textContent = (
        "Updated "
        + new Date().toLocaleTimeString()
      );

      renderOverview(overview);
    } catch (error) {
      if (requestId !== state.requestSequence) {
        return;
      }

      const message = (
        error.name === "AbortError"
        ? "Host overview request timed out."
        : error.message
      );

      setApiState(
        "error",
        "Host API unavailable"
      );
      elements.content.hidden = true;
      showMessage(message, true);
    } finally {
      window.clearTimeout(timeoutId);
      setLoading(false);
    }
  }

  function updateHeartbeatAge() {
    if (!state.overview) {
      return;
    }

    elements.heartbeatAge.textContent = formatAge(
      currentHeartbeatAge()
    );
  }

  function scheduleRefresh() {
    if (state.refreshTimer !== null) {
      window.clearInterval(state.refreshTimer);
    }

    state.refreshTimer = window.setInterval(
      loadOverview,
      REFRESH_INTERVAL_MS
    );
  }

  function initialize() {
    state.hostId = resolveHostId();

    if (!state.hostId) {
      setApiState(
        "error",
        "Invalid Host route"
      );
      showMessage(
        "The Host identifier is missing from the URL.",
        true
      );
      return;
    }

    elements.refresh.addEventListener(
      "click",
      loadOverview
    );

    elements.runLimit.addEventListener(
      "change",
      loadOverview
    );

    window.setInterval(
      updateHeartbeatAge,
      1000
    );

    scheduleRefresh();
    loadOverview();
  }

  initialize();
})();
