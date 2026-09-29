# 狄西斯的日落回廊 v0.12 · 建筑模型（Blender）
# 墙体重新建：一整圈干净的墙 + 布尔开洞（窗洞、门洞、墙里楼梯的空腔都是单独的切割体，修改器不应用，挪切割体就能改）。
# 其余构件用灰盒导出的几何：顶点焊接、三角面并成四边面，按构件拆成单独物体（每根柱子、每层楼板、每一级屋顶踏步……），轴心放在构件底部。
# 然后量数值、存 .blend、导出给 UE 的 FBX、导回来复核、写 UE 脚本要用的期望值。
# 运行：python3 build_blend2.py <temple.glb> <data.json> <输出目录>
import bpy, bmesh, json, math, sys, os, re
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

GLB, DATA, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
D = json.load(open(DATA))
dm = D['dims']; F = dm['F']; RIN, ROUT = dm['R_IN'], dm['R_OUT']; TR0, TR1, HEAD = dm['TUN_R0'], dm['TUN_R1'], dm['TUN_HEAD']
NAME = 'Dysis_Temple_v0_12'

def P(az, r, y=0.0):   # 施工图坐标（方位角、半径、高）→ Blender（X 东、Y 北、Z 上）
    a = math.radians(az); return Vector((r * math.sin(a), r * math.cos(a), y))
def az_of(v): return math.degrees(math.atan2(v.x, v.y)) % 360

# ───────── 1. 导入，材质合并成一套 ─────────
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0; sc.unit_settings.length_unit = 'METERS'
bpy.ops.import_scene.gltf(filepath=GLB)
for o in list(sc.objects):
    if o.type == 'EMPTY': bpy.data.objects.remove(o)
canon = {}
def base_of(m): return m.name.split('.')[0].removeprefix('M_')
for m in list(bpy.data.materials):
    b = base_of(m)
    if b not in canon: canon[b] = m
for o in sc.objects:
    for s in o.material_slots:
        if s.material: s.material = canon[base_of(s.material)]
for b, m in canon.items():
    m.name = 'M_' + b
    try:   # 视图里的实体颜色跟材质一样
        c = m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value; m.diffuse_color = (c[0], c[1], c[2], 1)
    except Exception: pass
for m in list(bpy.data.materials):
    if m.users == 0: bpy.data.materials.remove(m)
def mat(b):
    if b not in canon:
        m = bpy.data.materials.new('M_' + b); m.use_nodes = True; canon[b] = m
    return canon[b]

bycat = {}
for o in sc.objects:
    if o.type == 'MESH': bycat.setdefault(o.name.split('__')[0], []).append(o)

def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active; ob.name = name; ob.data.name = name
    return ob

def clean(ob):   # 焊接重合的顶点、三角面并成四边面、去掉退化面；清掉导入带的自定义法线
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges)
    bmesh.ops.join_triangles(bm, faces=bm.faces, angle_face_threshold=math.radians(0.5), angle_shape_threshold=math.radians(180),
                             cmp_seam=False, cmp_sharp=False, cmp_uvs=False, cmp_vcols=False, cmp_materials=True)
    bm.to_mesh(ob.data); bm.free()
    if ob.data.has_custom_normals:
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.mesh.customdata_custom_splitnormals_clear()

def loose_parts(bm):
    bm.faces.ensure_lookup_table(); seen = set(); parts = []
    for f in bm.faces:
        if f.index in seen: continue
        st = [f]; seen.add(f.index); comp = []
        while st:
            x = st.pop(); comp.append(x)
            for e in x.edges:
                for g in e.link_faces:
                    if g.index not in seen: seen.add(g.index); st.append(g)
        vs = {v for g in comp for v in g.verts}
        lo = Vector((min(v.co.x for v in vs), min(v.co.y for v in vs), min(v.co.z for v in vs)))
        hi = Vector((max(v.co.x for v in vs), max(v.co.y for v in vs), max(v.co.z for v in vs)))
        c = sum((v.co for v in vs), Vector()) / len(vs)
        parts.append({'faces': [g.index for g in comp], 'lo': lo, 'hi': hi, 'c': c, 'az': az_of(c), 'r': math.hypot(c.x, c.y),
                      'size': max(hi.x - lo.x, hi.y - lo.y), 'mats': {g.material_index for g in comp}})
    return parts

def compact_materials(me):
    used = sorted({p.material_index for p in me.polygons}); mats = [me.materials[i] for i in used]
    remap = {o: n for n, o in enumerate(used)}
    idx = [remap[p.material_index] for p in me.polygons]
    me.materials.clear()
    for m in mats: me.materials.append(m)
    me.polygons.foreach_set('material_index', idx); me.update()

def pivot_of(me, ring):   # 轴心：绕殿心的环形构件放在殿心、构件底部；其余放在构件底面中心
    vs = [v.co for v in me.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))); hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    if ring: return Vector((0, 0, lo.z))
    return Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))

def split_by(ob, labeler, ring_labels=()):
    """按连通块分组：labeler(块信息) → 名字；同名的块合成一个物体。"""
    bm = bmesh.new(); bm.from_mesh(ob.data); parts = loose_parts(bm); bm.free()
    names = [m.name for m in ob.data.materials]
    groups = {}
    for p in parts:
        p['matnames'] = {names[i] for i in p['mats']}
        groups.setdefault(labeler(p), []).extend(p['faces'])
    out = []
    for lab, idxs in groups.items():
        keep = set(idxs)
        bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context='FACES')
        me = bpy.data.meshes.new('SM_' + lab); bm.to_mesh(me); bm.free()
        for m in ob.data.materials: me.materials.append(m)
        compact_materials(me)
        pv = pivot_of(me, lab in ring_labels or any(lab.startswith(r) for r in ring_labels)); me.transform(Matrix.Translation(-pv))
        o = bpy.data.objects.new('SM_' + lab, me); o.location = pv
        out.append(o)
    bpy.data.objects.remove(ob)
    return out

def smooth(ob, angle=30):   # 平滑着色，折角大于 30° 的边硬
    me = ob.data
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    try: me.set_sharp_from_angle(angle=math.radians(angle))
    except Exception: me.polygons.foreach_set('use_smooth', [False] * len(me.polygons))
    me.update()

# ───────── 2. 灰盒构件：清理、拆分 ─────────
FL = ['L0', 'L1', 'L2', 'L3']
def floor_ix(z):
    i = 0
    for k in range(4):
        if z >= F[k] - 0.05: i = k
    return i
def lab_columns(p): return f"Col_{FL[floor_ix(p['lo'].z)]}_{round(p['az']) % 360:03d}"
def lab_floors(p):
    if 'M_poolBed' in p['matnames']: return 'PoolBed'
    if p['size'] > 25: return 'Floor_' + FL[min(range(4), key=lambda k: abs(p['hi'].z - F[k]))]
    if p['lo'].z > dm['CEIL'] - 0.5: return 'Waterfall_CeilingLip'
    if abs(p['hi'].z - D['ledge']['y']) < 0.05: return 'SunNiche_Ledge'
    if abs(p['hi'].z - D['sluicePlat']['y']) < 0.05 and abs(p['az'] - 111) < 12: return 'Sluice_Platform'
    if abs(p['hi'].z - 0.9) < 0.05: return 'Waterfall_BackLedge'
    return f"Seam_Stone_{round(p['az']):03d}"
def lab_parapets(p): return 'Parapet_' + FL[floor_ix(p['lo'].z)]
peri_r = D.get('peri', {}).get('r', 20)
portico_ix = {}
def lab_site(p):
    if p['size'] > 60: return 'Terrain'
    if p['r'] > 45: return 'Island'
    small = p['size'] < 3.6 and p['lo'].z > -0.05 and p['hi'].z < 15.5
    if small:
        if abs(p['r'] - peri_r) < 1.0: return f"PeriCol_{round(p['az']) % 360:03d}"
        key = (round(p['az']), round(p['r']))
        return 'PorticoCol_' + key.__repr__()
    if p['size'] > 40 and p['lo'].z >= 15.0: return 'Peristyle_Entablature'
    if p['size'] > 40: return 'Podium'
    if p['lo'].z >= 15.0: return 'Portico_Roof'
    if p['hi'].z <= 0.05: return 'Portico_Steps'
    return 'Site_Misc'

