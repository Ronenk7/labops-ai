"use strict";

const state = {
  runs: [],
  incidents: [],
  overview: null,
  incidentSummary: null,
  incidentSortKey: "last_seen_at",
  incidentSortDirection: "desc",
  sortKey: "generated_at",
  sortDirection: "desc",
  refreshTimer: null,
  countdownTimer: null,
  nextRefreshAt: null,
  liveSource: null,
  liveRunTimer: null,
  latestObservedRunId: null,
  liveHistory: {
    cpu: [],
    memory: [],
    disk: [],
    network: []
  },
  hostSuggestionTimer: null,
  hostSuggestionRequest: 0
};

const elements = {
  connectionDot: document.querySelector("#connection-dot"),
  connectionLabel: document.querySelector("#connection-label"),
  refreshButton: document.querySelector("#refresh-button"),
  refreshInterval: document.querySelector("#refresh-interval"),
  refreshCountdown: document.querySelector("#refresh-countdown"),
  exportButton: document.querySelector("#export-button"),
  printButton: document.querySelector("#print-button"),
  liveStreamState: document.querySelector(
    "#live-stream-state"
  ),
  liveCore: document.querySelector("#live-core"),
  livePressure: document.querySelector("#live-pressure"),
  liveStatus: document.querySelector("#live-status"),
  liveSampledAt: document.querySelector(
    "#live-sampled-at"
  ),
  liveUptime: document.querySelector("#live-uptime"),
  liveProcesses: document.querySelector(
    "#live-processes"
  ),
  liveCpuCard: document.querySelector(
    "#live-cpu-card"
  ),
  liveMemoryCard: document.querySelector(
    "#live-memory-card"
  ),
  liveDiskCard: document.querySelector(
    "#live-disk-card"
  ),
  liveCpu: document.querySelector("#live-cpu"),
  liveMemory: document.querySelector("#live-memory"),
  liveDisk: document.querySelector("#live-disk"),
  liveCpuCores: document.querySelector(
    "#live-cpu-cores"
  ),
  liveNetworkRx: document.querySelector(
    "#live-network-rx"
  ),
  liveNetworkTx: document.querySelector(
    "#live-network-tx"
  ),
  liveLoad1: document.querySelector("#live-load-1"),
  liveLoad5: document.querySelector("#live-load-5"),
  liveLoad15: document.querySelector("#live-load-15"),
  liveCpuSparkline: document.querySelector(
    "#live-cpu-sparkline"
  ),
  liveMemorySparkline: document.querySelector(
    "#live-memory-sparkline"
  ),
  liveDiskSparkline: document.querySelector(
    "#live-disk-sparkline"
  ),
  liveNetworkSparkline: document.querySelector(
    "#live-network-sparkline"
  ),
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
  incidentCenterLabel: document.querySelector(
    "#incident-center-label"
  ),
  incidentActiveCount: document.querySelector(
    "#incident-active-count"
  ),
  incidentCriticalCount: document.querySelector(
    "#incident-critical-count"
  ),
  incidentAcknowledgedCount: document.querySelector(
    "#incident-acknowledged-count"
  ),
  incidentResolvedCount: document.querySelector(
    "#incident-resolved-count"
  ),
  sourceSystemCount: document.querySelector(
    "#source-system-count"
  ),
  sourceNetworkCount: document.querySelector(
    "#source-network-count"
  ),
  sourceServiceCount: document.querySelector(
    "#source-service-count"
  ),
  sourceProcessCount: document.querySelector(
    "#source-process-count"
  ),
  sourceLogCount: document.querySelector(
    "#source-log-count"
  ),
  incidentResultCount: document.querySelector(
    "#incident-result-count"
  ),
  incidentFilters: document.querySelector(
    "#incident-filters"
  ),
  incidentStatusFilter: document.querySelector(
    "#incident-status-filter"
  ),
  incidentSeverityFilter: document.querySelector(
    "#incident-severity-filter"
  ),
  incidentSourceFilter: document.querySelector(
    "#incident-source-filter"
  ),
  incidentActiveFilter: document.querySelector(
    "#incident-active-filter"
  ),
  incidentLimitFilter: document.querySelector(
    "#incident-limit-filter"
  ),
  clearIncidentFilters: document.querySelector(
    "#clear-incident-filters"
  ),
  incidentTableBody: document.querySelector(
    "#incident-table-body"
  ),
  incidentTableMessage: document.querySelector(
    "#incident-table-message"
  ),
  filters: document.querySelector("#filters"),
  hostFilter: document.querySelector("#host-filter"),
  hostAutocomplete: document.querySelector(
    "#host-autocomplete"
  ),
  hostSuggestions: document.querySelector(
    "#host-suggestions"
  ),
  hostSuggestionsButton: document.querySelector(
    "#host-suggestions-button"
  ),
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


const incidentStatusRank = {
  RESOLVED: 1,
  ACKNOWLEDGED: 2,
  OPEN: 3
};

function formatTransferRate(bytesPerSecond) {
  const units = ["B/s", "KB/s", "MB/s", "GB/s"];
  let value = Math.max(0, bytesPerSecond);
  let unitIndex = 0;

  while (
    value >= 1024
    && unitIndex < units.length - 1
  ) {
    value /= 1024;
    unitIndex += 1;
  }

  const precision = value >= 100 ? 0 : 1;

  return `${value.toFixed(precision)} ${
    units[unitIndex]
  }`;
}

function formatUptime(seconds) {
  const totalSeconds = Math.max(
    0,
    Math.floor(seconds)
  );
  const days = Math.floor(
    totalSeconds / 86400
  );
  const hours = Math.floor(
    (totalSeconds % 86400) / 3600
  );
  const minutes = Math.floor(
    (totalSeconds % 3600) / 60
  );

  if (days > 0) {
    return `${days}d ${hours}h`;
  }

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }

  return `${minutes}m`;
}

