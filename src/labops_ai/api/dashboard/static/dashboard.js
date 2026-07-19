"use strict";

const state = {
  runs: [],
  overview: null,
  sortKey: "generated_at",
  sortDirection: "desc",
  refreshTimer: null,
  countdownTimer: null,
  nextRefreshAt: null
};

const elements = {
  connectionDot: document.querySelector("#connection-dot"),
  connectionLabel: document.querySelector("#connection-label"),
  refreshButton: document.querySelector("#refresh-button"),
  refreshInterval: document.querySelector("#refresh-interval"),
  refreshCountdown: document.querySelector("#refresh-countdown"),
  exportButton: document.querySelector("#export-button"),
  printButton: document.querySelector("#print-button"),
  overviewCaption: document.querySelector("#overview-caption"),
  currentHealth: document.querySelector("#current-health"),
  latestHost: document.querySelector("#latest-host"),
  healthScore: document.querySelector("#health-score"),
  sampleSize: document.querySelector("#sample-size"),
  incidentTotal: document.querySelector("#incident-total"),
  healthyStreak: document.querySelector("#healthy-streak"),
  trendPeriod: document.querySelector("#trend-period"),
  trendChart: document.querySelector("#trend-chart"),
  donut: document.querySelector("#status-donut"),
  donutTotal: document.querySelector("#donut-total"),
  healthyCount: document.querySelector("#healthy-count"),
  warningCount: document.querySelector("#warning-count"),
  criticalCount: document.querySelector("#critical-count"),
  reliabilityList: document.querySelector("#reliability-list"),
  filters: document.querySelector("#filters"),
  hostFilter: document.querySelector("#host-filter"),
  statusFilter: document.querySelector("#status-filter"),
  limitFilter: document.querySelector("#limit-filter"),
  clearFilters: document.querySelector("#clear-filters"),
  tableBody: document.querySelector("#runs-table-body"),
  tableMessage: document.querySelector("#table-message"),
  updatedAt: document.querySelector("#updated-at"),
  drawer: document.querySelector("#run-drawer"),
  drawerBackdrop: document.querySelector("#drawer-backdrop"),
  drawerClose: document.querySelector("#drawer-close"),
  drawerTitle: document.querySelector("#drawer-title"),
  drawerContent: document.querySelector("#drawer-content"),
  toast: document.querySelector("#toast")
};

const severityRank = {
  HEALTHY: 1,
  WARNING: 2,
  CRITICAL: 3
};

function formatDate(value) {
  return new Intl.DateTimeFormat(
    undefined,
    {
      dateStyle: "medium",
      timeStyle: "medium"
    }
  ).format(new Date(value));
}

function buildRunsParameters(includeStatus = true) {
  const parameters = new URLSearchParams({
    limit: elements.limitFilter.value
  });

  const hostName = elements.hostFilter.value.trim();

  if (hostName) {
    parameters.set("host_name", hostName);
  }

  if (includeStatus && elements.statusFilter.value) {
    parameters.set("status", elements.statusFilter.value);
  }

  return parameters;
}

async function fetchJson(url) {
  const response = await fetch(
    url,
    {
      headers: {
        Accept: "application/json"
      }
    }
  );

  if (!response.ok) {
    let message = `HTTP ${response.status}`;

    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      // Keep the fallback message.
    }

    throw new Error(message);
  }

  return response.json();
}

function createElement(
  tagName,
  className,
  text
) {
  const element = document.createElement(tagName);

  if (className) {
    element.className = className;
  }

  if (text !== undefined) {
    element.textContent = text;
  }

  return element;
}

function createStatusChip(status) {
  return createElement(
    "span",
    `status-chip status-chip--${status}`,
    status
  );
}

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.className = isError
    ? "toast toast--visible toast--error"
    : "toast toast--visible";

  window.setTimeout(
    () => {
      elements.toast.className = "toast";
    },
    2800
  );
}

function setConnection(online, version = "") {
  elements.connectionDot.classList.toggle(
    "connection__dot--online",
    online
  );

  elements.connectionLabel.textContent = online
    ? `Healthy · API ${version}`
    : "API unavailable";
}

