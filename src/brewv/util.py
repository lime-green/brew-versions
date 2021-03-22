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


def download_file(url, destination_path, sha256_verification=None):
    logger.info(f"GET {url}")
    response = requests.get(url)
    response.raise_for_status()

    # This doesn't offer much security benefit since it comes from
    # the same source as the content itself
    if "X-Checksum-Sha256" in response.headers and response.headers[
        "X-Checksum-Sha256"
    ] != sha_256(response.content):
        logger.error("SHA256 mismatch occured in transit")
        raise HashMismatch

    if sha256_verification:
        if sha256_verification == sha_256(response.content):
            logger.info("SHA256 verified successfully")
        else:
            raise HashMismatch

    with open(destination_path, "wb") as f:
        f.write(response.content)


def check_output(*args, **kwargs):
    return subprocess.check_output(*args, **kwargs).decode().strip()


def mac_ver():
    return platform.mac_ver()[0]


def is_supported_mac_ver():
    return mac_ver() in MAC_VER_TO_CODENAME


def sha_256(content):
    return hashlib.sha256(content).hexdigest()
