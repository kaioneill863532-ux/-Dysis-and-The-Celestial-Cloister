# 交接：在 UE 里实现“日月轨道 + 站在哪里决定几点”

给新开的 Claude Code 会话看的。你没有之前那个会话的记忆，所需的东西都在这个仓库里；照这份文档从头做，做完按最后一节回报。

## 你要做的范围

**要做：**
1. 把 v0.12 建筑模型导进 UE，跑核对脚本，确认全部通过。
2. 太阳、月亮在天上的固定轨道：给一个时刻 H，算出太阳和月亮的方向，让平行光朝着它们。
3. “时间由玩家站的位置决定”：玩家在哪层、走到哪个方位角、在墙里楼梯的哪个高度、在屋顶环道的哪里，每帧算出当前时刻 H，再按 H 摆日月。这包括每一层从哪里开始、走到哪里结束、走一米时间走多快。

**不要做（组员来写）：**
- 光柱、光阶、七色光带、影桥等由光产生的东西，以及“照到以后出现可以踩的路”这类效果。
- 机关的动作、材质、特效、UI 和剧情。
- “接住最后一缕光”的判定，也就是什么时候变成夜里。你只需提供一个开关让他们调用。
- 光柱、月石上的时间：你的函数要能接受这些区域名并按规则算出 H，但玩家什么时候站在光柱上，由组员的代码来告诉你。

**不许改的：** 各项常数和规则。以下三处任何一处和你的理解不一致，都以它为准，不要“修正”它；觉得它有问题就写进回报里：
- `golden_time.json`（灰盒导出的标准答案）
- `reference_time.py`
- 灰盒 `prototype/temple/index.html`

## 依据的先后顺序

1. `docs/ue-handoff/reference_time.py`：灰盒时间和日月那部分代码的逐行 Python 翻译，已经和标准答案逐条比对过（7860/7860 条时间取样全对，日月方向最大偏差 5e-7）。**照它写 C++。**
2. `docs/ue-handoff/golden_time.json`：由灰盒同一套代码算出的标准答案，内容包括：
   - 常数、每层的时间线、墙里的两段楼梯
   - 7860 个“站在这里 → 几点”的取样
   - 1201 个时刻的日月方向，以及 UE 平行光的 Pitch/Yaw
3. 灰盒 `prototype/temple/index.html`，可以在浏览器里直接打开玩。相关函数：`skyDir`、`sunDir`、`moonDir`、`lineZone`、`zoneOf`、`timeAt`、`timeAt0`、`crownDay`、`crownNight`、`tunnelTime`、`setTime`、`tick`。
4. `docs/systems.md`、`docs/施工图-v0.12.html`、`models/temple-v0.12/README.md`：用来看设计意图。`docs/ue-spec.*` 是较早的版本，数字和上面几项冲突时以上面为准。

---

## 第 0 步：导入模型并核对

1. 克隆本仓库，分支用 `claude/game-design-explanation-l17xqm`（它就是默认分支）。
2. 找到 `models/temple-v0.12/`，其中：
   - `Dysis_Temple_v0_12.fbx`：建筑，每个构件一个网格，另有 3 块红色方位标记。
   - `Dysis_Kit_v0_12.fbx`：构件库，含外立面 21 种和机关部件。必须和上面那个 FBX 放在同一个文件夹。
   - `ue_import_temple.py`：导入、摆放、核对一步完成。
3. UE 5.x 里打开“Python Editor Script Plugin”。操作路径：编辑 → 插件，打开后重启编辑器。
4. 打开或新建要放神殿的关卡。
5. 把 `ue_import_temple.py` 第 28 行的 `FBX = r"C:/Dysis/Dysis_Temple_v0_12.fbx"` 改成本机的实际路径。改脚本的副本就行，不要把本机路径提交进仓库。
6. 执行这个脚本。有两种方式：
   - 用 UE MCP 的 Python 执行；
   - 在输出日志的 Python 命令行里输入：`exec(open(r"<路径>/ue_import_temple.py", encoding="utf-8").read())`
7. 看结果：
   - 输出日志最后一行应该是 **全部通过**（331/331 项）；完整报告在 `项目/Saved/Dysis_Temple_v0_12_UE核对.txt`。
   - 大纲视图的 `Dysis_Temple_v0_12` 文件夹下应该有 440 个 Actor，其中 184 个可移动、67 个挂了父子关系、4 个不挡东西（水面、瀑布、海、虹桥）。
   - 如果有没通过的项，把报告里带 ✘ 的行原样回报，先不要往下做。
