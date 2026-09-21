"""Elevator dispatch: same-direction preference + floor distance; reject if car full.

Fire recall: cars dump load and head to the building recall floor; frozen calls
are refused by dispatch and excluded from congestion.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CarState:
    car_id: int
    floor: int
    direction: str  # "up" | "down" | "idle"
    load: int
    capacity: int


@dataclass(frozen=True)
class CallRequest:
    call_id: int
    floor: int
    direction: str  # desired travel after boarding
    passengers: int = 1
    status: str = "waiting"  # "waiting" | "frozen" | "assigned" | "rejected"


@dataclass(frozen=True)
class ScoreResult:
    car_id: int
    score: float
    accepted: bool
    reason: str


SAME_DIR_BONUS = 40.0
IDLE_BONUS = 20.0
DISTANCE_WEIGHT = 5.0


def score_car(car: CarState, call: CallRequest) -> ScoreResult:
    if call.status == "frozen":
        return ScoreResult(car.car_id, -1e9, False, "呼梯冻结，召回期间拒绝派工")

    if car.load + call.passengers > car.capacity:
        return ScoreResult(car.car_id, -1e9, False, "轿厢满员")

    distance = abs(car.floor - call.floor)
    score = 100.0 - distance * DISTANCE_WEIGHT

    if car.direction == "idle":
        score += IDLE_BONUS
    elif car.direction == call.direction:
        # approaching or already going same way
        if car.direction == "up" and car.floor <= call.floor:
            score += SAME_DIR_BONUS
        elif car.direction == "down" and car.floor >= call.floor:
            score += SAME_DIR_BONUS
        else:
            score -= 15.0  # same dir but already passed
    else:
        score -= 25.0

    return ScoreResult(car.car_id, score, True, "ok")


def pick_car(cars: list[CarState], call: CallRequest) -> ScoreResult | None:
    results = [score_car(c, call) for c in cars]
    accepted = [r for r in results if r.accepted]
    if not accepted:
        return None
    return max(accepted, key=lambda r: r.score)


def recall_direction(car_floor: int, recall_floor: int) -> str:
    """Direction the car must travel to reach the recall floor."""
    if car_floor < recall_floor:
        return "up"
    if car_floor > recall_floor:
        return "down"
    return "idle"


def recall_car_state(car: CarState, recall_floor: int) -> CarState:
    """Car state after fire recall: unloaded, at the recall floor."""
    return CarState(
        car_id=car.car_id,
        floor=recall_floor,
        direction=recall_direction(car.floor, recall_floor),
        load=0,
        capacity=car.capacity,
    )


def congestion_by_floor(calls: list[CallRequest]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for c in calls:
        if c.status != "waiting":
            continue
        counts[c.floor] = counts.get(c.floor, 0) + c.passengers
    return counts
