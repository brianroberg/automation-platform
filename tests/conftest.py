"""Pytest configuration for the test suite."""
import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register custom command line options."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests (disabled by default).",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as requiring external services")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Deselect integration tests unless --integration flag provided."""
    if config.getoption("--integration"):
        return

    integration_items = [item for item in items if "integration" in item.keywords]
    if not integration_items:
        return

    for item in integration_items:
        items.remove(item)

    config.hook.pytest_deselected(items=integration_items)
