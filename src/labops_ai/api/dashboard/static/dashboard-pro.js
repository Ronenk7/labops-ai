"use strict";

const proUiState = {
  previousLiveMetrics: null
};


function proElement(tagName, className = "", text = undefined) {
  const element = document.createElement(tagName);

  if (className) {
    element.className = className;
  }

  if (text !== undefined) {
    element.textContent = text;
  }

  return element;
}


function proHumanize(value) {
  return String(value)
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      character => character.toUpperCase()
    );
}


function proIsMeaningful(value) {
  if (value === null || value === undefined) {
    return false;
  }

  if (typeof value === "string") {
    return value.trim() !== "";
  }

  if (Array.isArray(value)) {
    return value.length > 0;
  }

  return true;
}


function proMeaningfulEntries(record, omittedKeys = []) {
  const omitted = new Set(omittedKeys);

  return Object.entries(record).filter(
    ([key, value]) => (
      !omitted.has(key)
      && proIsMeaningful(value)
    )
  );
}


function proCreateFieldGrid(record, omittedKeys = []) {
  const grid = proElement(
    "div",
    "pro-field-grid"
  );

  const entries = proMeaningfulEntries(
    record,
    omittedKeys
  );

  for (const [key, value] of entries) {
    const field = proElement(
      "div",
      "pro-field"
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
      field.classList.add("pro-field--wide");
    }

    field.append(
      proElement(
        "span",
        "pro-field__label",
        proHumanize(key)
      ),
      proElement(
        "strong",
        "pro-field__value",
        formatDiagnosticValue(key, value)
      )
    );

    grid.appendChild(field);
  }

  return grid;
}


function proCreateStatus(status) {
  return createStatusChip(status || "HEALTHY");
}


function proStatusIsAttention(status) {
  return status && status !== "HEALTHY";
}


function proCreateKpi(
  label,
  value,
  description,
  status = null
) {
  const card = proElement(
    "article",
    "pro-kpi"
  );

  if (status) {
    card.dataset.status = status;
  }

  card.append(
    proElement(
      "span",
      "pro-kpi__label",
      label
    ),
    proElement(
      "strong",
      "pro-kpi__value",
      String(value)
    ),
    proElement(
      "small",
      "pro-kpi__description",
      description
    )
  );

  return card;
}


function proCreateSection(
  id,
  eyebrow,
  title,
  status = null
) {
  const section = proElement(
    "section",
    "pro-section"
  );
  section.id = id;

  if (proStatusIsAttention(status)) {
    section.classList.add(
      "pro-section--attention"
    );
  }

  const heading = proElement(
    "header",
    "pro-section__heading"
  );

  const titleBlock = proElement("div");

  titleBlock.append(
    proElement(
      "span",
      "pro-section__eyebrow",
      eyebrow
    ),
    proElement(
      "h3",
      "pro-section__title",
      title
    )
  );

  heading.appendChild(titleBlock);

  if (status) {
    heading.appendChild(proCreateStatus(status));
  }

  section.appendChild(heading);
  return section;
}


function proCreateMetricCard(metric) {
  const value = Number(metric.value_percent || 0);
  const card = proElement(
    "article",
    "pro-metric"
  );

  card.dataset.status = metric.health_status;

  const heading = proElement(
    "div",
    "pro-metric__heading"
  );

  const labelBlock = proElement("div");

  labelBlock.append(
    proElement(
      "span",
      "pro-metric__name",
      metric.label || metric.metric_name
    ),
    proElement(
      "small",
      "pro-metric__code",
      metric.metric_name
    )
  );

  heading.append(
    labelBlock,
    proElement(
      "strong",
      "pro-metric__value",
      `${value.toFixed(1)}%`
    )
  );

  const track = proElement(
    "div",
    "pro-meter"
  );
  const fill = proElement(
    "span",
    "pro-meter__fill"
  );

  fill.style.width = `${Math.min(100, value)}%`;
  track.appendChild(fill);

  card.append(
    heading,
    track,
    proCreateStatus(metric.health_status)
  );

  return card;
}


