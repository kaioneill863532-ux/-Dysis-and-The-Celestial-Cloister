# 日落回廊 v0.12 · 在 PIE 里真的站上去：pie_spots.json 的 27 个点（UE 编辑器 Python）
#
# 开 PIE → 把玩家的脚底传送到每个点（DebugTeleportFeet，和控制台 Dysis.Go 一样；屋顶环道的点站到那个 XY 上真实的踏面）→ 站稳 → 读区域、H、主光、
# 以及关卡里那盏主光平行光组件的真实 Pitch/Yaw → 和 json 比（H 1e-3，角度 0.01°）→ 每个点截一张图 → 关 PIE。
# 结果：项目/Saved/Dysis_PieSpots.txt（和 .json），截图在 项目/Saved/Screenshots/Dysis/。
# 用法：打开放好神殿和天的关卡（ue/Scripts/dysis_setup_sky.py 跑过），执行这个脚本；它挂在编辑器 tick 上一帧一帧跑，
#       脚本本身马上返回，PIE 跑完会自己关掉，最后在输出日志里打印“全部通过”或列出没过的点。
import unreal, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else "."
SPOTS_PATH = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "ue-handoff", "pie_spots.json"))
GOLDEN_DIR = os.path.dirname(SPOTS_PATH)
SAVED = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
SHOT_DIR = os.path.join(SAVED, "Screenshots", "Dysis").replace("\\", "/")
TOL_H, TOL_DEG = 1e-3, 0.01
SHOT_RES = "1600x900"

spots = json.load(open(SPOTS_PATH, encoding="utf-8"))
sys.path.insert(0, GOLDEN_DIR)
try:
    import reference_time as _ref
    REF = _ref.DysisTime(json.load(open(os.path.join(GOLDEN_DIR, "golden_time.json"), encoding="utf-8")))
except Exception as e:
    REF = None; unreal.log_warning("没载入 reference_time.py（只影响“按实际脚底重算”那一列）：%s" % e)
os.makedirs(SHOT_DIR, exist_ok=True)

def ang(a, b): return abs(((a - b) % 360 + 540) % 360 - 180)
def ref_H(zone, foot, night):
    if REF is None: return None
    az = math.degrees(math.atan2(foot[1], foot[0])) % 360
    h = REF.time_at(zone, az=az, y=foot[2] / 100, pos_ue=list(foot), night=night, sticky=None)
    return h

def surface_z(w, x, y, z0, z1, ignore):
    hit = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x, y, z0), unreal.Vector(x, y, z1), unreal.TraceTypeQuery.ECC_VISIBILITY,
                                                 True, ignore, unreal.DrawDebugTrace.NONE, True)
    if not hit: return None
    p = next((v for v in hit.to_tuple() if hasattr(v, "z")), None)
    return p.z if p else None
def ref_rot(H, body):
    if REF is None: return None
    r = _ref.ue_light_rotation(_ref.sun_dir(H) if body == "sun" else _ref.moon_dir(H))
    return r["pitch"], r["yaw"] % 360

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