8. 导入后的坐标约定：**+X = 北，+Y = 东，Z 向上，1 m = 100 cm，神殿中心在原点。** 施工图上方位角 az、半径 r、高度 y 的点，在 UE 里是：
   - X = 100·r·cos(az)
   - Y = 100·r·sin(az)
   - Z = 100·y

   反过来：az = atan2(Y, X)（换算成 0–360°），y = Z/100。

## 第 1 步：天空和时间的函数库（C++）

新建 C++ 类 `UDysisSkyLibrary : UBlueprintFunctionLibrary`。函数名和参数必须和下面一样，核对脚本就是按这些名字调用的：

```cpp
// H 是时角（度）；钟点 = 12:00 + H/15
UFUNCTION(BlueprintPure, Category="Dysis|Sky")
static FVector DysisSunDir(float H);            // 太阳方向单位向量，UE 坐标：X=北、Y=东、Z=上
UFUNCTION(BlueprintPure, Category="Dysis|Sky")
static FVector DysisMoonDir(float H);           // 月亮方向（时角比太阳晚 180°）
UFUNCTION(BlueprintPure, Category="Dysis|Sky")
static FRotator DysisLightRotation(FVector Dir);// 平行光朝向：光从 Dir 那边射过来。Pitch = −高度角，Yaw = 方位角 + 180，Roll = 0

// 人踩在 Zone 上、脚底位置是 PosCm（UE 厘米）时的时刻 H。
// Sticky = 上一刻的 H；传 −999 表示“没有上一刻”：规则里该用 sticky 的地方就原样返回 −999。
// bNight = 已经接住最后一缕光（夜里）：最后结果夹在 [H_TOP, H_END]（所以夜里 −999 会变成 H_TOP）。
UFUNCTION(BlueprintCallable, Category="Dysis|Sky")
static float DysisTimeAt(const FString& Zone, FVector PosCm, bool bNight, float Sticky);
```

写法：

- **逐函数照 `reference_time.py` 翻译**，内部一律用 double：`sky_dir`、`LineZone`、`PieceZone`、`crown_day`、`crown_night`、`tunnel`、`moonbr_t`、`time_at`、`_raw`。
  - `az` 从 PosCm 算：atan2(Y, X)，换成度数后取 0–360。
  - `y` = PosCm.Z / 100。
  - 月桥 `moonbr` 在 `moonBridgePtsUE`（厘米）里找离 PosCm 最近的点，用它的序号插值。
- 常数、各层时间线、两段楼梯、`beamTimeY`、`moonBridgePtsUE` 这些数据**不要手抄**。写一个小 Python 脚本，从 `golden_time.json` 读出来生成 `DysisSkyData.generated.h`，并把这个脚本一起提交，以后数据变了重跑它就行。需要的键是：`consts`、`zones.day`、`zones.night`、`tunnels`、`beamTimeY`、`moonBridgePtsUE`。
- 天空公式，LAT = 35°，太阳赤纬 DEC_SUN = −21°，月亮赤纬 DEC_MOON = +20°：
  ```
  E = −cosδ·sinH
  N =  sinδ·cosφ − cosδ·cosH·sinφ
  U =  sinδ·sinφ + cosδ·cosH·cosφ        （φ = LAT；月亮用 H − 180）
  UE 向量 = (N, E, U)
  ```
- `DysisTimeAt` 必须接受的区域名见下表。不认识的名字一律返回 Sticky。

| 区域名 | 白天 | 夜里（再夹到 [H_TOP, H_END]） |
|---|---|---|
| `L0` `L1` `L2` `L3` | 各层白天时间线 `zones.day[层].f(az)` | 各层夜里时间线 `zones.night[层].f(az)`；L0 是折线 |
| `crown` 屋顶环道 | `crown_day(az)` | `crown_night(az)` |
| `tun:TS` `tun:TR` 墙里楼梯 | 按高度在上门、下门两个时刻之间插值 | 同左，用夜里的时间线 |
| `rbridge` 细桥 | H_OC | H_J |
| `ledge` 日之龛前的石沿 | H_M | H_M |
| `moonbr` 月桥 | 按最近点在 MOONBR_H0 → H1 之间插值 | 同左 |
| `rainbow` `sill` 虹桥、窗下石沿 | RELIEF_H | RELIEF_H |
| `wfback` 瀑布后的石沿、女神台座 | L0 时间线在 115.5° 的值 | 同左，用夜里的时间线 |
| `gbridge` `shadowbr` `pav` 半桥、影桥、水亭 | Sticky | H_BR |
| `out` 殿外（地形、台基、岛） | H_I | Sticky |
| `pool` 池底 | Sticky | Sticky |
| `beam:isle` / `beam:oculus` / `beam:mirror` | H_I / H_OC / H_M | 同左 |
| `beam:b1` `b2` `h1` `h2` `h3` | 按 `beamTimeY[id] = [y0, H0, y1, H1]` 用高度线性插值（不夹） | 同左 |