function proCreateNetworkCard(check) {
  const card = proElement(
    "article",
    "pro-network-card"
  );

  card.dataset.status = check.health_status;

  const header = proElement(
    "header",
    "pro-network-card__header"
  );

  const titleBlock = proElement("div");

  titleBlock.append(
    proElement(
      "span",
      "pro-network-card__type",
      check.check_type
    ),
    proElement(
      "strong",
      "pro-network-card__target",
      check.target
    )
  );

  header.append(
    titleBlock,
    proCreateStatus(check.health_status)
  );

  const latency = Number(check.latency_ms || 0);
  const latencyBlock = proElement(
    "div",
    "pro-latency"
  );

  const latencyHeading = proElement(
    "div",
    "pro-latency__heading"
  );

  latencyHeading.append(
    proElement("span", "", "Response time"),
    proElement(
      "strong",
      "",
      check.latency_ms === null
        ? "Not available"
        : `${latency.toFixed(2)} ms`
    )
  );

  const latencyTrack = proElement(
    "div",
    "pro-latency__track"
  );
  const latencyFill = proElement(
    "span",
    "pro-latency__fill"
  );

  latencyFill.style.width = `${
    Math.min(100, latency / 2)
  }%`;

  latencyTrack.appendChild(latencyFill);
  latencyBlock.append(
    latencyHeading,
    latencyTrack
  );

  const details = proCreateFieldGrid(
    check,
    [
      "check_type",
      "target",
      "health_status",
      "latency_ms",
      "failure_reason",
      "error_message"
    ]
  );

  card.append(
    header,
    latencyBlock,
    details
  );

  if (
    proIsMeaningful(check.failure_reason)
    || proIsMeaningful(check.error_message)
  ) {
    const alert = proElement(
      "div",
      "pro-inline-alert"
    );

    alert.textContent = (
      check.error_message
      || check.failure_reason
    );

    card.appendChild(alert);
  }

  return card;
}


function proCreateDisclosure(
  title,
  status,
  summaryText,
  record,
  omittedKeys,
  openByDefault = false
) {
  const disclosure = document.createElement(
    "details"
  );

  disclosure.className = "pro-disclosure";
  disclosure.dataset.status = status;
  disclosure.open = (
    openByDefault
    || proStatusIsAttention(status)
  );

  const summary = document.createElement("summary");
  const identity = proElement(
    "div",
    "pro-disclosure__identity"
  );

  identity.append(
    proElement(
      "strong",
      "pro-disclosure__title",
      title
    ),
    proElement(
      "span",
      "pro-disclosure__summary",
      summaryText
    )
  );

  summary.append(
    identity,
    proCreateStatus(status),
    proElement(
      "span",
      "pro-disclosure__chevron",
      "⌄"
    )
  );

  disclosure.append(
    summary,
    proCreateFieldGrid(record, omittedKeys)
  );

  return disclosure;
}


function proCreateEmptyState(title, description) {
  const empty = proElement(
    "div",
    "pro-empty-state"
  );

  empty.append(
    proElement(
      "span",
      "pro-empty-state__mark",
      "✓"
    ),
    proElement(
      "strong",
      "",
      title
    ),
    proElement(
      "p",
      "",
      description
    )
  );

  return empty;
}


function proCountAnomalies(diagnostics) {
  const collections = [
    diagnostics.system.metrics || [],
    diagnostics.network.checks || [],
    diagnostics.services.records || [],
    diagnostics.processes.records || [],
    diagnostics.logs.records || []
  ];

  return collections.reduce(
    (total, records) => (
      total
      + records.filter(
        record => (
          record.health_status
          && record.health_status !== "HEALTHY"
        )
      ).length
    ),
    0
  );
}


function proCreateComponentCard(
  label,
  status,
  itemCount,
  targetId
) {
  const button = proElement(
    "button",
    "pro-component-card"
  );

  button.type = "button";
  button.dataset.status = status;

  button.append(
    proElement(
      "span",
      "pro-component-card__label",
      label
    ),
    proElement(
      "strong",
      "pro-component-card__count",
      String(itemCount)
    ),
    proCreateStatus(status),
    proElement(
      "small",
      "",
      "Open details"
    )
  );

  button.addEventListener(
    "click",
    () => {
      document
        .querySelector(`#${targetId}`)
        ?.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
    }
  );

  return button;
}


