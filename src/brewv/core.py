import contextlib
import json
import os
import platform
import requests
import subprocess
import sys

from requests.exceptions import HTTPError

from .constants import BOTTLE_FILE_SUFFIX, IS_MAC_OS, MAC_VER_TO_CODENAME, SYSTEM
from .util import (
    check_output,
    download_file,
    is_supported_mac_ver,
    logger,
    mac_ver,
    symlink_force,
)


class BottleNotFound(Exception):
    pass


class SourceVersionNotFound(Exception):
    pass


def _get_formula_info(formula_name):
    return json.loads(check_output(["brew", "info", "--json=v1", formula_name]))[0]


def _build_bottle_os_identifier():
    if IS_MAC_OS:
        assert is_supported_mac_ver()
        codename = MAC_VER_TO_CODENAME[mac_ver()].replace(" ", "_").lower()

        if platform.machine() == "arm64":
            return f"arm64_{codename}"
        return codename

    return f"{platform.machine()}_linux"


@contextlib.contextmanager
def _install_formula_from_tap(formula_name, version, bottle_cache_file, allow_slow):
    formula_info = _get_formula_info(formula_name)
    is_homebrew_tap = formula_info["tap"] == "homebrew/core"

    if not allow_slow and is_homebrew_tap:
        logger.error(
            "Exiting since the slow option is not enabled."
            " Enable this option to do a slow git search on the homebrew repository"
        )
        sys.exit(1)

    tap_user, tap_repo = formula_info["tap"].split("/")
    brew_repo = os.path.join(
        check_output(["brew", "--repository"]),
        f"Library/Taps/{tap_user}/homebrew-{tap_repo}",
    )

    os.chdir(brew_repo)
    logger.warning("Searching for version in git directory, this may take a while...")
    sha = check_output(
        f"git grep -F '{version}' `git rev-list master -- Formula/{formula_name}.rb`"
        f" -- Formula/{formula_name}.rb | head -n1 | cut -f1 -d':'",
        shell=True,
    )
    if not sha:
        logger.error(f"Could not find a source version for {formula_name} {version}")
        sys.exit(1)

    logger.info(f"Found a version in commit: {sha}")
    subprocess.run(
        ["git", "checkout", sha],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )

    try:
        formula_info = _get_formula_info(formula_name)
        bottle_info = (
            formula_info.get("bottle", {})
            .get("stable", {})
            .get("files", {})
            .get(_build_bottle_os_identifier(), {})
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


def download_bottle(bottle_file_name, destination_path):
    bottle_base_urls = dict(
        Darwin="https://homebrew.bintray.com/bottles",
        Linux="https://linuxbrew.bintray.com/bottles",
    )
    url = f"{bottle_base_urls[SYSTEM]}/{bottle_file_name}"

    try:
        download_file(url, destination_path)
    except HTTPError as e:
        if e.response.status_code < 500:
            raise BottleNotFound
        raise


def fetch_listed_bottle_versions(formula_name):
    subject = "homebrew" if IS_MAC_OS else "linuxbrew"
    url = "https://api.bintray.com/search/packages"
    params = dict(
        name=formula_name,
        subject=subject,
        repo="bottles",
    )

    response = requests.get(url, params=params)
    if not response.ok or not response.json():
        return [], None
    return response.json()[0]["versions"], response.json()[0]["latest_version"]


def switch(formula_name, version=None, allow_slow=False):
    if "/" in formula_name:
        tap, formula_name = formula_name.rsplit("/", 1)
        logger.info(f"Tapping {tap}")
        subprocess.check_output(["brew", "tap", tap])

    listed_bottle_versions, latest_version = fetch_listed_bottle_versions(formula_name)
    # Only error if there are bottles that exist
    if listed_bottle_versions:
        pretty_versions = "\n- ".join(listed_bottle_versions)
        if not version:
            logger.warning(
                f"Found the following bottle versions for {formula_name}: \n- {pretty_versions}"  # noqa
            )
            sys.exit(1)
        if version not in listed_bottle_versions:
            logger.error(
                f"{version} is not an available version for {formula_name}: \n- {pretty_versions}"  # noqa
            )
            sys.exit(1)
    elif not version:
        logger.error("Version must be given since no existing bottles were found")
        sys.exit(1)

    logger.info(f"Switching {formula_name} to version {version}")
    brew_cache_dir = check_output(["brew", "--cache"])
    bottle_cache_name = f"{formula_name}--{version}"
    bottle_cache_file = os.path.join(
        brew_cache_dir,
        f"{bottle_cache_name}.{_build_bottle_os_identifier()}.{BOTTLE_FILE_SUFFIX}",
    )

    with contextlib.ExitStack() as stack:
        if os.path.isfile(bottle_cache_file):
            logger.info(f"Found bottle in cache: {bottle_cache_file}")
            formula_installation = bottle_cache_file
        else:
            logger.info("Not in cache: finding bottle to download")
            bottle_file_name = (
                f"{formula_name}-{version}"
                f".{_build_bottle_os_identifier()}.{BOTTLE_FILE_SUFFIX}"
            )
            try:
                download_bottle(bottle_file_name, bottle_cache_file)
                formula_installation = bottle_cache_file
                # We don't have a SHA to check against
                logger.warning(
                    "Bottle successfully downloaded, but cannot verify SHA256"
                )
            except BottleNotFound:
                logger.warning(f"No bottle was found for {formula_name} {version}")
                formula_installation = stack.enter_context(
                    _install_formula_from_tap(
                        formula_name, version, bottle_cache_file, allow_slow
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