function appendLiveHistory(key, value) {
  const values = state.liveHistory[key];
  values.push(Number(value));

  if (values.length > 32) {
    values.shift();
  }
}

function renderLiveSparkline(element, values) {
  element.replaceChildren();

  if (values.length < 2) {
    return;
  }

  const maximum = Math.max(...values, 1);
  const minimum = Math.min(...values, 0);
  const range = Math.max(maximum - minimum, 1);

  const points = values.map(
    (value, index) => {
      const x = (
        index / (values.length - 1)
      ) * 100;
      const y = (
        25
        - ((value - minimum) / range) * 21
      );

      return `${x.toFixed(2)},${y.toFixed(2)}`;
    }
  );

  const area = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "polygon"
  );
  area.setAttribute(
    "points",
    `0,28 ${points.join(" ")} 100,28`
  );
  area.setAttribute(
    "class",
    "live-sparkline__area"
  );

  const line = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "polyline"
  );
  line.setAttribute("points", points.join(" "));

  element.append(area, line);
}

function animateLiveCard(card) {
  card.classList.remove("is-updating");
  void card.offsetWidth;
  card.classList.add("is-updating");

  window.setTimeout(
    () => card.classList.remove("is-updating"),
    520
  );
}

function updateLiveGauge(
  card,
  valueElement,
  value
) {
  const normalized = Math.min(
    100,
    Math.max(0, Number(value))
  );

  card.style.setProperty(
    "--value",
    normalized.toFixed(2)
  );
  valueElement.textContent =
    `${normalized.toFixed(1)}%`;

  animateLiveCard(card);
}