function proCreateLiveComparison() {
  const panel = proElement(
    "section",
    "pro-live-comparison"
  );

  const heading = proElement(
    "div",
    "pro-live-comparison__heading"
  );

  heading.append(
    proElement(
      "span",
      "pro-live-comparison__beacon"
    ),
    proElement(
      "strong",
      "",
      "Live now"
    ),
    proElement(
      "small",
      "",
      "Current host telemetry — separate from this ZIP snapshot"
    )
  );

  const metrics = proElement(
    "div",
    "pro-live-comparison__metrics"
  );

  for (
    const [key, label]
    of [
      ["cpu_percent", "CPU"],
      ["memory_percent", "Memory"],
      ["disk_percent", "Disk"]
    ]
  ) {
    const item = proElement(
      "div",
      "pro-live-comparison__metric"
    );

    const value = proElement(
      "strong",
      "",
      "—"
    );

    value.dataset.proLiveValue = key;

    item.append(
      proElement("span", "", label),
      value
    );

    metrics.appendChild(item);
  }

  panel.append(heading, metrics);
  return panel;
}


function proUpdateLiveComparison(metrics) {
  if (!metrics) {
    return;
  }

  document
    .querySelectorAll("[data-pro-live-value]")
    .forEach(
      element => {
        const key = element.dataset.proLiveValue;
        const value = Number(metrics[key] || 0);

        element.textContent = `${value.toFixed(1)}%`;
      }
    );
}


function proCreateNavigation(items) {
  const navigation = proElement(
    "nav",
    "pro-run-nav"
  );

  for (const [label, targetId] of items) {
    const button = proElement(
      "button",
      "pro-run-nav__button",
      label
    );

    button.type = "button";

    button.addEventListener(
      "click",
      () => {
        document
          .querySelector(`#${targetId}`)
          ?.scrollIntoView({
            behavior: "smooth",
            block: "start"
          });
      }
    );

    navigation.appendChild(button);
  }

  return navigation;
}


