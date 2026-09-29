# 预览：鸟瞰、剖面、墙里楼梯的展开剖面；wire=1 时叠上布线
import bpy, math, sys
from mathutils import Vector
src, outdir, which, samples, wire = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5] == '1'
bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples
try: sc.cycles.use_denoising = True
except Exception: pass
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.62, 0.7, 0.82, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.55
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN')); sc.collection.objects.link(sun); sun.data.energy = 2.6; sun.data.angle = math.radians(2)
def aim(ob, target): ob.rotation_euler = (target - ob.location).to_track_quat('-Z', 'Y').to_euler()
def P(az, r, y=0.0): a = math.radians(az); return Vector((r * math.sin(a), r * math.cos(a), y))
sun.location = P(235, 50, 40); aim(sun, Vector((0, 0, 0)))
if wire:
    wm = bpy.data.materials.new('WIRE'); wm.use_nodes = True; wm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.05, 0.05, 0.08, 1)
    for ob in list(sc.objects):
        if ob.type != 'MESH' or ob.name.startswith('CUT_') or ob.hide_render: continue
        cp = ob.copy(); sc.collection.objects.link(cp)
        m = cp.modifiers.new('wf', 'WIREFRAME'); m.thickness = 0.025; m.use_replace = True; m.use_even_offset = False
        cp.data = ob.data; cp.active_material = wm
        for s in cp.material_slots: s.link = 'OBJECT'; s.material = wm
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam
def shot(path, loc, target, lens=35, ortho=None, clip=(0.1, 1000)):
    cam.location = loc; aim(cam, target)
    cam.data.type = 'ORTHO' if ortho else 'PERSP'
    if ortho: cam.data.ortho_scale = ortho
    cam.data.lens = lens; cam.data.clip_start, cam.data.clip_end = clip
    sc.render.filepath = path; bpy.ops.render.render(write_still=True); print('wrote', path)
if which == 'aerial': shot(f'{outdir}/preview_aerial.png', P(212, 105, 48), Vector((0, 0, 15)), lens=38)
if which == 'section': shot(f'{outdir}/preview_section.png', P(180, 80, 18.5), P(0, 0, 18.5), ortho=86, clip=(80.0, 400))
if which == 'plan': shot(f'{outdir}/preview_plan.png', Vector((0, 0, 120)), Vector((0, 0.001, 0)), ortho=80, clip=(1, 400))
if which == 'ts':   # 站在殿心朝 290° 看，近裁剪 16.3 m：正好从楼梯中线剖开，看到西北墙里的 TS 楼梯
    shot(f'{outdir}/preview_stair_TS.png', Vector((0, 0, 19)), P(290, 10, 19), ortho=13, clip=(16.3, 60))
if which == 'tr':
    shot(f'{outdir}/preview_stair_TR.png', Vector((0, 0, 10)), P(145, 10, 10), ortho=13, clip=(16.3, 60))
if which == 'wallclose':   # 从殿里看 c 窗和 b2 窗一带的墙
    shot(f'{outdir}/preview_wall_inside.png', P(80, 6, 20), P(262, 15.5, 19.5), lens=30)
if which == 'planL1':   # 从上往下看二层（把 7 m 以上的裁掉），叠布线
    shot(f'{outdir}/preview_plan_L1.png', Vector((0, 0, 120)), Vector((0, 0.001, 0)), ortho=36, clip=(113, 400))
if which == 'aerialwire':
    shot(f'{outdir}/preview_aerial_wire.png', P(212, 105, 48), Vector((0, 0, 15)), lens=38)
if which == 'facadekit':   # 外立面按构件种类上色：同一种颜色相同（共用一份网格）
    import colorsys
    kinds = sorted({o.data.name for o in sc.objects if o.type == 'MESH' and o.name.startswith('SM_Facade_') and o.data.name.startswith('SM_Kit_')})
    for i, k in enumerate(kinds):
        m = bpy.data.materials.new('K' + k); m.use_nodes = True
        m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*colorsys.hsv_to_rgb((i * 0.618) % 1, 0.55, 0.95), 1)
        for o in sc.objects:
            if o.type == 'MESH' and o.data.name == k:
                for s in o.material_slots: s.link = 'OBJECT'; s.material = m
    shot(f'{outdir}/preview_facade_kit.png', P(118, 62, 20), P(118, 0, 16), lens=40)
if which in ('mechW', 'mechE'):   # 剖面里把机关标成橙色；朝西看是西半边（三相像、天鹅、双子、拉杆 A），朝东看是东半边（女神、日之龛、拉杆 B、浮雕）
    hm = bpy.data.materials.new('HL'); hm.use_nodes = True
    bs = hm.node_tree.nodes['Principled BSDF']; bs.inputs['Base Color'].default_value = (1.0, 0.45, 0.08, 1)
    for o in sc.objects:
        if o.type == 'MESH' and o.name.startswith('SM_Mech_') and not o.name.startswith('SM_Mech_Water'):
            for s in o.material_slots: s.link = 'OBJECT'; s.material = hm
    for n in ('SM_Mech_Water_Sea',):
        if n in bpy.data.objects: bpy.data.objects[n].hide_render = True
    look = 280 if which == 'mechW' else 110
    for z in (3, 10, 18, 26):   # 中庭里挂几盏灯（光圈合着，屋顶是暗的）
        L = bpy.data.objects.new(f'PL{z}', bpy.data.lights.new(f'PL{z}', 'POINT')); L.data.energy = 700; L.data.shadow_soft_size = 2.0
        L.location = (0, 0, z); sc.collection.objects.link(L)
    shot(f'{outdir}/preview_{which}.png', P((look + 180) % 360, 7.5, 13), P(look, 13, 14), lens=14)
