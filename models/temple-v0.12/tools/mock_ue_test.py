# 在没有 UE 的地方把 ue_import_temple.py 跑一遍：假的 unreal 模块，网格直接从 FBX 文件读，
# 按 UE 的 FBX 导入规则换算（节点变换烘进顶点，FBX 的 Y 向上右手系 → UE 的 Z 向上左手系：UE = (x, z, y)，单位厘米）。
# 射线用 mathutils 的 BVH 在摆好的构件上打。
import sys, types, struct, zlib, math, json, os
import bpy   # mathutils 跟着 bpy 一起来
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree

SCRIPT, FBX = sys.argv[1], sys.argv[2]
FLIP = len(sys.argv) > 3 and sys.argv[3] == 'mirror'   # 故意镜像，看脚本能不能发现

# ── 读 FBX ──
def parse_fbx(path):
    data = open(path, 'rb').read(); ver = struct.unpack('<I', data[23:27])[0]; big = ver >= 7500
    def rd_prop(b, i):
        t = chr(b[i]); i += 1
        if t in 'YCIFDL':
            fmt = {'Y': '<h', 'C': '<?', 'I': '<i', 'F': '<f', 'D': '<d', 'L': '<q'}[t]; n = struct.calcsize(fmt); return struct.unpack(fmt, b[i:i + n])[0], i + n
        if t in 'SR':
            n = struct.unpack('<I', b[i:i + 4])[0]; i += 4; v = b[i:i + n]; return (v.decode('utf8', 'replace') if t == 'S' else v), i + n
        ln, enc, cl = struct.unpack('<III', b[i:i + 12]); i += 12; raw = b[i:i + cl]; i += cl
        if enc: raw = zlib.decompress(raw)
        fmt = {'f': 'f', 'd': 'd', 'l': 'q', 'i': 'i', 'b': '?'}[t]; return list(struct.unpack('<%d%s' % (ln, fmt), raw)), i
    def rd_node(b, i):
        if big: end, np_, pl = struct.unpack('<QQQ', b[i:i + 24]); i += 24
        else: end, np_, pl = struct.unpack('<III', b[i:i + 12]); i += 12
        nl = b[i]; i += 1
        if end == 0: return None, i
        name = b[i:i + nl].decode(); i += nl; props = []
        for _ in range(np_): v, i = rd_prop(b, i); props.append(v)
        kids = []
        while i < end:
            k, i = rd_node(b, i)
            if k is None: break
            kids.append(k)
        return (name, props, kids), end
    i = 27; top = []
    while i < len(data) - 200:
        n, i2 = rd_node(data, i)
        if n is None: break
        top.append(n); i = i2
    find = lambda nodes, name: [n for n in nodes if n[0] == name]
    gs = {p[1][0]: p[1][-1] for p in find(find(top, 'GlobalSettings')[0][2], 'Properties70')[0][2]}
    assert gs['UpAxis'] == 1 and gs['FrontAxis'] == 2 and gs['CoordAxis'] == 0 and gs['UnitScaleFactor'] == 1.0, gs
    objs = find(top, 'Objects')[0][2]; conns = find(top, 'Connections')[0][2]
    geos = {n[1][0]: n for n in objs if n[0] == 'Geometry'}
    out = {}
    for n in objs:
        if n[0] != 'Model': continue
        name = n[1][1].split('\x00')[0]
        pr = {p[1][0]: p[1][-3:] for p in find(n[2], 'Properties70')[0][2]}
        T = Vector(pr.get('Lcl Translation', [0, 0, 0])); R = pr.get('Lcl Rotation', [0, 0, 0]); S = pr.get('Lcl Scaling', [1, 1, 1])
        Mx = Matrix.Translation(T) @ Euler([math.radians(x) for x in R], 'XYZ').to_matrix().to_4x4() @ Matrix.Diagonal((*S, 1))
        gid = [c[1][1] for c in conns if c[1][2] == n[1][0] and c[1][1] in geos][0]
        g = geos[gid][2]; v = find(g, 'Vertices')[0][1][0]; pvi = find(g, 'PolygonVertexIndex')[0][1][0]
        verts = []
        for k in range(0, len(v), 3):
            w = Mx @ Vector((v[k], v[k + 1], v[k + 2]))        # FBX 全局（厘米，Y 向上）；导入时烘进顶点
            u = Vector((w.x, w.z, w.y))                           # UE：Z 向上、左手
            if FLIP: u.y = -u.y
            verts.append(u)
        polys, cur = [], []
        for idx in pvi:
            if idx < 0: cur.append(-idx - 1); polys.append(cur); cur = []
            else: cur.append(idx)
        out[name] = (verts, polys)
    return out

