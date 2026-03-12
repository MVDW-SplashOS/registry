import logging
import sys

logging.basicConfig(
    level=logging.WARNING,
    format="[LibRegistry] %(levelname)s: %(message)s",
    stream=sys.stderr,
)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(f"libregistry.{name}")


def print_error(message):
    logger = get_logger("error")
    logger.error(message)