每层时间线是这样工作的：沿方位角均匀变化，在接缝（瀑布，方位角 116°–140°）处断开。
- 白天：顺时针走时间变大。
- 夜里：逆时针走时间变大（k 为负）。
- 接缝里面的点：靠近 140° 那半边取起点值，靠近 116° 那半边取终点值。

## 第 2 步：让天上的日月跟着 H 走

在关卡里放一个 `ADysisSkyActor`（C++ 或蓝图都可以），暴露 `SetTime(float H)`，每次调用时做下面的事：

- **太阳光**：一盏 DirectionalLight，开 Atmosphere Sun Light，Index 0。
- **月光**：再放一盏 DirectionalLight，Index 1。或者学灰盒只用一盏，在日月之间切换。两种都行，但**方向必须精确**。
- 按灰盒 `setTime` 的规则切换和调亮度。颜色和强度的具体数值可以按 UE 的曝光重新调，**但切换的时机和方向不能变**：
  - 太阳高度 alt > −0.8° 时，主光是太阳：
    - 朝向 = `DysisLightRotation(DysisSunDir(H))`
    - k = smoothstep(2, 25, alt)
    - 灰盒亮度 = lerp(2.4, 3.6, k)·smoothstep(−0.8, 1.2, alt)
  - 否则主光是月亮：
    - 朝向 = `DysisLightRotation(DysisMoonDir(H))`
    - 灰盒亮度 = 0.55·smoothstep(0, 7, 月亮高度)·smoothstep(−0.8, −5, alt)
  - 月亮圆盘的不透明度 = smoothstep(−1.5, 1, 月亮高度)·smoothstep(4, −2, alt)。放在月亮方向很远的地方，没有就先用一个简单的发光平面。
  - 星空绕天极转 −H（可选）。
- 如果场景里有 SkyAtmosphere，天色会跟着太阳自己变；不需要再做别的。

## 第 3 步：玩家的时间组件（每帧算 H）

`UDysisTimeComponent`（ActorComponent）挂在玩家 Character 上，Tick Group 用 PostPhysics，保证 CharacterMovement 已经更新过脚下的地面。它的状态和接口：

- 状态：
  - `float H`：当前时刻，开始时是 H_I，也就是岛上的 13:29。
  - `float Sticky`：上一刻的 H。
  - `bool bNight`
  - `FString Zone`：脚下的区域。
- 给组员用的接口：
  - `SetNight(bool)`：变成夜里的那一刻，令 Sticky = H，同灰盒 `catchLight`。
  - `SetForcedTime(float)` / `ClearForcedTime()`：过场时强制钉住时刻，同灰盒 `state.forceH`。
  - `SetZoneOverride(FString)` / `ClearZoneOverride()`：组员的光柱、月石站上去时告诉你区域名，例如 `beam:b1`。
  - 事件 `OnTimeChanged(float H)`：组员的光、机关可以订阅。

**每帧按灰盒 `tick` 的做法：**

```
如果有强制时刻：H = 强制值
否则如果在地上（CharacterMovement->IsMovingOnGround()）：
    Zone = ZoneOverride 非空 ? ZoneOverride : 区域判定(CurrentFloor.HitResult 的 Actor, 脚底位置)
    H = DysisTimeAt(Zone, 脚底位置, bNight, Sticky)
否则（跳起、下落）：H = Sticky
Sticky = H
SkyActor->SetTime(H)
```

- **脚底位置** = Actor 位置 − (0, 0, 胶囊半高)。灰盒里的位置就是脚底；拿胶囊中心去算，楼梯和高度判定都会错。
- 没有平滑，也没有插值：站到哪里就是那一刻。灰盒就是这样做的，跨层时天会“跳”，这是设计。