renderRunDetails = function renderProfessionalRunDetails(
  payload
) {
  const run = payload.run;
  const diagnostics = payload.diagnostics;

  const systemMetrics =
    diagnostics.system.metrics || [];
  const networkChecks =
    diagnostics.network.checks || [];
  const serviceRecords =
    diagnostics.services.records || [];
  const processRecords =
    diagnostics.processes.records || [];
  const logRecords =
    diagnostics.logs.records || [];
  const incidents =
    diagnostics.incidents.records || [];

  const anomalyCount = proCountAnomalies(
    diagnostics
  );

  elements.drawerTitle.textContent =
    "Run intelligence";
  elements.drawerContent.replaceChildren();

  const root = proElement(
    "div",
    "run-story"
  );

  const hero = proElement(
    "section",
    "run-story__hero"
  );
  hero.dataset.status = diagnostics.overall_status;

  const heroMain = proElement(
    "div",
    "run-story__hero-main"
  );

  heroMain.append(
    proElement(
      "span",
      "run-story__eyebrow",
      "Historical diagnostic snapshot"
    ),
    proElement(
      "h2",
      "run-story__title",
      `Run #${run.run_id}`
    )
  );

  const heroMeta = proElement(
    "div",
    "run-story__meta"
  );

  heroMeta.append(
    proElement(
      "span",
      "",
      diagnostics.host_name
    ),
    proElement(
      "span",
      "",
      formatDate(run.generated_at)
    ),
    proElement(
      "span",
      "",
      `${systemMetrics.length
        + networkChecks.length
        + serviceRecords.length
        + processRecords.length
        + logRecords.length} checks`
    )
  );

  heroMain.appendChild(heroMeta);

  const heroStatus = proElement(
    "div",
    "run-story__hero-status"
  );

  heroStatus.append(
    proElement(
      "span",
      "",
      "Overall result"
    ),
    proElement(
      "strong",
      "",
      diagnostics.overall_status
    ),
    proElement(
      "small",
      "",
      anomalyCount
        ? `${anomalyCount} items require attention`
        : "No anomalies detected"
    )
  );

  hero.append(heroMain, heroStatus);

  const liveComparison = proCreateLiveComparison();

  const kpiGrid = proElement(
    "section",
    "pro-kpi-grid"
  );

  kpiGrid.append(
    proCreateKpi(
      "Attention items",
      anomalyCount,
      anomalyCount
        ? "Non-healthy diagnostic records"
        : "Snapshot is clean",
      anomalyCount ? "WARNING" : "HEALTHY"
    ),
    proCreateKpi(
      "Active incidents",
      diagnostics.incidents.active_count || 0,
      "Open at snapshot time",
      diagnostics.incidents.active_count
        ? "CRITICAL"
        : "HEALTHY"
    ),
    proCreateKpi(
      "Network checks",
      networkChecks.length,
      "DNS and TCP probes",
      diagnostics.network.overall_status
    ),
    proCreateKpi(
      "Services observed",
      serviceRecords.length,
      "systemd units checked",
      diagnostics.services.overall_status
    )
  );

  const componentGrid = proElement(
    "section",
    "pro-component-grid"
  );

  componentGrid.append(
    proCreateComponentCard(
      "System",
      diagnostics.system.overall_status,
      systemMetrics.length,
      "pro-system"
    ),
    proCreateComponentCard(
      "Network",
      diagnostics.network.overall_status,
      networkChecks.length,
      "pro-network"
    ),
    proCreateComponentCard(
      "Services",
      diagnostics.services.overall_status,
      serviceRecords.length,
      "pro-services"
    ),
    proCreateComponentCard(
      "Processes",
      diagnostics.processes.overall_status,
      processRecords.length,
      "pro-processes"
    ),
    proCreateComponentCard(
      "Logs",
      diagnostics.logs.overall_status,
      logRecords.length,
      "pro-logs"
    ),
    proCreateComponentCard(
      "Incidents",
      incidents.length
        ? incidents[0].severity
        : "HEALTHY",
      incidents.length,
      "pro-incidents"
    )
  );

  const navigation = proCreateNavigation([
    ["Overview", "pro-overview"],
    ["System", "pro-system"],
    ["Network", "pro-network"],
    ["Services", "pro-services"],
    ["Processes", "pro-processes"],
    ["Logs", "pro-logs"],
    ["Incidents", "pro-incidents"]
  ]);

  const overviewSection = proCreateSection(
    "pro-overview",
    "Snapshot context",
    "Run overview",
    diagnostics.overall_status
  );

  const overviewGrid = proElement(
    "div",
    "pro-overview-grid"
  );

  overviewGrid.append(
    proCreateKpi(
      "Generated",
      formatDate(diagnostics.generated_at),
      "Timestamp stored inside the ZIP"
    ),
    proCreateKpi(
      "Host",
      diagnostics.host_name,
      "Monitored system"
    ),
    proCreateKpi(
      "Resolved incidents",
      diagnostics.incidents.resolved_count || 0,
      "Resolved at snapshot time"
    )
  );

  const technicalDetails =
    document.createElement("details");

  technicalDetails.className =
    "pro-technical-details";

  const technicalSummary =
    document.createElement("summary");

  technicalSummary.textContent =
    "Technical bundle metadata";

  technicalDetails.append(
    technicalSummary,
    proCreateFieldGrid(
      {
        bundle_id: run.bundle_id,
        archive_path: run.archive_path,
        schema_version:
          diagnostics.schema_version,
        report_generated_at:
          diagnostics.generated_at
      }
    )
  );

  overviewSection.append(
    overviewGrid,
    technicalDetails
  );

  const systemSection = proCreateSection(
    "pro-system",
    "Resource telemetry",
    "System metrics",
    diagnostics.system.overall_status
  );

  const metricGrid = proElement(
    "div",
    "pro-metric-grid"
  );

  if (systemMetrics.length) {
    for (const metric of systemMetrics) {
      metricGrid.appendChild(
        proCreateMetricCard(metric)
      );
    }
  } else {
    metricGrid.appendChild(
      proCreateEmptyState(
        "No system metrics",
        "The ZIP did not contain system telemetry."
      )
    );
  }

  systemSection.appendChild(metricGrid);

  const networkSection = proCreateSection(
    "pro-network",
    "Connectivity evidence",
    "Network checks",
    diagnostics.network.overall_status
  );

  const networkGrid = proElement(
    "div",
    "pro-network-grid"
  );

  if (networkChecks.length) {
    for (const check of networkChecks) {
      networkGrid.appendChild(
        proCreateNetworkCard(check)
      );
    }
  } else {
    networkGrid.appendChild(
      proCreateEmptyState(
        "No network checks",
        "No DNS or TCP probes were recorded."
      )
    );
  }

  networkSection.appendChild(networkGrid);

  const servicesSection = proCreateSection(
    "pro-services",
    "systemd state",
    "Service checks",
    diagnostics.services.overall_status
  );

  const servicesList = proElement(
    "div",
    "pro-disclosure-list"
  );

  if (serviceRecords.length) {
    for (const service of serviceRecords) {
      servicesList.appendChild(
        proCreateDisclosure(
          service.label || service.service_name,
          service.health_status,
          [
            service.active_state,
            service.sub_state
          ].filter(Boolean).join(" · "),
          service,
          [
            "label",
            "health_status",
            "failure_reason",
            "error_message"
          ]
        )
      );
    }
  } else {
    servicesList.appendChild(
      proCreateEmptyState(
        "No services configured",
        "This run did not contain service checks."
      )
    );
  }

  servicesSection.appendChild(servicesList);

  const processesSection = proCreateSection(
    "pro-processes",
    "Runtime state",
    "Process checks",
    diagnostics.processes.overall_status
  );

  const processesList = proElement(
    "div",
    "pro-disclosure-list"
  );

  if (processRecords.length) {
    for (const process of processRecords) {
      processesList.appendChild(
        proCreateDisclosure(
          process.label || process.process_name,
          process.health_status,
          `${process.instance_count} instance${
            process.instance_count === 1 ? "" : "s"
          } · ${Number(
            process.total_memory_mb || 0
          ).toFixed(1)} MB`,
          process,
          [
            "label",
            "health_status",
            "failure_reason",
            "error_message"
          ]
        )
      );
    }
  } else {
    processesList.appendChild(
      proCreateEmptyState(
        "No processes configured",
        "This run did not contain process checks."
      )
    );
  }

  processesSection.appendChild(processesList);

  const logsSection = proCreateSection(
    "pro-logs",
    "Evidence scan",
    "Log analysis",
    diagnostics.logs.overall_status
  );

  const logsList = proElement(
    "div",
    "pro-disclosure-list"
  );

  if (logRecords.length) {
    for (const log of logRecords) {
      logsList.appendChild(
        proCreateDisclosure(
          log.label || log.source_id,
          log.health_status,
          `${log.total_lines_scanned} lines · `
          + `${log.match_count} matches`,
          log,
          [
            "label",
            "health_status",
            "failure_reason",
            "error_message"
          ]
        )
      );
    }
  } else {
    logsList.appendChild(
      proCreateEmptyState(
        "No log sources configured",
        "This run did not contain log analysis."
      )
    );
  }

  logsSection.appendChild(logsList);

  const incidentsSection = proCreateSection(
    "pro-incidents",
    "Operational impact",
    "Incident snapshot",
    incidents.length
      ? incidents[0].severity
      : "HEALTHY"
  );

  const incidentList = proElement(
    "div",
    "pro-disclosure-list"
  );

  if (incidents.length) {
    for (const incident of incidents) {
      incidentList.appendChild(
        proCreateDisclosure(
          incident.incident_id,
          incident.severity,
          incident.description,
          incident,
          [
            "incident_id",
            "severity",
            "description"
          ],
          true
        )
      );
    }
  } else {
    incidentList.appendChild(
      proCreateEmptyState(
        "No incidents in this run",
        "The snapshot completed without operational incidents."
      )
    );
  }

  incidentsSection.appendChild(incidentList);

  root.append(
    hero,
    liveComparison,
    kpiGrid,
    componentGrid,
    navigation,
    overviewSection,
    systemSection,
    networkSection,
    servicesSection,
    processesSection,
    logsSection,
    incidentsSection
  );

  elements.drawerContent.appendChild(root);

  proUpdateLiveComparison(
    proUiState.previousLiveMetrics
  );
};