function renderLiveMetrics(metrics) {
  appendLiveHistory(
    "cpu",
    metrics.cpu_percent
  );
  appendLiveHistory(
    "memory",
    metrics.memory_percent
  );
  appendLiveHistory(
    "disk",
    metrics.disk_percent
  );
  appendLiveHistory(
    "network",
    (
      metrics.network_receive_bps
      + metrics.network_transmit_bps
    )
  );

  updateLiveGauge(
    elements.liveCpuCard,
    elements.liveCpu,
    metrics.cpu_percent
  );
  updateLiveGauge(
    elements.liveMemoryCard,
    elements.liveMemory,
    metrics.memory_percent
  );
  updateLiveGauge(
    elements.liveDiskCard,
    elements.liveDisk,
    metrics.disk_percent
  );

  elements.livePressure.textContent =
    `${Math.max(
      metrics.cpu_percent,
      metrics.memory_percent,
      metrics.disk_percent
    ).toFixed(0)}%`;

  elements.liveStatus.textContent =
    metrics.status;
  elements.liveSampledAt.textContent =
    new Date(
      metrics.sampled_at
    ).toLocaleTimeString();
  elements.liveUptime.textContent =
    formatUptime(metrics.uptime_seconds);
  elements.liveProcesses.textContent =
    String(metrics.process_count);
  elements.liveCpuCores.textContent =
    `${metrics.cpu_count} logical CPU cores`;

  elements.liveNetworkRx.textContent =
    formatTransferRate(
      metrics.network_receive_bps
    );
  elements.liveNetworkTx.textContent =
    formatTransferRate(
      metrics.network_transmit_bps
    );

  elements.liveLoad1.textContent =
    metrics.load_1.toFixed(2);
  elements.liveLoad5.textContent =
    metrics.load_5.toFixed(2);
  elements.liveLoad15.textContent =
    metrics.load_15.toFixed(2);

  elements.liveCore.classList.remove(
    "live-core--HEALTHY",
    "live-core--WARNING",
    "live-core--CRITICAL"
  );
  elements.liveCore.classList.add(
    `live-core--${metrics.status}`
  );

  renderLiveSparkline(
    elements.liveCpuSparkline,
    state.liveHistory.cpu
  );
  renderLiveSparkline(
    elements.liveMemorySparkline,
    state.liveHistory.memory
  );
  renderLiveSparkline(
    elements.liveDiskSparkline,
    state.liveHistory.disk
  );
  renderLiveSparkline(
    elements.liveNetworkSparkline,
    state.liveHistory.network
  );
}

function setLiveStreamState(stateName, label) {
  if (!elements.liveStreamState) {
    return;
  }

  elements.liveStreamState.classList.remove(
    "live-stream-state--online",
    "live-stream-state--error"
  );

  if (stateName === "online") {
    elements.liveStreamState.classList.add(
      "live-stream-state--online"
    );
  }

  if (stateName === "error") {
    elements.liveStreamState.classList.add(
      "live-stream-state--error"
    );
  }

  elements.liveStreamState.textContent = label;
}

function connectLiveStream() {
  if (
    !elements.liveStreamState
    || !elements.liveCore
    || typeof window.EventSource !== "function"
  ) {
    return;
  }

  if (state.liveSource) {
    state.liveSource.close();
  }

  setLiveStreamState(
    "connecting",
    "Connecting to live stream"
  );

  const source = new EventSource(
    "/api/v1/live/stream"
  );

  state.liveSource = source;

  source.addEventListener(
    "open",
    () => {
      setLiveStreamState(
        "online",
        "Live · updating every 2 seconds"
      );
    }
  );

  source.addEventListener(
    "metrics",
    event => {
      try {
        renderLiveMetrics(
          JSON.parse(event.data)
        );
      } catch {
        setLiveStreamState(
          "error",
          "Invalid live signal"
        );
      }
    }
  );

  source.addEventListener(
    "error",
    () => {
      setLiveStreamState(
        "error",
        "Reconnecting to live stream"
      );
    }
  );
}

async function watchLatestRun() {
  window.clearTimeout(state.liveRunTimer);

  try {
    const latestRun = await fetchJson(
      "/api/v1/runs/latest"
    );

    if (state.latestObservedRunId === null) {
      state.latestObservedRunId =
        latestRun.run_id;
    } else if (
      latestRun.run_id
      !== state.latestObservedRunId
    ) {
      state.latestObservedRunId =
        latestRun.run_id;

      showToast(
        `New monitoring run #${
          latestRun.run_id
        } received.`
      );

      await loadDashboard(false);
    }
  } catch {
    // The scheduled dashboard refresh remains
    // the fallback when history is unavailable.
  } finally {
    state.liveRunTimer = window.setTimeout(
      watchLatestRun,
      5000
    );
  }
}

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

