# UE 实现：日月轨道 + “站在哪里决定几点”

按 `docs/ue-handoff/README.md` 做的 UE 5.8 部分。UE 工程不在这个仓库里，这里只放代码和脚本；下表是它们在 UE 工程（`<工程>` = 有 `Dysis.uproject` 的那个文件夹）里的位置。

| 仓库里 | 放到 UE 工程里 | 是什么 |
|---|---|---|
| `ue/Source/Dysis/Sky/DysisSkyLibrary.h/.cpp` | `<工程>/Source/Dysis/Sky/` | `UDysisSkyLibrary`：日月方向、平行光朝向、`DysisTimeAt`、`DysisZoneOf`（逐函数照 `reference_time.py`） |
| `ue/Source/Dysis/Sky/DysisSkyData.generated.h` | 同上 | 常数、各层时间线、墙里楼梯、光路高度、月桥点。**由脚本生成，不要手改** |
| `ue/Source/Dysis/Sky/DysisSkyActor.h/.cpp` | 同上 | `ADysisSkyActor`：太阳光（Atmosphere Sun Light 0）+ 月光（1）+ 月亮圆盘，`SetTime(H)` |
| `ue/Source/Dysis/Sky/DysisTimeComponent.h/.cpp` | 同上 | `UDysisTimeComponent`：挂在玩家身上，每帧算 H；控制台 `Dysis.Go`、`Dysis.Where` |
| `ue/Source/Dysis/Player/DysisCharacter.h/.cpp`、`DysisGameMode.h/.cpp` | `<工程>/Source/Dysis/Player/` | 测试用的第一人称玩家（WASD、鼠标、空格跳、Shift 跑）和 GameMode。组员有自己的 Character 就不用它，把 `UDysisTimeComponent` 加过去即可 |
| `ue/Tools/gen_sky_data.py` | 不用放 | 从 `docs/ue-handoff/golden_time.json` 生成 `DysisSkyData.generated.h` |
| `ue/Tools/ue_run.py` | 不用放 | 从编辑器外面把 Python 发进编辑器执行（要开 Python 的 Remote Execution） |
| `ue/Scripts/dysis_tag_zones.py` | 编辑器里执行 | 按交接文档第 3 步的表给 Actor 打 Tag `DysisZone=<区域名>` |
| `ue/Scripts/dysis_setup_sky.py` | 编辑器里执行 | 建月亮圆盘材质，摆 DysisSky、SkyAtmosphere、SkyLight、HeightFog、PlayerStart，关卡 GameMode 设成 DysisGameMode |
| `ue/Tests/dysis_pie_spots.py` | 编辑器里执行 | PIE 里站上 `pie_spots.json` 的 27 个点，比对并截图 |
| `ue/Tests/dysis_pie_walk.py` | 编辑器里执行 | PIE 里真的走：一层顺时针一圈、边走边跳、两段墙里楼梯 |
| `ue/Reports/` | — | 这次跑出来的四份报告 |

`<工程>/Source/Dysis/Dysis.Build.cs` 里要有 `EnhancedInput`（模板自带），再加一行：

```csharp
PublicIncludePaths.Add(ModuleDirectory);   // Source/Dysis 下的子文件夹按 "Sky/xxx.h" 引用
```

## 从头做一遍的顺序

1. 数据变了先重跑 `python ue/Tools/gen_sky_data.py`，再把 `ue/Source/Dysis` 整个复制到 `<工程>/Source/Dysis`，关掉编辑器编译（`Build.bat DysisEditor Win64 Development -Project=<工程>/Dysis.uproject`）。
2. 新建一个普通关卡（不用 World Partition），我用的是 `/Game/Dysis/Maps/Dysis_Temple`。
3. 跑 `models/temple-v0.12/ue_import_temple.py`（本机副本里改 FBX 路径）→ 要 **全部通过**（331/331）。
4. 跑 `ue/Scripts/dysis_tag_zones.py` → 保存关卡。
5. 跑 `ue/Scripts/dysis_setup_sky.py` → **单独再保存一次关卡**（别在同一个脚本里摆完马上存，见下面“注意”）。
6. 测试 A：`docs/ue-handoff/ue_verify_time.py`（和 `golden_time.json` 放一起，直接在 docs 里跑就行）。
7. 测试 B：`ue/Tests/dysis_pie_spots.py`、`ue/Tests/dysis_pie_walk.py`。它们挂在编辑器 tick 上自己跑完、自己关 PIE，报告写到 `<工程>/Saved/`。
   编辑器不在前台时 UE 会把 PIE 降到几帧每秒，先在 编辑器偏好 → 性能 里关掉“处于后台时占用较少 CPU”，跑完再打开。

