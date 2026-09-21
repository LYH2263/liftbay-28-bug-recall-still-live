import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  getBuildings,
  getCalls,
  getCars,
  type Building,
  type Call,
  type Car,
} from "../api/client";

const POLL_MS = 6000;

/** 通用轮询：挂载立即拉取，之后每 ms 刷新。返回最近一次数据。 */
export function usePolling<T>(fn: () => Promise<T>, ms = POLL_MS) {
  const [data, setData] = useState<T | null>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  useEffect(() => {
    let alive = true;
    const load = () =>
      fnRef.current()
        .then((v) => {
          if (alive) setData(v);
        })
        .catch(() => {});
    load();
    const t = setInterval(load, ms);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [ms]);
  return data;
}

type BuildingState = {
  buildings: Building[];
  cars: Car[];
  calls: Call[];
  refresh: () => void;
};

const BuildingContext = createContext<BuildingState>({
  buildings: [],
  cars: [],
  calls: [],
  refresh: () => {},
});

export function BuildingProvider({ children }: { children: ReactNode }) {
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [cars, setCars] = useState<Car[]>([]);
  const [calls, setCalls] = useState<Call[]>([]);

  const load = useCallback(() => {
    getBuildings().then(setBuildings).catch(() => {});
    getCars().then(setCars).catch(() => {});
    getCalls().then(setCalls).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [load]);

  return (
    <BuildingContext.Provider value={{ buildings, cars, calls, refresh: load }}>
      {children}
    </BuildingContext.Provider>
  );
}

export function useBuildingState() {
  return useContext(BuildingContext);
}
