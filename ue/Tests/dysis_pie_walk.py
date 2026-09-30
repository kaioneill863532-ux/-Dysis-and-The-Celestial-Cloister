# 日落回廊 v0.12 · PIE 里“手动”走一遍（UE 编辑器 Python，用 AddMovementInput 真的走，不是传送）
#
#   1. 一层顺时针绕回廊走一圈（142° → 112°，半径 14.7 m，避开 13.8 m 上的柱子）：H 应该一路变大、和 reference 一致，
#      太阳一路往西（方位角变大）、变低（高度角变小）。
#   2. 边走边跳：离地的每一帧 H 都等于起跳那一刻的 H；落地后才跳到新位置的时刻。
#   3. 墙里楼梯：TS 从三层门口往下走到二层，TR 从一层门口往上走到二层（半径 16.3 m）：H 随脚底高度连续变化，
#      每一帧和 reference 的 tunnel(y) 一致。
# 结果：项目/Saved/Dysis_PieWalk.txt
import unreal, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else "."
GOLDEN_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "ue-handoff"))
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
sys.path.insert(0, GOLDEN_DIR)
import reference_time as ref
REF = ref.DysisTime(json.load(open(os.path.join(GOLDEN_DIR, "golden_time.json"), encoding="utf-8")))

def azr(v): return math.degrees(math.atan2(v.y, v.x)) % 360, math.hypot(v.x, v.y) / 100
def unwrap(a, a0): return a if a >= a0 else a + 360   # 顺时针走过 360° 的方位角展开

def surface_z(w, x, y, z0, z1, ignore):
    hit = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x, y, z0), unreal.Vector(x, y, z1), unreal.TraceTypeQuery.ECC_VISIBILITY,
                                                 True, ignore, unreal.DrawDebugTrace.NONE, True)
    if not hit: return None
    p = next((v for v in hit.to_tuple() if hasattr(v, "z")), None)
    return p.z if p else None

# 每一段：起点（az, r, 找踏面的高度范围）、沿半径 r 顺时针走、什么时候停、要检查什么
LEGS = [
    dict(name="一层顺时针一圈", az0=142.0, r=14.7, zrange=(150, -50), stop=lambda az, y: unwrap(az, 141) >= 360 + 112, zone="L0", maxf=4000, jump_every=0),
    dict(name="一层边走边跳", az0=200.0, r=14.7, zrange=(150, -50), stop=lambda az, y: unwrap(az, 199) >= 250, zone="L0", maxf=1500, jump_every=40),
    dict(name="墙里楼梯 TS 三层→二层（往下）", az0=262.0, r=16.3, zrange=(2400, 2100), stop=lambda az, y: az >= 321.0 or y <= 14.52, zone="tun:TS", maxf=3000, jump_every=0),
    dict(name="墙里楼梯 TR 一层→二层（往上）", az0=113.5, r=16.3, zrange=(700, 500), stop=lambda az, y: az >= 178.0 or y >= 14.48, zone="tun:TR", maxf=3000, jump_every=0),
]

# 编辑器不在前台时 UE 会把 PIE 降到几帧每秒（编辑器偏好 → 性能 → “处于后台时占用较少 CPU”）。测试期间关掉，跑完恢复原样。
# UE 5.8 的 Python 读不到这个位域属性；读不到就提醒一下，由人（或 MCP 的 ConfigSettings 工具）先在偏好设置里关掉。
try:
    _perf = unreal.find_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    _throttle0 = _perf.get_editor_property("throttle_cpu_when_not_foreground")
except Exception:
    _perf = _throttle0 = None
    unreal.log_warning("读不到“处于后台时占用较少 CPU”设置；编辑器不在前台时 PIE 会很慢，建议先在 编辑器偏好 → 性能 里关掉")
def _throttle(on):
    if _perf is None or on is None: return
    try: _perf.set_editor_property("throttle_cpu_when_not_foreground", on)
    except Exception as e: unreal.log_warning("没改成后台降频设置：%r" % e)