made = {}   # 类别 → [物体]
def take(cat, labeler=None, single=None, ring=()):
    objs = bycat.get(cat, [])
    if not objs: return []
    ob = join(objs, cat); clean(ob)
    if single:
        me = ob.data; pv = pivot_of(me, single in ring); me.transform(Matrix.Translation(-pv)); ob.location = pv
        ob.name = ob.data.name = 'SM_' + single; compact_materials(me); res = [ob]
    else: res = split_by(ob, labeler, ring)
    for o in res: smooth(o)
    return res

made['Floors'] = take('Floors', lab_floors, ring=('Floor_', 'PoolBed'))
made['Parapets'] = take('Parapets', lab_parapets, ring=('Parapet_',))
made['Columns'] = take('Columns', lab_columns)
# 外立面：灰盒导出时每件构件单独一组，带着摆放信息（方位角 az、半径 r、底高 y）。
# 每件一个物体：轴心在构件底部贴外墙的那一点，正面朝外（物体的 −Y 朝外，和 Blender 前视图一样），只绕 Z 转。
# 一模一样的构件共用一份网格（关联复制）：改网格同类的一起变；只想换某一件，先把它设成单独用户。
TYPE_CN = {'BlindArch': '盲拱', 'BlindArchWin': '盲拱（带小窗）', 'BlindArchTunWin': '盲拱（墙里楼梯的窗）', 'Statue': '雕像',
           'Pilaster': '壁柱', 'WinFrame': '主光窗窗框', 'DoorFrame': '北门门框'}
FAC_GROUP = {'BlindArch': 'FacadeArch', 'BlindArchWin': 'FacadeArch', 'BlindArchTunWin': 'FacadeArch', 'Statue': 'FacadeStatue',
             'Pilaster': 'FacadePil', 'WinFrame': 'FacadeFrame', 'DoorFrame': 'FacadeFrame'}
kit = {}; kit_count = {}; fac_inst = []; fac_dev = 0.0
for key in ('FacadeArch', 'FacadePil', 'FacadeFrame', 'FacadeStatue', 'FacadeRing'): made[key] = []
def world_pts(ob): return [(ob.matrix_world @ v.co).copy() for v in ob.data.vertices]
from mathutils.kdtree import KDTree
def max_nn(a, b):   # a 里每个点到 b 里最近点的距离，取最大
    kd = KDTree(len(b))
    for i, q in enumerate(b): kd.insert(q, i)
    kd.balance(); return max(kd.find(q)[2] for q in a)
def localize_share(ob, base, th, kind, prefix):
    """把物体换成自己的轴心（base，绕 Z 转 th），和同一种的共用网格；返回和原位的最大偏差（m）。"""
    before = world_pts(ob)
    ob.data.transform(Matrix.Rotation(-th, 4, 'Z') @ Matrix.Translation(-base))
    ob.rotation_mode = 'XYZ'; ob.location = base; ob.rotation_euler = (0, 0, th); compact_materials(ob.data)
    # 同一种：同类型、顶点数一样、每个顶点到对方最近顶点不超过 2 mm（面数可能差一两个：三角面合没合）
    mine = [v.co.copy() for v in ob.data.vertices]; same = None
    for km in kit.get(kind, []):
        if len(km.vertices) != len(mine) or [m.name for m in km.materials] != [m.name for m in ob.data.materials]: continue
        theirs = [v.co.copy() for v in km.vertices]
        if max_nn(mine, theirs) < 0.002 and max_nn(theirs, mine) < 0.002: same = km; break
    if same:
        old = ob.data; ob.data = same; bpy.data.meshes.remove(old)
    else:
        n = len(kit.get(kind, [])); ob.data.name = prefix + kind + (f'_v{n + 1}' if n else ''); smooth(ob)
        kit.setdefault(kind, []).append(ob.data)
    kit_count[ob.data.name] = kit_count.get(ob.data.name, 0) + 1
    bpy.context.view_layer.update()
    after = world_pts(ob)
    return max(max_nn(after, before), max_nn(before, after))
for cat in sorted(c for c in bycat if c.startswith('Facade~')):
    objs = bycat[cat]; sub = {k: objs[0].get(k) for k in ('t', 'band', 'k', 'key', 'az', 'r', 'y')}
    ob = join(objs, 'tmp'); clean(ob)
    for pk in list(ob.keys()): del ob[pk]
    if sub['t'] == 'Ring':   # 整圈的线脚、檐口、女儿墙：绕殿心一圈，轴心在殿心
        me = ob.data; pv = pivot_of(me, True); me.transform(Matrix.Translation(-pv)); ob.location = pv
        ob.name = me.name = 'SM_Facade_' + sub['key']; compact_materials(me); smooth(ob); made['FacadeRing'].append(ob); continue
    t, band, k = sub['t'], sub['band'], sub['k']
    az = sub['az']; base = P(az, sub['r'], sub['y']); th = math.pi - math.radians(az)
    kind = t + (f'_L{band}' if band is not None else '') + (f"_{sub['key']}" if sub['key'] else '')
    fac_dev = max(fac_dev, localize_share(ob, base, th, kind, 'SM_Kit_Facade_'))
    ob.name = 'SM_Facade_' + kind + (f'_{k:02d}' if k is not None else '')
    ob['类型'] = TYPE_CN[t]; ob['方位角'] = round(az, 3); ob['底高'] = round(sub['y'], 3)
    if band is not None: ob['所在层'] = ['一层', '二层', '三层', '四层'][band]
    made[FAC_GROUP[t]].append(ob); fac_inst.append(ob)
# 机关、道具、雕像、水面：灰盒导出时一个部件一组，带着轴心（转轴、铰链、滑动的基准点）、朝向（绕竖轴）、怎么动、挂在哪个部件下面
MECH_COL = [('Slider', '日2 推拉石板'), ('LeverA', '日2 拉杆'), ('LeverB', '日2 拉杆'), ('IrisRelief', '日2 伊莉丝浮雕'), ('Mirror', '日3 三相像'),
            ('SunNiche', '日3 日之龛'), ('Sill', '虹 窗台石沿和虹之龛'), ('Prism', '虹 棱镜'), ('Selene', '虹 塞勒涅浮雕'), ('RainbowBridge', '虹 虹桥（光）'),
            ('Swan', '月2 天鹅'), ('MoonRelief', '月3 月亮浮雕'), ('StairSeal', '墙里楼梯 下门石板'), ('StairWindows', '墙里楼梯 外窗石块'),
            ('Twins', '月4 双子'), ('MoonBridge', '月4 月桥'), ('Goddess', '月5 女神'), ('HalfBridge', '月5 半桥'), ('MoonShrine', '月之龛'),
            ('Sluice', '水闸石台矮栏'), ('RoofBridgeDoor', '屋顶 桥门'), ('RoofSteps', '屋顶 升降踏步'), ('RainbowArch', '屋顶 虹门（在最高一级上）'), ('Armillary', '浑天仪'), ('IrisBlades', '屋顶 光圈叶片'), ('Water', '水面 瀑布 海')]
MECH_TITLE = dict(MECH_COL)
PART_CN = {'Panel_b2': '石板（上升的窗 b2）', 'Panel_iris': '石板（虹的窗 iris）', 'Rail_b2': '滑轨（b2）', 'Rail_iris': '滑轨（iris）', 'Arm': '杆', 'Base': '底座',
           'Chain': '铜链', 'Relief': '浮雕', 'CarvedBow': '刻着的虹', 'Lip': '铜唇（水帘）', 'Ledge': '窗下石沿', 'Niche': '虹之龛', 'NicheDoorL': '龛门（左）',
           'NicheDoorR': '龛门（右）', 'NicheShard': '虹之碎片', 'Glass': '棱镜', 'Wheel': '铜轮', 'Slit': '铜缝', 'Column': '铜柱', 'Mirror': '铜镜',
           'Statue': '像', 'Crank': '绞盘', 'Plinth': '台座', 'Lid': '盖子', 'Shard': '碎片', 'Box': '铜匣', 'Swan': '天鹅', 'Goddess': '女神像',
           'Door': '石门', 'Disk': '银月亮', 'Block': '月石（会隐去的那块墙）', 'WallBlock': '厚墙正面的月石', 'ThickWall': '厚墙和龛', 'Castor': '卡斯托耳',
           'Pollux': '波吕丢刻斯', 'Deck': '桥面', 'Leaf': '门扇', 'Top': '屋顶接光台', 'Pavilion': '水亭', 'Pool': '水庭水面', 'Waterfall': '瀑布水帘',
           'Sea': '海面', 'Light': '虹桥', 'Rail': '矮栏'}
