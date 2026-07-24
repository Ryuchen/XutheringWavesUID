import pytest

from XutheringWavesUID.wutheringwaves_gachalog import gacha_handler
from XutheringWavesUID.wutheringwaves_gachalog.merge_utils import (
    GachaMergeError,
)


def _xhh_data(records: list[dict]) -> dict:
    return {
        "user_info": {"uid": "101353996"},
        "gacha_record": [
            {
                "pool_type": "限定池",
                "records": records,
            }
        ],
    }


def test_xhh_current_pity_summary_without_name_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gacha_handler, "_XHH_NAME_TO_ID", {"安可": 1303})
    original = {"info": {"uid": "101353996"}, "list": []}
    records = [
        {
            "idx": gacha_handler.XHH_CURRENT_PITY_IDX,
            "timestamp": 1784882945,
            "diff": 7,
        },
        {
            "idx": 1,
            "timestamp": 1784796545,
            "diff": 2,
            "name": "安可",
        },
    ]

    merged = gacha_handler.merge_xhh_data(original, _xhh_data(records))

    assert len(merged["list"]) == 2
    assert [item["qualityLevel"] for item in merged["list"]] == [5, 3]
    assert merged["list"][0]["name"] == "安可"


def test_xhh_non_summary_record_still_requires_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gacha_handler, "_XHH_NAME_TO_ID", {"安可": 1303})
    original = {"info": {"uid": "101353996"}, "list": []}
    records = [
        {
            "idx": 1,
            "timestamp": 1784796545,
            "diff": 2,
        }
    ]

    with pytest.raises(GachaMergeError, match="五星记录缺少名称"):
        gacha_handler.merge_xhh_data(original, _xhh_data(records))