function renderOverview(overview) {
  state.overview = overview;

  const latest = overview.latest_run;

  elements.currentHealth.textContent = latest
    ? latest.overall_status
    : "No data";

  elements.currentHealth.className =
    `summary-card__value status-text--${
      latest ? latest.overall_status : "EMPTY"
    }`;

  elements.latestHost.textContent = latest
    ? `Latest host: ${latest.host_name}`
    : "No monitoring runs";

  elements.healthScore.textContent =
    `${overview.health_score.toFixed(1)}%`;

  elements.sampleSize.textContent =
    `${overview.sample_size} analyzed runs`;

  elements.incidentTotal.textContent =
    String(overview.active_incident_total);

  elements.healthyStreak.textContent =
    String(overview.current_healthy_streak);

  elements.overviewCaption.textContent = latest
    ? (
        `Latest run #${latest.run_id} · `
        + `${formatDate(latest.generated_at)}`
      )
    : "No monitoring data is currently available.";

  renderDistribution(overview.status_distribution);
  renderReliability(overview.component_reliability);
  renderTrend(overview.trend);
}

function renderDistribution(distribution) {
  const total =
    distribution.healthy
    + distribution.warning
    + distribution.critical;

  const healthyPercent = total
    ? distribution.healthy / total * 100
    : 0;

  const warningPercent = total
    ? distribution.warning / total * 100
    : 0;

  const healthyEnd = healthyPercent;
  const warningEnd = healthyEnd + warningPercent;

  elements.donut.style.background = total
    ? (
        "conic-gradient("
        + `var(--green) 0 ${healthyEnd}%,`
        + `var(--amber) ${healthyEnd}% ${warningEnd}%,`
        + `var(--red) ${warningEnd}% 100%)`
      )
    : "conic-gradient(var(--line) 0 100%)";

  elements.donutTotal.textContent = String(total);
  elements.healthyCount.textContent =
    String(distribution.healthy);
  elements.warningCount.textContent =
    String(distribution.warning);
  elements.criticalCount.textContent =
    String(distribution.critical);
}

function renderReliability(reliability) {
  const componentLabels = {
    system: "System",
    network: "Network",
    services: "Services",
    processes: "Processes",
    logs: "Logs"
  };

  elements.reliabilityList.replaceChildren();

  for (const [key, label] of Object.entries(componentLabels)) {
    const value = reliability[key];
    const row = createElement("div", "reliability-row");
    const heading = createElement(
      "div",
      "reliability-row__heading"
    );
    const bar = createElement("div", "reliability-bar");
    const fill = document.createElement("span");

    heading.append(
      createElement("span", "", label),
      createElement("strong", "", `${value.toFixed(1)}%`)
    );

    bar.appendChild(fill);
    row.append(heading, bar);
    elements.reliabilityList.appendChild(row);

    window.requestAnimationFrame(
      () => {
        fill.style.width = `${value}%`;
      }
    );
  }
}

