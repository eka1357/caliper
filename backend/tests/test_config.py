from caliper import config


def test_paths_are_absolute_under_repo():
    for p in (config.CACHE_DIR, config.QUANTIPHY_DIR, config.FIELD_DIR):
        assert p.is_absolute()
    assert (config.ROOT / "AGENTS.md").exists()


def test_prices_and_limits():
    assert config.SAM_USD_PER_FRAME == 0.0002
    assert config.MUSE_MAX_OUTPUT_TOKENS >= 4000