# ── 假的 unreal ──
U = types.ModuleType('unreal'); LOGS = []
U.log = lambda s: LOGS.append(str(s)); U.log_warning = lambda s: LOGS.append('WARN ' + str(s))
class Obj:
    def __init__(self, **kw): self.__dict__['_p'] = dict(kw)
    def set_editor_property(self, k, v): self._p[k] = v
    def get_editor_property(self, k):
        if k not in self._p: self._p[k] = Obj()
        return self._p[k]
class V(Vector): pass
def Vec(x=0.0, y=0.0, z=0.0): return Vector((x, y, z))
U.Vector = Vec
class Rot:
    def __init__(self, roll=0.0, pitch=0.0, yaw=0.0): self.roll, self.pitch, self.yaw = roll, pitch, yaw
U.Rotator = Rot
U.FbxImportUI = lambda: Obj(static_mesh_import_data=Obj())
U.FBXImportType = types.SimpleNamespace(FBXIT_STATIC_MESH='SM')
U.FBXNormalImportMethod = types.SimpleNamespace(FBXNIM_IMPORT_NORMALS='N')
U.AssetImportTask = lambda: Obj()
U.CollisionTraceFlag = types.SimpleNamespace(CTF_USE_COMPLEX_AS_SIMPLE='CAS')
ASSETS = {}
class StaticMesh:
    def __init__(self, name, verts, polys):
        self.name, self.verts, self.polys = name, verts, polys; self.props = {'body_setup': Obj()}
    def get_name(self): return self.name
    def get_bounding_box(self):
        lo = Vector((min(v.x for v in self.verts), min(v.y for v in self.verts), min(v.z for v in self.verts)))
        hi = Vector((max(v.x for v in self.verts), max(v.y for v in self.verts), max(v.z for v in self.verts)))
        return Obj(min=lo, max=hi)
    def get_editor_property(self, k): return self.props[k]
    def get_num_triangles(self, lod): return sum(len(p) - 2 for p in self.polys)
U.StaticMesh = StaticMesh
IMPORTED = {}
class Tools:
    def import_asset_tasks(self, tasks):
        t = tasks[0]; smd = t._p['options']._p['static_mesh_import_data']._p
        IMPORTED.update(smd); assert smd['transform_vertex_to_absolute'] and not smd['combine_meshes'] and not smd['auto_generate_collision']
        ms = parse_fbx(t._p['filename']); print('导入', os.path.basename(t._p['filename']), len(ms), '个网格')
        for n, (v, p) in ms.items(): ASSETS[t._p['destination_path'] + '/' + n] = StaticMesh(n, v, p)
U.AssetToolsHelpers = types.SimpleNamespace(get_asset_tools=lambda: Tools())
U.EditorAssetLibrary = types.SimpleNamespace(list_assets=lambda d, recursive=True, include_folder=False: [k for k in ASSETS if k.startswith(d)],
                                             load_asset=lambda p: ASSETS[p], save_loaded_asset=lambda m: True)
