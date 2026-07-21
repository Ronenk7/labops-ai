"use strict";

(() => {
  const REFRESH_INTERVAL_SECONDS = 15;
  const REQUEST_TIMEOUT_MS = 5000;

  const availabilityRisk = {
    OFFLINE: 3,
    STALE: 2,
    ONLINE: 1,
    UNKNOWN: 0
  };

  const state = {
    hosts: [],
    loadedAt: Date.now(),
    selectedHostId: null,
    refreshTimer: null,
    secondTimer: null,
    nextRefreshAt: null,
    requestSequence: 0
  };

  const elements = {
    page: document.body,
    apiState: document.querySelector(
      "#fleet-api-state"
    ),
    apiLabel: document.querySelector(
      "#fleet-api-label"
    ),
    refresh: document.querySelector("#fleet-refresh"),
    countdown: document.querySelector(
      "#fleet-countdown"
    ),
    updated: document.querySelector("#fleet-updated"),
    total: document.querySelector("#fleet-total"),
    online: document.querySelector("#fleet-online"),
    stale: document.querySelector("#fleet-stale"),
    offline: document.querySelector("#fleet-offline"),
    resultCount: document.querySelector(
      "#fleet-result-count"
    ),
    search: document.querySelector("#fleet-search"),
    statusFilter: document.querySelector(
      "#fleet-status-filter"
    ),
    sort: document.querySelector("#fleet-sort"),
    grid: document.querySelector("#fleet-host-grid"),
    message: document.querySelector("#fleet-message"),
    drawer: document.querySelector("#host-drawer"),
    drawerBackdrop: document.querySelector(
      "#host-drawer-backdrop"
    ),
    drawerClose: document.querySelector(
      "#host-drawer-close"
    ),
    drawerTitle: document.querySelector(
      "#host-drawer-title"
    ),
    drawerContent: document.querySelector(
      "#host-drawer-content"
    ),
    toast: document.querySelector("#fleet-toast")
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
    const age = Number(value);

    if (!Number.isFinite(age) || age < 0) {
      return 0;
    }

    return age;
  }

  function currentAge(host) {
    const elapsed = Math.max(
      0,
      (Date.now() - state.loadedAt) / 1000
    );

    return (
      safeAge(host.heartbeat_age_seconds)
      + elapsed
    );
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

    const minutes = Math.floor(
      totalSeconds / 60
    );

    if (minutes < 60) {
      return `${minutes}m ago`;
    }

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    if (hours < 24) {
      return remainingMinutes
        ? `${hours}h ${remainingMinutes}m ago`
        : `${hours}h ago`;
    }

    const days = Math.floor(hours / 24);
    const remainingHours = hours % 24;

    return remainingHours
      ? `${days}d ${remainingHours}h ago`
      : `${days}d ago`;
  }

  function formatDate(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "Unknown";
    }

    return date.toLocaleString();
  }

  function setLoading(loading) {
    elements.page.setAttribute(
      "aria-busy",
      String(loading)
    );
    elements.refresh.disabled = loading;
  }

  function setApiState(stateName, label) {
    elements.apiState.classList.remove(
      "fleet-api-state--online",
      "fleet-api-state--error"
    );

    if (stateName === "online") {
      elements.apiState.classList.add(
        "fleet-api-state--online"
      );
    }

    if (stateName === "error") {
      elements.apiState.classList.add(
        "fleet-api-state--error"
      );
    }

    elements.apiLabel.textContent = label;
  }

  function showToast(message, error = false) {
    elements.toast.textContent = message;
    elements.toast.classList.toggle(
      "fleet-toast--error",
      error
    );
    elements.toast.classList.add(
      "fleet-toast--visible"
    );

    window.setTimeout(
      () => {
        elements.toast.classList.remove(
          "fleet-toast--visible"
        );
      },
      2600
    );
  }

  function showMessage(message, error = false) {
    elements.message.hidden = false;
    elements.message.textContent = message;
    elements.message.classList.toggle(
      "fleet-message--error",
      error
    );
  }

  function hideMessage() {
    elements.message.hidden = true;
    elements.message.classList.remove(
      "fleet-message--error"
    );
  }

  function countStatus(status) {
    return state.hosts.filter(
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
      countStatus("ONLINE")
    );
    elements.stale.textContent = String(
      countStatus("STALE")
    );
    elements.offline.textContent = String(
      countStatus("OFFLINE")
    );
  }

  function matchesSearch(host, searchTerm) {
    if (!searchTerm) {
      return true;
    }

    const searchableValues = [
      host.host_id,
      host.host_name,
      host.address,
      host.operating_system,
      host.architecture,
      host.agent_version
    ];

    return searchableValues.some(
      value => (
        String(value || "")
          .toLowerCase()
          .includes(searchTerm)
      )
    );
  }

  function visibleHosts() {
    const searchTerm = (
      elements.search.value
        .trim()
        .toLowerCase()
    );
    const status = elements.statusFilter.value;
    const sortMode = elements.sort.value;

    const hosts = state.hosts.filter(
      host => (
        matchesSearch(host, searchTerm)
        && (
          !status
          || normalizeAvailability(
            host.availability
          ) === status
        )
      )
    );

    hosts.sort(
      (left, right) => {
        if (sortMode === "name") {
          return String(left.host_name).localeCompare(
            String(right.host_name)
          );
        }

        if (sortMode === "newest") {
          return (
            new Date(right.last_seen_at).getTime()
            - new Date(left.last_seen_at).getTime()
          );
        }

        if (sortMode === "oldest") {
          return (
            new Date(left.last_seen_at).getTime()
            - new Date(right.last_seen_at).getTime()
          );
        }

        const leftStatus = normalizeAvailability(
          left.availability
        );
        const rightStatus = normalizeAvailability(
          right.availability
        );

        const riskDifference = (
          availabilityRisk[rightStatus]
          - availabilityRisk[leftStatus]
        );

        if (riskDifference !== 0) {
          return riskDifference;
        }

        return String(left.host_name).localeCompare(
          String(right.host_name)
        );
      }
    );

    return hosts;
  }

  function createAvailability(host) {
    const availability = normalizeAvailability(
      host.availability
    );

    return createElement(
      "span",
      (
        "host-availability "
        + `host-availability--${
          availability.toLowerCase()
        }`
      ),
      availability
    );
  }

  function createMetric(label, value) {
    const metric = createElement(
      "div",
      "host-card__metric"
    );

    metric.append(
      createElement("span", "", label),
      createElement(
        "strong",
        "",
        value || "—"
      )
    );

    return metric;
  }

  function createHostCard(host) {
    const availability = normalizeAvailability(
      host.availability
    );
    const card = createElement(
      "button",
      (
        "host-card "
        + `host-card--${availability.toLowerCase()}`
      )
    );

    card.type = "button";
    card.dataset.hostId = host.host_id;
    card.setAttribute(
      "aria-label",
      `Open details for ${host.host_name}`
    );

    const header = createElement(
      "div",
      "host-card__header"
    );
    const identity = createElement(
      "div",
      "host-card__identity"
    );

    identity.append(
      createElement(
        "strong",
        "",
        host.host_name
      ),
      createElement(
        "code",
        "",
        host.host_id
      )
    );

    header.append(
      identity,
      createAvailability(host)
    );

    const platform = createElement(
      "div",
      "host-card__platform",
      host.operating_system
    );

    const metrics = createElement(
      "div",
      "host-card__metrics"
    );

    metrics.append(
      createMetric("Address", host.address),
      createMetric(
        "Architecture",
        host.architecture
      ),
      createMetric(
        "Agent version",
        host.agent_version
      ),
      createMetric(
        "Registered",
        formatDate(host.registered_at)
      )
    );

    const footer = createElement(
      "div",
      "host-card__footer"
    );
    const age = createElement(
      "span",
      "",
      "Last heartbeat "
    );
    const ageValue = createElement(
      "strong",
      "",
      formatAge(currentAge(host))
    );

    ageValue.dataset.hostAge = host.host_id;
    age.append(ageValue);

    footer.append(
      age,
      createElement(
        "span",
        "host-card__open",
        "Inspect →"
      )
    );

    card.append(
      header,
      platform,
      metrics,
      footer
    );

    card.addEventListener(
      "click",
      () => openHostDrawer(host.host_id)
    );

    return card;
  }

  function renderHosts() {
    renderSummary();

    const hosts = visibleHosts();
    elements.grid.replaceChildren();

    elements.resultCount.textContent = (
      `${hosts.length} of ${state.hosts.length} `
      + "registered Hosts"
    );

    if (state.hosts.length === 0) {
      showMessage(
        "No Agents have registered with the Host Registry yet."
      );
      return;
    }

    if (hosts.length === 0) {
      showMessage(
        "No Hosts match the current search and filters."
      );
      return;
    }

    hideMessage();

    const fragment = document.createDocumentFragment();

    hosts.forEach(
      host => {
        fragment.append(
          createHostCard(host)
        );
      }
    );

    elements.grid.append(fragment);
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

  function renderHostDrawer(host) {
    elements.drawerTitle.textContent =
      host.host_name;
    elements.drawerContent.replaceChildren();

    const hero = createElement(
      "section",
      "host-drawer__hero"
    );

    hero.append(
      createAvailability(host),
      createElement(
        "h3",
        "",
        host.host_name
      ),
      createElement(
        "code",
        "",
        host.host_id
      )
    );

    const details = createElement(
      "div",
      "host-detail-list"
    );

    details.append(
      createDetailItem(
        "Current availability",
        normalizeAvailability(
          host.availability
        )
      ),
      createDetailItem(
        "Heartbeat age",
        formatAge(currentAge(host))
      ),
      createDetailItem(
        "Last heartbeat",
        formatDate(host.last_seen_at)
      ),
      createDetailItem(
        "Status evaluated",
        formatDate(host.evaluated_at)
      ),
      createDetailItem(
        "First registered",
        formatDate(host.registered_at)
      ),
      createDetailItem(
        "Reported address",
        host.address
      ),
      createDetailItem(
        "Operating system",
        host.operating_system
      ),
      createDetailItem(
        "Architecture",
        host.architecture
      ),
      createDetailItem(
        "Agent version",
        host.agent_version
      )
    );

    elements.drawerContent.append(
      hero,
      details
    );
  }

  function openHostDrawer(hostId) {
    const host = state.hosts.find(
      item => item.host_id === hostId
    );

    if (!host) {
      return;
    }

    state.selectedHostId = hostId;
    renderHostDrawer(host);

    elements.drawer.classList.add(
      "host-drawer--open"
    );
    elements.drawer.setAttribute(
      "aria-hidden",
      "false"
    );
  }

  function closeHostDrawer() {
    state.selectedHostId = null;

    elements.drawer.classList.remove(
      "host-drawer--open"
    );
    elements.drawer.setAttribute(
      "aria-hidden",
      "true"
    );
  }

  function updateAges() {
    state.hosts.forEach(
      host => {
        const ageElement = document.querySelector(
          `[data-host-age="${CSS.escape(
            host.host_id
          )}"]`
        );

        if (ageElement) {
          ageElement.textContent = formatAge(
            currentAge(host)
          );
        }
      }
    );

    if (state.selectedHostId) {
      const selectedHost = state.hosts.find(
        host => (
          host.host_id
          === state.selectedHostId
        )
      );

      if (selectedHost) {
        renderHostDrawer(selectedHost);
      }
    }

    if (state.nextRefreshAt) {
      const seconds = Math.max(
        0,
        Math.ceil(
          (
            state.nextRefreshAt
            - Date.now()
          ) / 1000
        )
      );

      elements.countdown.textContent =
        `${seconds}s`;
    }
  }

  async function loadHosts(showSuccess = false) {
    const requestId = state.requestSequence + 1;
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
          `Host Registry returned ${response.status}.`
        );
      }

      const payload = await response.json();

      if (!Array.isArray(payload)) {
        throw new Error(
          "Host Registry returned invalid data."
        );
      }

      if (requestId !== state.requestSequence) {
        return;
      }

      state.hosts = payload;
      state.loadedAt = Date.now();

      setApiState(
        "online",
        "Host Registry online"
      );

      elements.updated.textContent = (
        "Updated "
        + new Date().toLocaleTimeString()
      );

      renderHosts();

      if (showSuccess) {
        showToast("Host Fleet refreshed.");
      }
    } catch (error) {
      if (requestId !== state.requestSequence) {
        return;
      }

      const message = (
        error.name === "AbortError"
        ? "Host Registry request timed out."
        : error.message
      );

      setApiState(
        "error",
        "Registry unavailable"
      );
      showMessage(
        `Unable to load Host Fleet: ${message}`,
        true
      );
      showToast(message, true);
    } finally {
      window.clearTimeout(timeout);

      if (requestId === state.requestSequence) {
        setLoading(false);
      }
    }
  }

  function scheduleRefresh() {
    window.clearTimeout(state.refreshTimer);

    state.nextRefreshAt = (
      Date.now()
      + REFRESH_INTERVAL_SECONDS * 1000
    );

    state.refreshTimer = window.setTimeout(
      async () => {
        await loadHosts(false);
        scheduleRefresh();
      },
      REFRESH_INTERVAL_SECONDS * 1000
    );
  }

  async function refreshFleet(showSuccess = false) {
    await loadHosts(showSuccess);
    scheduleRefresh();
  }

  elements.search.addEventListener(
    "input",
    renderHosts
  );
  elements.statusFilter.addEventListener(
    "change",
    renderHosts
  );
  elements.sort.addEventListener(
    "change",
    renderHosts
  );

  elements.refresh.addEventListener(
    "click",
    () => refreshFleet(true)
  );

  elements.drawerClose.addEventListener(
    "click",
    closeHostDrawer
  );
  elements.drawerBackdrop.addEventListener(
    "click",
    closeHostDrawer
  );

  document.addEventListener(
    "keydown",
    event => {
      if (event.key === "Escape") {
        closeHostDrawer();
      }
    }
  );

  document.addEventListener(
    "visibilitychange",
    () => {
      if (!document.hidden) {
        refreshFleet(false);
      }
    }
  );

  window.addEventListener(
    "beforeunload",
    () => {
      window.clearTimeout(state.refreshTimer);
      window.clearInterval(state.secondTimer);
    }
  );

  state.secondTimer = window.setInterval(
    updateAges,
    1000
  );

  refreshFleet(false);
})();
