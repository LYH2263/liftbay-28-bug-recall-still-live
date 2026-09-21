"""消防召回 API 测试：进入召回冻结/禁派/禁登记，解除后恢复可派。"""

import os

# 必须在导入 app 之前设置：让 lifespan 的建表走 SQLite 而非 Postgres
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SEED_ON_EMPTY"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import Building, CallTicket, ElevatorCar

RECALL_FLOOR = 1


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        db = TestingSession()
        b = Building(name="测试楼", floors=10, recall_floor=RECALL_FLOOR)
        db.add(b)
        db.flush()
        db.add_all(
            [
                ElevatorCar(building_id=b.id, label="T1", floor=6, direction="up", load=3, capacity=10),
                ElevatorCar(building_id=b.id, label="T2", floor=1, direction="idle", load=0, capacity=10),
            ]
        )
        db.add_all(
            [
                CallTicket(building_id=b.id, floor=4, direction="up", passengers=2, status="waiting"),
                CallTicket(building_id=b.id, floor=8, direction="down", passengers=1, status="waiting"),
            ]
        )
        db.commit()
        db.close()
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _building_id(client: TestClient) -> int:
    return client.get("/api/buildings").json()[0]["id"]


def _enter_recall(client: TestClient) -> dict:
    bid = _building_id(client)
    r = client.post(f"/api/buildings/{bid}/recall", json={"active": True})
    assert r.status_code == 200
    return r.json()


def test_recall_freezes_calls_and_empties_cars(client):
    body = _enter_recall(client)
    assert body["recall_active"] is True
    assert body["recall_floor"] == RECALL_FLOOR

    cars = client.get("/api/cars").json()
    assert all(c["load"] == 0 for c in cars)
    assert all(c["floor"] == RECALL_FLOOR for c in cars)
    by_label = {c["label"]: c for c in cars}
    assert by_label["T1"]["direction"] == "down"  # 6F → 1F 需下行
    assert by_label["T2"]["direction"] == "idle"  # 已在召回层

    calls = client.get("/api/calls").json()
    assert {c["status"] for c in calls} == {"frozen"}


def test_dispatch_frozen_call_rejected(client):
    _enter_recall(client)
    calls = client.get("/api/calls").json()
    for c in calls:
        r = client.post("/api/dispatch", json={"call_id": c["id"]})
        assert r.status_code == 409
        assert "冻结" in r.json()["detail"]
        # 冻结单状态不变
    assert {c["status"] for c in client.get("/api/calls").json()} == {"frozen"}


def test_new_call_blocked_during_recall(client):
    bid = _building_id(client)
    _enter_recall(client)
    r = client.post(
        "/api/calls",
        json={"building_id": bid, "floor": 3, "direction": "up", "passengers": 1},
    )
    assert r.status_code == 409
    assert "召回" in r.json()["detail"]


def test_congestion_drops_to_zero_during_recall(client):
    before = client.get("/api/congestion").json()
    assert sum(x["passengers"] for x in before) == 3

    _enter_recall(client)

    after = client.get("/api/congestion").json()
    assert sum(x["passengers"] for x in after) == 0


def test_release_restores_waiting_and_car_stays_empty_at_recall_floor(client):
    bid = _building_id(client)
    _enter_recall(client)

    r = client.post(f"/api/buildings/{bid}/recall", json={"active": False})
    assert r.status_code == 200
    assert r.json()["recall_active"] is False

    # 轿厢保持召回后的零载荷、停在召回层
    cars = client.get("/api/cars").json()
    assert all(c["load"] == 0 for c in cars)
    assert all(c["floor"] == RECALL_FLOOR for c in cars)

    # 冻结单恢复为 waiting，拥堵重新计入
    calls = client.get("/api/calls").json()
    assert {c["status"] for c in calls} == {"waiting"}
    cong = client.get("/api/congestion").json()
    assert sum(x["passengers"] for x in cong) == 3

    # 原单可再派
    r = client.post("/api/dispatch", json={"call_id": calls[0]["id"]})
    assert r.status_code == 200
    assert r.json()["status"] == "assigned"
    assert r.json()["assigned_car_id"] is not None


def test_replay_records_recall_events(client):
    bid = _building_id(client)
    _enter_recall(client)
    client.post(f"/api/buildings/{bid}/recall", json={"active": False})

    logs = client.get("/api/replay").json()
    details = [l["detail"] for l in logs]
    assert any("消防召回启动" in d for d in details)
    assert any("呼梯冻结" in d for d in details)
    assert any("解除消防召回" in d for d in details)
    assert any("恢复待派" in d for d in details)


def test_recall_is_idempotent(client):
    bid = _building_id(client)
    _enter_recall(client)
    r = client.post(f"/api/buildings/{bid}/recall", json={"active": True})
    assert r.status_code == 200
    assert r.json()["recall_active"] is True
    # 重复进入不重复冻结、不产生额外日志
    logs = client.get("/api/replay").json()
    assert sum("消防召回启动" in l["detail"] for l in logs) == 1