def part_cn(mech, part):
    m = re.match(r'(Up|Dn)(\d\d)(_Shaft|_Curb)?$', part)
    if mech in ('RoofSteps', 'IrisBlades') and m:
        n = f"{'上行' if m.group(1) == 'Up' else '下行'}第 {int(m.group(2))} 级"
        return n + {None: ('踏面' if mech == 'RoofSteps' else '的光圈叶片'), '_Shaft': '的柱身', '_Curb': '的铜沿'}[m.group(3)]
    if mech == 'RoofSteps' and part == 'TopBar': return '最高一级尽头的铜栏杆'
    if mech == 'RainbowArch': return '虹门、水盆、接光台的台子'
    return PART_CN.get(part, part.replace('_', ' '))
mech_inst = []; mech_dev = 0.0; mech_parent = {}; mech_info = {}; made['Mech'] = []
for cat in sorted(c for c in bycat if c.startswith('Mech~')):
    objs = bycat[cat]; o0 = objs[0]
    sub = {k: o0.get(k) for k in ('mech', 'part', 'px', 'py', 'pz', 'yaw', 'kind', 'parent', 'motion', 'nocol')}
    ob = join(objs, 'tmp'); clean(ob)
    for pk in list(ob.keys()): del ob[pk]
    base = Vector((sub['px'], -sub['pz'], sub['py'])); th = float(sub['yaw'] or 0.0)   # 灰盒（Y 向上）→ Blender（Z 向上）；绕 Y 的角 = 绕 Z 的角
    kind = sub['kind'] or f"{sub['mech']}_{sub['part']}"
    mech_dev = max(mech_dev, localize_share(ob, base, th, kind, 'SM_Kit_Mech_'))
    ob.name = f"SM_Mech_{sub['mech']}_{sub['part']}"
    ob['所属机关'] = MECH_TITLE.get(sub['mech'], sub['mech']); ob['部件'] = part_cn(sub['mech'], sub['part'])
    ob['怎么动'] = sub['motion'] or ''
    if sub['parent']: mech_parent[ob.name] = 'SM_Mech_' + (sub['parent'].replace('/', '_') if '/' in sub['parent'] else f"{sub['mech']}_{sub['parent']}")   # 'RoofSteps/Up16'：挂到别的机关的部件下
    mech_info[ob.name] = {'mech': sub['mech'], 'part': sub['part'], 'motion': sub['motion'] or '', 'nocol': bool(sub['nocol'])}
    mech_inst.append(ob); made['Mech'].append(ob)
bpy.context.view_layer.update()
for ob in mech_inst:   # 挂到父部件下面（世界位置不变）：拉杆的杆挂在底座上，龛门挂在龛上，龛挂在石沿上……
    pn = mech_parent.get(ob.name)
    if pn: mw = ob.matrix_world.copy(); ob.parent = bpy.data.objects[pn]; ob.matrix_world = mw
bpy.context.view_layer.update()
made['Site'] = take('Site', lab_site, ring=('Terrain', 'Podium', 'Peristyle_Entablature'))
# 门廊柱子按方位排号
pcs = sorted([o for o in made['Site'] if o.name.startswith('SM_PorticoCol_')], key=lambda o: (az_of(o.location) + 180) % 360)
for i, o in enumerate(pcs): o.name = o.data.name = f'SM_PorticoCol_{i + 1:02d}'
made['Pavilion'] = take('Pavilion', single='Pavilion', ring=('Pavilion',))
roof = []
for cat in sorted(c for c in bycat if c == 'RoofRing' or c.startswith('RoofRing-')):
    lab = 'Roof_SeamOuter' if cat == 'RoofRing' else 'Roof_' + cat.split('-')[1]
    roof += take(cat, single=lab)
made['RoofRing'] = roof
made['RoofBridge'] = take('RoofBridge', single='RoofBridge')
# 灰盒的墙、窗拱、墙中楼梯不要了，下面重新建
for cat in ('Wall', 'WindowArches', 'WallStairs'):
    for o in bycat.get(cat, []): bpy.data.objects.remove(o)
marks = []
for o in bycat.get('Markers', []):
    o.name = o.data.name = 'SM_' + o.name.split('__')[1]; marks.append(o)
    for sl in o.material_slots: sl.material.name = 'M_marker'   # 标记方块的轴心留在殿心（UE 脚本靠它们认朝向）

# ───────── 3. 墙体：整圈墙 + 布尔开洞 ─────────
def tri_fan(bm, ring, center):   # 凸多边形：从中心点扇形三角化
    c = bm.verts.new(center)
    for i in range(len(ring)): bm.faces.new((c, ring[i], ring[(i + 1) % len(ring)]))
def finish(bm, name, mats, col):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    o = bpy.data.objects.new(name, me); col.objects.link(o); return o

