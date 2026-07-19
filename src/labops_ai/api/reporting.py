"""Build downloadable run history reports."""
from __future__ import annotations

import csv
from io import StringIO
from collections.abc import Sequence

from labops_ai.api.schemas import RunHistoryResponse


class RunHistoryCsvReportBuilder:
    """Create an Excel-compatible run history CSV report."""

    @staticmethod
    def build(
        entries: Sequence[RunHistoryResponse],
    ) -> str:
        """Build a complete CSV report."""
        if any(
            not isinstance(entry, RunHistoryResponse)
            for entry in entries
        ):
            raise TypeError(
                "Every report entry must be a "
                "RunHistoryResponse."
            )

        output = StringIO(newline="")
        writer = csv.writer(
            output,
            lineterminator="\n",
        )

        writer.writerow(
            [
                "Run ID",
                "Generated At",
                "Host",
                "Overall",
                "System",
                "Network",
                "Services",
                "Processes",
                "Logs",
                "Active Incidents",
                "Resolved Incidents",
                "Bundle ID",
                "Archive Path",
            ]
        )

        for entry in entries:
            writer.writerow(
                [
                    entry.run_id,
                    entry.generated_at.isoformat(),
                    entry.host_name,
                    entry.overall_status.value,
                    entry.system_status.value,
                    entry.network_status.value,
                    entry.service_status.value,
                    entry.process_status.value,
                    entry.log_status.value,
                    entry.active_incident_count,
                    entry.resolved_incident_count,
                    entry.bundle_id,
                    entry.archive_path,
                ]
            )

        return "\ufeff" + output.getvalue()
