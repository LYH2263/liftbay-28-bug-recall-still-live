from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Building, CallTicket, DispatchLog, ElevatorCar
from app.schemas.schemas import (
    BuildingOut,
    CallCreate,
    CallOut,
    CarOut,
    CongestionFloor,
    DispatchRequest,
    LogOut,
    RecallRequest,
)
from app.services.dispatch_engine import (
    CallRequest,
    CarState,
    congestion_by_floor,
    pick_car,
    recall_car_state,
)

api_router = APIRouter()


@api_router.get("/health")
def health():
    return {"status": "ok"}


@api_router.get("/buildings", response_model=list[BuildingOut])
def buildings(db: Session = Depends(get_db)):
    return db.scalars(select(Building).order_by(Building.id)).all()


@api_router.post("/buildings/{building_id}/recall", response_model=BuildingOut)
def set_recall(building_id: int, body: RecallRequest, db: Session = Depends(get_db)):
    b = db.get(Building, building_id)
    if not b:
        raise HTTPException(404, "楼栋不存在")
    if body.active == b.recall_active:
        return b  # 幂等：重复进入/解除不产生副作用
    if body.active:
        waiting = db.scalars(
            select(CallTicket).where(
                CallTicket.building_id == b.id, CallTicket.status == "waiting"
            )
        ).all()
        for t in waiting:
            t.status = "frozen"
            db.add(DispatchLog(call_id=t.id, car_id=None, detail="消防召回：呼梯冻结"))
        car_rows = db.scalars(
            select(ElevatorCar).where(ElevatorCar.building_id == b.id)
        ).all()
        for c in car_rows:
            recalled = recall_car_state(
                CarState(c.id, c.floor, c.direction, c.load, c.capacity), b.recall_floor
            )
            c.floor, c.direction = recalled.floor, recalled.direction
        b.recall_active = True
        db.add(
            DispatchLog(
                call_id=None,
                car_id=None,
                detail=f"消防召回启动：冻结 {len(waiting)} 单，{len(car_rows)} 台轿厢空载驶向 {b.recall_floor}F",
            )
        )
    else:
        frozen = db.scalars(
            select(CallTicket).where(
                CallTicket.building_id == b.id, CallTicket.status == "frozen"
            )
        ).all()
        for t in frozen:
            t.status = "waiting"
            db.add(DispatchLog(call_id=t.id, car_id=None, detail="解除召回：恢复待派"))
        b.recall_active = False
        db.add(
            DispatchLog(
                call_id=None,
                car_id=None,
                detail=f"解除消防召回：恢复 {len(frozen)} 单待派，轿厢留守 {b.recall_floor}F 空载",
            )
        )
    db.commit()
    db.refresh(b)
    return b


@api_router.get("/cars", response_model=list[CarOut])
def cars(db: Session = Depends(get_db)):
    return db.scalars(select(ElevatorCar).order_by(ElevatorCar.id)).all()


@api_router.get("/calls", response_model=list[CallOut])
def calls(db: Session = Depends(get_db)):
    return db.scalars(select(CallTicket).order_by(CallTicket.id.desc())).all()


@api_router.post("/calls", response_model=CallOut)
def create_call(body: CallCreate, db: Session = Depends(get_db)):
    b = db.get(Building, body.building_id)
    if not b:
        raise HTTPException(404, "楼栋不存在")
    if body.floor > b.floors:
        raise HTTPException(400, "楼层超出")
    if body.direction not in ("up", "down"):
        raise HTTPException(400, "方向无效")
    ticket = CallTicket(
        building_id=body.building_id,
        floor=body.floor,
        direction=body.direction,
        passengers=body.passengers,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@api_router.post("/dispatch", response_model=CallOut)
def dispatch(body: DispatchRequest, db: Session = Depends(get_db)):
    ticket = db.get(CallTicket, body.call_id)
    if not ticket:
        raise HTTPException(404, "呼梯不存在")
    if ticket.status not in ("waiting", "frozen"):
        raise HTTPException(400, "呼梯已处理")
    building = db.get(Building, ticket.building_id)
    car_rows = db.scalars(
        select(ElevatorCar).where(ElevatorCar.building_id == ticket.building_id)
    ).all()
    cars = [
        CarState(c.id, c.floor, c.direction, c.load, c.capacity) for c in car_rows
    ]
    call = CallRequest(ticket.id, ticket.floor, ticket.direction, ticket.passengers, ticket.status)
    best = pick_car(cars, call)
    if best is None:
        db.add(DispatchLog(call_id=ticket.id, car_id=None, detail="全部轿厢满员，拒绝派工"))
        ticket.status = "rejected"
        db.commit()
        db.refresh(ticket)
        raise HTTPException(409, "无可用轿厢（满员）")
    car = db.get(ElevatorCar, best.car_id)
    assert car
    ticket.status = "assigned"
    ticket.assigned_car_id = car.id
    ticket.score = f"{best.score:.1f}"
    car.load += ticket.passengers
    car.floor = ticket.floor
    car.direction = ticket.direction
    db.add(
        DispatchLog(
            call_id=ticket.id,
            car_id=car.id,
            detail=f"派予 {car.label}，评分 {best.score:.1f}（同向/距离综合）",
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@api_router.get("/replay", response_model=list[LogOut])
def replay(db: Session = Depends(get_db)):
    return db.scalars(select(DispatchLog).order_by(DispatchLog.id.desc())).all()


@api_router.get("/congestion", response_model=list[CongestionFloor])
def congestion(db: Session = Depends(get_db)):
    open_calls = db.scalars(
        select(CallTicket).where(CallTicket.status.in_(["waiting", "frozen"]))
    ).all()
    counts = congestion_by_floor(
        [CallRequest(c.id, c.floor, c.direction, c.passengers, c.status) for c in open_calls]
    )
    return [
        CongestionFloor(floor=f, passengers=p)
        for f, p in sorted(counts.items(), key=lambda x: -x[1])
    ]