function renderTrend(points) {
  elements.trendChart.replaceChildren();

  if (!points.length) {
    elements.trendChart.appendChild(
      createElement(
        "div",
        "table-message",
        "No trend information is available."
      )
    );
    return;
  }

  const width = 900;
  const height = 300;
  const padding = {
    left: 58,
    right: 25,
    top: 25,
    bottom: 43
  };
  const usableWidth =
    width - padding.left - padding.right;
  const usableHeight =
    height - padding.top - padding.bottom;

  const yForStatus = {
    HEALTHY: padding.top + 15,
    WARNING: padding.top + usableHeight / 2,
    CRITICAL: padding.top + usableHeight - 15
  };

  const xForIndex = index => {
    if (points.length === 1) {
      return padding.left + usableWidth / 2;
    }

    return (
      padding.left
      + index / (points.length - 1) * usableWidth
    );
  };

  const namespace = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(namespace, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute(
    "aria-label",
    "Recent monitoring health trend"
  );

  const definitions = document.createElementNS(
    namespace,
    "defs"
  );
  const gradient = document.createElementNS(
    namespace,
    "linearGradient"
  );
  gradient.id = "trend-area-gradient";
  gradient.setAttribute("x1", "0");
  gradient.setAttribute("y1", "0");
  gradient.setAttribute("x2", "0");
  gradient.setAttribute("y2", "1");

  const topStop = document.createElementNS(
    namespace,
    "stop"
  );
  topStop.setAttribute("offset", "0%");
  topStop.setAttribute("stop-color", "#d86624");
  topStop.setAttribute("stop-opacity", "0.24");

  const bottomStop = document.createElementNS(
    namespace,
    "stop"
  );
  bottomStop.setAttribute("offset", "100%");
  bottomStop.setAttribute("stop-color", "#d86624");
  bottomStop.setAttribute("stop-opacity", "0");

  gradient.append(topStop, bottomStop);
  definitions.appendChild(gradient);
  svg.appendChild(definitions);

  for (const status of ["HEALTHY", "WARNING", "CRITICAL"]) {
    const y = yForStatus[status];
    const line = document.createElementNS(
      namespace,
      "line"
    );
    line.setAttribute("x1", padding.left);
    line.setAttribute("x2", width - padding.right);
    line.setAttribute("y1", y);
    line.setAttribute("y2", y);
    line.setAttribute("class", "chart-grid");

    const label = document.createElementNS(
      namespace,
      "text"
    );
    label.setAttribute("x", 2);
    label.setAttribute("y", y + 4);
    label.setAttribute("class", "chart-label");
    label.textContent = status;

    svg.append(line, label);
  }

  const coordinates = points.map(
    (point, index) => ({
      x: xForIndex(index),
      y: yForStatus[point.status],
      point
    })
  );

  const linePath = coordinates
    .map(
      (coordinate, index) =>
        `${index === 0 ? "M" : "L"} `
        + `${coordinate.x} ${coordinate.y}`
    )
    .join(" ");

  const areaPath = (
    linePath
    + ` L ${coordinates.at(-1).x} `
    + `${height - padding.bottom}`
    + ` L ${coordinates[0].x} `
    + `${height - padding.bottom} Z`
  );

  const area = document.createElementNS(
    namespace,
    "path"
  );
  area.setAttribute("d", areaPath);
  area.setAttribute("class", "chart-area");

  const path = document.createElementNS(
    namespace,
    "path"
  );
  path.setAttribute("d", linePath);
  path.setAttribute("class", "chart-path");

  svg.append(area, path);

  for (const coordinate of coordinates) {
    const circle = document.createElementNS(
      namespace,
      "circle"
    );
    circle.setAttribute("cx", coordinate.x);
    circle.setAttribute("cy", coordinate.y);
    circle.setAttribute("r", "7");
    circle.setAttribute(
      "class",
      `chart-point chart-point--${coordinate.point.status}`
    );

    const title = document.createElementNS(
      namespace,
      "title"
    );
    title.textContent = (
      `Run #${coordinate.point.run_id} · `
      + `${coordinate.point.status} · `
      + `${formatDate(coordinate.point.generated_at)}`
    );

    circle.appendChild(title);
    svg.appendChild(circle);
  }

  elements.trendChart.appendChild(svg);
  elements.trendPeriod.textContent =
    `${points.length} recent runs`;
}

function getSortedRuns() {
  const sortedRuns = [...state.runs];
  const multiplier =
    state.sortDirection === "asc" ? 1 : -1;

  sortedRuns.sort(
    (left, right) => {
      let leftValue = left[state.sortKey];
      let rightValue = right[state.sortKey];

      if (state.sortKey === "generated_at") {
        leftValue = new Date(leftValue).getTime();
        rightValue = new Date(rightValue).getTime();
      }

      if (state.sortKey === "overall_status") {
        leftValue = severityRank[leftValue];
        rightValue = severityRank[rightValue];
      }

      if (
        typeof leftValue === "string"
        && typeof rightValue === "string"
      ) {
        return (
          leftValue.localeCompare(rightValue)
          * multiplier
        );
      }

      return (leftValue - rightValue) * multiplier;
    }
  );

  return sortedRuns;
}

function createTableCell(content, className = "") {
  const cell = createElement("td", className);

  if (content instanceof Node) {
    cell.appendChild(content);
  } else {
    cell.textContent = String(content);
  }

  return cell;
}

function renderRuns(runs) {
  state.runs = runs;
  elements.tableBody.replaceChildren();

  if (!runs.length) {
    elements.tableMessage.hidden = false;
    elements.tableMessage.textContent =
      "No runs match the selected filters.";
    return;
  }

  elements.tableMessage.hidden = true;

  for (const run of getSortedRuns()) {
    const row = document.createElement("tr");
    row.tabIndex = 0;
    row.dataset.runId = String(run.run_id);

    row.append(
      createTableCell(`#${run.run_id}`, "run-id"),
      createTableCell(formatDate(run.generated_at)),
      createTableCell(run.host_name),
      createTableCell(
        createStatusChip(run.overall_status)
      ),
      createTableCell(
        createStatusChip(run.system_status)
      ),
      createTableCell(
        createStatusChip(run.network_status)
      ),
      createTableCell(
        createStatusChip(run.service_status)
      ),
      createTableCell(
        createStatusChip(run.process_status)
      ),
      createTableCell(
        createStatusChip(run.log_status)
      ),
      createTableCell(run.incident_count),
      createTableCell(
        createElement(
          "button",
          "open-run",
          "›"
        )
      )
    );

    row.addEventListener(
      "click",
      () => openRunDrawer(run)
    );

    row.addEventListener(
      "keydown",
      event => {
        if (
          event.key === "Enter"
          || event.key === " "
        ) {
          event.preventDefault();
          openRunDrawer(run);
        }
      }
    );

    elements.tableBody.appendChild(row);
  }
}

function addDetailItem(container, label, value) {
  const item = createElement("div", "detail-item");
  item.append(
    createElement("span", "", label),
    createElement("strong", "", value)
  );
  container.appendChild(item);
}

function openRunDrawer(run) {
  elements.drawerTitle.textContent = `Run #${run.run_id}`;
  elements.drawerContent.replaceChildren();

  const summarySection = createElement(
    "section",
    "detail-section"
  );
  summarySection.appendChild(
    createElement("h3", "", "Summary")
  );

  const detailGrid = createElement(
    "div",
    "detail-grid"
  );

  addDetailItem(
    detailGrid,
    "Generated",
    formatDate(run.generated_at)
  );
  addDetailItem(detailGrid, "Host", run.host_name);
  addDetailItem(
    detailGrid,
    "Overall",
    run.overall_status
  );
  addDetailItem(
    detailGrid,
    "Incidents",
    String(run.incident_count)
  );

  summarySection.appendChild(detailGrid);

  const componentsSection = createElement(
    "section",
    "detail-section"
  );
  componentsSection.appendChild(
    createElement("h3", "", "Component health")
  );

  const componentList = createElement(
    "div",
    "component-list"
  );

  const components = {
    System: run.system_status,
    Network: run.network_status,
    Services: run.service_status,
    Processes: run.process_status,
    Logs: run.log_status
  };

  for (const [label, status] of Object.entries(components)) {
    const row = document.createElement("div");
    row.append(
      createElement("span", "", label),
      createStatusChip(status)
    );
    componentList.appendChild(row);
  }

  componentsSection.appendChild(componentList);

  const artifactsSection = createElement(
    "section",
    "detail-section"
  );
  artifactsSection.appendChild(
    createElement("h3", "", "Diagnostic artifacts")
  );

  const artifactsGrid = createElement(
    "div",
    "detail-grid"
  );

  addDetailItem(
    artifactsGrid,
    "Bundle ID",
    run.bundle_id
  );
  addDetailItem(
    artifactsGrid,
    "Archive",
    run.archive_path
  );

  artifactsSection.appendChild(artifactsGrid);

  elements.drawerContent.append(
    summarySection,
    componentsSection,
    artifactsSection
  );

  elements.drawer.classList.add("drawer--open");
  elements.drawer.setAttribute("aria-hidden", "false");
}

function closeRunDrawer() {
  elements.drawer.classList.remove("drawer--open");
  elements.drawer.setAttribute("aria-hidden", "true");
}

async function loadDashboard(showSuccess = false) {
  elements.refreshButton.disabled = true;

  try {
    const runsParameters = buildRunsParameters(true);
    const overviewParameters = buildRunsParameters(false);

    const [health, overview, runs] = await Promise.all([
      fetchJson("/api/v1/health"),
      fetchJson(
        `/api/v1/dashboard/overview?`
        + overviewParameters.toString()
      ),
      fetchJson(
        `/api/v1/runs?${runsParameters.toString()}`
      )
    ]);

    setConnection(true, health.version);
    renderOverview(overview);
    renderRuns(runs);

    elements.updatedAt.textContent =
      `Updated ${new Date().toLocaleTimeString()}`;

    if (showSuccess) {
      showToast("Dashboard data refreshed.");
    }
  } catch (error) {
    setConnection(false);
    elements.tableMessage.hidden = false;
    elements.tableMessage.textContent =
      `Unable to load reports: ${error.message}`;
    showToast(error.message, true);
  } finally {
    elements.refreshButton.disabled = false;
    scheduleAutoRefresh();
  }
}

function scheduleAutoRefresh() {
  window.clearTimeout(state.refreshTimer);
  window.clearInterval(state.countdownTimer);

  const intervalSeconds = Number(
    elements.refreshInterval.value
  );

  if (!intervalSeconds) {
    elements.refreshCountdown.textContent =
      "Auto refresh is off";
    state.nextRefreshAt = null;
    return;
  }

  state.nextRefreshAt =
    Date.now() + intervalSeconds * 1000;

  state.refreshTimer = window.setTimeout(
    () => loadDashboard(false),
    intervalSeconds * 1000
  );

  const updateCountdown = () => {
    const secondsRemaining = Math.max(
      0,
      Math.ceil(
        (state.nextRefreshAt - Date.now()) / 1000
      )
    );

    elements.refreshCountdown.textContent =
      `Next refresh in ${secondsRemaining}s`;
  };

  updateCountdown();
  state.countdownTimer = window.setInterval(
    updateCountdown,
    1000
  );
}

function exportCsv() {
  const parameters = buildRunsParameters(true);
  parameters.set("limit", "1000");

  window.location.href =
    `/api/v1/runs/export.csv?${parameters.toString()}`;
}

elements.filters.addEventListener(
  "submit",
  event => {
    event.preventDefault();
    loadDashboard(false);
  }
);

elements.clearFilters.addEventListener(
  "click",
  () => {
    elements.hostFilter.value = "";
    elements.statusFilter.value = "";
    elements.limitFilter.value = "20";
    loadDashboard(false);
  }
);

elements.refreshButton.addEventListener(
  "click",
  () => loadDashboard(true)
);

elements.refreshInterval.addEventListener(
  "change",
  scheduleAutoRefresh
);

elements.exportButton.addEventListener(
  "click",
  exportCsv
);

elements.printButton.addEventListener(
  "click",
  () => window.print()
);

elements.drawerClose.addEventListener(
  "click",
  closeRunDrawer
);

elements.drawerBackdrop.addEventListener(
  "click",
  closeRunDrawer
);

document.addEventListener(
  "keydown",
  event => {
    if (event.key === "Escape") {
      closeRunDrawer();
    }
  }
);

document
  .querySelectorAll("[data-sort]")
  .forEach(
    button => {
      button.addEventListener(
        "click",
        () => {
          const key = button.dataset.sort;

          if (state.sortKey === key) {
            state.sortDirection =
              state.sortDirection === "asc"
                ? "desc"
                : "asc";
          } else {
            state.sortKey = key;
            state.sortDirection = "asc";
          }

          renderRuns(state.runs);
        }
      );
    }
  );

loadDashboard(false);
