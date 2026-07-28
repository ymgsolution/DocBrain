"""Shared test constants.

Deliberately not in conftest.py: importing from a conftest makes it
resolvable under two module names ("conftest" and "tests.conftest"), which
mypy reports as a duplicate source file. Fixtures belong in conftest;
plain constants belong here.
"""

TEST_PASSWORD = "Test@123"
