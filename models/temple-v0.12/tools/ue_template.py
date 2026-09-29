# 狄西斯的日落回廊 v0.12 · 建筑模型导入 UE、按施工图摆好、核对数值
#
# 用法（UE 5.x 编辑器）：
#   1. 编辑 → 插件，打开 “Python Editor Script Plugin”，重启编辑器。
#   2. 新建一个空关卡（或打开要放神殿的关卡）。把下面 FBX 改成 Dysis_Temple_v0_12.fbx 实际放的位置
#      （构件库 Dysis_Kit_v0_12.fbx 放在同一个文件夹里）。
#   3. 工具 → 执行 Python 脚本…，选这个文件。
#      也可以在输出日志的 Python 命令行里：exec(open(r"D:/路径/ue_import_temple.py", encoding="utf-8").read())
#   4. 看输出日志。最后一行是“全部通过”，或者列出没过的项。完整报告另存在 项目/Saved/Dysis_Temple_v0_12_UE核对.txt。
#
# 脚本做的事：
#   · 导入两个 FBX：建筑（每个构件一个静态网格）和构件库（外立面的盲拱、壁柱、雕像、窗框，机关的每个部件，每种一个静态网格）。
#     不自动生成简单碰撞，碰撞按网格本身（复杂碰撞当简单碰撞用），人能在楼板、楼梯上走。
#   · 在关卡里摆出全部构件（大纲视图 Dysis_Temple_v0_12 文件夹下，按类别分子文件夹）。外立面 158 件各是一个 Actor，
#     用构件库里的网格，轴心在构件底部贴外墙的地方、正面朝外；换一件就换它的网格，整批换就替换构件库资源的引用。
#   · 用三块红色方位标记认出导入后的朝向，把整座建筑转到施工图的坐标：+X 朝北、+Y 朝东、Z 向上，1 m = 100 cm。
#     施工图里方位角 az、半径 r、高 y 的点，在 UE 里就是 X = 100·r·cos(az)，Y = 100·r·sin(az)，Z = 100·y。
#   · 核对：比例、朝向、方位标记位置、每个构件的包围盒，还有和 Blender 里同一批竖直射线（各层地面和楼板底、栏杆顶、池底、
#     窗台和拱顶、墙里楼梯的每一片踏步、屋顶环道每一级、细桥……），射线落点要和施工图的高度对上。
#
#   · 机关（石板、拉杆、三相像、天鹅、双子、女神、棱镜、浑天仪、光圈叶片……）每个部件一个 Actor，轴心在转轴、铰链或滑动的基准点上，
#     设成可移动（Movable），按父子关系挂好（拉杆的杆挂在底座上、龛门挂在龛上……）；水面、瀑布、海、虹桥不挡东西（NoCollision）。
#     每个部件怎么动见“机关清单.md”。
#
# 光柱、光阶、七色光带、影桥这些是按时间算出来的光，不是模型，不在里面。
import unreal, math, json, os

FBX = r"C:/Dysis/Dysis_Temple_v0_12.fbx"    # ← 改成 FBX 实际放的位置
FBX_KIT = os.path.join(os.path.dirname(FBX), "Dysis_Kit_v0_12.fbx")   # 构件库：外立面 + 机关（默认和上面同一个文件夹）
DEST = "/Game/Dysis/Temple_v0_12"            # 导入到内容浏览器的哪个文件夹
DO_IMPORT = True                             # 已经导过、只想重新摆放和核对，改成 False
KEEP_MARKERS = True                          # 核对完不想留三块红色方块，改成 False
FOLDER = "Dysis_Temple_v0_12"                # 大纲视图里的文件夹

EXPECT = json.loads(r'''__EXPECT__''')

log_lines = []
def log(s=""):
    log_lines.append(s); unreal.log(s)

# ───────── 1. 导入 ─────────
def set_opt(obj, name, value):
    try: obj.set_editor_property(name, value)
    except Exception as e: log(f"  （这个版本没有导入选项 {name}，跳过）")

