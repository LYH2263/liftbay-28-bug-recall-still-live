import { useState } from "react";
import { createCall, STATUS_META } from "../api/client";
import { useBuildingState } from "../state/BuildingProvider";

const DIR_LABEL: Record<string, string> = { up: "上行", down: "下行" };

export default function CallsPage() {
  const { buildings, calls, refresh } = useBuildingState();
  const [bid, setBid] = useState<number | "">("");
  const [floor, setFloor] = useState(5);
  const [dir, setDir] = useState<"up" | "down">("up");
  const [pax, setPax] = useState(1);
  const [err, setErr] = useState("");

  const selectedBid = bid === "" ? buildings[0]?.id : bid;
  const cur = buildings.find((b) => b.id === selectedBid);
  const recallActive = !!cur?.recall_active;

  async function create() {
    if (selectedBid === undefined) return;
    setErr("");
    try {
      await createCall({ building_id: selectedBid, floor, direction: dir, passengers: pax });
      refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  return (<>
    <h2>呼梯</h2>
    <div className="toolbar">
      <select value={selectedBid ?? ""} onChange={e => setBid(Number(e.target.value))}>{buildings.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select>
      <input type="number" value={floor} onChange={e => setFloor(Number(e.target.value))} style={{ width: 72 }} />
      <select value={dir} onChange={e => setDir(e.target.value as "up" | "down")}><option value="up">上行</option><option value="down">下行</option></select>
      <input type="number" value={pax} min={1} onChange={e => setPax(Number(e.target.value))} style={{ width: 64 }} />
      <button onClick={create} disabled={recallActive}>登记呼梯</button>
      {recallActive && <span className="recall-badge">召回中 · 禁止登记（{cur?.recall_floor}F 召回）</span>}
    </div>
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>ID</th><th>楼层</th><th>方向</th><th>人数</th><th>状态</th><th>轿厢</th><th>评分</th></tr></thead>
    <tbody>{calls.map(c => <tr key={c.id}><td>{c.id}</td><td className="mono">{c.floor}</td><td>{DIR_LABEL[c.direction] ?? c.direction}</td><td>{c.passengers}</td>
      <td><span className={STATUS_META[c.status].cls}>{STATUS_META[c.status].label}</span></td>
      <td>{c.assigned_car_id ?? "—"}</td><td className="mono">{c.score || "—"}</td></tr>)}</tbody></table>
  </>);
}
