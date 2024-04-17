from pytest import fixture
from unittest.mock import MagicMock, patch

@fixture
def session():
    return MagicMock()

@fixture(autouse=True)
def session_builder(session):
    with patch('snowflake.snowpark.session.Session.builder') as builder:
        builder.getOrCreate.return_value = session
        yield builder

def normalize_spaces(input):
    return ' '.join(input.split())
