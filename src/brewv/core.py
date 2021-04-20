import contextlib
import json
import os
import subprocess
import sys

from .bottle import (
    BottleNotFound,
    build_bottle_os_identifier,
    download_bottle,
    get_bottle_cache_location,
)
from .util import (
    check_output,
    download_file,
    logger,
    symlink_force,
)


class SourceVersionNotFound(Exception):
    pass


def _get_formula_info(formula_name):
    return json.loads(check_output(["brew", "info", "--json=v1", formula_name]))[0]


@contextlib.contextmanager
def _install_formula_from_tap(
    formula_name, version, bottle_cache_file, allow_slow, source_revision
):
    formula_info = _get_formula_info(formula_name)
    is_homebrew_tap = formula_info["tap"] == "homebrew/core"
    tap_user, tap_repo = formula_info["tap"].split("/")
    brew_repo = os.path.join(
        check_output(["brew", "--repository"]),
        f"Library/Taps/{tap_user}/homebrew-{tap_repo}",
    )

    if not source_revision:
        if not allow_slow and is_homebrew_tap:
            logger.error(
                "Exiting since the slow option is not enabled."
                " Enable this option to do a slow git search on the homebrew repository"
            )
            sys.exit(1)

        os.chdir(brew_repo)
        logger.warning(
            "Searching for version in git directory, this may take a while..."
        )
        source_revision = check_output(
            f"git grep -F '{version}' `git rev-list master -- Formula/{formula_name}.rb`"  # noqa
            f" -- Formula/{formula_name}.rb | head -n1 | cut -f1 -d':'",
            shell=True,
        )

    if not source_revision:
        logger.error(f"Could not find a source version for {formula_name} {version}")
        sys.exit(1)

    logger.info(f"Found version in commit: {source_revision}")
    subprocess.run(
        ["git", "checkout", source_revision],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )

    try:
        formula_info = _get_formula_info(formula_name)
        bottle_info = (
            formula_info.get("bottle", {})
            .get("stable", {})
            .get("files", {})
            .get(build_bottle_os_identifier(), {})
        )
        if bottle_info:
            logger.info("Found bottle in tap config")
            bottle_url = bottle_info["url"]
            bottle_sha256 = bottle_info["sha256"]
            download_file(
                bottle_url, bottle_cache_file, sha256_verification=bottle_sha256
            )

            yield bottle_cache_file
        else:
            logger.info("Did not find bottle in tap config, installing from source")
            yield formula_name
    finally:
        subprocess.run(
            ["git", "checkout", "master"],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )


def switch(formula_name, version, allow_slow=False):
    if "/" in formula_name:
        tap, formula_name = formula_name.rsplit("/", 1)
        logger.info(f"Tapping {tap}")
        subprocess.check_output(["brew", "tap", tap])

    logger.info(f"Switching {formula_name} to version {version}")
    bottle_cache_file = get_bottle_cache_location(formula_name, version)

    with contextlib.ExitStack() as stack:
        if os.path.isfile(bottle_cache_file):
            logger.info(f"Found bottle in cache: {bottle_cache_file}")
            formula_installation = bottle_cache_file
        else:
            logger.info("Not in cache: finding bottle to download")

            try:
                download_bottle(formula_name, version, bottle_cache_file)
                formula_installation = bottle_cache_file
            except BottleNotFound as e:
                logger.warning(f"No bottle was found for {formula_name} {version}")
                formula_installation = stack.enter_context(
                    _install_formula_from_tap(
                        formula_name,
                        version,
                        bottle_cache_file,
                        allow_slow,
                        e.source_revision,
                    )
                )

        try:
            check_output(["brew", "unlink", formula_name], stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            pass

        try:
            subprocess.run(
                ["brew", "install", formula_installation],
                check=True,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            sys.stderr.write(e.stderr.decode())
            sys.exit(e.returncode)

        brew_prefix = check_output(["brew", "--prefix"])
        formula_cellar_path = os.path.join(
            brew_prefix, "Cellar", formula_name, version, "bin", formula_name
        )
        brew_bin_path = os.path.join(brew_prefix, "bin")
        formula_bin_to_cellar_relative_path = os.path.relpath(
            formula_cellar_path, brew_bin_path
        )

        logger.debug("Linking homebrew binary")
        symlink_force(
            formula_bin_to_cellar_relative_path,
            os.path.join(brew_bin_path, formula_name),
        )

        logger.info(f"Pinning {formula_name}")
        check_output(["brew", "pin", formula_name], stderr=subprocess.DEVNULL)
