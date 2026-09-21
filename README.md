# LiftBay

电梯派梯：同向优先与楼层距离评分，轿厢满员拒绝派工。支持消防召回。

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4200 |
| API | http://localhost:9200 |
| API 文档 | http://localhost:9200/docs |
| Postgres | localhost:5443 |

健康检查：`GET http://localhost:9200/api/health`

## 页面

- `/buildings` — 楼栋
- `/cars` — 轿厢
- `/calls` — 呼梯
- `/dispatch` — 派工
- `/replay` — 回放
- `/congestion` — 拥堵

## 使用说明

1. 查看楼栋与轿厢状态。
2. 在呼梯页登记请求，在派工页按评分分配轿厢。
3. 回放页查看派工轨迹，拥堵页查看高峰楼层。

## 消防召回

- 楼栋页按「进入召回」一键召回：全部轿厢载荷清零并驶向楼栋召回层（方向为驶向召回层所需方向），全部 waiting 呼梯转为冻结（frozen）。
- 召回期间：派工对冻结单直接拒绝（409），禁止登记新呼梯（409），拥堵统计不计入冻结单。
- 楼栋页按「解除召回」：冻结单恢复为 waiting 可再派，轿厢保持零载荷停在召回层。
- 接口：`POST /api/buildings/{id}/recall`，body `{"active": true|false}`，重复进入/解除为幂等操作。
- 召回与解除事件写入回放（含楼栋级摘要，呼梯列为 `—`）。

> 注意：本次变更新增了 `buildings.recall_floor / recall_active` 列。已有数据卷请重建：`docker compose down -v && docker compose up --build`。

## 开发与测试

```bash
docker compose exec api pytest -q
```
