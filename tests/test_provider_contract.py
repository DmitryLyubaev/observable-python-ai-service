import socket

import pytest
from conftest import record


def test_contradictory_or_foreign_citation_rejected(store):
    from p19.controlled import ControlledProvider
    from p19.evidence import lookup, seed
    from p19.provider import InvalidProviderOutput, validate_reply

    seed(store)
    evidence = lookup(record(1), store)
    for profile in ["contradictory", "foreign_citation", "malformed"]:
        reply = ControlledProvider(profile).invoke(record(1), evidence, 1, 10)
        with pytest.raises(InvalidProviderOutput):
            validate_reply(reply, evidence)


def test_controlled_provider_uses_no_network(store, monkeypatch):
    from p19.controlled import ControlledProvider
    from p19.provider import validate_reply

    evidence = {"receiver_outcome": "unresolved", "records": []}

    def denied(*args, **kwargs):
        raise AssertionError("network_used")

    monkeypatch.setattr(socket, "create_connection", denied)
    reply = ControlledProvider("success").invoke(record(), evidence, 1, 10)
    assert validate_reply(reply, evidence)["receiver_outcome"] == "unresolved"
    assert reply["usage"]["provenance"] == "simulated"
