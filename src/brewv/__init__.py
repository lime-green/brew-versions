import logging
import os

import colorlog

from .cli import cli


def main():
    log_level = os.environ.get("BREWV_LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(fmt="%(log_color)s[%(name)s]: %(message)s")
    )
    logging.basicConfig(handlers=[handler], level=getattr(logging, log_level))
    cli()
