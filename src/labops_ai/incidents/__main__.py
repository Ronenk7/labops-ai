"""Display the current persisted incident management state."""
from labops_ai.incidents.incident_loader import (
    IncidentManagementConfigLoader,
)
from labops_ai.incidents.incident_report import (
    print_incident_report,
)
from labops_ai.incidents.incident_store import JsonIncidentStore


def main() -> None:
    """Load and display the current incident state."""
    config = IncidentManagementConfigLoader().load()
    store = JsonIncidentStore(config=config.storage)
    state = store.load()

    print_incident_report(
        actions=(),
        state=state,
        report=config.report,
    )


if __name__ == "__main__":
    main()