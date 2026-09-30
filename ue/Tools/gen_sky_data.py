# 从 docs/ue-handoff/golden_time.json 生成 Source/Dysis/Sky/DysisSkyData.generated.h（常数、各层时间线、墙里楼梯、光路高度、月桥点）。
# 数据变了就重跑：python gen_sky_data.py [golden_time.json] [输出的 .h]
# 默认读仓库里的 golden，写到仓库 ue/Source/Dysis/Sky/ 下；再把 ue/Source 同步到 UE 工程（见 ue/README.md）。
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
GOLDEN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "docs", "ue-handoff", "golden_time.json")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "ue", "Source", "Dysis", "Sky", "DysisSkyData.generated.h")

g = json.load(open(GOLDEN, encoding="utf-8"))
c = g["consts"]

def num(x):
    r = repr(float(x))
    return r if ("e" in r or "." in r or "inf" in r or "nan" in r) else r + ".0"

out = []
w = out.append
w("// 自动生成，不要手改。来源：docs/ue-handoff/golden_time.json（%s）。重新生成：python ue/Tools/gen_sky_data.py" % g.get("meta", {}).get("version", "?"))
w("#pragma once")
w("")
w("#include \"CoreMinimal.h\"")
w("")
w("namespace DysisSkyData")
w("{")
w("\t// ───── consts ─────")
for k, v in c.items():
    if isinstance(v, list):
        w("\tinline constexpr double %s[%d] = { %s };" % (k, len(v), ", ".join(num(x) for x in v)))
    else:
        w("\tinline constexpr double %s = %s;" % (k, num(v)))
w("")
w("\t// ───── 每层的时间线：line 沿方位角线性；piece 折线（两头之外保持端点值） ─────")
w("\tstruct FZoneLine { bool bPiece; double Lo, Hi, A0, H0, K; int32 NumPts; double Pts[8][2]; };")
floors = ["L0", "L1", "L2", "L3"]
for part, arr in (("day", "DayZones"), ("night", "NightZones")):
    rows = []
    for fl in floors:
        d = g["zones"][part][fl]
        if d["kind"] == "line":
            rows.append("\t\t{ false, %s, %s, %s, %s, %s, 0, {} },  // %s" % (num(d["lo"]), num(d["hi"]), num(d["a0"]), num(d["h0"]), num(d["k"]), fl))
        else:
            pts = sorted(d["pts"])
            assert len(pts) <= 8
            rows.append("\t\t{ true, %s, %s, 0.0, 0.0, 0.0, %d, { %s } },  // %s" % (num(d["lo"]), num(d["hi"]), len(pts), ", ".join("{ %s, %s }" % (num(a), num(h)) for a, h in pts), fl))
    w("\tinline constexpr FZoneLine %s[4] = {  // %s，下标 = 层号" % (arr, part))
    out.extend(rows)
    w("\t};")
w("")
w("\t// ───── 墙里的两段楼梯 ─────")
w("\tstruct FTunnel { const TCHAR* Id; double ATop, ABot, YTop, YBot, TopDoor, BotDoor; };")
w("\tinline constexpr FTunnel Tunnels[%d] = {" % len(g["tunnels"]))
for t in g["tunnels"]:
    w("\t\t{ TEXT(\"%s\"), %s, %s, %s, %s, %s, %s }," % (t["id"], num(t["aTop"]), num(t["aBot"]), num(t["yTop"]), num(t["yBot"]), num(t["topDoor"]), num(t["botDoor"])))
w("\t};")
w("")
w("\t// ───── 光路上按高度插值：[y0, H0, y1, H1] ─────")
w("\tstruct FBeamTimeY { const TCHAR* Id; double Y0, H0, Y1, H1; };")
w("\tinline constexpr FBeamTimeY BeamTimeY[%d] = {" % len(g["beamTimeY"]))
for k, v in g["beamTimeY"].items():
    w("\t\t{ TEXT(\"%s\"), %s }," % (k, ", ".join(num(x) for x in v)))
w("\t};")
w("")
w("\t// ───── 月桥：沿桥的点（UE 厘米），按最近点的序号插值 ─────")
pts = g["moonBridgePtsUE"]
w("\tinline constexpr int32 NumMoonBridgePts = %d;" % len(pts))
w("\tinline constexpr double MoonBridgePtsUE[%d][3] = {" % len(pts))
for p in pts:
    w("\t\t{ %s }," % ", ".join(num(x) for x in p))
w("\t};")
w("}")
w("")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8-sig", newline="\n").write("\n".join(out))
print("写好了：%s（%d 个常数，%d 段楼梯，%d 条光路，%d 个月桥点）" % (OUT, len(c), len(g["tunnels"]), len(g["beamTimeY"]), len(pts)))
