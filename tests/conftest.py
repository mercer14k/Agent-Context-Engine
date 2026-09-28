from pathlib import Path
import pytest
from agent_context_engine.store import Access
from agent_context_engine.telemetry import Telemetry
from agent_context_engine.tokens import available


@pytest.fixture
def access():
    return Access('test-host', frozenset({'a', 'b', 'default'}))


@pytest.fixture
def db(tmp_path):
    value = Telemetry(tmp_path/'metrics.db')
    yield value
    value.close()


@pytest.fixture
def tokenizer():
    return available(Path(__file__).resolve().parents[1]/'.ace-local/tokenizer')