const proBaseRenderLiveMetrics =
  renderLiveMetrics;


renderLiveMetrics = function renderProfessionalLiveMetrics(
  metrics
) {
  const previous =
    proUiState.previousLiveMetrics;

  proBaseRenderLiveMetrics(metrics);

  const pulse = document.querySelector(
    "#live-pulse"
  );

  if (pulse) {
    pulse.dataset.status = metrics.status;
  }

  const comparisons = [
    [
      elements.liveCpuCard,
      metrics.cpu_percent,
      previous?.cpu_percent
    ],
    [
      elements.liveMemoryCard,
      metrics.memory_percent,
      previous?.memory_percent
    ],
    [
      elements.liveDiskCard,
      metrics.disk_percent,
      previous?.disk_percent
    ]
  ];

  for (
    const [card, currentValue, previousValue]
    of comparisons
  ) {
    if (
      card
      && previousValue !== undefined
      && Math.abs(
        Number(currentValue)
        - Number(previousValue)
      ) >= 0.1
    ) {
      card.classList.remove(
        "pro-value-change"
      );

      void card.offsetWidth;

      card.classList.add(
        "pro-value-change"
      );
    }
  }

  proUiState.previousLiveMetrics = {
    ...metrics
  };

  proUpdateLiveComparison(metrics);
};
/* Live chart precision tooltips */

