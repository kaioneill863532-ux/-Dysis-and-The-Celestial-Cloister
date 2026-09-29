# 日落回廊 v0.12 · 时间与日月的参考实现（纯 Python，不依赖任何库）
#
# 这是灰盒 prototype/temple/index.html 里“位置决定时间、时间决定日月方向”那部分的逐行翻译，
# 用来：① 给 UE 那边照着写 C++ / 蓝图；② 自己跑一遍和 golden_time.json（灰盒导出的标准答案）逐条比对。
#
# 运行：python3 reference_time.py golden_time.json      → 打印比对结果，全部通过才算规则没写错
#
# 约定：方位角 az，北 0°，顺时针（东 90°）；高 y 米；H 是时角（度），钟点 = 12:00 + H/15。
# UE 坐标：X = 100·北，Y = 100·东，Z = 100·高（厘米）；az = atan2(Y, X)。
import json, math, sys

# ───────── 小工具（和灰盒同名） ─────────
def wrap360(a): return a % 360.0
def ang_diff(a, b): return ((a - b) % 360.0 + 540.0) % 360.0 - 180.0
def clamp(x, a, b): return min(b, max(a, x))
def lerp(a, b, t): return a + (b - a) * t
def in_arc(az, arc):
    a0, a1 = arc; t = az
    while t < a0: t += 360.0
    while t >= a0 + 360.0: t -= 360.0
    return t <= a1

# ───────── 天：固定的倾斜圆轨道 ─────────
LAT, DEC_SUN, DEC_MOON = math.radians(35), math.radians(-21), math.radians(20)
def sky_dir(H_deg, dec):
    """返回单位向量 (东, 北, 上)。"""
    H = math.radians(H_deg)
    E = -math.cos(dec) * math.sin(H)
    N = math.sin(dec) * math.cos(LAT) - math.cos(dec) * math.cos(H) * math.sin(LAT)
    U = math.sin(dec) * math.sin(LAT) + math.cos(dec) * math.cos(H) * math.cos(LAT)
    return E, N, U
def sun_dir(H): return sky_dir(H, DEC_SUN)
def moon_dir(H): return sky_dir(H - 180.0, DEC_MOON)          # 月亮的时角比太阳晚 180°
def az_alt(v):
    E, N, U = v
    return math.degrees(math.atan2(E, N)) % 360.0, math.degrees(math.asin(clamp(U, -1, 1)))
def ue_light_rotation(v):
    """UE 平行光（+X 北、+Y 东）朝向：光从天体射过来。Pitch = −高度角，Yaw = 方位角 + 180。"""
    az, alt = az_alt(v); return {'pitch': -alt, 'yaw': (az + 180.0) % 360.0, 'roll': 0.0}

# ───────── 每层的时间线 ─────────
class LineZone:
    """一层一段：沿方位角均匀变化，接缝 [116°,140°] 处断开。白天顺时针时间变大，夜里逆时针变大（k 为负）。"""
    def __init__(self, d, seam):
        self.seam, self.lo, self.hi, self.a0, self.h0, self.k = seam, d['lo'], d['hi'], d['a0'], d['h0'], d['k']
    def un(self, az):
        t = wrap360(az)
        return t + 360.0 if t < self.lo else t
    def f(self, az):
        t = self.un(az)
        if in_arc(az, self.seam): t = self.lo if ang_diff(az, (self.seam[0] + self.seam[1]) / 2) > 0 else self.hi
        return self.h0 + self.k * (t - self.a0)
class PieceZone:
    """折线：几个 (方位, H) 点连起来，两头之外保持端点的值（夜里水庭用）。"""
    def __init__(self, d, seam):
        self.seam, self.lo, self.hi, self.q = seam, d['lo'], d['hi'], sorted(d['pts'])
    def un(self, az):
        t = wrap360(az)
        return t + 360.0 if t < self.lo else t
    def fU(self, t):
        q = self.q
        if t <= q[0][0]: return q[0][1]
        for i in range(1, len(q)):
            if t <= q[i][0]: return q[i - 1][1] + (q[i][1] - q[i - 1][1]) * (t - q[i - 1][0]) / (q[i][0] - q[i - 1][0])
        return q[-1][1]
    def f(self, az):
        t = self.un(az)
        if in_arc(az, self.seam): t = self.lo if ang_diff(az, (self.seam[0] + self.seam[1]) / 2) > 0 else self.hi
        return self.fU(t)

