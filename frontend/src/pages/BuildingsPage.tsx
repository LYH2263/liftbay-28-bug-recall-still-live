import { useEffect, useState } from "react";
import { api } from "../api/client";
type B = { id: number; name: string; floors: number; recall_floor: number; recall_active: boolean };
export default function BuildingsPage() {
  const [rows, setRows] = useState<B[]>([]);
  const [err, setErr] = useState("");
  const reload = () => api<B[]>("/buildings").then(setRows);
  useEffect(() => { reload(); }, []);
  async function toggle(b: B) {
    setErr("");
    try {
      await api(`/buildings/${b.id}/recall`, { method: "POST", body: JSON.stringify({ active: !b.recall_active }) });
      reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>楼栋</h2>
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>名称</th><th>楼层数</th><th>召回层</th><th>消防召回</th><th></th></tr></thead>
    <tbody>{rows.map(b => <tr key={b.id}>
      <td>{b.name}</td><td className="mono">{b.floors}</td><td className="mono">{b.recall_floor}F</td>
      <td>{b.recall_active ? <span className="recall-badge">召回中</span> : <span className="recall-ok">正常</span>}</td>
      <td><button className={b.recall_active ? "btn-release" : "btn-recall"} onClick={() => toggle(b)}>
        {b.recall_active ? "解除召回" : "进入召回"}
      </button></td>
    </tr>)}</tbody></table>
  </>);
}