ACTORS = []
class Actor:
    def __init__(self, mesh, loc, rot):
        self.mesh, self.loc, self.yaw = mesh, Vector((loc.x, loc.y, loc.z)), rot.yaw; self.folder = ''; self.label = ''
        a = math.radians(self.yaw); c, s = math.cos(a), math.sin(a)
        self.wv = [Vector((v.x * c - v.y * s, v.x * s + v.y * c, v.z)) + self.loc for v in mesh.verts]   # UE：Yaw 正方向 X→Y
        self.bvh = BVHTree.FromPolygons(self.wv, mesh.polys)
    def set_actor_label(self, l): self.label = l
    def set_folder_path(self, f): self.folder = f
    def get_folder_path(self): return self.folder
    def destroy_actor(self): ACTORS.remove(self)
    def get_actor_bounds(self, only):   # 和 UE 一样：把网格的包围盒 8 个角变换过去再取包围盒（转过的构件会偏大）
        b = self.mesh.get_bounding_box(); lo, hi = b._p['min'], b._p['max']; a = math.radians(self.yaw); c, s = math.cos(a), math.sin(a)
        cs = [Vector((x * c - y * s, x * s + y * c, z)) + self.loc for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
        l2 = Vector((min(v.x for v in cs), min(v.y for v in cs), min(v.z for v in cs))); h2 = Vector((max(v.x for v in cs), max(v.y for v in cs), max(v.z for v in cs)))
        return (l2 + h2) / 2, (h2 - l2) / 2
    def get_actor_location(self): return self.loc
    @property
    def static_mesh_component(self): return self
    def set_mobility(self, m): self.mobility = m
    def set_collision_profile_name(self, n): self.nocol = (n == 'NoCollision')
    def attach_to_actor(self, parent, socket, a, b, c, weld): assert parent in ACTORS; self.parent = parent
    def get_actor_rotation(self): return Rot(yaw=self.yaw)
class ActorSub:
    def get_all_level_actors(self): return list(ACTORS)
    def spawn_actor_from_object(self, m, loc, rot): a = Actor(m, loc, rot); ACTORS.append(a); return a
U.EditorActorSubsystem = ActorSub; U.UnrealEditorSubsystem = type('UES', (), {'get_editor_world': lambda self: 'WORLD'})
U.get_editor_subsystem = lambda cls: cls()
class Hit:
    def __init__(self, loc, d): self.loc, self.d = loc, d
    def to_tuple(self): return (-1, 0.5, self.d, self.loc, self.loc, Vector((0, 0, 1)), Vector((0, 0, 1)), Vector(), Vector(), 0.0, 0, 0, 0, True, False, None, None, None, '', '')
NTRACE = [0]
def line_trace_single(world, s, e, ch, cplx, ignore, dbg, ignore_self):
    NTRACE[0] += 1; d = e - s; L = d.length; best = None
    for a in ACTORS:
        if a in ignore or getattr(a, 'nocol', False): continue   # NoCollision 的射线打不到
        h = a.bvh.ray_cast(s, d.normalized(), L)
        if h[0] is not None and (best is None or h[3] < best[1]): best = (h[0], h[3])
    return None if best is None else Hit(best[0], best[1])
U.SystemLibrary = types.SimpleNamespace(line_trace_single=line_trace_single)
U.ComponentMobility = types.SimpleNamespace(MOVABLE='M'); U.AttachmentRule = types.SimpleNamespace(KEEP_WORLD='KW')
U.TraceTypeQuery = types.SimpleNamespace(TRACE_TYPE_QUERY1=1); U.DrawDebugTrace = types.SimpleNamespace(NONE=0)
U.Paths = types.SimpleNamespace(project_saved_dir=lambda: os.path.dirname(os.path.abspath(SCRIPT)))
class Slow:
    def __init__(self, n, t): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def make_dialog(self, b): pass
    def enter_progress_frame(self, n): pass
U.ScopedSlowTask = Slow
sys.modules['unreal'] = U

src = open(SCRIPT, encoding='utf-8').read().replace('FBX = r"C:/Dysis/Dysis_Temple_v0_12.fbx"', f'FBX = r"{os.path.abspath(FBX)}"')
exec(compile(src, SCRIPT, 'exec'), {'__name__': '__main__'})
print('\n'.join(l for l in LOGS if not l.startswith('  （')))
print('traces', NTRACE[0], 'actors', len(ACTORS), 'movable', sum(1 for a in ACTORS if getattr(a, 'mobility', None)), 'attached', sum(1 for a in ACTORS if getattr(a, 'parent', None)), 'nocol', sum(1 for a in ACTORS if getattr(a, 'nocol', False)))
