# 狄西斯的日落回廊 v0.12 · 建筑模型（Blender）
# 墙体重新建：一整圈干净的墙 + 布尔开洞（窗洞、门洞、墙里楼梯的空腔都是单独的切割体，修改器不应用，挪切割体就能改）。
# 其余构件用灰盒导出的几何：顶点焊接、三角面并成四边面，按构件拆成单独物体（每根柱子、每层楼板、每一级屋顶踏步……），轴心放在构件底部。
# 然后量数值、存 .blend、导出给 UE 的 FBX、导回来复核、写 UE 脚本要用的期望值。
# 运行：python3 build_blend2.py <temple.glb> <data.json> <输出目录>
import bpy, bmesh, json, math, sys, os
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
for cat in sorted(c for c in bycat if c.startswith('Facade~')):
    objs = bycat[cat]; sub = {k: objs[0].get(k) for k in ('t', 'band', 'k', 'key', 'az', 'r', 'y')}
    ob = join(objs, 'tmp'); clean(ob)
    for pk in list(ob.keys()): del ob[pk]
    if sub['t'] == 'Ring':   # 整圈的线脚、檐口、女儿墙：绕殿心一圈，轴心在殿心
        me = ob.data; pv = pivot_of(me, True); me.transform(Matrix.Translation(-pv)); ob.location = pv
        ob.name = me.name = 'SM_Facade_' + sub['key']; compact_materials(me); smooth(ob); made['FacadeRing'].append(ob); continue
    t, band, k = sub['t'], sub['band'], sub['k']
    before = world_pts(ob)
    az = sub['az']; base = P(az, sub['r'], sub['y']); th = math.pi - math.radians(az)
    ob.data.transform(Matrix.Rotation(-th, 4, 'Z') @ Matrix.Translation(-base))
    ob.rotation_mode = 'XYZ'; ob.location = base; ob.rotation_euler = (0, 0, th); compact_materials(ob.data)
    kind = t + (f'_L{band}' if band is not None else '') + (f"_{sub['key']}" if sub['key'] else '')
    # 同一种：同类型、顶点数一样、每个顶点到对方最近顶点不超过 2 mm
    mine = [v.co.copy() for v in ob.data.vertices]; same = None
    for km in kit.get(kind, []):
        if len(km.vertices) != len(mine) or [m.name for m in km.materials] != [m.name for m in ob.data.materials]: continue   # 面数可能差一两个（三角面合没合），形状一样就算
        theirs = [v.co.copy() for v in km.vertices]
        if max_nn(mine, theirs) < 0.002 and max_nn(theirs, mine) < 0.002: same = km; break
    if same:
        old = ob.data; ob.data = same; bpy.data.meshes.remove(old)
    else:
        n = len(kit.get(kind, [])); ob.data.name = 'SM_Kit_Facade_' + kind + (f'_v{n + 1}' if n else ''); smooth(ob)
        kit.setdefault(kind, []).append(ob.data)
    kit_count[ob.data.name] = kit_count.get(ob.data.name, 0) + 1
    ob.name = 'SM_Facade_' + kind + (f'_{k:02d}' if k is not None else '')
    ob['类型'] = TYPE_CN[t]; ob['方位角'] = round(az, 3); ob['底高'] = round(sub['y'], 3)
    if band is not None: ob['所在层'] = ['一层', '二层', '三层', '四层'][band]
    bpy.context.view_layer.update()
    after = world_pts(ob)
    _dv = max(max_nn(after, before), max_nn(before, after)); fac_dev = max(fac_dev, _dv)
    made[FAC_GROUP[t]].append(ob); fac_inst.append(ob)
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
made['RoofArch'] = take('RoofArch', single='RainbowArch')
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
colf('Site', '06 场地·台基·柱廊·门廊·小岛'); colf('Pavilion', '07 水亭'); colf('RoofRing', '08 屋顶环道（每一块单独，升降用）')
colf('RoofBridge', '09 屋顶细桥'); colf('RoofArch', '10 虹门'); colf('Markers', '99 方位标记（核对用，可删）')
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
        cols[cat].objects.link(o)
for o in marks:
    for c in list(o.users_collection): c.objects.unlink(o)
    cols['Markers'].objects.link(o)