## 给组员的接口

**`UDysisTimeComponent`**（挂在玩家 Character 上，Tick Group = PostPhysics）

| | |
|---|---|
| `H`、`Sticky`、`bNight`、`Zone`、`FootCm` | 当前时刻、上一刻、是不是夜里、脚下区域、算时间用的脚底位置（只读） |
| `SetNight(bool)` | 接住最后一缕光的那一刻调用：`Sticky = H`（同灰盒 `catchLight`） |
| `SetForcedTime(H)` / `ClearForcedTime()` | 过场钉住时刻（同灰盒 `state.forceH`） |
| `SetZoneOverride("beam:b1")` / `ClearZoneOverride()` | 光柱、月石、影桥、虹桥这些“光做的路”站上去时告诉组件区域名 |
| `OnTimeChanged(H)` | H 变了就广播 |
| `SkyActor` | 要摆的天；不填就找关卡里第一个 `ADysisSkyActor` |
| `bFootOnFloorSurface` | 默认开：脚底高度取竖直往下打到的面（见“和交接文档不一样的地方”第 1 条） |

**`UDysisSkyLibrary`**（蓝图里在 Dysis|Sky 下）：`DysisSunDir(H)`、`DysisMoonDir(H)`、`DysisLightRotation(Dir)`、`DysisTimeAt(Zone, PosCm, bNight, Sticky)`、
`DysisZoneOf(Ground, FootCm)`、`DysisAzAlt(Dir)`、`DysisClockHours(H)`、`DysisConst("H_TOP")`（灰盒常数按名字取）。

**`ADysisSkyActor`**：`SetTime(H)`、`IsSunMain()`、`GetMainLightRotation()`、`GetSunDir()`、`GetMoonDir()`、`GetAltitudes()`、`GetMoonDiscOpacity()`；
`PreviewH` 在编辑器里直接拖就能看某个时刻的天；`SunLuxPerGreyboxUnit`、`MoonLuxPerGreyboxUnit`、颜色是给美术按 UE 曝光调的（切换时机和方向是写死的规则）。

**控制台（PIE 里）**：`Dysis.Go <X> <Y> <Z> [night]` 把脚底传送到 UE 厘米坐标，站稳后打印区域、H、钟点、主光、Pitch/Yaw；`Dysis.Where` 打印当前状态。

## 实现说明

- 所有计算用 double；`DysisTimeAt` 按交接文档用 float 进出（H 最大 ~200，float 误差 ~1e-5，远小于 1e-3）。
- 天：两盏平行光各自一直朝着自己的天体（太阳 / 月亮）。太阳高度 > −0.8° 时太阳是主光、月光强度 0；否则反过来。亮度按灰盒公式，再乘换算系数。
- 月亮圆盘是一个无光照半透明的球，放在月亮方向 4 km 处，角直径 1.36°（和灰盒 8000 远、半径 95 一样）；不透明度按灰盒公式。星空没做（可选）。
- 区域：读 Actor 的 Tag `DysisZone=<区域名>`；`SM_Wall` 的 Tag 是 `wall`，脚底半径 15.5–16.8 m 时按方位角分出 `tun:TS`（250°–330°）/ `tun:TR`（105°–185°）；没有 Tag 的按脚底高度兜底（灰盒 `zoneOf`）。
- 每帧：强制时刻 > 在地上按脚下算 > 空中保持 `Sticky`；没有平滑。

