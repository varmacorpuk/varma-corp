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
    for s in symbols:
        assert "GOLD" not in s.upper()
        assert "XAU" not in s.upper()
        assert i_asset_equity(w, s)


def i_asset_equity(w, s):
    item = next(i for i in w["items"] if i["symbol"] == s)
    return item["asset_class"] == "listed_equity"
