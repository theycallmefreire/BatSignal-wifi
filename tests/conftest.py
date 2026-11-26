import copy

import pytest


@pytest.fixture
def rooms():
    return {
        "Sala": [{"tempo": "12:00:00", "forca": 0}, {"tempo": "12:00:05", "forca": 100}],
        "Escritório": [{"tempo": "12:01:00", "forca": 42}],
    }


@pytest.fixture
def survey(rooms):
    return {"nome": "Casa", "data": "2026-04-01 12:00:00", "comodos": copy.deepcopy(rooms)}
