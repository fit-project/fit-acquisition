from __future__ import annotations

import pytest

from fit_acquisition.class_names import ClassNames


@pytest.mark.unit
def test_class_names_register_get_and_contains() -> None:
    registry = ClassNames()
    registry.register("CUSTOM", "TaskCustom")

    assert registry.get("CUSTOM") == "TaskCustom"
    assert "CUSTOM" in registry
    assert registry.CUSTOM == "TaskCustom"


@pytest.mark.unit
def test_class_names_unknown_attribute_raises() -> None:
    registry = ClassNames()

    with pytest.raises(AttributeError):
        _ = registry.DOES_NOT_EXIST
