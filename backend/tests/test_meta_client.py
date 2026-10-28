from caliper import config
from caliper.meta_client import (
    DiskCache,
    cached_call,
    muse_cost_usd,
    normalize_usage,
    request_key,
)


def test_request_key_ignores_dict_order():
    assert request_key({"a": 1, "b": [1, 2]}) == request_key({"b": [1, 2], "a": 1})
    assert request_key({"a": 1}) != request_key({"a": 2})


def test_cached_call_hits_disk_on_second_call(tmp_path):
    cache = DiskCache(tmp_path)
    calls = []

    def fn():
        calls.append(1)
        return {"text": "ok"}, {"input_tokens": 10, "output_tokens": 2}

    first, hit1 = cached_call("chat", {"model": "m", "q": "x"}, fn, cache)
    second, hit2 = cached_call("chat", {"model": "m", "q": "x"}, fn, cache)
    assert (hit1, hit2) == (False, True)
    assert len(calls) == 1
    assert second["response"] == {"text": "ok"}
    assert second["usage"] == {"input_tokens": 10, "output_tokens": 2}
    assert first["key"] == second["key"]


def test_cached_call_kind_is_part_of_key(tmp_path):
    cache = DiskCache(tmp_path)
    a, _ = cached_call("chat", {"q": 1}, lambda: ({}, {}), cache)
    b, _ = cached_call("responses", {"q": 1}, lambda: ({}, {}), cache)
    assert a["key"] != b["key"]


def test_chat_create_nth_gives_retries_their_own_entries(tmp_path, monkeypatch):
    from caliper import meta_client

    answers = iter(["first", "second"])

    def fake_cached_call(kind, payload, fn, cache):
        return {"response": next(answers), "payload": payload}, False

    monkeypatch.setattr(meta_client, "cached_call", fake_cached_call)
    monkeypatch.setattr(meta_client, "_occurrences", {})
    a = meta_client.chat_create_nth({"model": "m", "q": 1}, DiskCache(tmp_path))
    b = meta_client.chat_create_nth({"model": "m", "q": 1}, DiskCache(tmp_path))
    assert "occurrence" not in a["payload"]  # first call keeps the plain key
    assert b["payload"]["occurrence"] == 1


def test_normalize_usage_both_shapes():
    assert normalize_usage({"prompt_tokens": 5, "completion_tokens": 3}) == {
        "input_tokens": 5,
        "output_tokens": 3,
    }
    assert normalize_usage({"input_tokens": 7, "output_tokens": 1}) == {
        "input_tokens": 7,
        "output_tokens": 1,
    }
    assert normalize_usage(None) == {"input_tokens": 0, "output_tokens": 0}


def test_muse_cost_matches_price_table():
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert muse_cost_usd(usage) == config.MUSE_USD_PER_M_INPUT + config.MUSE_USD_PER_M_OUTPUT
