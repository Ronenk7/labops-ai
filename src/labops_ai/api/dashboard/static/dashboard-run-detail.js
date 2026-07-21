"use strict";

(() => {
  const REQUEST_TIMEOUT_MS = 7000;

  const state = {
    runId: null,
    requestSequence: 0
  };

  const elements = {
    page: document.body,
    apiState: document.querySelector("#run-api-state"),
    apiLabel: document.querySelector("#run-api-label"),
    refresh: document.querySelector("#run-refresh"),
    message: document.querySelector("#run-message"),
    content: document.querySelector("#run-content"),
    title: document.querySelector("#run-title"),
    bundleId: document.querySelector("#run-bundle-id"),
    overallStatus: document.querySelector(
      "#run-overall-status"
    ),
    downloadZip: document.querySelector(
      "#run-download-zip"
    ),
    hostName: document.querySelector("#run-host-name"),
    generatedAt: document.querySelector(
      "#run-generated-at"
    ),
    activeIncidents: document.querySelector(
      "#run-active-incidents"
    ),
    resolvedIncidents: document.querySelector(
      "#run-resolved-incidents"
    ),
    systemMetrics: document.querySelector(
      "#run-system-metrics"
    ),
    networkContent: document.querySelector(
      "#run-network-content"
    ),
    servicesContent: document.querySelector(
      "#run-services-content"
    ),
    processesContent: document.querySelector(
      "#run-processes-content"
    ),
    logsContent: document.querySelector(
      "#run-logs-content"
    ),
    incidentsContent: document.querySelector(
      "#run-incidents-content"
    )
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

  function resolveRunId() {
    const segments = window.location.pathname
      .split("/")
      .filter(Boolean);
    const runId = Number(segments[segments.length - 1]);

    return (
      Number.isInteger(runId) && runId > 0
        ? runId
        : null
    );
  }

  function normalizeStatus(value) {
    const normalized = String(
      value || "UNKNOWN"
    ).toUpperCase();

    const accepted = new Set([
      "HEALTHY",
      "WARNING",
      "CRITICAL",
      "PASSED",
      "ACTIVE",
      "RUNNING",
      "ANALYZED"
    ]);

    return accepted.has(normalized)
      ? normalized
      : "UNKNOWN";
  }

  function createStatusPill(status) {
    const normalized = normalizeStatus(status);

    return createElement(
      "span",
      (
        "run-status-pill "
        + `run-status-pill--${normalized.toLowerCase()}`
      ),
      normalized
    );
  }

  function formatDate(value) {
    const date = new Date(value);

    return Number.isNaN(date.getTime())
      ? "Unknown"
      : date.toLocaleString();
  }

  function formatNumber(value, digits = 2) {
    const number = Number(value);

    return Number.isFinite(number)
      ? number.toFixed(digits)
      : "—";
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
  }

  function showMessage(message, error = false) {
    elements.message.hidden = false;
    elements.message.textContent = message;
    elements.message.classList.toggle(
      "run-detail-message--error",
      error
    );
  }

  function hideMessage() {
    elements.message.hidden = true;
    elements.message.classList.remove(
      "run-detail-message--error"
    );
  }

  function renderSystemMetrics(metrics) {
    elements.systemMetrics.replaceChildren();

    if (!Array.isArray(metrics) || metrics.length === 0) {
      elements.systemMetrics.append(
        createElement(
          "div",
          "run-empty-state",
          "No system metrics were recorded."
        )
      );
      return;
    }

    const fragment = document.createDocumentFragment();

    metrics.forEach(
      metric => {
        const card = createElement(
          "article",
          "run-metric-card"
        );
        const header = createElement(
          "div",
          "run-metric-card__header"
        );

        header.append(
          createElement(
            "span",
            "",
            metric.label || metric.metric_name
          ),
          createStatusPill(metric.health_status)
        );

        card.append(
          header,
          createElement(
            "strong",
            "",
            `${formatNumber(metric.value_percent, 1)}%`
          )
        );

        fragment.append(card);
      }
    );

    elements.systemMetrics.append(fragment);
  }

  function createTable(headers, rows, emptyMessage) {
    if (!Array.isArray(rows) || rows.length === 0) {
      return createElement(
        "div",
        "run-empty-state",
        emptyMessage
      );
    }

    const wrapper = createElement(
      "div",
      "run-table-wrapper"
    );
    const table = createElement("table", "run-table");
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");

    headers.forEach(
      header => {
        headRow.append(
          createElement("th", "", header)
        );
      }
    );

    head.append(headRow);

    const body = document.createElement("tbody");

    rows.forEach(
      rowValues => {
        const row = document.createElement("tr");

        rowValues.forEach(
          value => {
            const cell = document.createElement("td");

            if (value instanceof Node) {
              cell.append(value);
            } else {
              cell.textContent = String(value ?? "—");
            }

            row.append(cell);
          }
        );

        body.append(row);
      }
    );

    table.append(head, body);
    wrapper.append(table);
    return wrapper;
  }

  function renderNetwork(checks) {
    const rows = (checks || []).map(
      check => [
        check.check_type,
        check.target,
        createStatusPill(
          check.health_status || check.check_status
        ),
        (
          check.latency_ms == null
            ? "—"
            : `${formatNumber(check.latency_ms)} ms`
        ),
        check.resolved_address || "—",
        (
          check.error_message
          || check.failure_reason
          || "—"
        )
      ]
    );

    elements.networkContent.replaceChildren(
      createTable(
        [
          "Type",
          "Target",
          "Status",
          "Latency",
          "Resolved address",
          "Failure"
        ],
        rows,
        "No network checks were recorded."
      )
    );
  }
  function renderServices(records) {
    const rows = (records || []).map(
      service => [
        service.label || service.service_name,
        service.service_name,
        createStatusPill(
          service.health_status || service.check_status
        ),
        service.active_state || "—",
        service.sub_state || "—",
        (
          service.error_message
          || service.failure_reason
          || "—"
        )
      ]
    );

    elements.servicesContent.replaceChildren(
      createTable(
        [
          "Service",
          "Unit",
          "Status",
          "Active state",
          "Sub-state",
          "Failure"
        ],
        rows,
        "No service records were recorded."
      )
    );
  }

  function renderProcesses(records) {
    const rows = (records || []).map(
      process => [
        process.label || process.process_name,
        process.process_name,
        createStatusPill(
          process.health_status || process.check_status
        ),
        process.instance_count ?? 0,
        createElement(
          "code",
          "run-code-list",
          Array.isArray(process.pids)
            ? process.pids.join(", ")
            : "—"
        ),
        `${formatNumber(process.total_cpu_percent, 1)}%`,
        `${formatNumber(process.total_memory_mb, 1)} MB`,
        (
          process.error_message
          || process.failure_reason
          || "—"
        )
      ]
    );

    elements.processesContent.replaceChildren(
      createTable(
        [
          "Process",
          "Name",
          "Status",
          "Instances",
          "PIDs",
          "CPU",
          "Memory",
          "Failure"
        ],
        rows,
        "No process records were recorded."
      )
    );
  }

  function renderLogs(records) {
    const rows = (records || []).map(
      record => [
        record.label || record.source_id,
        record.path,
        createStatusPill(
          record.health_status || record.scan_status
        ),
        record.total_lines_scanned ?? 0,
        record.match_count ?? 0,
        (
          record.error_message
          || record.failure_reason
          || "—"
        )
      ]
    );

    elements.logsContent.replaceChildren(
      createTable(
        [
          "Source",
          "Path",
          "Status",
          "Lines scanned",
          "Matches",
          "Failure"
        ],
        rows,
        "No log records were recorded."
      )
    );
  }

  function renderIncidents(records) {
    const rows = (records || []).map(
      incident => [
        incident.incident_id || "—",
        (
          incident.source_label
          || incident.source_id
          || "—"
        ),
        createStatusPill(incident.severity),
        incident.status || "—",
        incident.description || "—",
        incident.occurrence_count ?? 0
      ]
    );

    elements.incidentsContent.replaceChildren(
      createTable(
        [
          "Incident",
          "Source",
          "Severity",
          "Lifecycle",
          "Description",
          "Occurrences"
        ],
        rows,
        "No incidents were recorded for this run."
      )
    );
  }

  function renderDetails(payload) {
    const run = payload.run;
    const diagnostics = payload.diagnostics;

    document.title = `LabOps AI — Run #${run.run_id}`;
    elements.title.textContent = (
      `Monitoring run #${run.run_id}`
    );
    elements.bundleId.textContent = run.bundle_id;

    const overall = normalizeStatus(run.overall_status);
    elements.overallStatus.textContent = overall;
    elements.overallStatus.className = (
      "run-status-pill "
      + `run-status-pill--${overall.toLowerCase()}`
    );
    elements.downloadZip.href = (
      `/api/v1/runs/${run.run_id}/archive`
    );

    elements.hostName.textContent = run.host_name;
    elements.generatedAt.textContent = formatDate(
      run.generated_at
    );
    elements.activeIncidents.textContent = String(
      run.active_incident_count
    );
    elements.resolvedIncidents.textContent = String(
      run.resolved_incident_count
    );

    renderSystemMetrics(diagnostics.system?.metrics);
    renderNetwork(diagnostics.network?.checks);
    renderServices(diagnostics.services?.records);
    renderProcesses(diagnostics.processes?.records);
    renderLogs(diagnostics.logs?.records);
    renderIncidents(diagnostics.incidents?.records);

    hideMessage();
    elements.content.hidden = false;
  }

  async function loadDetails() {
    const requestId = state.requestSequence + 1;
    state.requestSequence = requestId;

    const controller = new AbortController();
    const timeoutId = window.setTimeout(
      () => controller.abort(),
      REQUEST_TIMEOUT_MS
    );

    setLoading(true);

    try {
      const response = await fetch(
        `/api/v1/runs/${state.runId}/details`,
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
          `Monitoring run ${state.runId} was not found.`
        );
      }

      if (!response.ok) {
        throw new Error(
          `Run details returned ${response.status}.`
        );
      }

      const payload = await response.json();

      if (
        !payload
        || typeof payload !== "object"
        || !payload.run
        || !payload.diagnostics
      ) {
        throw new Error(
          "Run Details API returned invalid data."
        );
      }

      if (requestId !== state.requestSequence) {
        return;
      }

      setApiState(
        "online",
        "Run Details API online"
      );
      renderDetails(payload);
    } catch (error) {
      if (requestId !== state.requestSequence) {
        return;
      }

      const message = (
        error.name === "AbortError"
        ? "Run Details request timed out."
        : error.message
      );

      setApiState(
        "error",
        "Run Details unavailable"
      );
      elements.content.hidden = true;
      showMessage(message, true);
    } finally {
      window.clearTimeout(timeoutId);
      setLoading(false);
    }
  }

  function initialize() {
    state.runId = resolveRunId();

    if (state.runId === null) {
      setApiState("error", "Invalid run route");
      showMessage(
        "The monitoring run identifier is invalid.",
        true
      );
      return;
    }

    elements.refresh.addEventListener(
      "click",
      loadDetails
    );

    loadDetails();
  }

  initialize();
})();