## 和交接文档 / 灰盒不一样、或者要注意的地方（规则一条没改）

1. **脚底高度**：交接文档写“Actor 位置 − 胶囊半高”。这样在楼梯上会错：CharacterMovement 让胶囊悬在地上 ~2 cm，而且胶囊（半径 35 cm）压在上一级踏步的边上，胶囊底落在两级踏面之间（实测 18.779，而正下方的踏面是 18.75）。灰盒的脚底是 `probe` 竖直往下打到的面，所以组件改成从脚上 0.4 m 竖直往下打一条射线，取正下方的面（打不到才用“胶囊底 − 离地距离”）。区域仍按交接文档用 `CurrentFloor` 的 Actor。
2. **强制时刻**：按交接文档的伪代码放在最前面（空中也生效）。灰盒里 `forceH` 在 `timeAt` 里，只在站在地上时生效，空中用 `sticky`。只有“过场时人在空中”才有区别。
3. **不认识的区域名**：交接文档说“一律返回 Sticky”；`reference_time.py` 在夜里还会再夹到 [H_TOP, H_END]。按 reference 做（ue_verify_time 也是这么比的）。`tun:` 后面跟不认识的楼梯名，reference 会抛 KeyError，C++ 返回 Sticky。
4. **屋顶升降踏步**（`SM_Mech_RoofSteps_Up*`）是按**升起**的姿态导入的（第 1 级 30.75 → 最高一级 ~38 m，见机关清单的轴心列）。`pie_spots.json` 里屋顶的点高度都是 30.3，站过去会掉到四层。环道的时间只看方位角，所以测试脚本对 `crown` 的点改成站到那个 XY 上真实的踏面。踏步怎么升降是机关的事，这里没动。
5. `pie_spots.json` 里有几个点正好在东西上，站不上去，会被推开：
   - 11 / 26（`tun:TR`，145°，y 10.25）：145° 那里的踏面是 10.82–11.10 m，10.25 的那一级在 140.6°（导入核对里每片踏面都和 Blender 对上了）。楼梯两头有平台，中间比“按方位角线性”陡，这个点在台阶里面。人被推到 142.5° 的 10.53 那一级，H 按实际脚底算是对的，但和 json 差 0.115。
   - 19（L2 夜，285°）：镜子的台座和雕像正好在这里，人站到台座上，方位角变了 2.8°，H 差 0.061。
   - 17、18（L3 90°、300°）、23（L0 30°）是柱子，21（L1 255°）是双子雕像，24（L0 100°）是水闸平台：被推开的方向是径向或者正好在平的那段，H 没变，都过了。
6. **虹桥** `SM_Mech_RainbowBridge_Light` 是不挡东西的（导入脚本设的 NoCollision），站不上去，`rainbow` 区域只能由组员用 `SetZoneOverride` 给；`shadowbr`（影桥）没有网格，同样。
7. **夜里的亮度**：UE 的自动曝光会把月光下的殿内提得和白天差不多亮（见截图 20）。方向和切换时机是对的；夜里要多暗请美术调 `MoonLuxPerGreyboxUnit` 或给关卡加 PostProcessVolume 限制曝光范围。
8. 三块红色方位标记（`SM_MARK_*`）还在关卡里（导入脚本 `KEEP_MARKERS = True`），不要可以删。
9. 观察（按规则就是这样，只是提一下）：白天从一层走 TR 上二层，时间是往回走的（31.81 → 28.37，因为 TR 下门在一层时间线的尾巴 112°，上门在二层时间线的前段 178.7°）；TS 从二层上三层是往前的（30.71 → 36.34）。golden 的楼梯取样也是这样。
10. UE 5.8.2 的 Python 在“两个编辑器同时开着同一个工程”时存盘崩过一次（调用栈全在 python311 / PythonScriptPlugin 里）。只开一个编辑器，摆完天以后单独再存一次，就没再出现。