# 日落回廊 v0.12 · 给神殿的 Actor 打区域 Tag（UE 编辑器 Python）
#
# 大纲里的名字（label）打包后就没了，所以按 docs/ue-handoff/README.md 第 3 步的表给每个 Actor 加 Tag “DysisZone=<区域名>”。
# 游戏里 UDysisSkyLibrary::DysisZoneOf 读这个 Tag；SM_Wall 标成 “wall”，再按脚底半径、方位角分出两段楼梯；
# 没有 Tag 的 Actor（柱子、栏杆……）按脚底高度兜底。
# 用法：先跑 models/temple-v0.12/ue_import_temple.py 摆好神殿，再执行这个脚本，然后保存关卡。再跑一次会先清掉旧的 DysisZone Tag。
import unreal, fnmatch

FOLDER = "Dysis_Temple_v0_12"
PREFIX = "DysisZone="
RULES = [   # (大纲名字的通配, 区域)；从上往下，先匹配到的算
    ("SM_Floor_L0", "L0"), ("SM_Sluice_Platform", "L0"), ("SM_Seam_Stone_116", "L0"), ("SM_Seam_Stone_140", "L0"),
    ("SM_Floor_L1", "L1"), ("SM_Mech_Twins_*", "L1"),
    ("SM_Floor_L2", "L2"), ("SM_Mech_Mirror_Plinth", "L2"),
    ("SM_Floor_L3", "L3"), ("SM_Mech_Swan_Plinth", "L3"),
    ("SM_PoolBed", "pool"),
    ("SM_SunNiche_Ledge", "ledge"),
    ("SM_Waterfall_BackLedge", "wfback"), ("SM_Mech_Goddess_Plinth", "wfback"),
    ("SM_Terrain", "out"), ("SM_Podium", "out"), ("SM_Island", "out"), ("SM_Portico_Steps", "out"),
    ("SM_Roof_Fix0[1-5]", "crown"), ("SM_Roof_Land", "crown"), ("SM_Roof_SeamOuter", "crown"),
    ("SM_Mech_RoofSteps_*", "crown"), ("SM_Mech_IrisBlades_*", "crown"),
    ("SM_RoofBridge", "rbridge"),
    ("SM_Pavilion", "pav"), ("SM_Mech_Armillary_Pavilion", "pav"),
    ("SM_Mech_MoonBridge_Deck", "moonbr"),
    ("SM_Mech_Sill_Ledge", "sill"), ("SM_Mech_Sill_Niche", "sill"),
    ("SM_Mech_HalfBridge_Deck", "gbridge"),
    ("SM_Mech_RainbowBridge_Light", "rainbow"),
    ("SM_Wall", "wall"),
]

def zone_for(label):
    for pat, z in RULES:
        if fnmatch.fnmatchcase(label, pat): return z
    return None

sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = [a for a in sub.get_all_level_actors() if str(a.get_folder_path()).startswith(FOLDER)]
counts, hit_rules = {}, set()
with unreal.ScopedEditorTransaction("Dysis: 打区域 Tag"):
    for a in actors:
        label = a.get_actor_label()
        tags = [t for t in a.tags if not str(t).startswith(PREFIX)]
        z = zone_for(label)
        if z:
            tags.append(unreal.Name(PREFIX + z)); counts[z] = counts.get(z, 0) + 1
            hit_rules.update(p for p, zz in RULES if zz == z and fnmatch.fnmatchcase(label, p))
        if list(a.tags) != tags:
            a.modify(); a.tags = tags
unused = [p for p, _ in RULES if p not in hit_rules]
unreal.log("DysisZone Tag：%d 个 Actor 里打了 %d 个：%s" % (len(actors), sum(counts.values()), ", ".join("%s %d" % kv for kv in sorted(counts.items()))))
if unused: unreal.log_warning("这些名字在关卡里没找到：%s" % unused)
unreal.log("没有 Tag 的按脚底高度兜底。记得保存关卡。")