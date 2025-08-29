"""Basic logging helpers used across the project."""
import logging

logging.basicConfig(level=logging.ERROR)


def log_error(error_message: str) -> None:
    """Log ``error_message`` using :mod:`logging`."""
    logging.error(error_message)


def send_alert(error_message: str) -> None:
    """Placeholder alert mechanism.

    In the production system this would post the message to a Slack channel.
    For testing we simply print the alert so that it is visible in logs.
    """
    print(f"ALERT: {error_message}")
