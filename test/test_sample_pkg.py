"""Self-test fixture: run by python-ci.yml via test-shared-workflows.yml."""

from fixtures.sample_pkg import add


def test_add():
    assert add(2, 3) == 5