class DysisTime:
    def __init__(self, g):
        c = self.c = g['consts']
        seam = c['SEAM']
        mk = lambda d: LineZone(d, seam) if d['kind'] == 'line' else PieceZone(d, seam)
        self.ZD = {k: mk(v) for k, v in g['zones']['day'].items()}
        self.ZN = {k: mk(v) for k, v in g['zones']['night'].items()}
        self.tunnels = {t['id']: t for t in g['tunnels']}
        self.timeY = g['beamTimeY']
        self.moonbr = g['moonBridgePtsUE']
    # 屋顶环道：白天从细桥落脚（J）顺时针走到接光台，时间从 H_OC 升到 H_TOP；夜里从接光台逆时针走回 J，再沿降下来的楼梯到四层
    def crown_day(self, az):
        c = self.c; raw = wrap360(az - c['J_AZ']); pc = wrap360(c['CATCH_AZ'] - c['J_AZ']); psi = 0.0 if raw > 300 else raw
        return lerp(c['H_OC'], c['H_TOP'], psi / pc) if psi <= pc else c['H_TOP'] + 0.02 * min(psi - pc, 12)
    def crown_night(self, az):
        c = self.c; back = wrap360(c['CATCH_AZ'] - az); tj = wrap360(c['CATCH_AZ'] - c['J_AZ']); jd = wrap360(c['J_AZ'] - c['DN_FOOT'])
        if back > 330: return c['H_TOP'] - 0.02 * min(360 - back, 12)
        if back <= tj: return lerp(c['H_TOP'], c['H_J'], back / tj)
        return lerp(c['H_J'], c['H_L3A'], clamp((back - tj) / jd, 0, 1))
    # 墙里的楼梯：按高度在上门、下门两处的时刻之间插值
    def tunnel(self, tid, y, night):
        T, Z, F = self.tunnels[tid], (self.ZN if night else self.ZD), self.c['F']
        fl = lambda yy: 'L%d' % F.index(yy)
        hTop, hBot = Z[fl(T['yTop'])].f(T['topDoor']), Z[fl(T['yBot'])].f(T['botDoor'])
        return lerp(hTop, hBot, clamp((T['yTop'] - y) / (T['yTop'] - T['yBot']), 0, 1))
    def moonbr_t(self, pos_ue):
        best, bd = 0, 1e18
        for i, p in enumerate(self.moonbr):
            d = sum((p[j] - pos_ue[j]) ** 2 for j in range(3))
            if d < bd: bd, best = d, i
        return best / (len(self.moonbr) - 1)
    def time_at(self, zone, az=0.0, y=0.0, pos_ue=None, night=False, sticky=None):
        """人站在 zone 里（踩在地上）时的时刻。sticky = 上一刻的值（空中、水里等“不动”的地方用它）。
        夜里（接住最后一缕光以后）结果夹在 [H_TOP, H_END] 之间。"""
        h = self._raw(zone, az, y, pos_ue, night, sticky)
        if night: h = clamp(h if h is not None else -1e9, self.c['H_TOP'], self.c['H_END'])
        return h
    def _raw(self, zone, az, y, pos_ue, night, sticky):
        c = self.c; Z = self.ZN if night else self.ZD
        if zone.startswith('beam:'):
            bid = zone[5:]
            if bid == 'isle': return c['H_I']
            if bid == 'oculus': return c['H_OC']
            if bid == 'mirror': return c['H_M']
            ty = self.timeY.get(bid)
            if not ty: return sticky
            return ty[1] + (ty[3] - ty[1]) * (y - ty[0]) / (ty[2] - ty[0])      # 光路上按高度线性插值（不夹）
        if zone.startswith('tun:'): return self.tunnel(zone[4:], y, night)
        if zone in ('L0', 'L1', 'L2', 'L3'): return Z[zone].f(az)
        if zone == 'crown': return self.crown_night(az) if night else self.crown_day(az)
        if zone == 'rbridge': return c['H_J'] if night else c['H_OC']
        if zone == 'ledge': return c['H_M']
        if zone == 'moonbr': return lerp(c['MOONBR_H0'], c['MOONBR_H1'], self.moonbr_t(pos_ue))
        if zone in ('rainbow', 'sill'): return c['RELIEF_H']
        if zone == 'wfback': return Z['L0'].f(c['SEAM'][0] - 0.5)
        if zone in ('gbridge', 'shadowbr', 'pav'): return c['H_BR'] if night else sticky
        if zone == 'out': return sticky if night else c['H_I']
        return sticky   # pool 等

# ───────── 和标准答案比对 ─────────
if __name__ == '__main__':
    g = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'golden_time.json'))
    T = DysisTime(g); bad = 0; n = 0
    for s in g['timeSamples']:
        z = s['zone']; pos = s.get('pos'); az = s.get('az', 0.0); y = s.get('y', 0.0)
        if pos and 'az' not in s: az = math.degrees(math.atan2(pos[1], pos[0])) % 360
        got = T.time_at(z, az=az, y=y, pos_ue=pos, night=s['night'], sticky=None)
        exp = s['H']; n += 1
        if exp == 'sticky': ok = got is None
        else: ok = got is not None and abs(got - exp) < 1e-4
        if not ok:
            bad += 1
            if bad <= 10: print('时间不对', s, '算出', got)
    print(f'时间取样 {n - bad}/{n} 对')
    worst = 0
    for s in g['sky']:
        for key, fn in (('sun', sun_dir), ('moon', moon_dir)):
            v = fn(s['H']); e = s[key]
            worst = max(worst, abs(v[0] - e['E']), abs(v[1] - e['N']), abs(v[2] - e['U']))
            r = ue_light_rotation(v); ru = s[key + 'UE']
            worst = max(worst, abs(r['pitch'] - ru['pitch']) / 100, abs(ang_diff(r['yaw'], ru['yaw'])) / 100)
    print(f'日月方向 {len(g["sky"])} 个时刻，最大偏差 {worst:.2e}')
    sys.exit(1 if bad or worst > 1e-5 else 0)
