from ka9q_beacon_monitor.observability import core


def test_build_identity_consumes_shared_environment_registry_names(monkeypatch) -> None:
    monkeypatch.setattr(core, "KA9Q_BUILD_VERSION_ENV", "TEST_BUILD_VERSION")
    monkeypatch.setattr(core, "KA9Q_BUILD_REVISION_ENV", "TEST_BUILD_REVISION")
    monkeypatch.setattr(core, "KA9Q_BUILD_TIME_UTC_ENV", "TEST_BUILD_TIME")

    identity = core.BuildIdentity.from_environment(
        {
            "TEST_BUILD_VERSION": "9.8.7",
            "TEST_BUILD_REVISION": "registry-proof",
            "TEST_BUILD_TIME": "2026-08-07T10:00:00Z",
        }
    )

    assert identity.version == "9.8.7"
    assert identity.revision == "registry-proof"
    assert identity.build_time_utc == "2026-08-07T10:00:00Z"
