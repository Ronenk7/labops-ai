"""Run the LabOps AI network connectivity monitor."""
from labops_ai.network import (ConnectivityConfigLoader, DnsConnectivityChecker, NetworkConnectivityMonitor, TcpConnectivityChecker, print_network_report)


def main() -> None:
    """Run configured DNS and TCP checks and print their report."""
    config = ConnectivityConfigLoader().load()

    dns_checker = DnsConnectivityChecker(config=config.dns_test)
    tcp_checker = TcpConnectivityChecker(tcp_config=config.tcp_test, connection_settings=config.connection)
    monitor = NetworkConnectivityMonitor(config=config, dns_checker=dns_checker, tcp_checker=tcp_checker)
    summary = monitor.run()
    print_network_report(summary=summary, report=config.report)


if __name__ == "__main__":
    main()