class Run:
    def __init__(self):
        self.phase, self.i, self.wait, self.rows, self.handle, self.frames = "begin", 0, 0, [], None, 0
    def world(self): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    def tick(self, dt):
        try: self.step()
        except Exception as e:
            unreal.log_error("PIE 测试出错：%r" % e); self.finish(error=repr(e))
    def step(self):
        self.frames += 1
        if self.frames > 20000: raise RuntimeError("超时")
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if self.phase == "begin":
            _throttle(False); les.editor_request_begin_play(); self.phase, self.wait = "wait_pie", 0; return
        w = self.world()
        if self.phase == "wait_pie":
            self.wait += 1
            if w is None: return
            pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
            if pawn is None: return
            self.pawn, self.pc = pawn, unreal.GameplayStatics.get_player_controller(w, 0)
            self.comp = pawn.get_component_by_class(unreal.DysisTimeComponent)
            skies = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DysisSkyActor)
            if self.comp is None or not skies: raise RuntimeError("玩家身上没有 DysisTimeComponent，或关卡里没有 DysisSkyActor")
            self.sky = skies[0]; self.phase, self.wait = "settle_start", 0; return
        if self.phase == "settle_start":
            self.wait += 1
            if self.wait < 30: return
            self.phase = "go"; return
        if self.phase == "go":
            if self.i >= len(spots): self.finish(); return
            s = spots[self.i]
            pos = list(s["pos"]); self.snap = None
            if s["zone"] == "crown":   # 屋顶环道的时间只看方位角；升降踏步是按升起的姿态导入的，站到这个 XY 上真实的踏面
                z = surface_z(w, pos[0], pos[1], 4000.0, 2900.0, [self.pawn])
                if z is not None: self.snap = z; pos[2] = z
            self.comp.debug_teleport_feet(unreal.Vector(*pos), bool(s["night"]), 6)
            if s["zone"].startswith("tun:"): yaw = (s["az"] + 90) % 360; pitch = 0.0      # 墙里楼梯：顺着楼梯看
            else: yaw = (s["az"] + 180) % 360; pitch = 14.0                                 # 回廊、屋顶：朝殿心看
            self.pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))
            self.phase, self.wait = "settle", 0; return
        if self.phase == "settle":
            self.wait += 1
            if self.wait < 12 or (not self.comp.is_on_ground() and self.wait < 120): return
            self.read(); self.phase, self.wait = "shot", 0; return
        if self.phase == "shot":
            self.wait += 1
            if self.wait == 1:
                s = spots[self.i]
                name = "%02d_%s_%s_az%g" % (self.i, s["zone"].replace(":", "-"), "night" if s["night"] else "day", s["az"])
                self.rows[-1]["shot"] = "%s/%s.png" % (SHOT_DIR, name)
                unreal.SystemLibrary.execute_console_command(w, 'HighResShot %s filename="%s/%s"' % (SHOT_RES, SHOT_DIR, name))
            if self.wait < 20: return
            self.i += 1; self.phase = "go"; return
    def read(self):
        s, c, sky = spots[self.i], self.comp, self.sky
        foot = c.get_editor_property("foot_cm"); foot = [foot.x, foot.y, foot.z]
        H = c.get_editor_property("h"); zone = c.get_editor_property("zone")
        body = "sun" if sky.is_sun_main() else "moon"
        light = sky.get_editor_property("sun_light" if body == "sun" else "moon_light")
        lr = light.get_world_rotation(); mr = sky.get_main_light_rotation()
        rH = ref_H(s["zone"], foot, bool(s["night"]))
        ok_zone = zone == s["zone"]; ok_H = abs(H - s["H"]) < TOL_H; ok_body = body == s["body"]
        ok_rot = ang(lr.pitch, s["pitch"]) < TOL_DEG and ang(lr.yaw, s["yaw"]) < TOL_DEG
        rr = ref_rot(H, body)
        ok_self = (zone == s["zone"] and rH is not None and abs(H - rH) < TOL_H and rr is not None
                   and ang(lr.pitch, rr[0]) < TOL_DEG and ang(lr.yaw, rr[1]) < TOL_DEG
                   and body == ("sun" if _ref.az_alt(_ref.sun_dir(H))[1] > -0.8 else "moon"))
        self.rows.append(dict(i=self.i, zone_exp=s["zone"], zone=zone, night=bool(s["night"]), H_exp=s["H"], H=H,
                              H_ref_at_foot=rH, body_exp=s["body"], body=body, pitch_exp=s["pitch"], pitch=lr.pitch,
                              yaw_exp=s["yaw"], yaw=lr.yaw % 360, lib_pitch=mr.pitch, lib_yaw=mr.yaw % 360,
                              foot=[round(v, 2) for v in foot], pos=s["pos"], snap_z=self.snap, on_ground=c.is_on_ground(), ok_self=ok_self,
                              ok=ok_zone and ok_H and ok_body and ok_rot, ok_zone=ok_zone, ok_H=ok_H, ok_body=ok_body, ok_rot=ok_rot))
    def finish(self, error=None):
        if self.handle is not None: unreal.unregister_slate_post_tick_callback(self.handle); self.handle = None
        try: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        except Exception: pass
        _throttle(_throttle0)
        lines = ["══ 日落回廊 v0.12 · PIE 里站上去：%d 个点 ══" % len(spots)]
        for r in self.rows:
            flag = ("✔" if r["ok"] else "✘") + ("✔" if r["ok_self"] else "✘")
            extra = "" if r["H_ref_at_foot"] is None else "  （按实际脚底重算 %.4f）" % r["H_ref_at_foot"]
            lines.append("%s %02d %-7s %-5s 区域 %s/%s  H %.4f/%.4f%s  主光 %s/%s  Pitch %.3f/%.3f  Yaw %.3f/%.3f  脚底 %s（期望 %s）" % (
                flag, r["i"], r["zone_exp"], "night" if r["night"] else "day", r["zone"], r["zone_exp"], r["H"], r["H_exp"], extra,
                r["body"], r["body_exp"], r["pitch"], r["pitch_exp"], r["yaw"], r["yaw_exp"], r["foot"], r["pos"])
                         + ("  站到踏面 z=%.1f" % r["snap_z"] if r["snap_z"] is not None else ""))
        n_ok = sum(1 for r in self.rows if r["ok"])
        n_self = sum(1 for r in self.rows if r["ok_self"])
        lines.append("第一个勾：和 json 比（区域、H 容差 %g、主光、平行光 Pitch/Yaw 容差 %g°）：%d/%d" % (TOL_H, TOL_DEG, n_ok, len(spots)))
        lines.append("第二个勾：一致性（区域对；H = reference 按实际脚底重算；主光和平行光朝向 = 按这个 H 算的日月方向）：%d/%d" % (n_self, len(spots)))
        lines.append("每行：UE 实测/json 期望")
        if error: lines.append("出错：" + error)
        lines.append("全部通过" if n_ok == len(spots) and not error else "没过，看上面带 ✘ 的行")
        lines.append("截图：" + SHOT_DIR)
        for l in lines: unreal.log(l)
        open(os.path.join(SAVED, "Dysis_PieSpots.txt"), "w", encoding="utf-8").write("\n".join(lines))
        json.dump(self.rows, open(os.path.join(SAVED, "Dysis_PieSpots.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

run = Run()
run.handle = unreal.register_slate_post_tick_callback(run.tick)
unreal.log("Dysis PIE 测试开始：%d 个点" % len(spots))