function closeHostSuggestions() {
  elements.hostSuggestions.hidden = true;
  elements.hostSuggestions.replaceChildren();
  elements.hostFilter.setAttribute(
    "aria-expanded",
    "false"
  );
}

function selectHostSuggestion(hostName) {
  elements.hostFilter.value = hostName;
  closeHostSuggestions();
  loadDashboard(false);
}

function renderHostSuggestions(hosts) {
  elements.hostSuggestions.replaceChildren();

  if (!hosts.length) {
    closeHostSuggestions();
    return;
  }

  for (const hostName of hosts) {
    const item = document.createElement("li");
    const button = createElement(
      "button",
      "",
      hostName
    );

    button.type = "button";
    button.setAttribute("role", "option");

    button.addEventListener(
      "click",
      () => selectHostSuggestion(hostName)
    );

    item.appendChild(button);
    elements.hostSuggestions.appendChild(item);
  }

  elements.hostSuggestions.hidden = false;
  elements.hostFilter.setAttribute(
    "aria-expanded",
    "true"
  );
}

async function requestHostSuggestions(prefix) {
  const requestNumber =
    ++state.hostSuggestionRequest;

  const parameters = new URLSearchParams({
    q: prefix,
    limit: "10"
  });

  try {
    const hosts = await fetchJson(
      `/api/v1/hosts/suggestions?`
      + parameters.toString()
    );

    if (
      requestNumber
      !== state.hostSuggestionRequest
    ) {
      return;
    }

    renderHostSuggestions(hosts);
  } catch (error) {
    if (
      requestNumber
      === state.hostSuggestionRequest
    ) {
      closeHostSuggestions();
      showToast(
        `Unable to load hosts: ${error.message}`,
        true
      );
    }
  }
}

