"""End-to-end API tests for portfolios, instruments and trades, including ownership."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Instrument
from tests.conftest import act_as

ENTRY_TIME = "2026-10-01T14:30:00Z"
EXIT_TIME = "2026-10-01T16:00:00Z"


# ---- helpers ----------------------------------------------------------------------------------

def make_portfolio(client: TestClient, name: str = "CME Competition") -> dict:
    r = client.post("/api/portfolios", json={"name": name, "account_type": "simulated", "starting_capital": "100000"})
    assert r.status_code == 201, r.json()
    return r.json()


def es_id(db: Session) -> int:
    return db.scalars(select(Instrument.id).where(Instrument.symbol == "ES")).one()


def make_es_contract(client: TestClient, db: Session) -> dict:
    r = client.post(
        f"/api/instruments/{es_id(db)}/contracts", json={"contract_month": "2026-12", "expiration_date": "2026-12-18"}
    )
    assert r.status_code == 201, r.json()
    return r.json()


def es_trade(portfolio: dict, contract: dict, **overrides) -> dict:
    body = {
        "portfolio_id": portfolio["id"],
        "instrument_id": contract["instrument_id"],
        "futures_contract_id": contract["id"],
        "direction": "long",
        "planned_quantity": "2",
        "planned_entry_price": "5000",
        "initial_stop_price": "4980",
        "targets": [{"price": "5040"}, {"price": "5060"}],
        "thesis": "Soft CPI print should support equities",
        "catalyst": "CPI release",
    }
    body.update(overrides)
    return body


@pytest.fixture
def setup(client: TestClient, db: Session, alice):
    portfolio = make_portfolio(client)
    contract = make_es_contract(client, db)
    return portfolio, contract


def error_fields(response) -> list[str]:
    return [e["field"] for e in response.json()["errors"]]


# ---- portfolios & instruments -----------------------------------------------------------------

def test_duplicate_portfolio_name_is_409(client, alice):
    make_portfolio(client)
    r = client.post("/api/portfolios", json={"name": "CME Competition", "account_type": "real", "starting_capital": "0"})
    assert r.status_code == 409


def test_portfolio_patch_changes_only_sent_fields(client, alice):
    p = make_portfolio(client)
    r = client.patch(f"/api/portfolios/{p['id']}", json={"starting_capital": "25000.50"})
    assert r.status_code == 200
    assert r.json()["starting_capital"] == "25000.50"
    assert r.json()["name"] == "CME Competition"


def test_futures_list_includes_tick_value(client, alice):
    r = client.get("/api/instruments", params={"asset_class": "future", "q": "ZN"})
    [zn] = r.json()
    assert Decimal(zn["tick_value"]) == Decimal("15.625")
    assert zn["price_format"] == "half_thirty_seconds"


def test_contract_code_uses_cme_month_letters(client, db, alice):
    assert make_es_contract(client, db)["code"] == "ESZ2026"


def test_contract_expiration_far_from_month_rejected(client, db, alice):
    r = client.post(
        f"/api/instruments/{es_id(db)}/contracts", json={"contract_month": "2026-12", "expiration_date": "2026-06-19"}
    )
    assert r.status_code == 422
    assert error_fields(r) == ["expiration_date"]


def test_stock_symbol_is_uppercased_and_unique(client, alice):
    r = client.post("/api/instruments/stocks", json={"symbol": " aapl ", "name": "Apple Inc."})
    assert r.status_code == 201
    assert r.json()["symbol"] == "AAPL"
    assert r.json()["tick_size"] is None
    assert client.post("/api/instruments/stocks", json={"symbol": "AAPL", "name": "Apple"}).status_code == 409


# ---- trade CRUD ------------------------------------------------------------------------------

def test_create_closed_trade_round_trips_exact_decimals(client, setup):
    portfolio, contract = setup
    body = es_trade(
        portfolio, contract,
        entry={"price": "5000.25", "executed_at": ENTRY_TIME, "fees": "4.20"},
        exit={"price": "5040.50", "executed_at": EXIT_TIME, "fees": "4.20"},
    )
    r = client.post("/api/trades", json=body)
    assert r.status_code == 201, r.json()
    trade = r.json()

    assert trade["status"] == "closed"
    assert trade["instrument"]["symbol"] == "ES"
    assert trade["futures_contract"]["code"] == "ESZ2026"
    assert [t["sequence"] for t in trade["targets"]] == [1, 2]
    entry, exit_ = trade["executions"]
    # Decimals come back as strings so no precision is lost in JSON.
    assert (entry["kind"], entry["price"], entry["quantity"]) == ("entry", "5000.2500000000", "2.000000")
    assert (exit_["kind"], exit_["price"], exit_["fees"]) == ("exit", "5040.5000000000", "4.20")


@pytest.mark.parametrize(
    "extra, expected_status",
    [({}, "planned"), ({"entry": {"price": "5000", "executed_at": ENTRY_TIME}}, "open")],
)
def test_status_is_derived(client, setup, extra, expected_status):
    portfolio, contract = setup
    r = client.post("/api/trades", json=es_trade(portfolio, contract, **extra))
    assert r.json()["status"] == expected_status


def test_partial_exit_status(client, setup):
    portfolio, contract = setup
    body = es_trade(
        portfolio, contract,
        entry={"price": "5000", "executed_at": ENTRY_TIME},
        exit={"price": "5040", "executed_at": EXIT_TIME, "quantity": "1"},
    )
    assert client.post("/api/trades", json=body).json()["status"] == "partially_closed"


def test_off_tick_price_rejected_with_field_name(client, setup):
    portfolio, contract = setup
    r = client.post("/api/trades", json=es_trade(portfolio, contract, entry={"price": "5000.30", "executed_at": ENTRY_TIME}))
    assert r.status_code == 422
    assert error_fields(r) == ["entry.price"]
    assert "0.25" in r.json()["errors"][0]["message"]


def test_futures_trade_requires_contract(client, setup):
    portfolio, contract = setup
    r = client.post("/api/trades", json=es_trade(portfolio, contract, futures_contract_id=None))
    assert error_fields(r) == ["futures_contract_id"]


def test_contract_must_match_instrument(client, db, setup):
    portfolio, contract = setup
    nq_id = db.scalars(select(Instrument.id).where(Instrument.symbol == "NQ")).one()
    r = client.post("/api/trades", json=es_trade(portfolio, contract, instrument_id=nq_id))
    assert error_fields(r) == ["futures_contract_id"]


def test_stock_trade_with_fractional_shares(client, setup):
    portfolio, _ = setup
    stock = client.post("/api/instruments/stocks", json={"symbol": "MSFT", "name": "Microsoft"}).json()
    body = {
        "portfolio_id": portfolio["id"], "instrument_id": stock["id"], "direction": "short",
        "planned_quantity": "10.5", "planned_entry_price": "410.255", "initial_stop_price": "420",
    }
    r = client.post("/api/trades", json=body)
    assert r.status_code == 201, r.json()
    assert r.json()["futures_contract"] is None


def test_schema_errors_use_same_shape(client, setup):
    portfolio, contract = setup
    naive_time = "2026-10-01T14:30:00"  # no timezone
    r = client.post(
        "/api/trades", json=es_trade(portfolio, contract, planned_quantity="-1", entry={"price": "5000", "executed_at": naive_time})
    )
    assert r.status_code == 422
    assert set(error_fields(r)) == {"planned_quantity", "entry.executed_at"}


def test_put_replaces_targets_and_adds_exit(client, setup):
    portfolio, contract = setup
    created = client.post(
        "/api/trades", json=es_trade(portfolio, contract, entry={"price": "5000", "executed_at": ENTRY_TIME})
    ).json()

    updated_body = es_trade(
        portfolio, contract,
        targets=[{"price": "5050"}],
        current_stop_price="5000",  # moved stop to breakeven — allowed
        entry={"price": "5000", "executed_at": ENTRY_TIME},
        exit={"price": "5050", "executed_at": EXIT_TIME},
        reflection="Followed the plan.",
    )
    r = client.put(f"/api/trades/{created['id']}", json=updated_body)
    assert r.status_code == 200, r.json()
    trade = r.json()
    assert trade["status"] == "closed"
    assert [t["price"] for t in trade["targets"]] == ["5050.0000000000"]
    assert trade["current_stop_price"] == "5000.0000000000"
    assert trade["initial_stop_price"] == "4980.0000000000"  # preserved


def test_initial_stop_locked_after_entry(client, setup):
    portfolio, contract = setup
    entry = {"price": "5000", "executed_at": ENTRY_TIME}
    created = client.post("/api/trades", json=es_trade(portfolio, contract, entry=entry)).json()

    r = client.put(f"/api/trades/{created['id']}", json=es_trade(portfolio, contract, entry=entry, initial_stop_price="4990"))
    assert r.status_code == 422
    assert error_fields(r) == ["initial_stop_price"]


def test_initial_stop_editable_while_planned(client, setup):
    portfolio, contract = setup
    created = client.post("/api/trades", json=es_trade(portfolio, contract)).json()
    r = client.put(f"/api/trades/{created['id']}", json=es_trade(portfolio, contract, initial_stop_price="4990"))
    assert r.status_code == 200


def test_delete_trade(client, setup):
    portfolio, contract = setup
    created = client.post("/api/trades", json=es_trade(portfolio, contract)).json()
    assert client.delete(f"/api/trades/{created['id']}").status_code == 204
    assert client.get(f"/api/trades/{created['id']}").status_code == 404


# ---- search & filters -------------------------------------------------------------------------

def test_filters_and_search(client, setup):
    portfolio, contract = setup
    other_portfolio = make_portfolio(client, "Class Trading")
    client.post("/api/trades", json=es_trade(portfolio, contract))  # planned long
    client.post("/api/trades", json=es_trade(
        portfolio, contract, direction="short", initial_stop_price="5020", targets=[{"price": "4950"}],
        thesis="Hot payrolls → yields up", entry={"price": "5000", "executed_at": ENTRY_TIME},
    ))
    client.post("/api/trades", json=es_trade(other_portfolio, contract))

    def ids(**params) -> int:
        return len(client.get("/api/trades", params=params).json())

    assert ids() == 3
    assert ids(portfolio_id=portfolio["id"]) == 2
    assert ids(direction="short") == 1
    assert ids(status="open") == 1
    assert ids(q="payrolls") == 1
    assert ids(q="es") == 3  # symbol match, case-insensitive
    assert ids(asset_class="stock") == 0
    assert ids(date_from="2026-10-01", date_to="2026-10-01", status="open") == 1
    assert ids(date_to="2026-09-30", status="open") == 0
    assert client.get("/api/trades", params={"status": "bogus"}).status_code == 422


# ---- ownership --------------------------------------------------------------------------------

def test_other_users_cannot_see_or_change_trades(client, setup, bob):
    portfolio, contract = setup
    trade = client.post("/api/trades", json=es_trade(portfolio, contract)).json()

    act_as(bob)
    assert client.get("/api/trades").json() == []
    assert client.get(f"/api/trades/{trade['id']}").status_code == 404
    assert client.put(f"/api/trades/{trade['id']}", json=es_trade(portfolio, contract)).status_code == 404
    assert client.delete(f"/api/trades/{trade['id']}").status_code == 404
    assert client.get("/api/portfolios").json() == []
    assert client.get(f"/api/portfolios/{portfolio['id']}").status_code == 404
    assert client.delete(f"/api/portfolios/{portfolio['id']}").status_code == 404
    # Bob cannot slip a trade into Alice's portfolio either.
    assert client.post("/api/trades", json=es_trade(portfolio, contract)).status_code == 404


def test_cannot_use_another_users_strategy(client, setup, bob, alice):
    portfolio, contract = setup
    act_as(bob)
    bobs_strategy = client.post("/api/strategies", json={"name": "Bob's breakout"}).json()

    act_as(alice)
    r = client.post("/api/trades", json=es_trade(portfolio, contract, strategy_id=bobs_strategy["id"]))
    assert r.status_code == 404
