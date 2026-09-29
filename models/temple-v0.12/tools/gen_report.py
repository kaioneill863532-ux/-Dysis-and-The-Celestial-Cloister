# 核对报告（Markdown）：Blender 里的核对 + 模拟 UE 跑脚本的结果 + 网格统计
import json, sys, re, subprocess
src = sys.argv[1]; C = json.load(open(f'{src}/check.json')); U = json.load(open(f'{src}/ue_expect.json'))
mock = subprocess.run(['python3', 'mock_ue_test.py', f'{src}/ue_import_temple.py', f'{src}/Dysis_Temple_v0_12.fbx'], capture_output=True, text=True).stdout
m = re.search(r'UE 核对：(\d+)/(\d+) 通过', mock); ue_pass, ue_tot = int(m.group(1)), int(m.group(2))
ue_groups = re.findall(r'^  (\S+)：(\d+)/(\d+)$', mock, re.M)
rows = C['rows']; npass = sum(1 for r in rows if r[4])
L = ['# 日落回廊 v0.12 建筑模型 · 数值核对报告', '',
     '模型按 v0.12 灰盒导出的几何建：墙体（含墙里的两段楼梯）在 Blender 里用整圈墙 + 布尔开洞重新建，其余构件（外立面、机关也一样）用灰盒几何清理后拆成单独物体。',
     '下面的数值都是**从做好的模型上量出来的**（射线打到模型表面、读顶点），和施工图 / 灰盒里的设计值对比。', '',
     '## 结论', '',
     f'| 在哪里量 | 通过 |', '|---|---|',
     f'| Blender（.blend 里算完布尔的模型） | **{npass} / {len(rows)}** |',
     f'| UE 导入脚本（在模拟的 UE 里跑：网格直接读 FBX 文件，按 UE 的导入规则换算） | **{ue_pass} / {ue_tot}** |', '',
     '模拟的 UE 能证明 FBX 的内容、脚本的换算和摆放逻辑是对的；真正的 UE 编辑器我这里跑不了，请在 UE 里执行一次 `ue_import_temple.py`，它会自己打出同样的核对报告（最后一行“全部通过”就对了）。', '',
     '## 网格', '']
by = {}
for n, f, q, t, nm in C['stats']:
    g = U['folders'].get(n, '?'); b = by.setdefault(g, [0, 0, 0, 0, 0]); b[0] += 1; b[1] += f; b[2] += q; b[3] += t; b[4] += nm
L += ['| 集合 | 物体数 | 面数 | 其中四边面 | 三角形（导出 UE） |', '|---|---:|---:|---:|---:|']
for g in sorted(by):
    b = by[g]; L.append(f'| {g} | {b[0]} | {b[1]} | {b[2]}（{100 * b[2] // max(1, b[1])}%） | {b[3]} |')
tot = [sum(b[i] for b in by.values()) for i in range(5)]
L.append(f'| **合计** | **{tot[0]}** | **{tot[1]}** | **{tot[2]}** | **{tot[3]}** |')
wall = next(s for s in C['stats'] if s[0] == 'SM_Wall')
L += ['', f'- 墙体开完所有洞以后是一个封闭实体（非流形边 {wall[4]} 条）。原来灰盒导出的墙是 7.5 万个碎三角面拼的，现在底模是 1440 个四边面的整圈墙，开洞以后 {wall[1]} 个面。',
      '- 其余构件：重合的顶点焊在一起，三角面并成四边面（整体 {:.0f}% 是四边面）；柱子的柱身和柱础、柱头之间这类看不见的接口是开口的，不影响使用。'.format(100 * tot[2] / tot[1]), '']
FK = {n: k for n, k in U['kit'].items() if n.startswith('SM_Kit_Facade_')}
nf = sum(1 for i in U['instances'] if i['grp'] == 'facade'); nm = sum(1 for i in U['instances'] if i['grp'] == 'mech')
L += ['## 外立面构件库', '', f"外立面拆成 {nf} 件，每件一个物体；一模一样的共用一份网格，一共 {len(FK)} 种：", '',
      '| 构件网格 | 用在几件 | 三角形 |', '|---|---:|---:|'] + [f"| `{n}` | {k['uses']} | {k['tris']} |" for n, k in FK.items()] + ['']
L += ['## 机关', '', f"机关、道具、雕像、水面一共 {nm} 个部件，每个部件一个物体，轴心放在转轴、铰链或滑动的基准点上；一模一样的共用网格（两根拉杆、双子两尊像、同宽的光圈叶片、屋顶上行 15 级踏面和铜沿、下行大部分踏面）。"
      '每个部件的轴心坐标、挂在哪个部件下、怎么动，见 [机关清单.md](机关清单.md)。', '']
L += ['## UE 脚本核对（模拟）', '', '| 分组 | 通过 |', '|---|---|'] + [f'| {g} | {a} / {b} |' for g, a, b in ue_groups] + ['']
L += ['## Blender 核对明细', '']
cur = None
for g, item, exp, got, ok in rows:
    if g != cur:
        L += ['', f'### {g}', '', '| 项目 | 设计值 | 模型上量到 | |', '|---|---|---|---|']; cur = g
    fmt = lambda x: '—' if x is None else (', '.join(str(v) for v in x) if isinstance(x, list) else str(x))
    L.append(f'| {item} | {fmt(exp)} | {fmt(got)} | {"✔" if ok else "✘"} |')
L += ['', '## 量法', '',
      '- 高度：在指定方位角、半径处从上往下（或从下往上）打一条竖直射线，读打到的高度。楼板取 r 13.8 m，避开柱子；栏杆取 r 12.34 m。',
      '- 主光窗：沿窗洞中线从内墙面外 5 cm 打到外墙面外 5 cm，中间不能碰到墙；窗台从窗洞中间往下打、拱顶往上打；窗洞左右各往外 0.25 m 要是墙。',
      '- 墙里楼梯：灰盒按 1.25° 一片摆踏步，每片取中点量踏面高度和头顶净高（顶 − 踏面）；门从殿里水平看进去要能看到楼梯外侧墙；朝外的小窗从楼梯里水平往外看要通。',
      '- 柱子：从中庭往外水平打射线，打到柱面的距离对上柱子半径才算“立着”。',
      '- 外立面、机关：每件换成自己的轴心、共用网格以后，和灰盒原位逐点比对。外立面每件从外面（半径 19 m）水平打一条射线到它正面，UE 里再打一遍比距离。',
      '- 机关位置：拉杆、石板、三相像和铜镜、天鹅、双子、女神、棱镜、日之龛、塞勒涅、浑天仪、半桥的轴心，和灰盒的设计值比；能踩的台面（三相像、天鹅、女神的台座，窗下石沿，半桥）从上往下打射线量高度，UE 里再打一遍。',
      '- FBX：导出后再导回 Blender，比较每个物体的包围盒。', '']
open(f'{src}/核对报告.md', 'w', encoding='utf-8').write('\n'.join(L)); print('ok', npass, len(rows), ue_pass, ue_tot)
