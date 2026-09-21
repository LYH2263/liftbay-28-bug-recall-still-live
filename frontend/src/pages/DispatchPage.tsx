import { useState } from "react";
import { dispatchCall, STATUS_META } from "../api/client";
import { useBuildingState } from "../state/BuildingProvider";

const DIR_LABEL: Record<string, string> = { up: "上行", down: "下行" };

export default function DispatchPage() {
  const { buildings, calls, refresh } = useBuildingState();
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const recallByBuilding = new Map(buildings.map((b) => [b.id, b.recall_active]));
  const anyRecall = buildings.some((b) => b.recall_active);
  const waiting = calls.filter((c) => c.status === "waiting");
  const frozen = calls.filter((c) => c.status === "frozen");

  async function run(id: number) {
    setMsg(""); setErr("");
    try {
      const c = await dispatchCall(id);
      setMsg(`呼梯 #${c.id} → 轿厢 ${c.assigned_car_id}，评分 ${c.score}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
    refresh();
  }

  return (<>
    <h2>派工</h2>
    {anyRecall && <div className="recall-banner">消防召回中 · 呼梯冻结，禁止派工；解除召回后恢复待派</div>}
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>呼梯</th><th>楼层</th><th>方向</th><th>人数</th><th></th></tr></thead>
    <tbody>{waiting.map(c => {
      const blocked = !!recallByBuilding.get(c.building_id);
      return <tr key={c.id}><td>#{c.id}</td><td>{c.floor}</td><td>{DIR_LABEL[c.direction] ?? c.direction}</td><td>{c.passengers}</td>
        <td><button onClick={() => run(c.id)} disabled={blocked} title={blocked ? "召回中禁止派工" : ""}>评分派轿厢</button></td></tr>;
    })}
      {!waiting.length && <tr><td colSpan={5}>暂无待派呼梯</td></tr>}
    </tbody></table>

    {frozen.length > 0 && (
      <>
        <h3 style={{ marginTop: "1.2rem" }}>召回冻结（{frozen.length} 单，不计入拥堵）</h3>
        <table className="table"><thead><tr><th>呼梯</th><th>楼层</th><th>方向</th><th>人数</th><th>状态</th></tr></thead>
          <tbody>{frozen.map(c => <tr key={c.id}><td>#{c.id}</td><td>{c.floor}</td><td>{DIR_LABEL[c.direction] ?? c.direction}</td><td>{c.passengers}</td>
            <td><span className={STATUS_META.frozen.cls}>{STATUS_META.frozen.label}</span></td></tr>)}</tbody></table>
      </>
    )}
  </>);
}
