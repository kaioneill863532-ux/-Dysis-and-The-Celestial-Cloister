# 日落回廊 v0.12 · 把天摆进关卡（UE 编辑器 Python）
#
# 做的事（再跑一次会先清掉上次摆的）：
#   1. 建月亮圆盘材质 /Game/Dysis/Sky/M_DysisMoonDisc（无光照、半透明，标量参数 Opacity）。
#   2. 在大纲 Dysis_Sky 文件夹下摆：ADysisSkyActor（太阳光 Index 0 + 月光 Index 1 + 月亮圆盘）、SkyAtmosphere、
#      SkyLight（实时捕捉）、ExponentialHeightFog、PlayerStart（门廊台阶上，面朝神殿）。
#   3. 关卡的 GameMode 覆盖设成 ADysisGameMode（玩家 = ADysisCharacter，身上有 UDysisTimeComponent）。
# 前提：C++ 已经编译好（unreal.DysisSkyActor 存在）；神殿已经用 ue_import_temple.py 摆好。
import unreal, math

SKY_FOLDER = "Dysis_Sky"
MAT_PATH = "/Game/Dysis/Sky/M_DysisMoonDisc"

def log(s): unreal.log(s); print(s)

# ───── 1. 月亮圆盘材质 ─────
def ensure_moon_material():
    if unreal.EditorAssetLibrary.does_asset_exist(MAT_PATH):
        return unreal.EditorAssetLibrary.load_asset(MAT_PATH)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    pkg, name = MAT_PATH.rsplit("/", 1)
    m = tools.create_asset(name, pkg, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mel = unreal.MaterialEditingLibrary
    col = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -600, -100)
    col.set_editor_property("parameter_name", "Color"); col.set_editor_property("default_value", unreal.LinearColor(0.79, 0.82, 0.86, 1))
    glow = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -600, 100)
    glow.set_editor_property("parameter_name", "Glow"); glow.set_editor_property("default_value", 6.0)
    mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 0)
    mel.connect_material_expressions(col, "", mul, "A"); mel.connect_material_expressions(glow, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -300, 250)
    op.set_editor_property("parameter_name", "Opacity"); op.set_editor_property("default_value", 0.0)
    mel.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    log("建好材质 " + MAT_PATH)
    return m

mat = ensure_moon_material()

if not hasattr(unreal, "DysisSkyActor"):
    raise RuntimeError("找不到 unreal.DysisSkyActor：先把 ue/Source 放进 UE 工程并编译（见 ue/README.md）")

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

# ───── 2. 摆天 ─────
old = [a for a in sub.get_all_level_actors() if str(a.get_folder_path()).startswith(SKY_FOLDER)]
for a in old: a.destroy_actor()
if old: log("清掉上次摆的 %d 个" % len(old))
# 关卡里别处已有的天光类 Actor 会和这里的重复，提醒一下
for cls in (unreal.DirectionalLight, unreal.SkyAtmosphere, unreal.SkyLight, unreal.ExponentialHeightFog, unreal.PlayerStart):
    extra = [a.get_actor_label() for a in sub.get_all_level_actors() if isinstance(a, cls)]
    if extra: unreal.log_warning("关卡里已经有 %s：%s（可能要删掉）" % (cls.__name__, extra))

def place(cls, label, loc=unreal.Vector(0, 0, 0), rot=unreal.Rotator(0, 0, 0)):
    a = sub.spawn_actor_from_class(cls, loc, rot)
    a.set_actor_label(label); a.set_folder_path(SKY_FOLDER)
    return a

sky = place(unreal.DysisSkyActor, "DysisSky")
sky.set_editor_property("moon_disc_material", mat)
atm = place(unreal.SkyAtmosphere, "SkyAtmosphere")
sl = place(unreal.SkyLight, "SkyLight")
slc = sl.get_component_by_class(unreal.SkyLightComponent)
slc.set_mobility(unreal.ComponentMobility.MOVABLE)
slc.set_editor_property("real_time_capture", True)
fog = place(unreal.ExponentialHeightFog, "HeightFog", unreal.Vector(0, 0, -200))
fog.get_component_by_class(unreal.ExponentialHeightFogComponent).set_editor_property("fog_density", 0.004)

# PlayerStart：门廊台阶上（施工图 az≈24°、r≈22 m 一带），从上往下打射线找地面；门廊有顶，所以从 2 m 高往下打
def ground_z(x, y):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 200), unreal.Vector(x, y, -600),
                                                 unreal.TraceTypeQuery.ECC_VISIBILITY, True, [], unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple): hit = hit[1] if (len(hit) >= 2 and isinstance(hit[0], bool) and hit[0]) else (None if isinstance(hit[0], bool) else hit[-1])
    if hit is None: return None
    t = hit.to_tuple()
    loc = next(v for v in t if hasattr(v, "z"))
    act = next((v for v in t if isinstance(v, unreal.Actor)), None)
    return loc.z, (act.get_actor_label() if act else "?")
start = None
for r_m in (22.0, 21.0, 23.0, 20.0, 24.0):
    for az in (24.0, 20.0, 28.0, 16.0, 32.0):
        x, y = 100 * r_m * math.cos(math.radians(az)), 100 * r_m * math.sin(math.radians(az))
        g = ground_z(x, y)
        if g and g[1] in ("SM_Portico_Steps", "SM_Podium") and -130 <= g[0] <= 10:
            start = (x, y, g[0], g[1]); break
    if start: break
if start is None: start = (2200.0, 900.0, 0.0, "?")
ps = place(unreal.PlayerStart, "PlayerStart", unreal.Vector(start[0], start[1], start[2] + 100),
           unreal.Rotator(0, 0, math.degrees(math.atan2(-start[1], -start[0]))))
log("PlayerStart 在 (%.0f, %.0f, %.0f)，脚下 %s，面朝神殿" % (start[0], start[1], start[2], start[3]))

# ───── 3. GameMode ─────
ws = world.get_world_settings()
ws.set_editor_property("default_game_mode", unreal.DysisGameMode.static_class())
log("关卡 GameMode 覆盖 = DysisGameMode")

sky.set_editor_property("preview_h", unreal.DysisSkyLibrary.dysis_const("H_I"))
# 保存放在脚本外面单独做（同一个脚本里摆完马上存，UE 5.8.2 的 Python 在存盘时崩过一次）
log("摆好了：DysisSky、SkyAtmosphere、SkyLight、HeightFog、PlayerStart。接着保存关卡（文件 → 保存当前关卡）。")