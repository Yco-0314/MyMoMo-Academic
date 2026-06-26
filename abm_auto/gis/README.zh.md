# abm_auto.gis —— GIS 模式

> 📖 English: [README.md](README.md)

`abm_auto` 的空间智能体建模层。它是**附加且导入隔离**的:GIS 依赖是可选 extra、按需懒加载,基础(非 GIS)安装保持轻量。

```bash
pip install abm-auto[gis]
```

`import abm_auto.gis` 本身不会拉入重依赖;若缺少该 extra,调用 `abm_auto.gis.require_gis()` 会给出清晰报错。

## 包含什么

**空间容器(Spaces)** —— 地理参考、带 CRS 的空间容器:

- `GeoNetwork`(`_geo_network`)—— 由线几何构建的道路/图网络(`GeoNetwork.from_lines(...)`),带节点吸附与最近节点查询。
- `RasterSpace` / `RasterField`(`_raster_space`)—— 地理参考栅格,包裹运行时 `Grid` 提供单元拓扑,并带仿射变换 + CRS + nodata。
- `PolygonSpace`(`_polygon_space`)—— 投影多边形上的稳定区域 ID,STRtree 索引的点-在-多边形与邻接判定。
- `PointSpace`(`_point_space`)—— 投影点云(`PointSpace.from_coords`)。
- `RasterTimeline`(`_temporal`)—— 时间索引的栅格帧序列。

**耦合算子(Coupling operators)**(`_coupling`)—— 组合两个空间层:

- `flood_depth_per_edge` —— 沿每条道路边采样的最大洪水深度。
- `point_risk_per_edge` —— 每条边附近的点计数。
- `polygon_overlap_areas`、`lines_in_polygon` —— 矢量 × 矢量叠加。
- DE-9IM 谓词(`intersects`、`contains`、`within`……)+ STRtree 索引的 `features_intersecting` / `features_containing`。

**平台层(Platform layer)**(`_platform`)—— 极简、Mesa 形态的底座抽象(`GISAgent`、`GISModel`、`AgentSet`、`DataCollector`),不依赖 Mesa。新的空间 ABM 继承 `GISAgent` + `GISModel` 即可,无需手写智能体状态、调度器、收集器和运行循环。确定性:模型上一条带种子的 RNG 链。

**动态模型** —— 建在平台层之上:

- `run_dynamic_congestion_routing`(`_dynamic_congestion`)—— 节点起步的智能体,在道路图上按动态拥堵成本路由并重规划。
- `run_dynamic_flood_evacuation`(`_dynamic_flood`)—— 智能体在时变洪水栅格上疏散,在被淹边搁浅、受阻时重规划。

**空间统计**(`_ops`)—— Moran's I 与 focal 算子。

**代码生成(Codegen)**(`_capabilities`、`_templates`、`_codegen_gate`、`_extractor`)—— 从 spec 生成完整的 `GISAgent`/`GISModel` ABM,由确定性的代码生成保真门把关(对生成代码做结构性检查,绝不采信生成器的一面之词)。每个 capability 把它的渲染参数声明为 schema,因此 extractor 提示会列出合法参数,`GISModelSpec.validate()` 在解析期就拒绝未知 / 类型错 / 越界的取值,而不是静默套用默认值。

**验证(Validation)**(`_spatial_validation`、`_network_validation`、`_observed_raster_bridge`)—— 把仿真栅格与观测栅格比对,并对重叠度 / 质心 / 损失指标设门。

## 设计要点

- **确定性。** 模型用单一带种子的 RNG 链;路由用带稳定 `repr` 键打破平局的确定性 Dijkstra,因此结果不随字典/堆的顺序变化而可复现。
- **导入隔离。** 重的 / 贴近 GDAL 的依赖(`rasterio`、`pyproj`、`geopandas`、`shapely`)只放在 `[gis]` extra 之后,并在用到它们的模块内部懒加载。
- **不改基础引擎。** GIS 代码组合运行时(`abm_auto.runtime`)与标定接缝,不修改它们。
