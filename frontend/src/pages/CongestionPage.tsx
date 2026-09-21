import { getCongestion } from "../api/client";
import { usePolling } from "../state/BuildingProvider";

export default function CongestionPage() {
  const rows = usePolling(getCongestion) ?? [];
  const max = Math.max(1, ...rows.map(r => r.passengers));
  return (<>
    <h2>拥堵</h2>
    <table className="table"><thead><tr><th>楼层</th><th>等待人数</th><th></th></tr></thead>
    <tbody>{rows.map(r => <tr key={r.floor}><td className="mono">{r.floor}F</td><td>{r.passengers}</td>
      <td><div className="congestion-bar" style={{ width: `${(r.passengers / max) * 240}px` }} /></td></tr>)}
      {!rows.length && <tr><td colSpan={3}>当前无等待拥堵（召回冻结单不计入）</td></tr>}
    </tbody></table>
  </>);
}
