import { useEffect, useState } from "react";
import { api } from "../api/client";
type B = { id: number; name: string; recall_floor: number; recall_active: boolean };
type Call = { id: number; building_id: number; floor: number; direction: string; passengers: number; status: string; score: string; assigned_car_id: number | null };
export default function DispatchPage() {
  const [rows, setRows] = useState<Call[]>([]);
  const [buildings, setBuildings] = useState<B[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const reload = () => {
    api<Call[]>("/calls").then(setRows);
    api<B[]>("/buildings").then(setBuildings).catch(() => {});
  };
  useEffect(() => {
    reload();
    const t = setInterval(reload, 6000);
    return () => clearInterval(t);
  }, []);
  const recallByBuilding = new Map(buildings.map(b => [b.id, b]));
  const anyRecall = buildings.some(b => b.recall_active);
  async function run(id: number) {
    setMsg(""); setErr("");
    try {
      const c = await api<Call>("/dispatch", { method: "POST", body: JSON.stringify({ call_id: id }) });
      setMsg(`呼梯 #${c.id} → 轿厢 ${c.assigned_car_id}，评分 ${c.score}`);
      reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); reload(); }
  }
  const pending = rows.filter(r => r.status === "waiting" || r.status === "frozen");
  return (<>
    <h2>派工</h2>
    {anyRecall && <div className="recall-banner">消防召回中 · 召回期间禁止派工，冻结单解除后恢复待派</div>}
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>呼梯</th><th>楼层</th><th>方向</th><th>人数</th><th>状态</th><th></th></tr></thead>
    <tbody>{pending.map(c => {
      const b = recallByBuilding.get(c.building_id);
      const frozen = c.status === "frozen" || !!b?.recall_active;
      return <tr key={c.id}><td>#{c.id}</td><td>{c.floor}</td><td>{c.direction}</td><td>{c.passengers}</td>
        <td>{c.status === "frozen" ? <span className="recall-badge">frozen</span> : c.status}</td>
        <td><button onClick={() => run(c.id)} disabled={frozen}>评分派轿厢</button></td></tr>;
    })}
      {!pending.length && <tr><td colSpan={6}>暂无待派呼梯</td></tr>}
    </tbody></table>
  </>);
}