**区域判定：** Actor 的标签（label）只在编辑器里有，打包后就没了。所以写一个编辑器 Python 脚本，按下表给每个 Actor 加一个 Tag `DysisZone=<区域名>`。游戏里读 Tag；没有 Tag 的 Actor 按高度兜底。

| Actor（大纲里的名字） | 区域 |
|---|---|
| `SM_Floor_L0`、`SM_Sluice_Platform`、`SM_Seam_Stone_116`、`SM_Seam_Stone_140` | `L0` |
| `SM_Floor_L1`、`SM_Mech_Twins_*`（双子所在的厚墙龛） | `L1` |
| `SM_Floor_L2`、`SM_Mech_Mirror_Plinth` | `L2` |
| `SM_Floor_L3`、`SM_Mech_Swan_Plinth` | `L3` |
| `SM_PoolBed` | `pool` |
| `SM_SunNiche_Ledge` | `ledge` |
| `SM_Waterfall_BackLedge`、`SM_Mech_Goddess_Plinth` | `wfback` |
| `SM_Terrain`、`SM_Podium`、`SM_Island`、`SM_Portico_Steps` | `out` |
| `SM_Roof_Fix01`–`05`、`SM_Roof_Land`、`SM_Roof_SeamOuter`、`SM_Mech_RoofSteps_*`、`SM_Mech_IrisBlades_*` | `crown` |
| `SM_RoofBridge` | `rbridge` |
| `SM_Pavilion`、`SM_Mech_Armillary_Pavilion` | `pav` |
| `SM_Mech_MoonBridge_Deck` | `moonbr` |
| `SM_Mech_Sill_Ledge`、`SM_Mech_Sill_Niche` | `sill` |
| `SM_Mech_HalfBridge_Deck` | `gbridge` |
| `SM_Mech_RainbowBridge_Light` | `rainbow` |
| `SM_Wall`（墙里的楼梯踏步在墙体网格里） | 见下 |

- **`SM_Wall`（墙里的两段楼梯）**：
  - 脚底半径 r = √(X²+Y²)/100 在 15.5–16.8 之间时，才算在墙里的楼梯上（踏步在 15.8–16.8，两头门口的门槛在 15.5–15.8，灰盒里这两部分都算楼梯）：
    - 方位角在 250°–330° → `tun:TS`（三层 ↔ 四层，y 14.5–23）
    - 方位角在 105°–185° → `tun:TR`（二层 ↔ 三层，y 6–14.5）
  - 其他位置按下面的高度兜底。
- **高度兜底**（灰盒 `zoneOf` 的最后几行）。y 是脚底高度（米），从上往下依次判断：
  - y > 30.0 → `crown`
  - y ≥ 22.7 → `L3`
  - y ≥ 14.2 → `L2`
  - y ≥ 5.7 → `L1`
  - y > −1 → `L0`
  - 否则 → `out`

  柱子、栏杆这些没有标签的构件都按这条走。

## 设计上日月怎么走（给你理解，数字以 golden 为准）

**整体走向：**
- 白天从 13:11 左右（一层入口附近）走到 16:45（屋顶接住最后一缕光）。太阳在西南，越往上越低。
- 接住以后是夜里：从 16:45 起，经屋顶、四层、三层、二层、一层，到 01:03。月亮从东边升起，最后越过头顶到西南。

**每层怎么走**（沿回廊半径 13.8 m，从 140° 顺时针绕一圈到 116°）：

| | 层 | H 起 → 止 | 每度 | 每米 | 天体 起 → 止（方位/高度） |
|---|---|---|---|---|---|
| 日 | L0 | 16.50 → 24.63 | +0.0242 | +0.1005 | 太阳 198.2°/31.8° → 206.5°/29.3° |
| 日 | L1 | 24.14 → 31.91 | +0.0231 | +0.0960 | 太阳 206.0°/29.5° → 213.4°/26.3° |
| 日 | L2 | 27.73 → 33.24 | +0.0164 | +0.0680 | 太阳 209.5°/28.1° → 214.6°/25.7° |
| 日 | L3 | 35.61 → 37.67 | +0.0061 | +0.0254 | 太阳 216.7°/24.6° → 218.5°/23.6° |
| 夜 | L0 | 195.65 → 163.60 | 折线 | — | 月亮 226.7°/69.6° → 131.8°/69.2° |
| 夜 | L1 | 151.96 → 127.77 | −0.0720 | −0.2989 | 月亮 113.9°/61.1° → 93.8°/41.9° |
| 夜 | L2 | 128.66 → 121.22 | −0.0221 | −0.0919 | 月亮 94.4°/42.6° → 89.9°/36.5° |
| 夜 | L3 | 114.18 → 80.50 | −0.1003 | −0.4162 | 月亮 86.0°/30.8° → 68.3°/4.0° |