const proTooltipState = {
  sampledAt: []
};


function ensureLiveChartTooltip() {
  let tooltip = document.querySelector(
    "#live-chart-tooltip"
  );

  if (!tooltip) {
    tooltip = proElement(
      "div",
      "live-chart-tooltip"
    );
    tooltip.id = "live-chart-tooltip";
    tooltip.hidden = true;
    tooltip.setAttribute("role", "tooltip");

    document.body.appendChild(tooltip);
  }

  return tooltip;
}


function showLiveChartTooltip(
  event,
  label,
  value,
  sampledAt
) {
  const tooltip = ensureLiveChartTooltip();

  tooltip.replaceChildren(
    proElement(
      "span",
      "live-chart-tooltip__label",
      label
    ),
    proElement(
      "strong",
      "live-chart-tooltip__value",
      value
    ),
    proElement(
      "small",
      "live-chart-tooltip__time",
      new Date(sampledAt).toLocaleTimeString()
    )
  );

  tooltip.hidden = false;

  const margin = 14;
  let left = event.clientX + margin;
  let top = event.clientY - 90;

  left = Math.min(
    left,
    window.innerWidth
      - tooltip.offsetWidth
      - margin
  );

  top = Math.max(margin, top);

  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}


function hideLiveChartTooltip() {
  const tooltip = document.querySelector(
    "#live-chart-tooltip"
  );

  if (tooltip) {
    tooltip.hidden = true;
  }
}


const proTooltipCharts = {
  "live-cpu-sparkline": {
    label: "CPU activity",
    format: value => `${Number(value).toFixed(1)}%`
  },
  "live-memory-sparkline": {
    label: "Memory pressure",
    format: value => `${Number(value).toFixed(1)}%`
  },
  "live-disk-sparkline": {
    label: "Disk occupancy",
    format: value => `${Number(value).toFixed(1)}%`
  },
  "live-network-sparkline": {
    label: "Aggregate network throughput",
    format: value => formatTransferRate(value)
  }
};


const proTooltipBaseSparkline =
  renderLiveSparkline;


renderLiveSparkline =
function renderSparklineWithTooltip(
  element,
  values
) {
  proTooltipBaseSparkline(element, values);

  const configuration =
    proTooltipCharts[element.id];

  if (!configuration || values.length < 2) {
    return;
  }

  element.addEventListener(
    "mousemove",
    event => {
      const bounds =
        element.getBoundingClientRect();

      const relativePosition = Math.min(
        1,
        Math.max(
          0,
          (event.clientX - bounds.left)
          / bounds.width
        )
      );

      const index = Math.round(
        relativePosition * (values.length - 1)
      );

      const sampledAt =
        proTooltipState.sampledAt[index]
        || new Date().toISOString();

      showLiveChartTooltip(
        event,
        configuration.label,
        configuration.format(values[index]),
        sampledAt
      );
    }
  );

  element.addEventListener(
    "mouseleave",
    hideLiveChartTooltip
  );
};


const proTooltipBaseLiveMetrics =
  renderLiveMetrics;


renderLiveMetrics =
function renderLiveMetricsWithTooltips(metrics) {
  proTooltipState.sampledAt.push(
    metrics.sampled_at
  );

  if (proTooltipState.sampledAt.length > 32) {
    proTooltipState.sampledAt.shift();
  }

  proTooltipBaseLiveMetrics(metrics);
};


window.addEventListener(
  "scroll",
  hideLiveChartTooltip,
  {
    passive: true
  }
);
