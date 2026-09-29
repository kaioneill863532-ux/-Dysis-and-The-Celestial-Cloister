# 日落回廊 v0.12 · 在 UE 编辑器里核对“时间 + 日月方向”的实现（UE Python）
#
# 前提：UE 工程里已经有一个 BlueprintFunctionLibrary（C++），名字默认 DysisSkyLibrary，提供下面 4 个静态函数（BlueprintCallable）：
#   float   DysisTimeAt(const FString& Zone, FVector PosCm, bool bNight, float Sticky)   // 人站在 Zone 里、位置 PosCm（UE 厘米）时的时刻 H
#                                                                                         // Sticky = 上一刻的 H；这里传 -999 表示“没有上一刻”：该用 sticky 的地方原样返回 -999（夜里会被夹到 H_TOP）
#   FVector DysisSunDir(float H)       // 太阳方向单位向量，UE 坐标（X 北、Y 东、Z 上）
#   FVector DysisMoonDir(float H)      // 月亮方向
#   FRotator DysisLightRotation(FVector Dir)   // 平行光朝向（光从 Dir 那边射过来）：Pitch = −高度角，Yaw = 方位角 + 180
# 在 UE 的 Python 里它们叫 unreal.DysisSkyLibrary.dysis_time_at(...) 等（自动转成小写下划线）。类名不一样就改下面 LIB。
#
# 用法：工具 → 执行 Python 脚本…，选这个文件（golden_time.json 放在同一个文件夹，或改 GOLDEN）。
# 结果打在输出日志里，另存到 项目/Saved/Dysis_TimeCheck.txt。全部通过才算和灰盒一致。
import unreal, json, math, os

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else ".", "golden_time.json")
LIB = getattr(unreal, "DysisSkyLibrary", None)

lines = []
def log(s): lines.append(s); unreal.log(s)
if LIB is None: raise RuntimeError("找不到 unreal.DysisSkyLibrary：先在 C++ 里写好函数库并编译（或者改脚本里的 LIB）")
g = json.load(open(GOLDEN, encoding="utf-8"))

# 1) 时间：站在哪里 → H
bad = n = 0
for s in g["timeSamples"]:
    pos = s.get("pos")
    if pos is None:   # 光路上的取样只给了高度
        pos = [0.0, 0.0, s.get("y", 0.0) * 100]
    got = LIB.dysis_time_at(s["zone"], unreal.Vector(*pos), bool(s["night"]), -999.0)
    exp = s["H"]; n += 1
    ok = (abs(got - (-999.0)) < 1e-3) if exp == "sticky" else abs(got - exp) < 1e-3
    if not ok:
        bad += 1
        if bad <= 20: log(f"✘ 时间 {s['zone']} night={s['night']} pos={pos}：期望 {exp}，UE {got:.5f}")
log(f"时间取样 {n - bad}/{n} 对")

# 2) 日月方向、平行光朝向
worst_d = worst_r = 0.0
for s in g["sky"]:
    for key, fn in (("sun", LIB.dysis_sun_dir), ("moon", LIB.dysis_moon_dir)):
        v = fn(s["H"]); e = s[key]
        worst_d = max(worst_d, abs(v.x - e["N"]), abs(v.y - e["E"]), abs(v.z - e["U"]))
        r = LIB.dysis_light_rotation(v); ru = s[key + "UE"]
        dy = abs(((r.yaw - ru["yaw"]) % 360 + 540) % 360 - 180)
        worst_r = max(worst_r, abs(r.pitch - ru["pitch"]), dy)
log(f"日月方向 {len(g['sky'])} 个时刻：方向最大偏差 {worst_d:.2e}（要 < 1e-4），光的朝向最大偏差 {worst_r:.4f}°（要 < 0.01°）")

ok = bad == 0 and worst_d < 1e-4 and worst_r < 0.01
log("全部通过" if ok else "没过，看上面带 ✘ 的行")
try:
    out = os.path.join(unreal.Paths.project_saved_dir(), "Dysis_TimeCheck.txt")
    open(out, "w", encoding="utf-8").write("\n".join(lines)); unreal.log(f"报告：{out}")
except Exception as e: unreal.log_warning(str(e))
