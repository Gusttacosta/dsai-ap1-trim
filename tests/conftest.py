"""
Pytest configuration and global fixtures.
"""
import pytest
import os
import sys

# Fixtures de banco dos testes de agendamento (sessionmaker, client, set_now).
from tests.agenda_fixtures import client, sessionmaker, set_now  # noqa: F401

# Ensure src is in pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

@pytest.fixture(scope="session")
def global_db_mock():
    return {"status": "connected"}

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup
    yield
    # Teardown
