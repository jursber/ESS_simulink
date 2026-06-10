"""API contract tests for simple-day catalog."""

from api.schemas import SimpleDayCatalogResponse
from src.data.simple_day_catalog import SimpleDayCatalog


def test_simple_day_catalog_response_contract_has_stable_groups():
    data = SimpleDayCatalog().list_catalog()
    response = SimpleDayCatalogResponse(**data)
    payload = response.model_dump()

    assert set(payload) == {"load", "pv", "spot", "monthly", "retail", "wholesale"}
    assert isinstance(payload["load"], list)
    assert isinstance(payload["pv"], list)
    assert isinstance(payload["spot"], list)
    if payload["load"]:
        item = payload["load"][0]
        assert {"id", "label", "category", "meta"} <= set(item)
        assert item["category"] == "load"


def test_simple_day_catalog_does_not_expose_absolute_paths():
    payload = SimpleDayCatalog().list_catalog()

    for items in payload.values():
        for item in items:
            file_path = str((item.get("meta") or {}).get("file") or "")
            assert ":/" not in file_path.replace("\\", "/")
