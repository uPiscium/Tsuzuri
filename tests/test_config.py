from pathlib import Path

from tsuzuri.config import RuntimeConfig


def test_runtime_config_loads_settings_env_file_and_environment(
    tmp_path: Path, monkeypatch
) -> None:
    settings_path = tmp_path / "settings.toml"
    settings_path.write_text(
        'searxng_base_url = "https://search.example"\n'
        'webdav_base_url = "https://webdav.example"\n'
        'blocklisted_domains = ["x.com"]\n',
        encoding="utf-8",
    )
    env_path = tmp_path / ".env"
    env_path.write_text(
        "NEXTCLOUD_USERNAME=file-user\nNEXTCLOUD_PASSWORD=file-pass\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TSUZURI_SETTINGS_PATH", str(settings_path))
    monkeypatch.setenv("NEXTCLOUD_PASSWORD", "env-pass")

    config = RuntimeConfig.from_env(env_file=env_path)

    assert config.searxng_base_url == "https://search.example"
    assert config.webdav_base_url == "https://webdav.example"
    assert config.blocklisted_domains == ["x.com"]
    assert config.nextcloud_username == "file-user"
    assert config.nextcloud_password == "env-pass"
