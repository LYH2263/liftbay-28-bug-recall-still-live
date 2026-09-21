from app.services.dispatch_engine import (
    CallRequest,
    CarState,
    congestion_by_floor,
    pick_car,
    recall_car_state,
    recall_direction,
    score_car,
)


def test_reject_when_full():
    car = CarState(1, 5, "idle", load=8, capacity=8)
    call = CallRequest(1, 5, "up", passengers=1)
    r = score_car(car, call)
    assert r.accepted is False
    assert "满员" in r.reason


def test_same_direction_beats_far_idle():
    cars = [
        CarState(1, 2, "up", load=1, capacity=10),
        CarState(2, 12, "idle", load=0, capacity=10),
    ]
    call = CallRequest(9, 4, "up", 1)
    best = pick_car(cars, call)
    assert best is not None
    assert best.car_id == 1


def test_closer_idle_wins_when_opposite():
    cars = [
        CarState(1, 10, "down", load=0, capacity=10),
        CarState(2, 3, "idle", load=0, capacity=10),
    ]
    call = CallRequest(3, 2, "up", 1)
    best = pick_car(cars, call)
    assert best is not None
    assert best.car_id == 2


def test_frozen_call_not_dispatched():
    cars = [CarState(1, 1, "idle", load=0, capacity=10)]
    call = CallRequest(7, 3, "up", 1, status="frozen")
    assert pick_car(cars, call) is None


def test_recall_direction_toward_recall_floor():
    assert recall_direction(6, 1) == "down"
    assert recall_direction(1, 1) == "idle"
    assert recall_direction(2, 5) == "up"


def test_recall_car_state_unloads_and_moves():
    car = CarState(1, 9, "up", load=5, capacity=10)
    r = recall_car_state(car, 1)
    assert r.floor == 1
    assert r.load == 0
    assert r.direction == "down"
    assert r.capacity == 10


def test_congestion_ignores_frozen():
    calls = [
        CallRequest(1, 5, "up", 2, status="waiting"),
        CallRequest(2, 5, "up", 3, status="frozen"),
        CallRequest(3, 7, "down", 1, status="frozen"),
    ]
    assert congestion_by_floor(calls) == {5: 2}
