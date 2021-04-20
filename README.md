# Brew Versions (`brewv`)
[![PyPI version](https://badge.fury.io/py/brew-versions.svg)](https://badge.fury.io/py/brew-versions)
![Python versions](https://img.shields.io/pypi/pyversions/brew-versions.svg?style=flat-square&label=Python%20Versions)

Manage multiple versions of your Homebrew packages with ease!
Homebrew makes this difficult as a design decision, but sometimes old packages
need to be installed and we need a way to do so easily.

## Installation
With [pipx](https://github.com/pipxproject/pipx)
```bash
pipx install brew-versions
```
Or just with pip:
```bash
python3 -m pip install --user brew-versions
```

## Usage

#### Switch to a specific version:
```bash
$ brewv switch wget 1.21
[brewv]: Switching wget to version 1.21
[brewv]: Not in cache: finding bottle to download
[brewv]: GET https://linuxbrew.bintray.com/bottles/wget-1.21.x86_64_linux.bottle.tar.gz
[brewv]: Bottle successfully downloaded, but cannot verify SHA256
[brewv]: Pinning wget
[brewv]: Successfully switched to wget 1.21
```

#### Installing from taps:
```bash
$ brewv switch jonchang/biology/bucky 1.4.4
[brewv]: Tapping jonchang/biology
[brewv]: Switching bucky to version 1.4.4
[brewv]: Not in cache: finding bottle to download
[brewv]: GET https://linuxbrew.bintray.com/bottles/bucky-1.4.4.x86_64_linux.bottle.tar.gz
[brewv]: No bottle was found for bucky 1.4.4
[brewv]: Searching for version in git directory, this may take a while...
[brewv]: Found a version in commit: eee76a60fb5d7c6b619d736b50ee10fe42a9c73c
[brewv]: Found bottle in tap config
[brewv]: GET https://dl.bintray.com/jonchang/bottles-biology/bucky-1.4.4.x86_64_linux.bottle.tar.gz
[brewv]: SHA256 verified successfully
[brewv]: Pinning bucky
[brewv]: Successfully switched to jonchang/biology/bucky 1.4.4
```

When no bottle is found for taps it will proceed with searching the
local tap repository for the correct version and installing from the bottle
defined in the formula if it exists, otherwise from source.

This is very slow for the main homebrew repository so this behaviour is disabled
when a bottle for a homebrew-core package cannot be found. You can supply
the option `brewv switch --slow ...`  to perform this search.

### Warnings
Proper SHA256 verification is not done when downloading bottles from the
main bottle repository. This is because to get the expected SHAs would mean searching
the huge homebrew-core repository.

While homebrew bottles exist for most operating
systems, if the bottle is not found then parsing old formulas fails quite often
since Homebrew updates their code frequently.