def import_fbx(path):
    if not os.path.isfile(path): raise RuntimeError(f"找不到 FBX：{path}，请改脚本最上面的 FBX 路径")
    ui = unreal.FbxImportUI()
    set_opt(ui, "import_mesh", True); set_opt(ui, "import_as_skeletal", False); set_opt(ui, "import_animations", False)
    set_opt(ui, "import_materials", True); set_opt(ui, "import_textures", False)
    set_opt(ui, "automated_import_should_detect_type", False)
    set_opt(ui, "mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    smd = ui.get_editor_property("static_mesh_import_data")
    for k, v in (("combine_meshes", False), ("auto_generate_collision", False), ("generate_lightmap_u_vs", False),
                 ("transform_vertex_to_absolute", True), ("bake_pivot_in_vertex", False),
                 ("convert_scene", True), ("force_front_x_axis", False), ("convert_scene_unit", False), ("import_uniform_scale", 1.0),
                 ("import_translation", unreal.Vector(0, 0, 0)), ("import_rotation", unreal.Rotator(roll=0, pitch=0, yaw=0))):
        set_opt(smd, k, v)
    try: set_opt(smd, "normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    except Exception: pass
    try: smd.set_editor_property("build_nanite", False)
    except Exception: pass
    task = unreal.AssetImportTask()
    for k, v in (("filename", path), ("destination_path", DEST), ("automated", True), ("replace_existing", True), ("save", True), ("options", ui)):
        task.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    log(f"导入完成：{path} → {DEST}")
if DO_IMPORT:
    import_fbx(FBX); import_fbx(FBX_KIT)

# ───────── 2. 找到导入的网格 ─────────
names = list(EXPECT["bounds_cm"]) + list(EXPECT["kit"])
meshes = {}
for path in unreal.EditorAssetLibrary.list_assets(DEST, recursive=True, include_folder=False):
    a = unreal.EditorAssetLibrary.load_asset(path)
    if not isinstance(a, unreal.StaticMesh): continue
    nm = a.get_name()
    if nm in names: meshes[nm] = a; continue
    for key in names:   # 有的版本会在前面加 FBX 文件名
        if nm.endswith("_" + key) and key not in meshes: meshes[key] = a
missing = [k for k in names if k not in meshes]
log(f"找到 {len(meshes)} / {len(names)} 个网格" + (f"；没找到：{missing}（看一下 {DEST} 里导进来的资源名）" if missing else ""))
for key in ("SM_MARK_N_0deg_r30", "SM_MARK_E_90deg_r30", "SM_MARK_UP_y45"):
    if key not in meshes: raise RuntimeError(f"没有方位标记 {key}，没法认朝向")

# 碰撞按网格本身（整圈墙、楼梯如果自动生成简单碰撞，会是一个大凸包把人挡在外面）
for key, m in meshes.items():
    try:
        bs = m.get_editor_property("body_setup")
        if bs: bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        unreal.EditorAssetLibrary.save_loaded_asset(m)
    except Exception as e: log(f"  {key} 设置碰撞没成功：{e}")

# ───────── 3. 用方位标记认朝向 ─────────
def box_of(m):
    b = m.get_bounding_box(); return b.get_editor_property("min"), b.get_editor_property("max")
def center_size(m):
    lo, hi = box_of(m)
    return (lo.x + hi.x) / 2, (lo.y + hi.y) / 2, (lo.z + hi.z) / 2, (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
nx, ny, _, sN = center_size(meshes["SM_MARK_N_0deg_r30"]); ex0, ey0, _, _ = center_size(meshes["SM_MARK_E_90deg_r30"])
yaw = -math.degrees(math.atan2(ny, nx))                   # 北标记转到 +X 要的 Yaw
if abs(yaw - round(yaw / 90.0) * 90.0) < 0.5: yaw = round(yaw / 90.0) * 90.0
# 完整的换算 M：Blender 里（东、北、上，米）的点 → 导入以后网格里的坐标（厘米）。标记方块在 Blender 里的中心：北 (0,30,0.5)、东 (30,0,0.5)、上 (0,0,45)
def cvec(key): x, y, z, _ = center_size(meshes[key]); return [x, y, z]
cU = cvec("SM_MARK_UP_y45"); cN_ = cvec("SM_MARK_N_0deg_r30"); cE_ = cvec("SM_MARK_E_90deg_r30")
colZ = [c / 45.0 for c in cU]; colX = [(cE_[i] - 0.5 * colZ[i]) / 30.0 for i in range(3)]; colY = [(cN_[i] - 0.5 * colZ[i]) / 30.0 for i in range(3)]
M = [[colX[i], colY[i], colZ[i]] for i in range(3)]
def mul(A, B): return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def mulv(A, v): return [sum(A[i][k] * v[k] for k in range(3)) for i in range(3)]
def inv(A):
    (a, b, c), (d, e, f), (g, h, i) = A; det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    return [[(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det], [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det], [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]]
def rz(deg): c, s_ = math.cos(math.radians(deg)), math.sin(math.radians(deg)); return [[c, -s_, 0], [s_, c, 0], [0, 0, 1]]
a = math.radians(yaw); ex, ey = ex0 * math.cos(a) - ey0 * math.sin(a), ex0 * math.sin(a) + ey0 * math.cos(a)
mirrored = ey < 0
log(f"导入后（没转之前）北标记在 ({nx:.0f}, {ny:.0f})，东标记在 ({ex0:.0f}, {ey0:.0f})；整座建筑 Yaw 转 {yaw:.1f}°，北朝 +X、东朝 +Y")
if mirrored: log("！！转完东标记落在 −Y：导入时左右镜像了。检查 FBX 导入选项里的 Convert Scene（要勾上）")

# ───────── 4. 摆进关卡 ─────────
try: actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
except Exception: actor_sub = None
def all_actors(): return actor_sub.get_all_level_actors() if actor_sub else unreal.EditorLevelLibrary.get_all_level_actors()
def spawn(m, rot):
    if actor_sub: return actor_sub.spawn_actor_from_object(m, unreal.Vector(0, 0, 0), rot)
    return unreal.EditorLevelLibrary.spawn_actor_from_object(m, unreal.Vector(0, 0, 0), rot)
old = [ac for ac in all_actors() if str(ac.get_folder_path()).startswith(FOLDER)]
for ac in old: ac.destroy_actor()   # 再跑一次脚本时先清掉上一次摆的
if old: log(f"清掉上次摆的 {len(old)} 个")
rot = unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw)
actors = {}
with unreal.ScopedSlowTask(len(names), "摆放日落回廊构件") as slow:
    slow.make_dialog(True)
    for key in EXPECT["bounds_cm"]:
        slow.enter_progress_frame(1)
        if key not in meshes: continue
        ac = spawn(meshes[key], rot); ac.set_actor_label(key)
        ac.set_folder_path(FOLDER + "/" + EXPECT["folders"].get(key, "其他")); actors[key] = ac
log(f"已摆放建筑 {len(actors)} 个构件：位置 (0,0,0)，旋转 Yaw {yaw:.1f}°（这些网格的轴心都在殿心）")
# 外立面：一件一个 Actor。位置 = 转过 yaw 的 M·(Blender 位置)；旋转 = R(yaw)·M·Rz(Blender 转角)·M⁻¹，只剩绕 Z 的转角
RY, Mi = rz(yaw), inv(M)
inst_actors = {}; inst_bad = []
for it in EXPECT["instances"]:
    if it["mesh"] not in meshes: continue
    loc = mulv(RY, mulv(M, it["b_loc"]))
    Q = mul(mul(RY, M), mul(rz(it["b_rot"]), Mi))
    if abs(Q[2][2] - 1) > 1e-3 or abs(Q[0][2]) > 1e-3 or abs(Q[1][2]) > 1e-3: inst_bad.append(it["name"])
    qy = math.degrees(math.atan2(Q[1][0], Q[0][0]))
    ac = (actor_sub.spawn_actor_from_object(meshes[it["mesh"]], unreal.Vector(*loc), unreal.Rotator(roll=0.0, pitch=0.0, yaw=qy)) if actor_sub
          else unreal.EditorLevelLibrary.spawn_actor_from_object(meshes[it["mesh"]], unreal.Vector(*loc), unreal.Rotator(roll=0.0, pitch=0.0, yaw=qy)))
    ac.set_actor_label(it["name"]); ac.set_folder_path(FOLDER + "/" + EXPECT["folders"].get(it["name"], "05 外立面"))
    inst_actors[it["name"]] = (ac, loc, qy)
n_fac = sum(1 for it in EXPECT["instances"] if it.get("grp") != "mech" and it["name"] in inst_actors)
log(f"已摆放外立面 {n_fac} 件、机关部件 {len(inst_actors) - n_fac} 件（用 {len(EXPECT['kit'])} 种构件网格）")
# 机关：可移动；水面、瀑布、海、虹桥不挡东西；按父子关系挂好（世界位置不变）
attach_ok = 0; attach_n = 0
for it in EXPECT["instances"]:
    if it.get("grp") != "mech" or it["name"] not in inst_actors: continue
    ac = inst_actors[it["name"]][0]
    try: ac.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    except Exception as e: log(f"  {it['name']} 设可移动没成功：{e}")
    if it.get("nocol"):
        try: ac.static_mesh_component.set_collision_profile_name("NoCollision")
        except Exception as e: log(f"  {it['name']} 关碰撞没成功：{e}")
for it in EXPECT["instances"]:
    if it.get("grp") != "mech" or not it.get("parent") or it["name"] not in inst_actors or it["parent"] not in inst_actors: continue
    attach_n += 1
    try:
        R = unreal.AttachmentRule.KEEP_WORLD
        inst_actors[it["name"]][0].attach_to_actor(inst_actors[it["parent"]][0], "", R, R, R, False); attach_ok += 1
    except Exception as e: log(f"  {it['name']} 挂到 {it['parent']} 没成功：{e}")
log(f"机关部件挂好父子关系 {attach_ok}/{attach_n}")

# ───────── 5. 核对 ─────────
rows = []   # (分组, 项目, 期望, 实测, 通过)
def row(g, item, exp, got, ok): rows.append((g, item, exp, got, ok))
row("比例", "标记方块边长（cm）", 100, round(max(sN), 2), all(abs(s - 100) < 0.5 for s in sN))
row("朝向", "东标记转完在 +Y（没有镜像）", "是", "否" if mirrored else "是", not mirrored)
row("导入", "网格个数（建筑 + 构件库）", len(names), len(meshes), not missing)
def world_bounds(ac):
    o, e = ac.get_actor_bounds(False)
    return [o.x - e.x, o.y - e.y, o.z - e.z], [o.x + e.x, o.y + e.y, o.z + e.z]
for key, ac in actors.items():
    lo, hi = world_bounds(ac); elo, ehi = EXPECT["bounds_cm"][key]
    d = max(max(abs(lo[i] - elo[i]) for i in range(3)), max(abs(hi[i] - ehi[i]) for i in range(3)))
    row("包围盒", f"{key}  X {lo[0]:.0f}~{hi[0]:.0f}  Y {lo[1]:.0f}~{hi[1]:.0f}  Z {lo[2]:.0f}~{hi[2]:.0f}", "偏差 ≤ 1 cm", f"{d:.2f} cm", d <= 1.0)
for key, (x, y, z) in EXPECT["markers_cm"].items():
    if key not in actors: continue
    lo, hi = world_bounds(actors[key]); c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    d = math.sqrt(sum((c[i] - (x, y, z)[i]) ** 2 for i in range(3)))
    row("方位标记", f"{key} 中心", f"({x}, {y}, {z})", f"({c[0]:.0f}, {c[1]:.0f}, {c[2]:.0f})", d <= 1.0)
for key, info in EXPECT["kit"].items():   # 构件库网格本身的大小（网格坐标，厘米）
    if key not in meshes: continue
    lo, hi = box_of(meshes[key]); elo, ehi = info["local_cm"]
    d = max(max(abs((lo.x, lo.y, lo.z)[i] - elo[i]) for i in range(3)), max(abs((hi.x, hi.y, hi.z)[i] - ehi[i]) for i in range(3)))
    row("构件库", f"{key}（{info['uses']} 件在用）网格大小", "偏差 ≤ 1 cm", f"{d:.2f} cm", d <= 1.0)
for grp, label in (("facade", "外立面"), ("mech", "机关")):
    its = [it for it in EXPECT["instances"] if it.get("grp", "facade") == grp]
    pos_ok = 0; worst_p = worst_y = 0.0
    for it in its:
        if it["name"] not in inst_actors: continue
        ac, loc, qy = inst_actors[it["name"]]
        l = ac.get_actor_location(); r_ = ac.get_actor_rotation()
        dp = math.sqrt((l.x - it["ue_loc"][0]) ** 2 + (l.y - it["ue_loc"][1]) ** 2 + (l.z - it["ue_loc"][2]) ** 2)
        dy = abs((r_.yaw - it["ue_yaw"] + 180) % 360 - 180)
        worst_p, worst_y = max(worst_p, dp), max(worst_y, dy)
        if dp <= 1.0 and dy <= 0.05: pos_ok += 1
        else: row(label, f"{it['name']} 位置 {l.x:.0f},{l.y:.0f},{l.z:.0f} Yaw {r_.yaw:.2f}", f"{it['ue_loc']} Yaw {it['ue_yaw']}", f"差 {dp:.1f} cm / {dy:.2f}°", False)
    row(label, f"每件的位置和朝向对上施工图（共 {len(its)} 件，最大偏差 {worst_p:.2f} cm、{worst_y:.3f}°）", len(its), pos_ok, pos_ok == len(its) and not inst_bad)
if attach_n: row("机关", "部件挂好父子关系", attach_n, attach_ok, attach_ok == attach_n)
ntri_ue = ntri_bl = 0; tri_ok = True
for key, m in meshes.items():   # 三角形数只作参考（UE 可能去掉退化三角形）
    try: ntri_ue += m.get_num_triangles(0); ntri_bl += EXPECT["tris"][key] if key in EXPECT["tris"] else EXPECT["kit"][key]["tris"]
    except Exception: tri_ok = False
if tri_ok: log(f"三角形总数：UE {ntri_ue}，Blender {ntri_bl}")

# 射线：和 Blender 里同一批。施工图坐标 → UE：X = 100·北，Y = 100·东，Z = 100·高
try: world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
except Exception: world = unreal.EditorLevelLibrary.get_editor_world()
ignore = [ac for k, ac in actors.items() if k.startswith("SM_MARK")]
def hit_of(r):   # 各版本返回值不太一样：打不到是 None，打到了是命中结果（个别版本是 (是否命中, 命中结果)）
    if r is None: return None
    if isinstance(r, tuple):
        if len(r) >= 2 and isinstance(r[0], bool): return r[1] if r[0] else None
        return r[-1]
    return r
def line(s, e): return hit_of(unreal.SystemLibrary.line_trace_single(world, s, e, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore, unreal.DrawDebugTrace.NONE, True))
def hit_z(hit):   # 命中点：命中结果里第一个向量就是 Location（直线射线上等于 ImpactPoint）
    for getter in (lambda h: h.to_tuple(), lambda h: unreal.GameplayStatics.break_hit_result(h)):
        try:
            vs = [v for v in getter(hit) if hasattr(v, "x") and hasattr(v, "y") and hasattr(v, "z")]
            if vs: return vs[0].z
        except Exception: pass
    return None
def trace_z(x, y, z, sgn, maxd):
    s = unreal.Vector(x, y, z); h = line(s, unreal.Vector(x, y, z + sgn * maxd))
    if h is None: return None
    zz = hit_z(h)
    if zz is not None: return zz
    lo, hi = 0.0, maxd   # 读不到命中点就二分：只看打没打到
    for _ in range(24):
        mid = (lo + hi) / 2
        if line(s, unreal.Vector(x, y, z + sgn * mid)) is None: lo = mid
        else: hi = mid
    return z + sgn * hi
tun_n, tun_ok = {}, {}; fac_n, fac_ok = {}, {}
def trace_dist(x, y, z, dx, dy, dz, maxd):
    s = unreal.Vector(x, y, z); h = line(s, unreal.Vector(x + dx * maxd, y + dy * maxd, z + dz * maxd))
    if h is None: return None
    for getter in (lambda h: h.to_tuple(), lambda h: unreal.GameplayStatics.break_hit_result(h)):
        try:
            vs = [v for v in getter(h) if hasattr(v, "x") and hasattr(v, "y") and hasattr(v, "z")]
            if vs: return math.sqrt((vs[0].x - x) ** 2 + (vs[0].y - y) ** 2 + (vs[0].z - z) ** 2)
        except Exception: pass
    lo, hi = 0.0, maxd
    for _ in range(24):
        mid = (lo + hi) / 2
        if line(s, unreal.Vector(x + dx * mid, y + dy * mid, z + dz * mid)) is None: lo = mid
        else: hi = mid
    return hi
for p in EXPECT["probes"]:
    x, y, z = p["N"] * 100, p["E"] * 100, p["U"] * 100
    if "dist" in p:   # 水平射线：从外面打到外立面构件的正面，比距离
        got = trace_dist(x, y, z, p["dN"], p["dE"], p["dU"], p["maxd"] * 100); exp = p["dist"] * 100
        ok = got is not None and abs(got - exp) <= p["tol"] * 100 + 0.5; k = p["kind"]
        fac_n[k] = fac_n.get(k, 0) + 1; fac_ok[k] = fac_ok.get(k, 0) + (1 if ok else 0)
        if not ok: row("外立面", p["item"], f"{exp:.1f}", None if got is None else f"{got:.1f}", False)
        continue
    got = trace_z(x, y, z, p["dir"], p["maxd"] * 100)
    exp = p["expect"] * 100; tol = p["tol"] * 100 + 0.5
    ok = got is not None and abs(got - exp) <= tol
    if p["g"] == "墙中楼梯" and "踏面 @" in p["item"]:
        k = p["item"].split()[0]; tun_n[k] = tun_n.get(k, 0) + 1; tun_ok[k] = tun_ok.get(k, 0) + (1 if ok else 0)
        if not ok: row("墙中楼梯", p["item"], f"{exp:.1f}", None if got is None else f"{got:.1f}", False)
        continue
    row(p["g"], f"{p['item']}（UE X {x:.0f} Y {y:.0f}）", f"{exp:.1f}", None if got is None else f"{got:.1f}", ok)
for k in tun_n: row("墙中楼梯", f"{k} 每片踏面高度（共 {tun_n[k]} 片）", tun_n[k], tun_ok[k], tun_ok[k] == tun_n[k])
for k in fac_n: row("外立面", f"{k}：从外面水平打到正面的距离（共 {fac_n[k]} 件）", fac_n[k], fac_ok[k], fac_ok[k] == fac_n[k])

if not KEEP_MARKERS:
    for k, ac in actors.items():
        if k.startswith("SM_MARK"): ac.destroy_actor()

# ───────── 6. 报告 ─────────
npass = sum(1 for r in rows if r[4])
groups = {}
for g, item, exp, got, ok in rows: groups.setdefault(g, [0, 0]); groups[g][0] += ok; groups[g][1] += 1
log(""); log(f"══ 日落回廊 v0.12 建筑 · UE 核对：{npass}/{len(rows)} 通过 ══")
for g, (a_, b_) in groups.items(): log(f"  {g}：{a_}/{b_}")
for g, item, exp, got, ok in rows:
    if not ok: log(f"✘ [{g}] {item}：期望 {exp}，实测 {got}")
log("全部通过" if npass == len(rows) else f"没过的有 {len(rows) - npass} 项，见上面带 ✘ 的行")
full = log_lines + ["", "── 全部核对项 ──"] + [f"{'✔' if ok else '✘'} [{g}] {item}：期望 {exp}，实测 {got}" for g, item, exp, got, ok in rows]
try:
    out = os.path.join(unreal.Paths.project_saved_dir(), "Dysis_Temple_v0_12_UE核对.txt")
    with open(out, "w", encoding="utf-8") as f: f.write("\n".join(full))
    unreal.log(f"完整报告：{out}")
except Exception as e: unreal.log_warning(f"报告没存成：{e}")
