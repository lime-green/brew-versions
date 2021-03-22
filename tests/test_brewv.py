import subprocess

import pytest
from brewv import cli
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem():
        yield runner


def test_it_runs_using_entrypoint():
    assert subprocess.check_output("brewv --help", shell=True) is not None


def test_it_runs_using_module():
    assert subprocess.check_output("python3 -m brewv --help", shell=True) is not None


def test_it_runs_using_cli(cli_runner):
    assert cli_runner.invoke(cli, ["--help"]).exit_code == 0
