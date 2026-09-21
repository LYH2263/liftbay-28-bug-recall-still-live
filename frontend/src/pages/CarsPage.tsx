import { useMemo } from "react";
import { useBuildingState } from "../state/BuildingProvider";

export default function CarsPage() {
  const { buildings, cars, calls } = useBuildingState();
  const byId = useMemo(() => new Map(buildings.map((b) => [b.id, b])), [buildings]);
  const building = buildings[0];
  const callFloors = useMemo(
    () => new Set(calls.filter(c => c.status === "waiting").map(c => c.floor)),
    [calls]
  );

  return (<>
    <h2>轿厢井道</h2>
    {building?.recall_active && <div className="recall-banner">消防召回中 · 全部轿厢空载驶至 {building.recall_floor}F</div>}
    <div className="shaft-wrap">
      {cars.map(car => {
        const b = byId.get(car.building_id) ?? building;
        const floors = b?.floors ?? 12;
        const levels = Array.from({ length: floors }, (_, i) => i + 1);
        return (
          <div className="shaft" key={car.id}>
            <h3>{car.label} · {car.load}/{car.capacity}</h3>
            {levels.map(f => (
              <div key={f} className={`floor-slot ${car.floor === f ? "has-car" : ""} ${callFloors.has(f) ? "has-call" : ""}`}>
                {car.floor === f ? car.direction : f}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  </>);
}
