import click
import os
from shutil import which

from . import core
from .constants import IS_LINUX, IS_MAC_OS, SYSTEM
from .util import is_supported_mac_ver, logger


@click.group()
def cli():
    if not which("brew"):
        raise click.ClickException("`brew` is not installed, please install it")

    if not IS_LINUX and not IS_MAC_OS:
        raise click.ClickException(f"Your system {SYSTEM} is not supported")

    if IS_MAC_OS and not is_supported_mac_ver():
        raise click.ClickException("Your macOS version is not supported")

    os.environ["HOMEBREW_NO_AUTO_UPDATE"] = "1"


@cli.command()
@click.argument("formula_name")
@click.argument("version", required=False)
@click.option(
    "--slow/--no-slow",
    "slow",
    default=False,
    type=bool,
    help="Enable this to allow searching the HUGE homebrew repository. This takes ages",
)
def switch(formula_name, slow, version=None):
    core.switch(formula_name, version, slow)
    logger.info(
        f"Successfully switched to {formula_name} {version}",
    )
