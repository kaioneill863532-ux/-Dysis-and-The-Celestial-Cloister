# 机关清单：每个部件的轴心（施工图坐标和 UE 坐标）、朝向、挂在哪、怎么动
import json, math, sys
src = sys.argv[1]; U = json.load(open(f'{src}/ue_expect.json'))
its = sorted([i for i in U['instances'] if i['grp'] == 'mech'], key=lambda i: (U['folders'][i['name']], i['name']))
L = ['# 日落回廊 v0.12 · 机关清单', '',
     '每个机关部件在 Blender 里是一个单独的物体，在 UE 里是一个 Actor（可移动）。**轴心**放在它动起来绕的那根轴、那个铰链，或者滑动的基准点上：程序做动画时直接转、挪这个 Actor 就行。',
     '', '- 施工图坐标：方位角 az（北 0°，顺时针）、离殿心的半径 r、高 y，单位米。',
     '- UE 坐标：X = 100·r·cos(az)，Y = 100·r·sin(az)，Z = 100·y，单位厘米；Yaw 是 Actor 的 Z 旋转。',
     '- “挂在”：UE 脚本已经把它挂到这个部件下面（Attach，保持世界位置），父部件动它跟着动。',
     '- 摆的状态：石板、拉杆、三相像（白天那一格、日相）、天鹅（开局那一格）、光圈（合拢）是开局的样子；窗台石沿和虹之龛、棱镜、半桥是**伸出来以后**的样子（灰盒开局时它们缩着、藏着，缩多少见“怎么动”）；屋顶的上行踏步是升起来以后的样子。',
     '- 水面、瀑布、海、虹桥在 UE 里设成 NoCollision（不挡人、不挡射线）。', '']
cur = None; prev_mo = None
for it in its:
    if it['mech'] != cur:
        cur = it['mech']; prev_mo = None; L += ['', f"## {U['folders'][it['name']].split(' ', 1)[1]}", '', '| 部件 | UE 名字 | 轴心 施工图（az°, r, y） | 轴心 UE（X, Y, Z） | Yaw | 挂在 | 怎么动 |', '|---|---|---|---|---:|---|---|']
    x, y, z = it['b_loc']; az = math.degrees(math.atan2(x, y)) % 360; r = math.hypot(x, y)
    X, Y, Z = it['ue_loc']
    par = it.get('parent') or ''
    mo = (it.get('motion') or '不动').replace('|', '／')
    if mo == prev_mo and len(mo) > 20: mo = '同上'
    else: prev_mo = mo
    L.append(f"| {it['part']} | `{it['name']}` | {az:.2f}°, {r:.2f}, {z:.2f} | {X:.0f}, {Y:.0f}, {Z:.0f} | {it['ue_yaw']:.1f}° | {('`' + par + '`') if par else ''} | {mo} |")
L += ['', '## 不在模型里的东西', '',
      '光柱、光阶（光本身就是路）、日光和月光的反射光路、七色光带、棱镜分出的色光和光斑、影桥（细桥的月影）、水雾、星空、太阳和月亮的圆盘：这些是按时间算出来的光和特效，不是模型，按系统文档和施工图里的公式在 UE 里做。',
      '看不见的碰撞体（护栏、空气墙）也没有导出：UE 里按需要自己加。']
open(f'{src}/机关清单.md', 'w', encoding='utf-8').write('\n'.join(L)); print('ok', len(its))
