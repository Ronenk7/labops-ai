"""Run the LabOps AI log analyzer."""
from labops_ai.logs import (
    FileLogScanner,
    LogAnalyzer,
    LogAnalyzerConfigLoader,
    print_log_report,
)


def main() -> None:
    """Analyze configured logs and print their report."""
    config = LogAnalyzerConfigLoader().load()
    scanner = FileLogScanner(config=config)
    analyzer = LogAnalyzer(
        config=config,
        scanner=scanner,
    )

    summary = analyzer.run()

    print_log_report(
        summary=summary,
        report=config.report,
    )


if __name__ == "__main__":
    main()