bpy.context.view_layer.layer_collection.children[NAME].children[cols['Cut'].name].hide_viewport = True   # 切割体默认隐藏（眼睛图标），布尔照样算
build = [o for cat, obs in made.items() for o in obs]

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
    h = ALL.ray_cast(p, Vector((0, 0, sgn)), maxd)
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
check('屋顶环道', '最高平台 @T_AZ', cr['TOP_Y'], down(P(cr['T_AZ'], 11.8, 45)))
w_up = ((cr['UP_TOP'][0] - cr['LAND'][1]) % 360) / 15
for k in (1, 5, 10, 15):
    a = cr['LAND'][1] + (k - 0.5) * w_up
    check('屋顶环道', f'上行第 {k} 级 @{a % 360:.1f}°', dm['RING_Y'] + k * cr['dz'], down(P(a, 13.2, 45)))
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
rows.append(('外立面', f'共用的网格（{len(KIT)} 种，同一种的构件共用一份）', len(KIT), len({o.data.name for o in fac_inst}), len(KIT) == len({o.data.name for o in fac_inst})))
rows.append(('外立面', '换成各自轴心、共用网格以后，每件的顶点和灰盒原位的最大偏差（m）', 0.0, round(fac_dev, 4), fac_dev < 0.002))
hp = {}
for ob in fac_inst:
    me = world_mesh(ob); own = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [q.vertices[:] for q in me.polygons])
    z0, z1 = min(v.co.z for v in me.vertices), max(v.co.z for v in me.vertices); bpy.data.meshes.remove(me)
    az = ob['方位角']; d = (P(az, -1, 0) - P(az, 0, 0)).normalized(); t = ob['类型']; hp.setdefault(t, [0, 0]); hp[t][1] += 1
    for f in (0.5, 0.3, 0.7, 0.1, 0.9, 0.03):
        st = P(az, 19.0, z0 + (z1 - z0) * f); ha = ALL.ray_cast(st, d, 5); ho = own.ray_cast(st, d, 5)
        if ha[0] is not None and ho[0] is not None and abs(ha[3] - ho[3]) < 1e-4:
            probes.append({'g': '外立面', 'item': f'{ob.name} 正面', 'kind': t, 'E': round(st.x, 4), 'N': round(st.y, 4), 'U': round(st.z, 4),
                           'dE': round(d.x, 6), 'dN': round(d.y, 6), 'dU': 0.0, 'maxd': 5, 'dist': round(ha[3], 4), 'tol': 0.01})
            hp[t][0] += 1; break
for t, (a, b) in hp.items():
    rows.append(('外立面', f'{t}：从外面水平打过去先打到它自己的件数（被柱廊、门廊挡住的不算）', f'≤ {b}', a, a > 0))
# 网格干不干净：每个物体的面数、四边面比例
stats = []
for ob in build:
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
fbx_placed = os.path.join(OUT, 'Dysis_Facade_Placed_v0_12.fbx'); export(fac_inst, fbx_placed)
fbx_kit = os.path.join(OUT, 'Dysis_Facade_Kit_v0_12.fbx')
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
folders = {o.name: o.users_collection[0].name for o in exp_objs + fac_inst}
bounds = {o.name: wbounds(o) for o in exp_objs}; tris = {o.name: ntris(o) for o in exp_objs}
pbounds = {o.name: wbounds(o) for o in fac_inst}
kitinfo = {o.name: {'local': wbounds(o, True), 'tris': ntris(o), 'uses': kit_count[o.name]} for o in tmp}
insts = []
for o in fac_inst:
    th = math.degrees(o.rotation_euler.z); L = o.location
    yaw = (90.0 - th + 180.0) % 360.0 - 180.0
    insts.append({'name': o.name, 'mesh': o.data.name, 'b_loc': [round(L.x, 5), round(L.y, 5), round(L.z, 5)], 'b_rot': round(th, 5),
                  'ue_loc': [round(L.y * 100, 2), round(L.x * 100, 2), round(L.z * 100, 2)], 'ue_yaw': round(yaw, 4)})
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
for label, path, exp, loc in (('建筑', fbx, bounds, False), ('外立面构件库', fbx_kit, kitinfo, True), ('外立面摆好的', fbx_placed, pbounds, False)):
    seen, worst = reimport(path, exp, loc)
    rows.append(('FBX 复核', f'{label} FBX 导回 Blender 的物体数（应为 {len(exp)}）', len(exp), seen, seen == len(exp)))
    rows.append(('FBX 复核', f'{label} FBX 导回后包围盒的最大偏差（m）', 0.0, round(worst, 4), worst < 0.005))

json.dump({'rows': rows, 'bounds': bounds, 'stats': stats}, open(os.path.join(OUT, 'check.json'), 'w'), ensure_ascii=False, indent=1)
ue = {'name': NAME, 'bounds_cm': {}, 'tris': tris, 'folders': folders, 'instances': insts,
      'kit': {n: {'local_cm': [[round(i['local'][0][0] * 100, 1), round(-i['local'][1][1] * 100, 1), round(i['local'][0][2] * 100, 1)], [round(i['local'][1][0] * 100, 1), round(-i['local'][0][1] * 100, 1), round(i['local'][1][2] * 100, 1)]], 'tris': i['tris'], 'uses': i['uses']} for n, i in kitinfo.items()}, 'markers_cm': {'SM_MARK_N_0deg_r30': [3000, 0, 50], 'SM_MARK_E_90deg_r30': [0, 3000, 50], 'SM_MARK_UP_y45': [0, 0, 4500]}, 'probes': probes}
for n, (lo, hi) in bounds.items():   # Blender（X 东、Y 北、Z 上，米）→ UE（X 北、Y 东、Z 上，厘米）
    ue['bounds_cm'][n] = [[round(lo[1] * 100, 1), round(lo[0] * 100, 1), round(lo[2] * 100, 1)], [round(hi[1] * 100, 1), round(hi[0] * 100, 1), round(hi[2] * 100, 1)]]
json.dump(ue, open(os.path.join(OUT, 'ue_expect.json'), 'w'), ensure_ascii=False)
print('objects', len(bounds), 'facade pieces', len(fac_inst), 'kit meshes', len(KIT), 'probes', len(probes))
npass = sum(1 for r in rows if r[4]); print('checks', len(rows), 'pass', npass)
for r in rows:
    if not r[4]: print('FAIL', r)