function scheduleHostSuggestions() {
  window.clearTimeout(
    state.hostSuggestionTimer
  );

  const prefix =
    elements.hostFilter.value.trim();

  if (!prefix) {
    closeHostSuggestions();
    return;
  }

  state.hostSuggestionTimer =
    window.setTimeout(
      () => requestHostSuggestions(prefix),
      250
    );
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

function buildIncidentParameters() {
  const parameters = new URLSearchParams({
    limit: elements.incidentLimitFilter.value
  });

  if (elements.incidentStatusFilter.value) {
    parameters.set(
      "status",
      elements.incidentStatusFilter.value
    );
  }

  if (elements.incidentSeverityFilter.value) {
    parameters.set(
      "severity",
      elements.incidentSeverityFilter.value
    );
  }

  if (elements.incidentSourceFilter.value) {
    parameters.set(
      "source_type",
      elements.incidentSourceFilter.value
    );
  }

  if (elements.incidentActiveFilter.value) {
    parameters.set(
      "active_only",
      elements.incidentActiveFilter.value
    );
  }

  return parameters;
}

function createIncidentStatusChip(status) {
  return createElement(
    "span",
    `incident-status incident-status--${status}`,
    status
  );
}

function createSourceBadge(sourceType) {
  return createElement(
    "span",
    "source-badge",
    sourceType
  );
}

function renderIncidentSummary(summary) {
  state.incidentSummary = summary;

  elements.incidentActiveCount.textContent =
    String(summary.active);
  elements.incidentCriticalCount.textContent =
    String(summary.critical);
  elements.incidentAcknowledgedCount.textContent =
    String(summary.acknowledged);
  elements.incidentResolvedCount.textContent =
    String(summary.resolved);

  const sources = summary.source_counts;

  elements.sourceSystemCount.textContent =
    String(sources.SYSTEM || 0);
  elements.sourceNetworkCount.textContent =
    String(sources.NETWORK || 0);
  elements.sourceServiceCount.textContent =
    String(sources.SERVICE || 0);
  elements.sourceProcessCount.textContent =
    String(sources.PROCESS || 0);
  elements.sourceLogCount.textContent =
    String(sources.LOG || 0);

  const healthContainer =
    elements.incidentCenterLabel.parentElement;

  healthContainer.classList.remove(
    "incident-health--attention",
    "incident-health--critical"
  );

  if (summary.critical > 0) {
    healthContainer.classList.add(
      "incident-health--critical"
    );

    elements.incidentCenterLabel.textContent =
      `${summary.critical} critical incident`
      + `${summary.critical === 1 ? "" : "s"}`;
  } else if (summary.active > 0) {
    healthContainer.classList.add(
      "incident-health--attention"
    );

    elements.incidentCenterLabel.textContent =
      `${summary.active} active incident`
      + `${summary.active === 1 ? "" : "s"}`;
  } else {
    elements.incidentCenterLabel.textContent =
      "No active incidents";
  }
}

function getSortedIncidents() {
  const incidents = [...state.incidents];
  const multiplier =
    state.incidentSortDirection === "asc" ? 1 : -1;

  incidents.sort(
    (left, right) => {
      let leftValue =
        left[state.incidentSortKey];
      let rightValue =
        right[state.incidentSortKey];

      if (
        state.incidentSortKey === "last_seen_at"
        || state.incidentSortKey === "first_seen_at"
      ) {
        leftValue = new Date(leftValue).getTime();
        rightValue = new Date(rightValue).getTime();
      }

      if (state.incidentSortKey === "severity") {
        leftValue = severityRank[leftValue];
        rightValue = severityRank[rightValue];
      }

      if (state.incidentSortKey === "status") {
        leftValue = incidentStatusRank[leftValue];
        rightValue = incidentStatusRank[rightValue];
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

  return incidents;
}

function renderIncidents(incidents) {
  state.incidents = incidents;
  elements.incidentTableBody.replaceChildren();

  elements.incidentResultCount.textContent =
    `${incidents.length} incident`
    + `${incidents.length === 1 ? "" : "s"}`;

  if (!incidents.length) {
    elements.incidentTableMessage.hidden = false;
    elements.incidentTableMessage.textContent =
      "No incidents match the selected filters.";
    return;
  }

  elements.incidentTableMessage.hidden = true;

  for (const incident of getSortedIncidents()) {
    const row = document.createElement("tr");
    row.tabIndex = 0;
    row.dataset.incidentId = incident.incident_id;

    row.append(
      createTableCell(
        incident.incident_id,
        "incident-id"
      ),
      createTableCell(
        formatDate(incident.last_seen_at)
      ),
      createTableCell(
        createSourceBadge(incident.source_type)
      ),
      createTableCell(
        createStatusChip(incident.severity)
      ),
      createTableCell(
        createIncidentStatusChip(incident.status)
      ),
      createTableCell(incident.occurrence_count),
      createTableCell(
        incident.description,
        "incident-description"
      ),
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
      () => openIncidentDrawer(incident)
    );

    row.addEventListener(
      "keydown",
      event => {
        if (
          event.key === "Enter"
          || event.key === " "
        ) {
          event.preventDefault();
          openIncidentDrawer(incident);
        }
      }
    );

    elements.incidentTableBody.appendChild(row);
  }
}

function openIncidentDrawer(incident) {
  elements.drawerTitle.textContent =
    incident.incident_id;
  elements.drawerContent.replaceChildren();

  const summarySection = createElement(
    "section",
    "detail-section"
  );

  summarySection.appendChild(
    createElement("h3", "", "Incident summary")
  );

  const summaryGrid = createElement(
    "div",
    "detail-grid"
  );

  addDetailItem(
    summaryGrid,
    "Source",
    `${incident.source_type}: ${incident.source_label}`
  );
  addDetailItem(
    summaryGrid,
    "Source ID",
    incident.source_id
  );
  addDetailItem(
    summaryGrid,
    "Severity",
    incident.severity
  );
  addDetailItem(
    summaryGrid,
    "Status",
    incident.status
  );
  addDetailItem(
    summaryGrid,
    "Occurrences",
    String(incident.occurrence_count)
  );
  addDetailItem(
    summaryGrid,
    "Lifecycle",
    incident.is_active ? "Active" : "Inactive"
  );

  summarySection.appendChild(summaryGrid);

  const timelineSection = createElement(
    "section",
    "detail-section"
  );

  timelineSection.appendChild(
    createElement("h3", "", "Timeline")
  );

  const timelineGrid = createElement(
    "div",
    "detail-grid"
  );

  addDetailItem(
    timelineGrid,
    "First seen",
    formatDate(incident.first_seen_at)
  );
  addDetailItem(
    timelineGrid,
    "Last seen",
    formatDate(incident.last_seen_at)
  );

  if (incident.resolved_at) {
    addDetailItem(
      timelineGrid,
      "Resolved",
      formatDate(incident.resolved_at)
    );
  }

  timelineSection.appendChild(timelineGrid);

  const descriptionSection = createElement(
    "section",
    "detail-section"
  );

  descriptionSection.appendChild(
    createElement("h3", "", "Description")
  );
  descriptionSection.appendChild(
    createElement(
      "div",
      "incident-description-card",
      incident.description
    )
  );

  elements.drawerContent.append(
    summarySection,
    timelineSection,
    descriptionSection
  );

  elements.drawer.classList.add("drawer--open");
  elements.drawer.setAttribute(
    "aria-hidden",
    "false"
  );
}

function renderRuns(runs) {
  const selectedLimit = Number(
    elements.limitFilter.value
  );
  const visibleRuns = runs.slice(0, selectedLimit);

  state.runs = visibleRuns;
  elements.tableBody.replaceChildren();

  if (!visibleRuns.length) {
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

function humanizeDiagnosticKey(key) {
  return key
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      character => character.toUpperCase()
    );
}

function formatDiagnosticValue(key, value) {
  if (value === null || value === undefined) {
    return "—";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (Array.isArray(value)) {
    return value.length
      ? value.join(", ")
      : "None";
  }

  if (typeof value === "number") {
    const formatted = Number.isInteger(value)
      ? String(value)
      : value.toFixed(2);

    if (key.endsWith("_percent")) {
      return `${formatted}%`;
    }

    if (key.endsWith("_ms")) {
      return `${formatted} ms`;
    }

    if (key.endsWith("_mb")) {
      return `${formatted} MB`;
    }

    if (key.endsWith("_seconds")) {
      return `${formatted} seconds`;
    }

    return formatted;
  }

  if (
    key.endsWith("_at")
    && typeof value === "string"
  ) {
    try {
      return formatDate(value);
    } catch {
      return value;
    }
  }

  return String(value);
}

function createDiagnosticCard(
  title,
  status,
  record
) {
  const card = createElement(
    "article",
    "diagnostic-record"
  );

  const header = createElement(
    "header",
    "diagnostic-record__header"
  );

  header.appendChild(
    createElement(
      "strong",
      "diagnostic-record__title",
      title
    )
  );

  if (status) {
    header.appendChild(
      createStatusChip(status)
    );
  }

  card.appendChild(header);

  const grid = createElement(
    "div",
    "diagnostic-record__grid"
  );

  for (
    const [key, value]
    of Object.entries(record)
  ) {
    const item = createElement(
      "div",
      "diagnostic-field"
    );

    if (
      [
        "description",
        "error_message",
        "failure_reason",
        "path",
        "target",
        "resolved_address",
        "pids"
      ].includes(key)
    ) {
      item.classList.add(
        "diagnostic-field--wide"
      );
    }

    item.append(
      createElement(
        "span",
        "diagnostic-field__label",
        humanizeDiagnosticKey(key)
      ),
      createElement(
        "strong",
        "diagnostic-field__value",
        formatDiagnosticValue(key, value)
      )
    );

    grid.appendChild(item);
  }

  card.appendChild(grid);
  return card;
}

function createDiagnosticGroup(
  title,
  overallStatus,
  records,
  getTitle,
  emptyMessage
) {
  const section = createElement(
    "section",
    "detail-section diagnostic-group"
  );

  const heading = createElement(
    "div",
    "diagnostic-group__heading"
  );

  heading.appendChild(
    createElement("h3", "", title)
  );

  if (overallStatus) {
    heading.appendChild(
      createStatusChip(overallStatus)
    );
  }

  section.appendChild(heading);

  const list = createElement(
    "div",
    "diagnostic-records"
  );

  if (!records.length) {
    list.appendChild(
      createElement(
        "div",
        "diagnostic-empty",
        emptyMessage
      )
    );
  } else {
    for (const record of records) {
      const status = (
        record.health_status
        || record.severity
        || null
      );

      list.appendChild(
        createDiagnosticCard(
          getTitle(record),
          status,
          record
        )
      );
    }
  }

  section.appendChild(list);
  return section;
}

function renderRunDetails(payload) {
  const run = payload.run;
  const diagnostics = payload.diagnostics;

  elements.drawerTitle.textContent =
    `Run #${run.run_id}`;

  elements.drawerContent.replaceChildren();

  const metadata = {
    run_id: run.run_id,
    generated_at: run.generated_at,
    report_generated_at:
      diagnostics.generated_at,
    host_name: diagnostics.host_name,
    overall_status:
      diagnostics.overall_status,
    bundle_id: run.bundle_id,
    archive_path: run.archive_path
  };

  const summarySection = createElement(
    "section",
    "detail-section diagnostic-group"
  );

  const summaryHeading = createElement(
    "div",
    "diagnostic-group__heading"
  );

  summaryHeading.append(
    createElement("h3", "", "Run summary"),
    createStatusChip(
      diagnostics.overall_status
    )
  );

  summarySection.append(
    summaryHeading,
    createDiagnosticCard(
      "Monitoring run",
      diagnostics.overall_status,
      metadata
    ),
    createDiagnosticCard(
      "Health summary",
      diagnostics.overall_status,
      diagnostics.summary
    )
  );

  const systemSection =
    createDiagnosticGroup(
      "System metrics",
      diagnostics.system.overall_status,
      diagnostics.system.metrics || [],
      metric => (
        metric.label || metric.metric_name
      ),
      "No system metrics were recorded."
    );

  const networkSection =
    createDiagnosticGroup(
      "Network checks",
      diagnostics.network.overall_status,
      diagnostics.network.checks || [],
      check => (
        `${check.check_type}: ${check.target}`
      ),
      "No network checks were recorded."
    );

  const serviceSection =
    createDiagnosticGroup(
      "Service checks",
      diagnostics.services.overall_status,
      diagnostics.services.records || [],
      service => (
        service.label
        || service.service_name
      ),
      "No services were configured."
    );

  const processSection =
    createDiagnosticGroup(
      "Process checks",
      diagnostics.processes.overall_status,
      diagnostics.processes.records || [],
      process => (
        process.label
        || process.process_name
      ),
      "No processes were configured."
    );

  const logSection =
    createDiagnosticGroup(
      "Log analysis",
      diagnostics.logs.overall_status,
      diagnostics.logs.records || [],
      log => (
        log.label || log.source_id
      ),
      "No log sources were configured."
    );

  const incidentSection =
    createDiagnosticGroup(
      "Incident snapshot",
      null,
      diagnostics.incidents.records || [],
      incident => incident.incident_id,
      "No incidents were present in this run."
    );

  elements.drawerContent.append(
    summarySection,
    systemSection,
    networkSection,
    serviceSection,
    processSection,
    logSection,
    incidentSection
  );
}

async function openRunDrawer(run) {
  elements.drawerTitle.textContent =
    `Run #${run.run_id}`;

  elements.drawerContent.replaceChildren(
    createElement(
      "div",
      "run-details-loading",
      "Loading real diagnostic data from ZIP…"
    )
  );

  elements.drawer.classList.add(
    "drawer--open"
  );
  elements.drawer.setAttribute(
    "aria-hidden",
    "false"
  );

  try {
    const details = await fetchJson(
      `/api/v1/runs/${run.run_id}/details`
    );

    renderRunDetails(details);
  } catch (error) {
    elements.drawerContent.replaceChildren(
      createElement(
        "div",
        "diagnostic-error",
        `Unable to load ZIP details: ${
          error.message
        }`
      )
    );

    showToast(error.message, true);
  }
}

function closeRunDrawer() {
  elements.drawer.classList.remove("drawer--open");
  elements.drawer.setAttribute("aria-hidden", "true");
}

async function loadDashboard(showSuccess = false) {
  elements.refreshButton.disabled = true;

  try {
    const runsParameters =
      buildRunsParameters(true);
    const overviewParameters =
      buildRunsParameters(false);
    const incidentParameters =
      buildIncidentParameters();

    const [
      health,
      overview,
      runs,
      incidentSummary,
      incidents
    ] = await Promise.all([
      fetchJson("/api/v1/health"),
      fetchJson(
        `/api/v1/dashboard/overview?`
        + overviewParameters.toString()
      ),
      fetchJson(
        `/api/v1/runs?${runsParameters.toString()}`
      ),
      fetchJson("/api/v1/incidents/summary"),
      fetchJson(
        `/api/v1/incidents?`
        + incidentParameters.toString()
      )
    ]);

    setConnection(true, health.version);
    renderOverview(overview);
    renderRuns(runs);
    renderIncidentSummary(incidentSummary);
    renderIncidents(incidents);

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

    elements.incidentTableMessage.hidden = false;
    elements.incidentTableMessage.textContent =
      `Unable to load incidents: ${error.message}`;

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

elements.hostFilter.addEventListener(
  "input",
  scheduleHostSuggestions
);

elements.hostSuggestionsButton.addEventListener(
  "click",
  () => {
    window.clearTimeout(
      state.hostSuggestionTimer
    );

    requestHostSuggestions(
      elements.hostFilter.value.trim()
    );
  }
);

elements.hostFilter.addEventListener(
  "keydown",
  event => {
    if (event.key === "Escape") {
      closeHostSuggestions();
      return;
    }

    if (
      event.key === "ArrowDown"
      && !elements.hostSuggestions.hidden
    ) {
      event.preventDefault();

      const firstSuggestion =
        elements.hostSuggestions.querySelector(
          "button"
        );

      if (firstSuggestion) {
        firstSuggestion.focus();
      }
    }
  }
);

document.addEventListener(
  "click",
  event => {
    if (
      !elements.hostAutocomplete.contains(
        event.target
      )
    ) {
      closeHostSuggestions();
    }
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

elements.incidentFilters.addEventListener(
  "submit",
  event => {
    event.preventDefault();
    loadDashboard(false);
  }
);

elements.clearIncidentFilters.addEventListener(
  "click",
  () => {
    elements.incidentStatusFilter.value = "";
    elements.incidentSeverityFilter.value = "";
    elements.incidentSourceFilter.value = "";
    elements.incidentActiveFilter.value = "";
    elements.incidentLimitFilter.value = "25";
    loadDashboard(false);
  }
);

elements.refreshButton.addEventListener(
  "click",
  async () => {
    connectLiveStream();
    await loadDashboard(true);
  }
);

elements.refreshInterval.addEventListener(
  "change",
  scheduleAutoRefresh
);


elements.limitFilter.addEventListener(
  "change",
  () => loadDashboard(false)
);

elements.statusFilter.addEventListener(
  "change",
  () => loadDashboard(false)
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

document
  .querySelectorAll("[data-incident-sort]")
  .forEach(
    button => {
      button.addEventListener(
        "click",
        () => {
          const key =
            button.dataset.incidentSort;

          if (state.incidentSortKey === key) {
            state.incidentSortDirection =
              state.incidentSortDirection === "asc"
                ? "desc"
                : "asc";
          } else {
            state.incidentSortKey = key;
            state.incidentSortDirection = "asc";
          }

          renderIncidents(state.incidents);
        }
      );
    }
  );


loadDashboard(false);

window.setTimeout(
  () => {
    try {
      connectLiveStream();
      watchLatestRun();
    } catch (error) {
      console.error(
        "Live dashboard startup failed.",
        error
      );
    }
  },
  0
);

window.addEventListener(
  "beforeunload",
  () => {
    if (state.liveSource) {
      state.liveSource.close();
    }

    window.clearTimeout(
      state.liveRunTimer
    );
  }
);