- 夜里是逆时针走的，表里“起 → 止”仍按顺时针列出，所以数值是变小的。
- H 每变 1，相当于 4 分钟。

**屋顶环道：**
- 白天：从细桥落脚点 J（218.08°）顺时针走到接光台（27.83°），H 从 H_OC 37.19 升到 H_TOP 71.36。
- 夜里：从接光台逆时针回到 J，H 从 71.36 到 76；再沿降下的楼梯走到四层（101°），H 从 76 到 82。

**关键时刻**（golden 的 `keys`）：

| 时刻 | 天体 | H | 钟点 | 方位/高度 |
|---|---|---|---|---|
| 序 · 岛上 | 太阳 | 22.37 | 13:29 | 204.25° / 30.11° |
| 日1 · 到二层 | 太阳 | 24.6 | 13:38 | 206.47° / 29.33° |
| 日2 · 到三层 | 太阳 | 29.6 | 13:58 | 211.28° / 27.35° |
| 日3 · 镜光 / 日之龛 | 太阳 | 33.5 | 14:14 | 214.85° / 25.60° |
| 日4 · 圆眼光柱 | 太阳 | 37.19 | 14:29 | 218.08° / 23.81° |
| 日5 · 接住最后一缕光 | 太阳 | 71.36 | 16:45 | 242.29° / 2.22° |
| 月1 · 到四层 | 月亮 | 82 | 17:28 | 69.11° / 5.11° |
| 月2 · 天鹅 | 月亮 | 102.18 | 18:49 | 79.73° / 21.01° |
| 月3 · 月亮浮雕 | 月亮 | 125.43 | 20:22 | 92.41° / 39.97° |
| 月4 · 双子合拢 / 月桥 | 月亮 | 144 | 21:36 | 105.76° / 54.98° |
| 月5 · 女神怀里的月亮 | 月亮 | 160.6 | 22:42 | 126.16° / 67.25° |
| 结束 | 月亮 | 195.65 | 01:03 | 226.71° / 69.62° |

## 第 4 步：测试（两项都要过）

**A. 函数库对标准答案**
- 把 `docs/ue-handoff/ue_verify_time.py` 和 `golden_time.json` 放在同一个文件夹，在 UE 编辑器里执行这个脚本。
- 输出日志最后一行必须是 **全部通过**：
  - 7860 个时间取样误差都 < 1e-3；
  - 1201 个时刻的日月方向偏差 < 1e-4；
  - 平行光朝向偏差 < 0.01°。
- 报告在 `Saved/Dysis_TimeCheck.txt`。
- 这个脚本已经用 `reference_time.py` 冒充 UE 跑过，全部通过，所以如果它报错，问题在你的 C++。

**B. 在 PIE 里真的站上去**
- `docs/ue-handoff/pie_spots.json` 列了 27 个点。每个点给出：
  - 位置（施工图的 az/r/y，以及 UE 厘米坐标）
  - 期望的区域和 H
  - 该由太阳还是月亮当主光
  - 平行光的 Pitch/Yaw
- 做法：
  1. 写一个控制台命令，例如 `Dysis.Go <X> <Y> <Z> [night]`：把玩家传送到那里（脚底对准，站稳一帧），打印 区域、H、主光、Pitch、Yaw。
  2. 用 Python 或自动化测试把 27 个点都跑一遍，和 json 比对。容差：H 1e-3，角度 0.01°。
  3. 每层各截一张图，接光前后各截一张，存到 `Saved/Screenshots/Dysis/`。
- 另外手动走一遍：一层顺时针走，看太阳平稳地往西偏低；跳起来时天不动；进墙里楼梯，边爬边变。

## 回报

- 提交到本分支 `claude/game-design-explanation-l17xqm`：C++ 源码、生成数据头文件的脚本、打 Tag 的编辑器脚本、测试脚本。提交说明写清楚做了什么。
  - UE 工程如果不在这个仓库里，就只提交代码和脚本，放到 `ue/` 目录下，并写明它们在 UE 工程里应放的位置。
- 回报给用户：
  - 两份核对报告的最后几行
  - 27 个点的比对结果
  - 截图位置
  - 有没有和灰盒对不上的地方，以及你是怎么处理的（原则是不改规则，只报告）
