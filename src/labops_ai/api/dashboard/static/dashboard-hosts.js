"use strict";

(() => {
  const REQUEST_TIMEOUT_MS = 5000;

  const state = {
    hosts: [],
    loadedAt: Date.now(),
    refreshTimer: null,
    ageTimer: null,
    requestSequence: 0
  };

  const elements = {
    section: document.querySelector("#monitored-hosts"),
    total: document.querySelector("#host-fleet-total"),
    online: document.querySelector("#host-fleet-online"),
    stale: document.querySelector("#host-fleet-stale"),
    offline: document.querySelector("#host-fleet-offline"),
    filter: document.querySelector("#host-fleet-filter"),
    refresh: document.querySelector("#host-fleet-refresh"),
    tableBody: document.querySelector(
      "#host-fleet-table-body"
    ),
    message: document.querySelector("#host-fleet-message"),
    updated: document.querySelector("#host-fleet-updated"),
    resultCount: document.querySelector(
      "#host-fleet-result-count"
    ),
    globalRefresh: document.querySelector("#refresh-button"),
    refreshInterval: document.querySelector(
      "#refresh-interval"
    )
  };

  if (!elements.section) {
    return;
  }

  const availabilityRank = {
    OFFLINE: 3,
    STALE: 2,
    ONLINE: 1,
    UNKNOWN: 0
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

  function safeAge(value) {
    const numericValue = Number(value);

    if (
      !Number.isFinite(numericValue)
      || numericValue < 0
    ) {
      return 0;
    }

    return numericValue;
  }

  function formatAge(seconds) {
    const totalSeconds = Math.max(
      0,
      Math.floor(seconds)
    );

    if (totalSeconds < 5) {
      return "just now";
    }

    if (totalSeconds < 60) {
      return `${totalSeconds}s ago`;
    }

    const totalMinutes = Math.floor(
      totalSeconds / 60
    );

    if (totalMinutes < 60) {
      return `${totalMinutes}m ago`;
    }

    const totalHours = Math.floor(
      totalMinutes / 60
    );
    const remainingMinutes = (
      totalMinutes % 60
    );

    if (totalHours < 24) {
      return remainingMinutes > 0
        ? `${totalHours}h ${remainingMinutes}m ago`
        : `${totalHours}h ago`;
    }

    const totalDays = Math.floor(
      totalHours / 24
    );
    const remainingHours = totalHours % 24;

    return remainingHours > 0
      ? `${totalDays}d ${remainingHours}h ago`
      : `${totalDays}d ago`;
  }

  function formatTimestamp(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "Unknown timestamp";
    }

    return date.toLocaleString();
  }

  function countAvailability(hosts, status) {
    return hosts.filter(
      host => (
        normalizeAvailability(
          host.availability
        ) === status
      )
    ).length;
  }

  function renderSummary() {
    elements.total.textContent = String(
      state.hosts.length
    );
    elements.online.textContent = String(
      countAvailability(
        state.hosts,
        "ONLINE"
      )
    );
    elements.stale.textContent = String(
      countAvailability(
        state.hosts,
        "STALE"
      )
    );
    elements.offline.textContent = String(
      countAvailability(
        state.hosts,
        "OFFLINE"
      )
    );
  }

  function sortedVisibleHosts() {
    const selectedStatus = (
      elements.filter.value
    );

    return state.hosts
      .filter(
        host => (
          !selectedStatus
          || normalizeAvailability(
            host.availability
          ) === selectedStatus
        )
      )
      .sort(
        (left, right) => {
          const leftStatus = normalizeAvailability(
            left.availability
          );
          const rightStatus = normalizeAvailability(
            right.availability
          );

          const statusDifference = (
            availabilityRank[rightStatus]
            - availabilityRank[leftStatus]
          );

          if (statusDifference !== 0) {
            return statusDifference;
          }

          return (
            new Date(
              right.last_seen_at
            ).getTime()
            - new Date(
              left.last_seen_at
            ).getTime()
          );
        }
      );
  }

  function createIdentityCell(host) {
    const cell = document.createElement("td");
    const identity = createElement(
      "div",
      "host-identity"
    );

    identity.append(
      createElement(
        "strong",
        "",
        host.host_name || "Unnamed host"
      ),
      createElement(
        "code",
        "",
        host.host_id || "Unknown ID"
      )
    );

    cell.append(identity);
    return cell;
  }

  function createStatusCell(host) {
    const cell = document.createElement("td");
    const availability = normalizeAvailability(
      host.availability
    );

    cell.append(
      createElement(
        "span",
        (
          "host-status "
          + `host-status--${availability.toLowerCase()}`
        ),
        availability
      )
    );

    return cell;
  }

  function createDetailCell(
    primary,
    secondary = ""
  ) {
    const cell = document.createElement("td");
    const detail = createElement(
      "div",
      "host-detail"
    );

    detail.append(
      createElement(
        "strong",
        "",
        primary || "—"
      )
    );

    if (secondary) {
      detail.append(
        createElement(
          "small",
          "",
          secondary
        )
      );
    }

    cell.append(detail);
    return cell;
  }

  function createAgeCell(host) {
    const cell = document.createElement("td");
    const wrapper = createElement(
      "div",
      "host-age"
    );
    const relative = createElement(
      "strong",
      "",
      formatAge(
        safeAge(
          host.heartbeat_age_seconds
        )
      )
    );
    const exact = createElement(
      "small",
      "",
      formatTimestamp(host.last_seen_at)
    );

    relative.dataset.hostAge = "true";
    relative.dataset.baseAge = String(
      safeAge(
        host.heartbeat_age_seconds
      )
    );
    relative.dataset.capturedAt = String(
      state.loadedAt
    );

    wrapper.append(relative, exact);
    cell.append(wrapper);

    return cell;
  }

  function createHostRow(host) {
    const row = document.createElement("tr");
    const platform = [
      host.operating_system,
      host.architecture
    ].filter(Boolean);

    row.dataset.hostId = String(
      host.host_id || ""
    );
    row.append(
      createIdentityCell(host),
      createStatusCell(host),
      createDetailCell(
        host.address,
        "Reported Agent address"
      ),
      createDetailCell(
        platform[0],
        platform[1]
      ),
      createDetailCell(
        host.agent_version,
        "Agent version"
      ),
      createAgeCell(host)
    );

    return row;
  }

  function showMessage(
    message,
    *,
    error = false
  ) {
    elements.message.hidden = false;
    elements.message.textContent = message;
    elements.message.classList.toggle(
      "host-fleet__message--error",
      error
    );
  }

  function hideMessage() {
    elements.message.hidden = true;
    elements.message.textContent = "";
    elements.message.classList.remove(
      "host-fleet__message--error"
    );
  }

  function renderHosts() {
    renderSummary();

    const hosts = sortedVisibleHosts();
    elements.tableBody.replaceChildren();

    elements.resultCount.textContent = (
      `${hosts.length} of ${state.hosts.length} hosts shown`
    );

    if (state.hosts.length === 0) {
      showMessage(
        "No monitored hosts have registered yet."
      );
      return;
    }

    if (hosts.length === 0) {
      showMessage(
        "No hosts match the selected availability."
      );
      return;
    }

    hideMessage();

    const fragment = document.createDocumentFragment();

    hosts.forEach(
      host => {
        fragment.append(
          createHostRow(host)
        );
      }
    );

    elements.tableBody.append(fragment);
  }

  function updateVisibleAges() {
    const now = Date.now();

    document
      .querySelectorAll("[data-host-age]")
      .forEach(
        element => {
          const baseAge = safeAge(
            element.dataset.baseAge
          );
          const capturedAt = Number(
            element.dataset.capturedAt
          );
          const elapsedSeconds = (
            Number.isFinite(capturedAt)
            ? Math.max(
              0,
              (now - capturedAt) / 1000
            )
            : 0
          );

          element.textContent = formatAge(
            baseAge + elapsedSeconds
          );
        }
      );
  }

  function setLoading(loading) {
    elements.section.setAttribute(
      "aria-busy",
      String(loading)
    );
    elements.refresh.disabled = loading;
  }

  async function loadHosts() {
    const requestId = (
      state.requestSequence + 1
    );
    state.requestSequence = requestId;

    const controller = new AbortController();
    const timeout = window.setTimeout(
      () => controller.abort(),
      REQUEST_TIMEOUT_MS
    );

    setLoading(true);

    try {
      const response = await fetch(
        "/api/v1/hosts",
        {
          cache: "no-store",
          headers: {
            Accept: "application/json"
          },
          signal: controller.signal
        }
      );

      if (!response.ok) {
        throw new Error(
          "Host registry request failed "
          + `(${response.status}).`
        );
      }

      const payload = await response.json();

      if (!Array.isArray(payload)) {
        throw new Error(
          "Host registry returned invalid data."
        );
      }

      if (
        requestId
        !== state.requestSequence
      ) {
        return;
      }

      state.hosts = payload;
      state.loadedAt = Date.now();

      renderHosts();
      updateVisibleAges();

      elements.updated.textContent = (
        "Hosts updated "
        + new Date().toLocaleTimeString()
      );
    } catch (error) {
      if (
        requestId
        !== state.requestSequence
      ) {
        return;
      }

      const message = (
        error.name === "AbortError"
        ? "Host registry request timed out."
        : error.message
      );

      showMessage(
        `Unable to load monitored hosts: ${message}`,
        {error: true}
      );

      elements.updated.textContent = (
        "Host update failed"
      );
    } finally {
      window.clearTimeout(timeout);

      if (
        requestId
        === state.requestSequence
      ) {
        setLoading(false);
      }
    }
  }

  function scheduleRefresh() {
    window.clearTimeout(
      state.refreshTimer
    );

    const configuredSeconds = Number(
      elements.refreshInterval
        ? elements.refreshInterval.value
        : 30
    );

    if (
      !Number.isFinite(configuredSeconds)
      || configuredSeconds <= 0
    ) {
      state.refreshTimer = null;
      return;
    }

    state.refreshTimer = window.setTimeout(
      async () => {
        await loadHosts();
        scheduleRefresh();
      },
      configuredSeconds * 1000
    );
  }

  elements.filter.addEventListener(
    "change",
    renderHosts
  );

  elements.refresh.addEventListener(
    "click",
    async () => {
      await loadHosts();
      scheduleRefresh();
    }
  );

  if (elements.globalRefresh) {
    elements.globalRefresh.addEventListener(
      "click",
      loadHosts
    );
  }

  if (elements.refreshInterval) {
    elements.refreshInterval.addEventListener(
      "change",
      scheduleRefresh
    );
  }

  document.addEventListener(
    "visibilitychange",
    () => {
      if (!document.hidden) {
        loadHosts();
        scheduleRefresh();
      }
    }
  );

  window.addEventListener(
    "beforeunload",
    () => {
      window.clearTimeout(
        state.refreshTimer
      );
      window.clearInterval(
        state.ageTimer
      );
    }
  );

  state.ageTimer = window.setInterval(
    updateVisibleAges,
    1000
  );

  loadHosts();
  scheduleRefresh();
})();