def ring_wall(n=360):
    bm = bmesh.new(); z0, z1 = dm['WALL_BASE'], dm['WALL_TOP']
    V = {(k, i): bm.verts.new(P(i * 360 / n, (RIN, ROUT)[k // 2], (z0, z1)[k % 2])) for k in range(4) for i in range(n)}
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((V[0, i], V[1, i], V[1, j], V[0, j])); bm.faces.new((V[2, i], V[2, j], V[3, j], V[3, i]))
        bm.faces.new((V[1, i], V[3, i], V[3, j], V[1, j])); bm.faces.new((V[0, i], V[0, j], V[2, j], V[2, i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('SM_Wall'); bm.to_mesh(me); bm.free(); me.materials.append(mat('stone'))
    return bpy.data.objects.new('SM_Wall', me)

def arched_cutter(o, head, col, ext=0.4):
    """斜穿墙的拱窗：内墙面上按弧长展开、外墙面上按 b0→b1 插值（和灰盒一样），两头各伸出墙面 ext 米。"""
    R = o['w'] / 2; y0, y1 = o['y0'], o['y1']; top = o['archTop'] if head else y1
    azI = lambda u: o['az'] + math.degrees(u / RIN)
    azO = lambda u: o['b0'] + (o['b1'] - o['b0']) * (u + R) / (2 * R)
    prof = [(-R, y0), (R, y0), (R, y1)]
    if head:
        N = 14; arc = []
        for j in range(1, N + 1):
            v = y1 + (top - y1) * j / N; arc.append((math.sqrt(max(0.0, R * R - (v - y1) ** 2)), v))
        prof += arc
        if arc[-1][0] < 1e-4: prof += [(-u, v) for u, v in reversed(arc[:-1])]
        else: prof += [(-u, v) for u, v in reversed(arc)]
    prof.append((-R, y1))
    bm = bmesh.new(); I, O = [], []
    for u, v in prof:
        a, b = P(azI(u), RIN, v), P(azO(u), ROUT, v); d = (b - a).normalized()
        I.append(a - d * ext); O.append(b + d * ext)
    vi = [bm.verts.new(p) for p in I]; vo = [bm.verts.new(p) for p in O]
    tri_fan(bm, vi, sum(I, Vector()) / len(I)); tri_fan(bm, vo[::-1], sum(O, Vector()) / len(O))
    for k in range(len(prof)):
        j = (k + 1) % len(prof)
        bm.faces.new((vi[k], vo[k], vo[j])); bm.faces.new((vi[k], vo[j], vi[j]))
    ob = finish(bm, 'CUT_窗_' + o['id'], [mat('stone')], col); ob['说明'] = f"{o['id']}：宽 {o['w']} m，窗台 {y0} m，拱顶 {top} m"
    return ob

def sector_cutter(name, a0, a1, r0, r1, z0, z1, col, bottom_mat=0, nseg=None):
    """扇形块（径向的侧面），bottom_mat=1 时底面用深色石（门槛）。"""
    n = nseg or max(1, math.ceil((a1 - a0) / 1.0))
    bm = bmesh.new(); A = [a0 + (a1 - a0) * i / n for i in range(n + 1)]
    V = {(k, i): bm.verts.new(P(A[i], (r0, r1)[k // 2], (z0, z1)[k % 2])) for k in range(4) for i in range(n + 1)}
    for i in range(n):
        j = i + 1
        bm.faces.new((V[0, i], V[1, i], V[1, j], V[0, j])); bm.faces.new((V[2, i], V[2, j], V[3, j], V[3, i]))
        bm.faces.new((V[1, i], V[3, i], V[3, j], V[1, j]))
        f = bm.faces.new((V[0, i], V[0, j], V[2, j], V[2, i])); f.material_index = bottom_mat
    bm.faces.new((V[0, 0], V[2, 0], V[3, 0], V[1, 0])); bm.faces.new((V[0, n], V[1, n], V[3, n], V[2, n]))
    return finish(bm, name, [mat('stone'), mat('stoneDark')], col)

def stair_cutter(T, col):
    """墙里楼梯的空腔：每 1.25° 一片，踏面 f、顶 f + 2.4；踏面和踢面用深色石。一整块封闭的台阶形管子。"""
    sl = sorted(T['slices'])
    for (a, b, f), (a2, b2, f2) in zip(sl, sl[1:]): assert abs(b - a2) < 1e-6, ('楼梯片之间有缝', T['id'], b, a2)
    bm = bmesh.new(); cache = {}
    def V(az, z, k):
        key = (round(az, 6), round(z, 6), k)
        if key not in cache: cache[key] = bm.verts.new(P(az, (TR0, TR1)[k], z))
        return cache[key]
    # 每片两侧竖线上的点（相邻片的踏面、顶面高度）
    def side_pts(i, which):
        a, b, f = sl[i]; x = a if which == 0 else b; zs = {f, f + HEAD}
        j = i - 1 if which == 0 else i + 1
        if 0 <= j < len(sl):
            g = sl[j][2]
            for z in (g, g + HEAD):
                if f < z < f + HEAD: zs.add(z)
        return x, sorted(zs)
    def zipper(k, L, R):   # 左右两条竖线之间的一片，按高度交错三角化
        (xa, za), (xb, zb) = L, R; i = j = 0; tris = []
        while i < len(za) - 1 or j < len(zb) - 1:
            if j == len(zb) - 1 or (i < len(za) - 1 and za[i + 1] <= zb[j + 1]):
                tris.append((V(xa, za[i], k), V(xb, zb[j], k), V(xa, za[i + 1], k))); i += 1
            else:
                tris.append((V(xa, za[i], k), V(xb, zb[j], k), V(xb, zb[j + 1], k))); j += 1
        for t in tris: bm.faces.new(t)
    for i in range(len(sl)):
        L, R = side_pts(i, 0), side_pts(i, 1)
        for k in (0, 1): zipper(k, L, R)
    # 外轮廓：底边（踏面、踢面）、顶边、两头
    outline = []   # (az, z, 是否踏步面)
    a, b, f = sl[0]; outline.append((a, f))
    for i, (a, b, f) in enumerate(sl):
        outline.append((b, f))
        if i + 1 < len(sl) and sl[i + 1][2] != f: outline.append((b, sl[i + 1][2]))
    bot = list(outline)
    top = []
    a, b, f = sl[-1]; top.append((b, f + HEAD))
    for i in range(len(sl) - 1, -1, -1):
        a, b, f = sl[i]; top.append((a, f + HEAD))
        if i > 0 and sl[i - 1][2] != f: top.append((a, sl[i - 1][2] + HEAD))
    loop = bot + top
    for i in range(len(loop)):
        (x0, z0), (x1, z1) = loop[i], loop[(i + 1) % len(loop)]
        if abs(x0 - x1) < 1e-9 and abs(z0 - z1) < 1e-9: continue
        fc = bm.faces.new((V(x0, z0, 0), V(x0, z0, 1), V(x1, z1, 1), V(x1, z1, 0)))
        fc.material_index = 1 if i < len(bot) - 1 else 0
    ob = finish(bm, 'CUT_楼梯_' + T['id'], [mat('stone'), mat('stoneDark')], col)
    ob['说明'] = f"墙里楼梯 {T['id']} 的空腔：半径 {TR0}–{TR1} m，净高 {HEAD} m，每 1.25° 一级"
    return ob

root = bpy.data.collections.new(NAME); sc.collection.children.link(root)
cols = {}
def colf(key, title):
    c = bpy.data.collections.new(title); root.children.link(c); cols[key] = c; return c
colf('Wall', '01 墙体（含墙里楼梯）'); colf('Cut', '01b 切割体（改窗洞门洞楼梯）')
colf('Floors', '02 楼板与台面'); colf('Parapets', '03 栏杆'); colf('Columns', '04 内圈柱子'); colf('Facade', '05 外立面')
for key, title in (('FacadeArch', '05a 盲拱（每间一个）'), ('FacadePil', '05b 壁柱'), ('FacadeFrame', '05c 主光窗窗框和北门门框'),
                   ('FacadeStatue', '05d 雕像'), ('FacadeRing', '05e 檐口和线脚（整圈）')):
    c = bpy.data.collections.new(title); cols['Facade'].children.link(c); cols[key] = c
colf('MechRoot', '11 机关与道具'); colf('Markers', '99 方位标记（核对用，可删）')
for i, title in enumerate(dict.fromkeys(t for _, t in MECH_COL)):
    c = bpy.data.collections.new(f'11.{i + 1:02d} {title}'); cols['MechRoot'].children.link(c); cols['Mech:' + title] = c
colf('Site', '06 场地·台基·柱廊·门廊·小岛'); colf('Pavilion', '07 水亭'); colf('RoofRing', '08 屋顶环道（不动的部分）')
colf('RoofBridge', '09 屋顶细桥')
wall = ring_wall(); cols['Wall'].objects.link(wall)
cuts = []
byid = {o['id']: o for o in D['wallCuts']}
for o in D['wallCuts']:
    if o['kind'] in ('main', 'door'): cuts.append(arched_cutter(o, byid.get(o['head']) if o['head'] else None, cols['Cut']))
for T, TG in zip(D['tunnels'], D['tunGeo']):
    cuts.append(stair_cutter(TG, cols['Cut']))
    for d in TG['doors']:   # 楼梯门：只挖内侧墙皮，多挖 5 cm 进空腔
        cuts.append(sector_cutter(f"CUT_楼梯门_{TG['id']}_{'上' if d['end'] == 'top' else '下'}", d['az'] - d['hw'], d['az'] + d['hw'], RIN - 0.4, TR0 + 0.05, d['y'], d['y'] + d['h'], cols['Cut'], bottom_mat=1, nseg=4))
    for k, w in enumerate(TG['windows']):   # 楼梯朝外的小窗：只挖外侧墙皮
        cuts.append(sector_cutter(f"CUT_楼梯窗_{TG['id']}_{k + 1}", w['az'] - w['hw'], w['az'] + w['hw'], TR1 - 0.05, ROUT + 0.4, w['y'], w['y'] + w['h'], cols['Cut'], nseg=3))
for c in cuts: c.display_type = 'WIRE'; c.hide_render = True
mod = wall.modifiers.new('开洞（切割体在 01b 集合里）', 'BOOLEAN')
mod.operation = 'DIFFERENCE'; mod.operand_type = 'COLLECTION'; mod.collection = cols['Cut']; mod.solver = 'EXACT'
try: mod.material_mode = 'TRANSFER'
except Exception: pass
smooth(wall)
wall.data.polygons.foreach_set('use_smooth', [abs(p.normal.z) < 0.5 for p in wall.data.polygons]); wall.data.update()   # 内外墙面平滑，顶底平
made['Wall'] = [wall]

# 分集合
for cat, obs in made.items():
    if cat == 'Wall': continue
    for o in obs:
        for c in list(o.users_collection): c.objects.unlink(o)
        (cols['Mech:' + MECH_TITLE[mech_info[o.name]['mech']]] if cat == 'Mech' else cols[cat]).objects.link(o)
for o in marks:
    for c in list(o.users_collection): c.objects.unlink(o)
    cols['Markers'].objects.link(o)
bpy.context.view_layer.layer_collection.children[NAME].children[cols['Cut'].name].hide_viewport = True   # 切割体默认隐藏（眼睛图标），布尔照样算
build = [o for cat, obs in made.items() if cat != 'Mech' for o in obs]   # 建筑（量建筑的数值只用这些）

# ───────── 4. 量数值（用算完布尔的结果） ─────────
dg = bpy.context.evaluated_depsgraph_get()
def world_mesh(ob):
    ev = ob.evaluated_get(dg); me = bpy.data.meshes.new_from_object(ev); me.transform(ob.matrix_world); return me
def bvh_of(obs):
    bm = bmesh.new()
    for ob in obs:
        me = world_mesh(ob); bm.from_mesh(me); bpy.data.meshes.remove(me)
    t = BVHTree.FromBMesh(bm); bm.free(); return t
ALL = bvh_of(build); WALL = bvh_of([wall])
FULL = bvh_of(build + [o for o in mech_inst if not mech_info[o.name]['nocol']])   # UE 里全部都在：交给 UE 的射线要在这个上面也打到同一处（水面、瀑布、虹桥不挡）
wme = world_mesh(wall)
rows = []; probes = []; LAST = None
def check(group, item, expect, got, tol=0.02):
    global LAST
    ok = got is not None and abs(got - expect) <= tol
    rows.append((group, item, round(expect, 3), None if got is None else round(got, 3), ok))
    if LAST is not None: add_probe(group, item, LAST, expect, tol)
    LAST = None
def add_probe(group, item, last, expect, tol):
    p, sgn, maxd, got = last
    h = FULL.ray_cast(p, Vector((0, 0, sgn)), maxd)
    if h[0] is None or got is None or abs(h[0].z - got) > 1e-4: return
    probes.append({'g': group, 'item': item, 'E': round(p.x, 4), 'N': round(p.y, 4), 'U': round(p.z, 4), 'dir': sgn, 'maxd': maxd, 'expect': round(expect, 4), 'tol': tol})
def _ray(p, sgn, bvh, maxd):
    global LAST
    hit = bvh.ray_cast(p, Vector((0, 0, sgn)), maxd); z = hit[0].z if hit[0] else None
    LAST = (p.copy(), sgn, maxd, z); return z
def down(p, bvh=ALL, maxd=60): return _ray(p, -1, bvh, maxd)
def up(p, bvh=ALL, maxd=60): return _ray(p, 1, bvh, maxd)
def hdist(p, d, bvh=ALL, maxd=60):
    hit = bvh.ray_cast(p, d.normalized(), maxd); return hit[3] if hit[0] else None

# 墙：内外半径、墙底墙顶、是不是封闭的实体
rr = [math.hypot(v.co.x, v.co.y) for v in wme.vertices]
check('墙体', '内墙面半径（最小）', RIN, min(rr), 0.01); check('墙体', '外墙面半径（最大）', ROUT, max(rr), 0.01)
check('墙体', '墙底', dm['WALL_BASE'], min(v.co.z for v in wme.vertices), 0.01); check('墙体', '墙顶', dm['WALL_TOP'], max(v.co.z for v in wme.vertices), 0.01)
bm = bmesh.new(); bm.from_mesh(wme); nm = sum(1 for e in bm.edges if not e.is_manifold); bm.free()
rows.append(('墙体', '开完洞以后是封闭实体（非流形边数）', 0, nm, nm == 0))
# 楼板
for az in (20, 75, 250, 345):   # 避开内圈柱子
    for i, f in enumerate(F):
        if i == 3 and 140 <= az <= 196: continue
        check('楼板', f'{["一层（水庭）","二层","三层","四层"][i]}地面 @{az}°', f, down(P(az, 13.8, f + 0.3)))
    for i in (1, 2, 3):
        check('楼板', f'{["","二层","三层","四层"][i]}楼板底 @{az}°', F[i] - dm['SLAB'], up(P(az, 13.8, F[i] - 1.0)))
check('楼板', '天花（四层顶）@60°', dm['CEIL'], up(P(60, 13.8, F[3] + 0.3)))
check('楼板', '池底 r 5', dm['POOL_BOTTOM'], down(P(0, 5, 1.0)))
check('楼板', '水闸石台面 @111.5°', D['sluicePlat']['y'], down(P(111.5, 13.0, 3)))
check('楼板', '日之龛石台面 @96°', D['ledge']['y'], down(P(96, 14.2, 22.0)))
check('楼板', '瀑布后石沿 @128°', 0.9, down(P(128, 14.5, 3)))
check('水亭', '亭面', D['pav']['top'], down(P(0, 1.2, 1.5)))
for az in (20, 60, 300):
    for i in (1, 2, 3):
        check('栏杆', f'{["","二层","三层","四层"][i]}栏杆顶 @{az}°', F[i] + dm['PARA_H'], down(P(az, (dm['R_A'] + dm['R_PARA']) / 2, F[i] + 2.0)))
colok = 0
for c in D['cols']['list']:
    spec = D['cols']['spec'][c['floor']]; y = (spec['y0'] + spec['y1']) / 2
    d = hdist(P(c['az'], 12.0, y), P(c['az'], 1.0, 0) - P(c['az'], 0, 0), ALL, 3)
    if d is not None and abs((12.0 + d) - (dm['R_COL'] - c['D'] / 2)) < 0.15: colok += 1
check('内圈柱子', f"立着的柱子数（应为 {len(D['cols']['list'])}）", len(D['cols']['list']), colok, 0)
peri = 0
for k in range(24):
    d = hdist(P(k * 15, 25.0, 6.0), P(k * 15, -1.0, 0) - P(k * 15, 0, 0), ALL, 6)
    if d is not None and abs((25.0 - d) - (D['peri']['r'] + D['peri']['D'] / 2)) < 0.25: peri += 1
check('场地', '外圈柱廊柱子数', 24, peri, 0)
check('场地', '台基面 @7.5° r 22.5', 0.0, down(P(7.5, 22.5, 3)))
check('场地', '台地面 @200° r 30', dm['TERR_Y'], down(P(200, 30, 3)))
check('场地', '开场小岛岛面', D['island']['top'], down(P(D['island']['az'], D['island']['r'], 0)))
# 主光窗、门
for o in D['openings']:
    ci, co = P((o['a0'] + o['a1']) / 2, RIN - 0.05, 0), P((o['b0'] + o['b1']) / 2, ROUT + 0.05, 0)
    y0, y1 = o['y0'], o['y1']; ym = (y0 + y1) / 2; d = (co - ci); L = d.length
    hit = WALL.ray_cast(ci + Vector((0, 0, ym)), d.normalized(), L)
    rows.append(('主光窗', f"{o['id']} 洞口中线穿墙（长 {L:.2f} m）", '通', '通' if hit[0] is None else f'在 {hit[3]:.2f} m 处被挡', hit[0] is None))
    mid = ci.lerp(co, 0.5)
    check('主光窗', f"{o['id']} 窗台", y0, down(mid + Vector((0, 0, y0 + 0.5)), WALL, 3))
    check('主光窗', f"{o['id']} 拱顶", o['archTop'], up(mid + Vector((0, 0, y0 + 0.5)), WALL, 10), 0.03)
    for side, a in (('左侧', o['a0'] - math.degrees(0.25 / RIN)), ('右侧', o['a1'] + math.degrees(0.25 / RIN))):
        p0 = P(a, RIN - 0.1, ym); dd = hdist(p0, P(a, 1, 0) - P(a, 0, 0), WALL, 1.0)
        rows.append(('主光窗', f"{o['id']} {side}紧挨着是墙", '有墙', '有墙' if dd is not None else '空', dd is not None))
# 墙里楼梯
rm = (TR0 + TR1) / 2
for t in D['tunnels']:
    ok = 0; clear_min = 99; prev = None; riser = 0
    for az, f, w in t['treads']:
        h = down(P(az, rm, f + 1.2), WALL, 3)
        if h is not None and abs(h - f) <= 0.02: ok += 1
        add_probe('墙中楼梯', f"{t['id']} 踏面 @{az:.2f}°", LAST, f, 0.02); LAST = None
        u = up(P(az, rm, (h if h is not None else f) + 0.05), WALL, 6); LAST = None
        if u is not None and h is not None: clear_min = min(clear_min, u - h)
        if prev is not None and h is not None: riser = max(riser, abs(h - prev))
        prev = h
    check('墙中楼梯', f"{t['id']} 踏面高度吻合的片数（共 {len(t['treads'])} 片）", len(t['treads']), ok, 0)
    rows.append(('墙中楼梯', f"{t['id']} 最小净高", f"≥ {HEAD - 0.02}", round(clear_min, 3), clear_min >= HEAD - 0.02))
    rows.append(('墙中楼梯', f"{t['id']} 相邻两片最大高差（灰盒能自动迈上 0.55）", '≤ 0.55', round(riser, 3), riser <= 0.55))
    for end, az, y in (('上门', t['topDoor'], t['yTop']), ('下门', t['botDoor'], t['yBot'])):
        d = hdist(P(az, RIN - 0.3, y + 1.2), P(az, 1, 0) - P(az, 0, 0), WALL, 3)
        rows.append(('墙中楼梯', f"{t['id']} {end}（{az:.1f}°，门槛 {y}）从殿里水平看进去", f"到楼梯外侧墙 {TR1 - RIN + 0.3:.2f} m",
                     None if d is None else round(d, 3), d is not None and abs(d - (TR1 - RIN + 0.3)) < 0.05))
        check('墙中楼梯', f"{t['id']} {end}门槛高", y, down(P(az, (RIN + TR0) / 2, y + 1.2), WALL, 3))
    for k, w in enumerate(next(g for g in D['tunGeo'] if g['id'] == t['id'])['windows']):   # 朝外的小窗：从楼梯里水平往外看得到天
        z = w['y'] + w['h'] / 2; d = hdist(P(w['az'], rm, z), P(w['az'], 1, 0) - P(w['az'], 0, 0), WALL, 2)
        rows.append(('墙中楼梯', f"{t['id']} 朝外小窗 {k + 1}（{w['az']:.1f}°，{w['y']:.2f}–{w['y'] + w['h']:.2f} m）从楼梯里看出去", '通', '通' if d is None else f'{d:.2f} m 处被挡', d is None))
# 屋顶
cr = D['crown']
check('屋顶环道', '环道面 @60°（固定段）', dm['RING_Y'], down(P(60, 13.2, 40)))
check('屋顶环道', '最高平台 @T_AZ（最高一级踏面）', cr['TOP_Y'], down(P(cr['T_AZ'], 11.8, 45), FULL))
w_up = ((cr['UP_TOP'][0] - cr['LAND'][1]) % 360) / 15
for k in (1, 5, 10, 15):
    a = cr['LAND'][1] + (k - 0.5) * w_up
    check('屋顶环道', f'上行第 {k} 级 @{a % 360:.1f}°', dm['RING_Y'] + k * cr['dz'], down(P(a, 13.2, 45), FULL))
rb = D['rbridge']; bm_ = (P(rb['S']['az'], rb['S']['r'], 33) + P(rb['E']['az'], rb['E']['r'], 33)) / 2
check('屋顶细桥', '桥面 @桥中', rb['y1'], down(bm_), 0.02)
for o in marks:
    c = sum((o.matrix_world @ v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
    exp = {'SM_MARK_N_0deg_r30': P(0, 30, 0.5), 'SM_MARK_E_90deg_r30': P(90, 30, 0.5), 'SM_MARK_UP_y45': Vector((0, 0, 45))}[o.name]
    rows.append(('方位标记', o.name, tuple(round(x, 2) for x in exp), tuple(round(x, 2) for x in c), (c - exp).length < 0.01))
# 外立面：一件件拆开以后的位置、共用网格；每件从外面水平打一条射线到它正面（给 UE 再打一遍）
from collections import Counter
cnt = Counter(o['类型'] for o in fac_inst)
rows.append(('外立面', '单独的构件数（' + '、'.join(f'{k} {v}' for k, v in cnt.items()) + '）', len(fac_inst), len(fac_inst), len(fac_inst) > 0))
KIT = [m for ms in kit.values() for m in ms]
FKIT = [m for m in KIT if m.name.startswith('SM_Kit_Facade_')]
rows.append(('外立面', f'共用的网格（{len(FKIT)} 种，同一种的构件共用一份）', len(FKIT), len({o.data.name for o in fac_inst}), len(FKIT) == len({o.data.name for o in fac_inst})))
rows.append(('外立面', '换成各自轴心、共用网格以后，每件的顶点和灰盒原位的最大偏差（m）', 0.0, round(fac_dev, 4), fac_dev < 0.002))
hp = {}
for ob in fac_inst:
    me = world_mesh(ob); own = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [q.vertices[:] for q in me.polygons])
    z0, z1 = min(v.co.z for v in me.vertices), max(v.co.z for v in me.vertices); bpy.data.meshes.remove(me)
    az = ob['方位角']; d = (P(az, -1, 0) - P(az, 0, 0)).normalized(); t = ob['类型']; hp.setdefault(t, [0, 0]); hp[t][1] += 1
    for f in (0.5, 0.3, 0.7, 0.1, 0.9, 0.03):
        st = P(az, 19.0, z0 + (z1 - z0) * f); ha = FULL.ray_cast(st, d, 5); ho = own.ray_cast(st, d, 5)
        if ha[0] is not None and ho[0] is not None and abs(ha[3] - ho[3]) < 1e-4:
            probes.append({'g': '外立面', 'item': f'{ob.name} 正面', 'kind': t, 'E': round(st.x, 4), 'N': round(st.y, 4), 'U': round(st.z, 4),
                           'dE': round(d.x, 6), 'dN': round(d.y, 6), 'dU': 0.0, 'maxd': 5, 'dist': round(ha[3], 4), 'tol': 0.01})
            hp[t][0] += 1; break
for t, (a, b) in hp.items():
    rows.append(('外立面', f'{t}：从外面水平打过去先打到它自己的件数（被柱廊、门廊挡住的不算）', f'≤ {b}', a, a > 0))
# 机关：换成各自轴心以后和灰盒原位的偏差；轴心和设计值对得上；能踩的台面高度（也交给 UE）
rows.append(('机关', f'单独的部件数（{len({mech_info[o.name]["mech"] for o in mech_inst})} 个机关、道具）', len(mech_inst), len(mech_inst), len(mech_inst) > 0))
rows.append(('机关', '换成各自轴心、共用网格以后，每件的顶点和灰盒原位的最大偏差（m）', 0.0, round(mech_dev, 4), mech_dev < 0.002))
OB = bpy.data.objects
def pivot_row(name, label, exp, tol=0.02, horiz=False):
    if name not in OB: rows.append(('机关位置', label, '有这个部件', '没有', False)); return
    L = OB[name].matrix_world.translation
    d = math.hypot(L.x - exp.x, L.y - exp.y) if horiz else (L - exp).length
    rows.append(('机关位置', label, f'({exp.x:.2f}, {exp.y:.2f}, {exp.z:.2f})', f'({L.x:.2f}, {L.y:.2f}, {L.z:.2f})', d <= tol))
def dP(d, y=None): return P(d['az'], d['r'], d['y'] if y is None else y)
Dm = D['mirror']; Dt = D['twins']; Dg = D['goddess']
for k in ('A', 'B'): pivot_row(f'SM_Mech_Lever{k}_Base', f'拉杆 {k} 底座（方位 {D["levers"][k]["az"]}°、半径 {D["levers"][k]["r"]}、二层地面）', dP(D['levers'][k]))
for sp, pid in zip(D['sliders'], ('b2', 'iris')):
    a = sp['az'] + (0 if sp['openAt'] else sp['shift'])
    pivot_row(f'SM_Mech_Slider_Panel_{pid}', f'推拉石板 {pid} 开局的位置（方位 {a:.2f}°、半径 {ROUT + 0.1:.2f}、中心高 {(sp["y0"] + sp["y1"]) / 2:.2f}）', P(a, ROUT + 0.1, (sp['y0'] + sp['y1']) / 2))
pivot_row('SM_Mech_Mirror_Statue', f'三相像（方位 {Dm["def"]["az"]}°、半径 {Dm["def"]["r"]}、台面 {Dm["top"]}）', P(Dm['def']['az'], Dm['def']['r'], Dm['top']))
pivot_row('SM_Mech_Mirror_Mirror', f'三相像铜镜中心（白天那一格：方位 {Dm["center"]["az"]}°、半径 {Dm["center"]["r"]}、高 {Dm["center"]["y"]}）', dP(Dm['center']), 0.03)
pivot_row('SM_Mech_Swan_Goddess', f'天鹅女神像（方位 {D["swan"]["az"]}°、半径 {D["swan"]["r"]}、台面 {F[3] + D["swan"]["plinth"]}）', P(D['swan']['az'], D['swan']['r'], F[3] + D['swan']['plinth']))
pivot_row('SM_Mech_Twins_Castor', f'卡斯托耳（方位 {Dt["castorAz"]}°、半径 {Dt["rCastor"]}）', P(Dt['castorAz'], Dt['rCastor'], F[1]))
pivot_row('SM_Mech_Twins_Pollux', f'波吕丢刻斯开局在龛里（方位 {Dt["wallAz"]}°、半径 {RIN + 0.15}）', P(Dt['wallAz'], RIN + 0.15, F[1]))
pivot_row('SM_Mech_Goddess_Statue', f'瀑布后的女神（方位 {Dg["az"]}°、半径 {Dg["r"]}、矮台面 {Dg["top"]}）', P(Dg['az'], Dg['r'], Dg['top']))
pivot_row('SM_Mech_Prism_Glass', f'棱镜（方位 {D["prism"]["pos"]["az"]}°、半径 {D["prism"]["pos"]["r"]}、高 {D["prism"]["pos"]["y"]}）', dP(D['prism']['pos']))
pivot_row('SM_Mech_SunNiche_Box', f'日之龛铜匣（方位 {D["ledge"]["az"]}°、半径 {RIN - 0.6}、石台 {D["ledge"]["y"]}）', P(D['ledge']['az'], RIN - 0.6, D['ledge']['y']))
se = D['selene']['eye']; pivot_row('SM_Mech_Selene_Relief', f'塞勒涅浮雕（眼睛在方位 {se["az"]}°、高 {se["y"]}；浮雕板中心比眼睛低 0.25）', P(se['az'], RIN - 0.04, se['y'] - 0.25), 0.03)
cc = D['crown']['catch']; pivot_row('SM_Mech_Armillary_Top', f'屋顶浑天仪（接光台：方位 {cc["az"]:.2f}°、半径 {cc["r"]}、平台 {D["crown"]["TOP_Y"]} + 1.55）', P(cc['az'], cc['r'], D['crown']['TOP_Y'] + 1.55))
pivot_row('SM_Mech_Armillary_Pavilion', f'水亭浑天仪（殿心，亭面 {D["pav"]["top"]} + 1.6）', Vector((0, 0, D['pav']['top'] + 1.6)))
pivot_row('SM_Mech_HalfBridge_Deck', f'半桥根部（方位 {D["halfBridge"]["g"]}°、半径 {D["dims"]["R_POOL"] + 0.35}）', P(D['halfBridge']['g'], D['dims']['R_POOL'] + 0.35, 0), 0.05)
# 能踩的台面：在部件自己身上从上往下打，打到的高度和设计值比；UE 里再打一遍
def top_probe(name, label, expect, center, radii, tol=0.02):
    if name not in OB: rows.append(('机关台面', label, expect, None, False)); return
    me = world_mesh(OB[name]); own = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [q.vertices[:] for q in me.polygons]); bpy.data.meshes.remove(me)
    for r in radii:
        for a in range(0, 360, 30):
            st = Vector((center.x + r * math.sin(math.radians(a)), center.y + r * math.cos(math.radians(a)), expect + 0.25))
            ho = own.ray_cast(st, Vector((0, 0, -1)), 1.0); hf = FULL.ray_cast(st, Vector((0, 0, -1)), 1.0)
            if ho[0] is not None and hf[0] is not None and abs(ho[0].z - hf[0].z) < 1e-4:
                global LAST
                LAST = (st.copy(), -1, 1.0, hf[0].z); check('机关台面', label, expect, hf[0].z, tol); return
    rows.append(('机关台面', label, expect, None, False))
top_probe('SM_Mech_Mirror_Plinth', '三相像的台面（三层地面 + 0.9）', F[2] + Dm['def']['plinth'], P(Dm['def']['az'], Dm['def']['r']), (1.0, 1.1))
top_probe('SM_Mech_Swan_Plinth', '天鹅女神像的台面（四层地面 + 0.5）', F[3] + D['swan']['plinth'], P(D['swan']['az'], D['swan']['r']), (0.45, 0.5))
top_probe('SM_Mech_Goddess_Plinth', '女神的矮台面（和水闸石台一样高）', Dg['top'], P(Dg['az'], Dg['r']), (1.0, 0.9, 0.8, 1.1))
top_probe('SM_Mech_Sill_Ledge', '南窗下的石沿（伸出来时）', D['sill']['y'], P(D['sill']['a0'] + 1.0, D['sill']['r0'] + 0.25), (0.0, 0.2))
top_probe('SM_Mech_HalfBridge_Deck', '半桥根部桥面（伸出来时，离池沿 0.3 m，和池沿差不多高 0）', 0.0, P(D['halfBridge']['g'], D['dims']['R_POOL'] + 0.35 - 0.3), (0.0,), 0.03)
# 屋顶升降踏步：上行 16 级踏面高度（升起以后）、柱身顶接着踏面底；下行 16 级白天都在环道面
def own_top(ob, pt):
    me = world_mesh(ob); t = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [q.vertices[:] for q in me.polygons]); bpy.data.meshes.remove(me)
    h = t.ray_cast(Vector((pt.x, pt.y, 60)), Vector((0, 0, -1)), 80); return h[0].z if h[0] else None
def zr(ob):
    me = world_mesh(ob); zs = [v.co.z for v in me.vertices]; bpy.data.meshes.remove(me); return min(zs), max(zs)
up_ok = gap_ok = dn_ok = 0; rm_ = (dm['IRIS_R'] + dm['CROWN_R1']) / 2
for k in range(1, 17):
    t = OB.get(f'SM_Mech_RoofSteps_Up{k:02d}'); sh = OB.get(f'SM_Mech_RoofSteps_Up{k:02d}_Shaft')
    if t is None or sh is None: continue
    L = t.matrix_world.translation; exp = dm['RING_Y'] + k * cr['dz']
    z = own_top(t, L)
    if z is not None and abs(z - exp) < 0.01: up_ok += 1
    if abs(zr(sh)[1] - zr(t)[0]) < 0.005 and abs(zr(sh)[0] - dm['CEIL']) < 0.005: gap_ok += 1
    hf = FULL.ray_cast(Vector((L.x, L.y, exp + 0.3)), Vector((0, 0, -1)), 1.0)
    if hf[0] is not None and z is not None and abs(hf[0].z - z) < 1e-4:
        probes.append({'g': '屋顶升降踏步', 'item': f'上行第 {k} 级踏面', 'E': round(L.x, 4), 'N': round(L.y, 4), 'U': round(exp + 0.3, 4), 'dir': -1, 'maxd': 1.0, 'expect': round(exp, 4), 'tol': 0.01})
rows.append(('屋顶升降踏步', f'上行 16 级踏面高度 = {dm["RING_Y"]} + k × {cr["dz"]}（升起以后）', 16, up_ok, up_ok == 16))
rows.append(('屋顶升降踏步', f'上行 16 级的柱身从天花 {dm["CEIL"]} 一直接到踏面底（没有缝）', 16, gap_ok, gap_ok == 16))
for k in range(1, 17):
    t = OB.get(f'SM_Mech_RoofSteps_Dn{k:02d}')
    if t is None: continue
    L = t.matrix_world.translation; a = math.atan2(L.x, L.y)
    zs = [own_top(t, Vector((r * math.sin(a), r * math.cos(a), 0))) for r in (13.2, 11.6, 14.2)]   # 跨接缝的几级只有内侧半块
    z = next((z for z in zs if z is not None), None)
    if z is not None and abs(z - dm['RING_Y']) < 0.01: dn_ok += 1
rows.append(('屋顶升降踏步', f'下行 16 级白天都在环道面 {dm["RING_Y"]}', 16, dn_ok, dn_ok == 16))
kids = [o for o in OB if o.name.startswith('SM_Mech_') and o.parent and o.parent.name == 'SM_Mech_RoofSteps_Up16']
rows.append(('屋顶升降踏步', '最高一级上挂着虹门、浑天仪、铜栏杆、铜沿、光圈叶片', 5, len(kids), len(kids) == 5))
# 网格干不干净：每个物体的面数、四边面比例
stats = []
for ob in build + mech_inst:
    me = world_mesh(ob); me.calc_loop_triangles(); nq = sum(1 for p in me.polygons if len(p.vertices) == 4)
    bmx = bmesh.new(); bmx.from_mesh(me); nme = sum(1 for e in bmx.edges if not e.is_manifold); bmx.free()
    stats.append((ob.name, len(me.polygons), nq, len(me.loop_triangles), nme)); bpy.data.meshes.remove(me)
bpy.data.meshes.remove(wme)

# ───────── 5. 存 .blend、导出 FBX（三角化、带修改器）、导回来复核 ─────────
os.makedirs(OUT, exist_ok=True)
blend = os.path.join(OUT, NAME + '.blend'); fbx = os.path.join(OUT, NAME + '.fbx')
bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
exp_objs = [o for o in build if o not in fac_inst] + marks
FBXOPT = dict(use_selection=True, object_types={'MESH'}, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
              mesh_smooth_type='FACE', use_mesh_modifiers=True, use_triangles=True, add_leaf_bones=False, bake_anim=False, path_mode='COPY')
def export(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=path, **FBXOPT)
export(exp_objs, fbx)
fbx_placed = os.path.join(OUT, 'Dysis_Placed_v0_12.fbx'); export(fac_inst + mech_inst, fbx_placed)
fbx_kit = os.path.join(OUT, 'Dysis_Kit_v0_12.fbx')
tmp = []
for me in KIT:   # 构件库：每种网格一个物体，放在原点不转（UE 里一种一个资源）
    o = bpy.data.objects.new(me.name, me); sc.collection.objects.link(o); tmp.append(o)
bpy.context.view_layer.update(); export(tmp, fbx_kit)
def wbounds(ob, local=False):
    me = world_mesh(ob) if not local else ob.data
    vs = [v.co for v in me.vertices]
    b = [[round(min(v[i] for v in vs), 4) for i in range(3)], [round(max(v[i] for v in vs), 4) for i in range(3)]]
    if not local: bpy.data.meshes.remove(me)
    return b
def ntris(ob):
    me = world_mesh(ob); me.calc_loop_triangles(); n = len(me.loop_triangles); bpy.data.meshes.remove(me); return n
folders = {o.name: o.users_collection[0].name for o in exp_objs + fac_inst + mech_inst}
bounds = {o.name: wbounds(o) for o in exp_objs}; tris = {o.name: ntris(o) for o in exp_objs}
pbounds = {o.name: wbounds(o) for o in fac_inst + mech_inst}
kitinfo = {o.name: {'local': wbounds(o, True), 'tris': ntris(o), 'uses': kit_count[o.name]} for o in tmp}
insts = []
for o in fac_inst + mech_inst:   # 世界里的位置和绕 Z 的转角（有父部件的也按世界算）
    mw = o.matrix_world; L = mw.translation; th = math.degrees(math.atan2(mw[1][0], mw[0][0]))
    yaw = (90.0 - th + 180.0) % 360.0 - 180.0
    it = {'name': o.name, 'mesh': o.data.name, 'b_loc': [round(L.x, 5), round(L.y, 5), round(L.z, 5)], 'b_rot': round(th, 5),
          'ue_loc': [round(L.y * 100, 2), round(L.x * 100, 2), round(L.z * 100, 2)], 'ue_yaw': round(yaw, 4), 'grp': 'mech' if o in mech_inst else 'facade'}
    if o in mech_inst:
        it['parent'] = mech_parent.get(o.name); it['nocol'] = mech_info[o.name]['nocol']; it['motion'] = mech_info[o.name]['motion']; it['part'] = o['部件']; it['mech'] = o['所属机关']
    insts.append(it)
for o in tmp: bpy.data.objects.remove(o)
def reimport(path, expect, local=False):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.fbx(filepath=path)
    worst = 0; seen = 0
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH' or ob.name not in expect: continue
        seen += 1; b = expect[ob.name]['local'] if local else expect[ob.name]
        vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
        bb = [[min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]]
        worst = max(worst, max(abs(bb[j][i] - b[j][i]) for i in range(3) for j in range(2)))
    return seen, worst
for label, path, exp, loc in (('建筑', fbx, bounds, False), ('构件库（外立面 + 机关）', fbx_kit, kitinfo, True), ('外立面和机关摆好的', fbx_placed, pbounds, False)):
    seen, worst = reimport(path, exp, loc)
    rows.append(('FBX 复核', f'{label} FBX 导回 Blender 的物体数（应为 {len(exp)}）', len(exp), seen, seen == len(exp)))
    rows.append(('FBX 复核', f'{label} FBX 导回后包围盒的最大偏差（m）', 0.0, round(worst, 4), worst < 0.005))

json.dump({'rows': rows, 'bounds': bounds, 'stats': stats}, open(os.path.join(OUT, 'check.json'), 'w'), ensure_ascii=False, indent=1)
ue = {'name': NAME, 'bounds_cm': {}, 'tris': tris, 'folders': folders, 'instances': insts,
      'kit': {n: {'local_cm': [[round(i['local'][0][0] * 100, 1), round(-i['local'][1][1] * 100, 1), round(i['local'][0][2] * 100, 1)], [round(i['local'][1][0] * 100, 1), round(-i['local'][0][1] * 100, 1), round(i['local'][1][2] * 100, 1)]], 'tris': i['tris'], 'uses': i['uses']} for n, i in kitinfo.items()}, 'markers_cm': {'SM_MARK_N_0deg_r30': [3000, 0, 50], 'SM_MARK_E_90deg_r30': [0, 3000, 50], 'SM_MARK_UP_y45': [0, 0, 4500]}, 'probes': probes}
for n, (lo, hi) in bounds.items():   # Blender（X 东、Y 北、Z 上，米）→ UE（X 北、Y 东、Z 上，厘米）
    ue['bounds_cm'][n] = [[round(lo[1] * 100, 1), round(lo[0] * 100, 1), round(lo[2] * 100, 1)], [round(hi[1] * 100, 1), round(hi[0] * 100, 1), round(hi[2] * 100, 1)]]
json.dump(ue, open(os.path.join(OUT, 'ue_expect.json'), 'w'), ensure_ascii=False)
print('objects', len(bounds), 'facade pieces', len(fac_inst), 'mech parts', len(mech_inst), 'kit meshes', len(KIT), 'probes', len(probes))
npass = sum(1 for r in rows if r[4]); print('checks', len(rows), 'pass', npass)
for r in rows:
    if not r[4]: print('FAIL', r)
