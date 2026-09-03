from varma.controls.addendum_m import ADDENDUM_M_ETP_SYMBOLS, WATCH_ONLY_LABEL


def test_watchlist_is_not_allow_list(client):
    w = client.get("/watchlist").json()
    c = client.get("/controls").json()
    assert w["is_execution_allow_list"] is False
    assert w["gold"] is False
    assert w["label"] == "TEMPORARY DEVELOPMENT DEFAULT"
    assert "AAPL" in c["allow_list"]
    assert c["allow_list_empty"] is False
    symbols = [i["symbol"] for i in w["items"]]
    assert symbols
    for etp in ADDENDUM_M_ETP_SYMBOLS:
        assert etp in symbols
        assert etp not in c["allow_list"]
    for s in symbols:
        assert "XAU" not in s.upper()
        item = next(i for i in w["items"] if i["symbol"] == s)
        if s in ADDENDUM_M_ETP_SYMBOLS:
            assert item["asset_class"] == "listed_etp"
            assert item["executable"] is False
            assert item["watch_only"] is True
            assert item["label"] == WATCH_ONLY_LABEL
        else:
            assert item["asset_class"] == "listed_equity"
            assert "GOLD" not in s.upper()
