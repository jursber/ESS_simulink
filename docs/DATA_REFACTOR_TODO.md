# 数据底层重构 TODO

> 当前轮目标：按业务属性重新划分数据定位维度，修正术语，并为未来真实数据接入留出可信度登记。最后更新：2026-06-07。

## 数据维度口径

- [x] 用户典型负荷：按 `profile` 管理，不按 `region` 管理。
- [x] 中长期持仓/日前持仓：属于交易策略，按 `profile + month/date` 管理，不按 `region` 管理。
- [x] 行政分时电价：按 `province/region + month + business_type` 管理。
- [x] 现货价格：按 `region + month/date` 管理，只保留日前统一出清价和实时统一出清价。
- [x] 光伏出力曲线：按 `region + curve_type` 管理。
- [x] 统调负荷：用于中长期分解曲线，按 `region + month/date` 管理；术语统一为“统调负荷”，避免称“系统负荷”。
- [x] 需量/容量单价：本轮先新增后端数据目录和读取接口，前端入口后续再定。

## 本轮实施项

- [x] 新增 `data/catalog/data_trust.csv`，登记现有核心数据可信度。
- [x] 将 `data/spot_price/202603.csv` 迁移到 `data/spot_price/henan/202603.csv`。
- [x] 将 `data/system_load/202603.csv` 迁移到 `data/dispatch_load/henan/202603.csv`，并在代码/文案中称为“统调负荷”。
- [x] 将 `data/contract_position/202603.csv` 迁移到 `data/trading_strategy/contract_position/mock_henan/202603.csv`。
- [x] 将 `data/dayahead_position/202603.csv` 迁移到 `data/trading_strategy/dayahead_position/mock_henan/202603.csv`。
- [x] 新增 `data/demand_capacity/henan/standard.csv`，保存需量/容量单价基础字段。
- [x] 更新 `DataLoader`：现货价格按 region 定位，用户典型负荷继续全局 profile 定位。
- [x] 更新 `ConfigLoader`：行政分时电价按 region/province 定位；持仓按 trading strategy profile 定位；统调负荷按 region 定位；新增需量/容量单价读取。
- [x] 更新 API 中“统调负荷”相关函数名和返回逻辑。
- [x] 清理前端/旧 Streamlit 页面中的“系统负荷/节点/阻塞”不合理展示文案。
- [x] 更新测试，确保全量测试通过。

## 待讨论项

- [x] 是否彻底删除阻塞成本字段，还是先兼容读取但不纳入计算。结论：当前口径删除，读取层兼容旧列并丢弃。
- [x] 是否移除 `price_node` / `PHYSICAL_NODE`，还是先从 UI 选项中隐藏。结论：从当前模型与 UI 移除。
- [ ] 需量/容量单价后续放在前端哪个参数面板。
