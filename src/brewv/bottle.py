import os
import platform

from requests.exceptions import HTTPError

from .constants import BOTTLE_FILE_SUFFIX, IS_MAC_OS, MAC_VER_TO_CODENAME, SYSTEM
from .util import (
    check_output,
    download_file,
    is_supported_mac_ver,
    logger,
    mac_ver,
    make_request,
)


class BottleNotFound(Exception):
    def __init__(self, source_revision=None):
        self.source_revision = source_revision


class BottleClient:
    def __init__(self, formula_name):
        self.formula_name = formula_name
        self.bottle_os_identifier = build_bottle_os_identifier()


class GithubBottleClient(BottleClient):
    GITHUB_AUTH = {"Authorization": "Bearer QQ=="}
    base_url = dict(
        Darwin="https://ghcr.io/v2/homebrew/core",
        Linux="https://ghcr.io/v2/linuxbrew/core",
    )[SYSTEM]

    def _parse_manifest(self, manifest_response, ref_name):
        source_revision = manifest_response["annotations"][
            "org.opencontainers.image.ref.name"
        ]

        for manifest in manifest_response["manifests"]:
            annotations = manifest["annotations"]
            if annotations["org.opencontainers.image.ref.name"] == ref_name:
                return annotations["sh.brew.bottle.digest"], source_revision

        return None, source_revision

    def download_bottle(self, version, destination_path):
        manifest_url = f"{self.base_url}/{self.formula_name}/manifests/{version}"
        ref_name = f"{version}.{self.bottle_os_identifier}"
        source_revision = None

        try:
            manifest = make_request(
                manifest_url,
                headers={
                    "Accept": "application/vnd.oci.image.index.v1+json",
                    **self.GITHUB_AUTH,
                },
            )
            bottle_digest, source_revision = self._parse_manifest(manifest, ref_name)

            if not bottle_digest:
                logger.info("No digest found in manifest")
                raise BottleNotFound(source_revision)

            bottle_url = (
                f"{self.base_url}/{self.formula_name}/blobs/sha256:{bottle_digest}"
            )
            download_file(
                bottle_url,
                destination_path,
                headers=self.GITHUB_AUTH,
                sha256_verification=bottle_digest,
            )
        except HTTPError:
            logger.warning("Got HTTP error when attempting to download bottle")
            raise BottleNotFound(source_revision)


class BintrayBottleClient(BottleClient):
    base_url = dict(
        Darwin="https://homebrew.bintray.com/bottles",
        Linux="https://linuxbrew.bintray.com/bottles",
    )[SYSTEM]
    subject = dict(Darwin="homebrew", Linux="linuxbrew")[SYSTEM]

    def download_bottle(self, version, destination_path):
        bottle_file_name = (
            f"{self.formula_name}-{version}"
            f".{self.bottle_os_identifier}.{BOTTLE_FILE_SUFFIX}"
        )
        url = f"{self.base_url}/{bottle_file_name}"

        try:
            download_file(url, destination_path)
        except HTTPError:
            logger.warning("Got HTTP error when attempting to download bottle")
            raise BottleNotFound


def download_bottle(formula_name, version, bottle_cache_file):
    clients = [GithubBottleClient(formula_name), BintrayBottleClient(formula_name)]
    source_revision = None

    for client in clients:
        logger.info(f"Trying bottle download with {client.__class__.__name__}")

        try:
            return client.download_bottle(version, bottle_cache_file)
        except BottleNotFound as e:
            source_revision = e.source_revision

    raise BottleNotFound(source_revision)


def build_bottle_os_identifier():
    if IS_MAC_OS:
        assert is_supported_mac_ver()
        codename = MAC_VER_TO_CODENAME[mac_ver()].replace(" ", "_").lower()

        if platform.machine() == "arm64":
            return f"arm64_{codename}"
        return codename

    return f"{platform.machine()}_linux"


def get_bottle_cache_location(formula_name, version):
    brew_cache_dir = check_output(["brew", "--cache"])
    bottle_cache_name = f"{formula_name}--{version}"
    return os.path.join(
        brew_cache_dir,
        f"{bottle_cache_name}.{build_bottle_os_identifier()}.{BOTTLE_FILE_SUFFIX}",
    )