class Walk:
    def __init__(self):
        self.phase, self.leg, self.f, self.wait, self.handle, self.log, self.frames = "begin", 0, 0, 0, None, [], 0
    def w(self): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    def tick(self, dt):
        try: self.step()
        except Exception as e:
            unreal.log_error("走一遍出错：%r" % e); self.log.append("出错：%r" % e); self.finish()
    def step(self):
        self.frames += 1
        if self.frames > 30000: raise RuntimeError("超时")
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if self.phase == "begin":
            _throttle(False); les.editor_request_begin_play(); self.phase = "wait_pie"; return
        w = self.w()
        if self.phase == "wait_pie":
            if w is None: return
            pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
            if pawn is None: return
            self.pawn = pawn; self.pc = unreal.GameplayStatics.get_player_controller(w, 0)
            self.comp = pawn.get_component_by_class(unreal.DysisTimeComponent)
            self.sky = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DysisSkyActor)[0]
            self.phase, self.wait = "warm", 0; return
        if self.phase == "warm":
            self.wait += 1
            if self.wait > 30: self.phase = "leg_start"
            return
        if self.phase == "leg_start":
            if self.leg >= len(LEGS): self.finish(); return
            L = LEGS[self.leg]; a = math.radians(L["az0"])
            x, y = 100 * L["r"] * math.cos(a), 100 * L["r"] * math.sin(a)
            z = surface_z(w, x, y, L["zrange"][0], L["zrange"][1], [self.pawn])
            if z is None: raise RuntimeError("%s：起点 (%.0f, %.0f) 下面没有踏面" % (L["name"], x, y))
            self.comp.debug_teleport_feet(unreal.Vector(x, y, z), False, 1)
            self.rec, self.f, self.wait = [], 0, 0; self.phase = "leg_settle"; return
        if self.phase == "leg_settle":
            self.wait += 1
            if self.wait < 15: return
            self.phase = "leg_walk"; return
        if self.phase == "leg_walk":
            L = LEGS[self.leg]; self.f += 1
            loc = self.pawn.get_actor_location(); az, r = azr(loc)
            foot = self.comp.get_editor_property("foot_cm")
            ground = self.comp.is_on_ground()
            sun = self.sky.get_sun_dir(); s_az, s_alt = ref.az_alt((sun.y, sun.x, sun.z))
            self.rec.append(dict(f=self.f, az=az, r=r, y=foot.z / 100, H=self.comp.get_editor_property("h"), zone=self.comp.get_editor_property("zone"),
                                 ground=ground, sun_az=s_az, sun_alt=s_alt, fx=foot.x, fy=foot.y, fz=foot.z))
            if L["stop"](az, foot.z / 100) and ground and self.f > 20 or self.f >= L["maxf"]:
                self.summarize(L); self.leg += 1; self.phase = "leg_start"; return
            a = math.radians(az)
            t = unreal.Vector(-math.sin(a), math.cos(a), 0)             # 顺时针（方位角变大）的切线
            rad = unreal.Vector(math.cos(a), math.sin(a), 0)
            k = max(-1.0, min(1.0, (L["r"] - r) * 1.5))                  # 拉回到半径 r
            d = unreal.Vector(t.x + rad.x * k, t.y + rad.y * k, 0)
            self.pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=math.degrees(math.atan2(d.y, d.x))))
            self.pawn.add_movement_input(d, 1.0, False)
            if L["jump_every"] and self.f % L["jump_every"] == 0 and ground: self.pawn.jump()
    def summarize(self, L):
        rec = [x for x in self.rec if x["f"] > 3]
        g = [x for x in rec if x["ground"]]
        name = L["name"]; out = ["── %s：%d 帧（站在地上 %d 帧）" % (name, len(rec), len(g))]
        if not g: self.log += out + ["  ✘ 一直不在地上"]; return
        zones = sorted(set(x["zone"] for x in g))
        worst, bad = 0.0, 0
        for x in g:
            rh = REF.time_at(x["zone"], az=math.degrees(math.atan2(x["fy"], x["fx"])) % 360, y=x["fz"] / 100, pos_ue=[x["fx"], x["fy"], x["fz"]], night=False, sticky=None)
            if rh is None: continue
            d = abs(x["H"] - rh); worst = max(worst, d); bad += d >= 1e-3
        out.append("  脚下区域：%s；每帧 H 和 reference（按实际脚底）最大差 %.2e，超过 1e-3 的 %d 帧" % (zones, worst, bad))
        main = [x for x in g if x["zone"] == L["zone"]]
        if L["zone"] == "L0" and not L["jump_every"]:
            a0 = main[0]["az"]; span = unwrap(main[-1]["az"], a0 - 1) - a0
            back = sum(1 for p, q in zip(main, main[1:]) if q["H"] < p["H"] - 1e-6 and unwrap(q["az"], a0 - 1) >= unwrap(p["az"], a0 - 1))
            out.append("  走过方位角 %.1f° → %.1f°（%.0f°），H %.3f → %.3f（%s → %s），反着变的帧 %d" % (
                main[0]["az"], main[-1]["az"], span, main[0]["H"], main[-1]["H"], clock(main[0]["H"]), clock(main[-1]["H"]), back))
            out.append("  太阳 方位 %.2f° → %.2f°、高度 %.2f° → %.2f°（往西偏低：%s）" % (main[0]["sun_az"], main[-1]["sun_az"], main[0]["sun_alt"], main[-1]["sun_alt"],
                       "是" if main[-1]["sun_az"] > main[0]["sun_az"] and main[-1]["sun_alt"] < main[0]["sun_alt"] else "否"))
            jumps = [x for x in rec if not x["ground"]]
            out.append("  %s" % ("没有离地" if not jumps else "中途离地 %d 帧（台阶、门槛）" % len(jumps)))
        if L["jump_every"]:
            air, runs, moved = [], [], 0
            prev_ground_H = None
            for x in rec:
                if x["ground"]: 
                    if air: runs.append(air); air = []
                    prev_ground_H = x["H"]
                else: air.append((x["H"], prev_ground_H, x["az"]))
            if air: runs.append(air)
            still = sum(1 for run in runs if all(abs(h - run[0][1]) < 1e-6 for h, _, _ in run))
            moved = sum(run[-1][2] - run[0][2] for run in runs) / max(1, len(runs))
            out.append("  跳了 %d 次，空中 %d 帧；每次空中 H 都等于起跳那一刻：%d/%d；每次在空中平均走过方位角 %.2f°" % (
                len(runs), sum(len(r) for r in runs), still, len(runs), moved))
        if L["zone"].startswith("tun:"):
            t = [x for x in g if x["zone"] == L["zone"]]
            if t:
                out.append("  在楼梯上 %d 帧：脚底 y %.2f → %.2f m，H %.3f → %.3f（%s → %s）" % (len(t), t[0]["y"], t[-1]["y"], t[0]["H"], t[-1]["H"], clock(t[0]["H"]), clock(t[-1]["H"])))
                steps = sorted(set(round(x["y"], 2) for x in t))
                out.append("  踩过 %d 个不同的踏面高度；最后到了方位角 %.1f°" % (len(steps), t[-1]["az"]))
            else: out.append("  ✘ 没走上楼梯")
        self.log += out
    def finish(self):
        if self.handle is not None: unreal.unregister_slate_post_tick_callback(self.handle); self.handle = None
        try: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        except Exception: pass
        _throttle(_throttle0)
        lines = ["══ 日落回廊 v0.12 · PIE 里走一遍 ══"] + self.log
        for l in lines: unreal.log(l)
        open(os.path.join(SAVED, "Dysis_PieWalk.txt"), "w", encoding="utf-8").write("\n".join(lines))

def clock(H):
    m = int(round(((12 + H / 15) % 24) * 60)); return "%02d:%02d" % (m // 60 % 24, m % 60)

walk = Walk()
walk.handle = unreal.register_slate_post_tick_callback(walk.tick)
unreal.log("Dysis 走一遍开始")