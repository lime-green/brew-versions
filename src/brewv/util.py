import errno
import hashlib
import logging
import os
import platform
import requests
import subprocess

from .constants import MAC_VER_TO_CODENAME

logger = logging.getLogger("brewv")


class HashMismatch(Exception):
    pass


def symlink_force(link_path, target):
    try:
        os.symlink(link_path, target)
    except OSError as e:
        if e.errno == errno.EEXIST:
            os.remove(target)
            os.symlink(link_path, target)
        else:
            raise


def download_file(url, destination_path, headers=None, sha256_verification=None):
    logger.info(f"GET {url}")
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    if sha256_verification:
        if sha256_verification == sha_256(response.content):
            logger.info("SHA256 verified successfully")
        else:
            raise HashMismatch

    with open(destination_path, "wb") as f:
        f.write(response.content)


def make_request(url, headers=None):
    logger.info(f"GET {url}")

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    if response.headers.get("content-type") in [
        "application/json",
        "application/vnd.oci.image.index.v1+json",
    ]:
        return response.json()
    return response.content


def check_output(*args, **kwargs):
    return subprocess.check_output(*args, **kwargs).decode().strip()


def mac_ver():
    """
    macOS versions increased from 10.13, 10.14, 10.15
    until Big Sur where it got wonky. Big Sur can be 10.16 or >= 11
    I'm assuming future versions will be similar: 11.x -> 12.x -> 13.x

    This will return a normalized mac_ver, that returns the string that can
    identify the OS version
    """
    mac_ver_ = platform.mac_ver()[0].split(".")
    if int(mac_ver_[0]) >= 11:
        return mac_ver_[0]
    return ".".join(mac_ver_[:2])


def is_supported_mac_ver():
    return mac_ver() in MAC_VER_TO_CODENAME


def sha_256(content):
    return hashlib.sha256(content).hexdigest()
