"""生成日落回廊的音效（第一、第二梯队）。

  python audio/tools/fetch_sources.py   # 先下载 Freesound 上的 CC0 素材到 audio/_src（不进仓库）
  python audio/tools/build.py           # 生成全部；或 build.py 3 5 14 只生成这几条

输出：audio/sfx/<编号>_<名字>/*.wav（48 kHz、16 位；点声源单声道，环境床和界面立体声），
audio/manifest.json（试听页和 README 用），audio/ir/IR_Temple_Rotunda.wav（殿内混响的脉冲响应）。
"""
import os, sys, json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import dsp
from dsp import (SR, secs, load, hp, lp, bp, eq, mix, fade, shape, db, expdecay, noise, modal, stone_knock,
                 bronze_ring, resample_pitch, norm_lufs, to_stereo, to_mono, widen, pan_sweep, grains, loopify,
                 sweep_filter, events, convolve, make_ir, beating_modes, GLASS, BOWL, STONE_BAR, BRONZE_PLATE)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "sfx")

# ───────────────────────── 音高：d 小调五声（D F G A C），都在灰盒时间和声的和弦里 ─────────────────────────
def hz(note):
    names = {"C": 0, "C#": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}
    n, o = note[:-1], int(note[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o + 1) - 69) / 12)


PENTA = ["D", "F", "G", "A", "C"]
LIGHT_NOTES = ["D5", "F5", "G5", "A5", "C6", "D6"]       # 日光：高一点、暖一点
MOON_NOTES = ["A3", "C4", "D4", "F4", "G4", "A4"]       # 月光：低一点、冷一点

# 素材的实测基频（Hz）
GLASS_RUBBED = {"419147": 791.0, "418150": 952.5, "419146": 1074.0, "198403": 739.4, "256251": 1477.2}
BOWL_STRUCK = {"59159": 447.0, "255762": 393.0}
BOWL_RUBBED = {"202004": 317.8, "573805": 546.5}

REG = []


def sound(num, key, zh, what, ue, tier):
    def deco(fn):
        REG.append(dict(num=num, key=key, zh=zh, what=what, ue=ue, tier=tier, fn=fn))
        return fn
    return deco


def src_len(sid):
    return len(load(sid)) / SR


def safe_start(sid, start, need):
    """起点太靠后读不够时往前挪。"""
    return max(0.0, min(start, src_len(sid) - need - 0.05))


def semis(f_from, f_to):
    return 12 * np.log2(f_to / f_from)


def nearest(table, f):
    return min(table.items(), key=lambda kv: abs(np.log2(kv[1] / f)))


# ───────────────────────── 常用的“真东西” ─────────────────────────
def trim_tail(x, tail_db=-46, fout=0.03):
    m = to_mono(x)
    k = secs(0.01)
    env = np.convolve(np.abs(m), np.ones(k) / k, mode="same")
    idx = np.where(env > env.max() * db(tail_db))[0]
    end = min(len(x), (idx[-1] if len(idx) else len(x)) + secs(0.015))
    return fade(x[:end], 0.002, fout)


def crest_db(x, win=0.1):
    c = x[: secs(win)]
    return 20 * np.log10((np.max(np.abs(c)) + 1e-12) / (dsp.rms(c) + 1e-12))


def step_pool(specs, hp_f=90, keep_db=12, post=0.38, max_pre=0.03, min_crest=0.0, max_crest=26.0):
    """从整段脚步录音里切出一步一步。specs: [(素材, 起, 止, 两步最小间隔)]"""
    out = []
    for sid, a, b, md in specs:
        x = hp(load(sid, start=a, dur=b - a), hp_f, order=3)
        ev = events(x, min_dist=md, post=post, max_pre=max_pre)
        if not ev:
            continue
        top = max(p for *_, p in ev)
        for s, e, p in ev:
            if p < top - keep_db:
                continue
            seg = trim_tail(x[secs(s):secs(e)])
            if len(seg) > secs(0.08) and min_crest <= crest_db(seg) <= max_crest:
                out.append(seg)
    return out


def peak_at(x, within=0.2):
    m = np.abs(to_mono(x[: secs(within)]))
    return int(np.argmax(m))


def align_add(base, layer, gain):
    """把 layer 的峰对齐到 base 的峰再叠上去。"""
    d = peak_at(base) - peak_at(layer)
    if d >= 0:
        layer = np.concatenate([np.zeros(d), layer])
    else:
        layer = layer[-d:]
    n = max(len(base), len(layer))
    y = np.zeros(n)
    y[: len(base)] += base
    y[: len(layer)] += gain * layer
    return y


def glass_tone(f, dur, attack=0.004, t60=0.6, start=1.5, src=None):
    """真实的摩擦水晶杯音（有自然的颤动），变到目标音高，按敲击的包络收住。"""
    sid, f0 = (src, GLASS_RUBBED[src]) if src else nearest(GLASS_RUBBED, f)
    st = semis(f0, f)
    need = dur * 2 ** (st / 12) + 0.05
    raw = load(sid, start=safe_start(sid, start, need), dur=need)
    y = resample_pitch(raw, st)[: secs(dur)]
    y = hp(y, 200)
    n = len(y)
    e = expdecay(n, t60)
    e[: secs(attack)] *= np.linspace(0, 1, secs(attack))
    return y * e


def glass_swell(f, dur, attack=0.6, release=1.0, start=2.0, src=None):
    """摩擦水晶杯的长音，慢慢起、慢慢收（没有敲击声）。"""
    sid, f0 = (src, GLASS_RUBBED[src]) if src else nearest(GLASS_RUBBED, f)
    st = semis(f0, f)
    need = dur * 2 ** (st / 12) + 0.05
    raw = load(sid, start=safe_start(sid, start, need), dur=need)
    y = hp(resample_pitch(raw, st)[: secs(dur)], 200)
    return y * dsp.env_ar(len(y), attack, release, curve=2.0)


def bowl_strike(f, dur, src=None, soft=0.0):
    """真实的颂钵敲击，变到目标音高。soft>0 把木槌的硬起音抹软（秒）。"""
    sid, f0 = (src, BOWL_STRUCK[src]) if src else nearest(BOWL_STRUCK, f)
    st = semis(f0, f)
    raw = load(sid, start=0.0, dur=dur * 2 ** (st / 12) + 0.6)
    # 找到敲击点
    i = int(np.argmax(np.abs(raw[: secs(1.0)])))
    raw = raw[max(0, i - secs(0.004)):]
    y = resample_pitch(raw, st)[: secs(dur)]
    y = fade(hp(y, 80), 0.001, min(0.4, dur / 3))
    if soft > 0:
        y[: secs(soft)] *= np.sin(np.linspace(0, np.pi / 2, secs(soft))) ** 2
    return y


def bowl_hum(f, dur, start=8.0, src=None, attack=0.4, release=0.8):
    """真实的摩擦颂钵长音，变到目标音高。"""
    sid, f0 = (src, BOWL_RUBBED[src]) if src else nearest(BOWL_RUBBED, f)
    st = semis(f0, f)
    need = dur * 2 ** (st / 12) + 0.05
    raw = load(sid, start=safe_start(sid, start, need), dur=need)
    y = hp(resample_pitch(raw, st)[: secs(dur)], 90)
    return y * dsp.env_ar(len(y), attack, release, curve=2.0)


def tinkles(n=40):
    """真实玻璃杯轻碰的一个个瞬间（做闪光颗粒）。"""
    x = hp(load("193823"), 1500, order=3)
    ev = events(x, min_dist=0.3, post=0.25, prom_db=18)
    return [trim_tail(x[secs(a):secs(b)], -40) for a, b, p in ev][:n]


def sparkle(dur, count, env=None, pitch=7.0, level=1.0, seed_=None):
    if seed_ is not None:
        dsp.seed(seed_)
    pool = tinkles()
    out = np.zeros((secs(dur), 2))
    for k in range(count):
        g = pool[dsp.RNG.integers(len(pool))]
        g = resample_pitch(g, pitch + dsp.RNG.uniform(-3, 5))
        g = lp(g, 11000) * dsp.RNG.uniform(0.3, 1.0)
        t = dsp.RNG.uniform(0, 1)
        a = 1.0 if env is None else float(np.interp(t, np.linspace(0, 1, len(env)), env))
        i = secs(t * dur * 0.92)
        g2 = to_stereo(g * a, dsp.RNG.uniform(-0.8, 0.8))
        j = min(len(out), i + len(g2))
        out[i:j] += g2[: j - i]
    return out * level


def mist(dur, lo=4000, hi=12000):
    """水雾：瀑布录音里最高的那一段（细细的嘶声），用来暗示“被照亮的雾”。"""
    x = load("559203", mono=False, start=30, dur=dur)
    return bp(x, lo, hi, order=2)


def stone_grit(dur, start=2.0, lo=300, hi=5000):
    """石头磨石头的细颗粒（来自真实石板门的录音）。"""
    x = load("844329", start=start, dur=dur)
    return bp(x, lo, hi)


def sandal_pool():
    # 只要脚跟落地那一下清楚的（峰值因数高），拖着走的沙沙声不要
    return step_pool([("734632", 10, 21, 0.3), ("119912", 0, 6, 0.3), ("119911", 0, 4.8, 0.3)], min_crest=18)


def sandal_run_pool():
    return step_pool([("734632", 0, 10, 0.22), ("734632", 25, 35, 0.3)], post=0.3, min_crest=18)


def stone_body_pool():
    return step_pool([("813622", 0, 6.7, 0.3)], hp_f=70, post=0.3)


def unit(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def cap(x, after_peak=0.17, fout=0.06):
    """一步只留峰后 after_peak 秒（凉鞋后面那一下拍脚跟不要，免得听成两步）。"""
    n = min(len(x), peak_at(x) + secs(after_peak))
    return fade(x[:n], 0.0, fout)


def footstep(sandal, body, body_gain, bright=0.0, low=0.0):
    sandal = cap(unit(sandal))
    b = lp(unit(body), 2600)
    b = b * expdecay(len(b), 0.22)
    y = align_add(sandal, b, body_gain)
    y = eq(y, "peak", 400, -2.0, 0.9)
    y = eq(y, "lowshelf", 160, low)
    y = eq(y, "highshelf", 7000, bright - 1.5)
    # 脚跟那一毫秒的尖峰削掉几 dB（录音里常见的处理），这样一组脚步的响度才对得齐
    y = dsp.limit(unit(y), -5.0)
    return fade(trim_tail(y), 0.0015, 0.03)


# ═════════════════════════ 第一梯队 ═════════════════════════

@sound(3, "Footstep_Stone", "脚步：石头/大理石",
       "皮凉鞋踩在大理石上。真实的凉鞋脚步（Vrymaa、ftpalad 的录音）一步一步切出来，下面垫一层真实的石地面脚步的“实”（SecureSubset），"
       "峰对齐后叠在一起；去掉 400 Hz 的闷、收一点刺耳的高频。走 10 个、快走 8 个、蹭地 4 个，响度都对齐。",
       "Sound Cue：Random（不重复）→ Modulator（音高 0.96–1.04，音量 0.9–1.0）。每次脚落地（动画通知或按步长）触发；"
       "Shift 快走用 Run 那一组。干声交付，殿内的混响交给 Audio Volume / 卷积混响（见 ir/）。", 1)
def b_foot_stone():
    dsp.seed(3)
    walk_s, run_s, body = sandal_pool(), sandal_run_pool(), stone_body_pool()
    files = []
    order = dsp.RNG.permutation(len(walk_s))
    for k in range(10):
        s = walk_s[order[k % len(walk_s)]]
        b = resample_pitch(body[k % len(body)], dsp.RNG.uniform(-1.5, 1.0))
        y = footstep(s, b, db(dsp.RNG.uniform(-7, -4.5)), low=1.0)
        files.append((f"SFX_Footstep_Stone_Walk_{k + 1:02d}", norm_lufs(y, -28), "走"))
    order = dsp.RNG.permutation(len(run_s))
    for k in range(8):
        s = run_s[order[k % len(run_s)]]
        b = resample_pitch(body[(k + 2) % len(body)], dsp.RNG.uniform(-1.0, 1.5))
        y = footstep(s, b, db(dsp.RNG.uniform(-7, -4)), bright=0.5, low=1.5)
        files.append((f"SFX_Footstep_Stone_Run_{k + 1:02d}", norm_lufs(y, -26), "快走"))
    # 蹭地：赤脚/凉鞋在石面上转身、停步时的擦声（SpliceSound 的瓷砖擦地录音）
    sc = step_pool([("197404", 0, 29, 0.3)], hp_f=120, keep_db=8, post=0.45)
    for k in range(4):
        y = trim_tail(eq(sc[(3 * k + 1) % len(sc)], "highshelf", 6000, -2))
        files.append((f"SFX_Footstep_Stone_Scuff_{k + 1:02d}", norm_lufs(y, -31), "蹭地"))
    return files


def light_step(s, f, level_glass, t60, seed_):
    dsp.seed(seed_)
    s = hp(cap(unit(s), 0.15), 240, order=2)
    s = eq(s, "highshelf", 5000, -2.0)
    # 冲击激起“光”的振动：模态（起音干净）+ 真实水晶杯（有颤动的身体）
    ex = hp(s[: secs(0.008)], 1200)
    m = modal([f * r for r in GLASS], [t60, t60 * 0.45, t60 * 0.25, t60 * 0.15, t60 * 0.1], [1, 0.22, 0.09, 0.04, 0.02], t60 * 1.6)
    m = m / (np.max(np.abs(m)) + 1e-9)
    g = glass_tone(f, t60 * 1.6, t60=t60 * 0.8, start=dsp.RNG.uniform(1.0, 6.0))
    g = g / (np.max(np.abs(g)) + 1e-9)
    ring = lp(0.55 * m + 0.6 * g, 7500)
    air = hp(noise(0.25), 6000) * expdecay(secs(0.25), 0.12) * 0.25
    d = peak_at(s)
    y = mix((s, 0), (ring, d / SR + 0.002, level_glass), (air, d / SR, level_glass))
    y = dsp.limit(unit(y), -4.0)
    return fade(trim_tail(y, -50, 0.08), 0.0015, 0.08)


@sound(4, "Footstep_LightPath", "脚步：光路",
       "脚下是光：同一双凉鞋的脚步，去掉石头的“实”（低频全拿掉，光没有分量），每一步激起一点水晶的余振——"
       "模态合成负责干净的起音，真实的摩擦水晶杯录音（PappaBert）负责有颤动的身体，音高在 d 小调五声里随机取（D5–D6），"
       "很轻、半秒就收住，走很久也不吵。",
       "和石头脚步同一套触发；脚下是光路（Zone 以 beam: 开头、月石、虹桥、影桥另有材质）时换这一组。Random 不重复，音高不要再随机（已经按音阶取好）。", 1)
def b_foot_light():
    walk_s, run_s = sandal_pool(), sandal_run_pool()
    files = []
    dsp.seed(4)
    notes = [hz(n) for n in LIGHT_NOTES]
    for k in range(10):
        s = walk_s[(k * 5 + 2) % len(walk_s)]
        y = light_step(s, notes[(k * 3) % len(notes)], db(-14), 0.5, 40 + k)
        files.append((f"SFX_Footstep_Light_Walk_{k + 1:02d}", norm_lufs(y, -29), "走"))
    for k in range(6):
        s = run_s[(k * 3 + 1) % len(run_s)]
        y = light_step(s, notes[(k * 2 + 1) % len(notes)], db(-15), 0.4, 60 + k)
        files.append((f"SFX_Footstep_Light_Run_{k + 1:02d}", norm_lufs(y, -27), "快走"))
    return files


def light_reveal(f_lo, f_hi, dur=2.4, seed_=0, glow=1.0):
    dsp.seed(seed_)
    a = glass_swell(f_lo, dur, attack=0.55, release=1.3, start=dsp.RNG.uniform(1.5, 5.0))
    b = glass_swell(f_hi, dur - 0.15, attack=0.7, release=1.2, start=dsp.RNG.uniform(1.5, 5.0))
    tone = mix((a, 0, 1.0), (b, 0.12, 0.55))
    tone = lp(tone, 6500)
    st = widen(tone, 0.5, 0.013)
    m = mist(dur) * 0.08 * glow
    m = shape(m, [(0, 0), (0.5, 1), (1.2, 0.6), (dur, 0)])
    sp = sparkle(dur, 8, env=[0.2, 1, 0.6, 0.1], pitch=9, level=0.11 * glow, seed_=seed_ + 100)
    y = mix((st, 0), (m, 0), (sp, 0.1))
    return fade(y, 0.05, 0.5)


LIGHT_DYADS = [("D5", "A5"), ("F5", "C6"), ("G5", "D6"), ("A5", "D6"), ("C5", "G5"), ("D5", "G5")]


@sound(5, "LightPath_Reveal", "光路显形",
       "一束光出现、可以走了。两只真实的摩擦水晶杯（变到 d 小调五声的四度、五度）慢慢起来，一点被照亮的水雾（瀑布录音最高的那一段），"
       "几颗很轻的玻璃闪光（jhumbucker 的玻璃轻碰）。没有敲击、没有尖的起音，2.4 秒左右收住；六个音高组合轮着用，听几十次也不腻。",
       "光路的可走状态从 false 变 true 时，在光束的中点（或玩家能看到的那一头）播放；6 个文件 Random 不重复。"
       "同一时间多束光一起出现只播一个。立体声，Spatialization 开、Spread 适中。", 1)
def b_light_reveal():
    files = []
    for k, (lo_, hi_) in enumerate(LIGHT_DYADS):
        y = light_reveal(hz(lo_), hz(hi_), 2.4, seed_=500 + k)
        files.append((f"SFX_LightPath_Reveal_{k + 1:02d}", norm_lufs(y, -25), "显形"))
    return files


def moon_appear(f, seed_):
    dsp.seed(seed_)
    s = bowl_strike(f, 1.6, soft=0.012)
    s = lp(s, 4500)
    h = bowl_hum(f, 1.6, start=dsp.RNG.uniform(6, 20), attack=0.18, release=1.0)
    grit = stone_grit(0.5, start=dsp.RNG.uniform(1, 12), lo=800, hi=6000)
    grit = grit * dsp.env_ar(len(grit), 0.12, 0.3)
    y = mix((s, 0.03, 0.8), (h, 0, 0.6), (grit, 0, 0.18))
    return fade(y, 0.01, 0.3)


def moon_vanish(f, dur, seed_, dust=1.0):
    dsp.seed(seed_)
    h = bowl_hum(f, dur, start=dsp.RNG.uniform(6, 20), attack=0.25, release=dur * 0.7)
    # 音高慢慢往下沉一点（像光退去）
    n = len(h)
    rate = 1 - 0.03 * np.linspace(0, 1, n) ** 2
    idx = np.cumsum(rate)
    idx = idx[idx < n - 1]
    h = np.interp(idx, np.arange(n), h)
    sand = load("627070", start=dsp.RNG.uniform(5, 50), dur=dur)
    sand = bp(sand, 1500, 9000)
    sand = shape(sand, [(0, 0), (0.25, 1), (dur * 0.6, 0.5), (dur, 0)])
    sp = sparkle(dur, 5, env=[1, 0.6, 0.2, 0], pitch=2, level=0.05, seed_=seed_ + 7)
    y = mix((h, 0), (sand * 0.22 * dust, 0), (to_mono(sp), 0))
    return fade(y, 0.02, 0.4)


@sound(6, "Moonstone", "月石显形、隐去",
       "月光照到的石头：显形是一只真实颂钵（Coleco 的敲击录音）把木槌的硬起音抹软，变到月光的低音区，下面垫同一音高的摩擦颂钵（ryancacophony）和一点石头的细砂；"
       "隐去是摩擦颂钵的长音一边淡出一边往下沉一点点，混着真实的沙子流下的细声（nicoproson），像石头化成月光的尘。"
       "另有一个大号的“墙隐去”（月亮浮雕、双子厚墙、月之龛那几块大月石共用）。",
       "Appear：月石的 k 从 0 往 1 走时触发（只在开始那一下）；Vanish：从 1 往 0 走时触发。音高已经分开，Random 不重复即可。"
       "Wall_Vanish 给一次性隐去的大块月石。单声道，放在月石的中心。", 1)
def b_moonstone():
    files = []
    for k, n in enumerate(["D4", "F4", "G4", "A4"]):
        files.append((f"SFX_Moonstone_Appear_{k + 1:02d}", norm_lufs(moon_appear(hz(n), 600 + k), -25), "显形"))
    for k, n in enumerate(["A4", "G4", "D4"]):
        files.append((f"SFX_Moonstone_Vanish_{k + 1:02d}", norm_lufs(moon_vanish(hz(n), 2.2, 650 + k), -27), "隐去"))
    big = mix((moon_vanish(hz("D4"), 3.6, 700, dust=2.2), 0), (moon_vanish(hz("A3"), 3.6, 701, dust=1.0), 0.05, 0.7))
    rumble = lp(load("844329", start=4, dur=3.6), 600) * dsp.env_ar(secs(3.6), 0.4, 2.5) * 0.25
    files.append(("SFX_Moonstone_Wall_Vanish", norm_lufs(mix((big, 0), (rumble, 0)), -23), "大块隐去"))
    return files


def cloth_pool():
    out = []
    for sid, a, b in [("391448", 0, 11.6), ("495390", 0, 6.9)]:
        x = hp(load(sid, start=a, dur=b - a), 150)
        for s, e, p in events(x, min_dist=0.35, post=0.35, prom_db=10, smooth=0.04):
            out.append(trim_tail(x[secs(s):secs(e)], -40))
    return out


@sound(8, "Jump_Land", "跳跃、落地",
       "起跳：凉鞋在石面上一蹬（真实的蹭地脚步）+ 长袍带起的一下衣料风声（saturdaysoundguy、Nox_Sound 的衣服挥动录音）。"
       "落地：两只脚前后差 15–30 毫秒落下，石地面的“实”比走路重，最后衣料落定一下。另有落在光上的版本：没有石头的重量，脚下一声水晶。",
       "Jump：起跳那一帧；Land_Stone：落到石头/青铜上（青铜落地见 28）；Land_Light：落到光路、月石上。"
       "下落时间长于 0.6 秒的落地可以把音量提高 2–3 dB。", 1)
def b_jump_land():
    dsp.seed(8)
    files = []
    sc = step_pool([("197404", 0, 29, 0.3)], hp_f=120, keep_db=8, post=0.3)
    cl = cloth_pool()
    walk_s, body = sandal_pool(), stone_body_pool()
    for k in range(4):
        push = unit(sc[(k * 2 + 3) % len(sc)][: secs(0.22)])
        push = dsp.limit(push, -9.0)                       # 蹭地里偶尔的尖“咔”压下去
        c = cl[(k * 3) % len(cl)]
        c = lp(c, 7000)
        y = mix((fade(push, 0.002, 0.06), 0, 0.9), (c, 0.03, 0.8))
        files.append((f"SFX_Jump_{k + 1:02d}", norm_lufs(fade(y, 0.002, 0.08), -26), "起跳"))
    for k in range(4):
        a = walk_s[(k * 4 + 1) % len(walk_s)]
        b = walk_s[(k * 4 + 6) % len(walk_s)]
        bod = resample_pitch(body[(k + 1) % len(body)], -2.0)
        fa = footstep(a, bod, db(-3), low=2.5)
        fb = footstep(b, body[(k + 3) % len(body)], db(-6), low=1.5)
        c = lp(cl[(k * 3 + 1) % len(cl)], 6000)
        y = mix((fa, 0), (fb, dsp.RNG.uniform(0.015, 0.03), 0.8), (c * 0.5, 0.05))
        files.append((f"SFX_Land_Stone_{k + 1:02d}", norm_lufs(trim_tail(y), -20), "落地·石头"))
    notes = [hz(n) for n in ["D5", "G5", "A5"]]
    for k in range(3):
        a = walk_s[(k * 5 + 2) % len(walk_s)]
        b = walk_s[(k * 5 + 4) % len(walk_s)]
        la = light_step(a, notes[k], db(-13), 0.8, 800 + k)
        lb = light_step(b, notes[k] * 1.5, db(-19), 0.5, 810 + k)
        y = mix((la, 0), (lb, 0.022, 0.7))
        files.append((f"SFX_Land_Light_{k + 1:02d}", norm_lufs(trim_tail(y, -50, 0.1), -23), "落地·光"))
    return files


def fall_wind(dur, seed_, rise=1.0):
    """下落时耳边的风：带通的粉噪，中心频率和响度随湍流抖动，越落越大。"""
    dsp.seed(seed_)
    n = secs(dur)
    out = np.zeros((n, 2))
    for ch in range(2):
        x = noise(dur, "pink")
        turb = np.interp(np.arange(n), np.linspace(0, n, 40), dsp.RNG.uniform(0.6, 1.4, 40))
        f = np.interp(np.arange(0, n, 256), [0, n * rise / dur if dur > 0 else n, n], [350, 900, 1000]) * turb[::256][: len(np.arange(0, n, 256))]
        y = sweep_filter(x, f, None, kind="bandpass", q=0.9)
        y += 0.5 * lp(x, 300)
        g = np.interp(np.arange(n), np.linspace(0, n, 60), dsp.RNG.uniform(0.7, 1.3, 60))
        out[:, ch] = y * g
    return out


@sound(9, "Fall_Respawn", "掉落、回到落脚点",
       "掉落：耳边的风越来越大（粉噪做的湍流风，中心频率和响度一直在抖），加上长袍被风吹着抖动；有一个起头（1.6 秒，风从无到大）和一个可以一直循环的风。"
       "回到落脚点：不惩罚——光像吸一口气一样聚回来（水晶杯音倒着长出来），落在一个温暖的五度上，最后一声很轻的落脚。日、夜各一个。",
       "Fall_Start：离开地面、下落速度超过阈值时播；接着播 Fall_Loop（Looping），回到落脚点时 0.15 秒淡出。"
       "Respawn_Day / Respawn_Night：人重新出现在落脚点的那一刻（白天用日光的，入夜以后用月光的）。", 1)
def b_fall():
    files = []
    w = fall_wind(1.8, 900, rise=1.6)
    cl = cloth_pool()
    flutter = np.zeros(secs(1.8))
    for k in range(5):
        c = cl[(k * 2) % len(cl)]
        i = secs(0.4 + 0.27 * k)
        j = min(len(flutter), i + len(c))
        flutter[i:j] += c[: j - i] * (0.3 + 0.12 * k)
    y = mix((w, 0), (to_stereo(lp(flutter, 5000)), 0, 0.5))
    y = hp(shape(y, [(0, 0), (0.25, 0.25), (1.4, 1), (1.8, 1)]), 30)
    files.append(("SFX_Fall_Start", norm_lufs(fade(y, 0.02, 0.02), -22, "integrated"), "掉落"))
    L = hp(fall_wind(7.0, 901, rise=0.1), 30)
    L = loopify(L, 1.5)
    files.append(("SFX_Fall_Loop", norm_lufs(L, -22, "integrated"), "掉落·循环", True))
    walk_s = sandal_pool()
    for name, (lo_, hi_), kind in [("Day", ("D5", "A5"), "glass"), ("Night", ("D4", "A4"), "bowl")]:
        dsp.seed(950 if kind == "glass" else 951)
        if kind == "glass":
            a = glass_swell(hz(lo_), 1.0, attack=0.05, release=0.9)
            b = glass_swell(hz(hi_), 1.0, attack=0.05, release=0.9)
        else:
            a = bowl_hum(hz(lo_), 1.0, attack=0.05, release=0.9)
            b = bowl_hum(hz(hi_), 1.0, attack=0.05, release=0.9)
        inhale = (a + 0.6 * b)[::-1]                 # 倒放：从无长到满，像光聚回来
        inhale = lp(inhale, 6000)
        bloom = (glass_tone(hz(lo_), 1.4, attack=0.02, t60=0.9) if kind == "glass" else bowl_strike(hz(lo_), 1.6, soft=0.02))
        step = hp(walk_s[7], 200) * 0.45
        y = mix((widen(inhale, 0.5), 0), (to_stereo(bloom * 0.7), 0.95), (to_stereo(step), 0.98), length=secs(2.1))
        y = fade(y, 0.02, 0.6)
        files.append((f"SFX_Respawn_{name}", norm_lufs(y, -24), "回到落脚点"))
    return files


@sound(10, "Waterfall", "瀑布",
       "从天花板一直泻进水庭的厚瀑布。近处：一段很稳的真实大瀑布（saralana，258 秒的录音里挑最匀的一段）打底，叠一层真实的小瀑布近距离的水花（Nox_Sound），"
       "低频稍微加厚（落差 30 米）；远处：同一瀑布滤到只剩低沉的轰鸣，窄一点，给殿里别的楼层。都是无缝循环。",
       "两层都 Looping，放在瀑布中心：Near 的衰减半径约 6–25 m，Far 约 15–60 m，两层叠着用。"
       "水闸打开以前两层都停；开闸时先播 14 的 Waterfall_Start，它的结尾直接接上这两条循环。", 1)
def b_waterfall():
    files = []
    a = load("559203", mono=False, start=60, dur=15)
    s = load("698306", mono=False, start=5, dur=15)
    near = mix((hp(a, 35), 0, 1.0), (hp(s, 300), 0, 0.45))
    near = eq(near, "lowshelf", 180, 3.0)
    near = eq(near, "highshelf", 9000, -2.0)
    near = loopify(near, 3.0)
    files.append(("SFX_Waterfall_Near_Loop", norm_lufs(near, -21, "integrated"), "近", True))
    b = load("559203", mono=False, start=150, dur=15)
    far = lp(hp(b, 30), 1100, order=3)
    far = eq(far, "lowshelf", 120, 4.0)
    m = far.mean(axis=1, keepdims=True)
    far = m + (far - m) * 0.4
    far = loopify(far, 3.0)
    files.append(("SFX_Waterfall_Far_Loop", norm_lufs(far, -24, "integrated"), "远", True))
    return files


@sound(11, "Sea_Waves", "海浪",
       "开场第一声。近处（岛上、海面高度）：真实的浪拍礁石（dan.pugsley，一个个浪的起落很清楚）；"
       "远处（台地、殿外回廊、殿里）：真实的“从崖上听海”（bruno.auzet），本来就是在悬崖上录的，再滤掉一点高频。都是无缝循环。",
       "Close：放在岛的外沿和崖脚，衰减半径约 10–40 m；Far：2D 或者放大半径（80 m 以上），殿外一直在，进殿以后用 Audio Volume 压低 8–12 dB、再低通到 800 Hz 左右。", 1)
def b_waves():
    files = []
    c = load("457956", mono=False, start=2, dur=34)
    c = hp(c, 40)
    c = eq(c, "highshelf", 8000, -2.0)
    c = loopify(c, 4.0)
    files.append(("SFX_Sea_Waves_Close_Loop", norm_lufs(c, -22, "integrated"), "近", True))
    f = load("525029", mono=False, start=40, dur=34)
    f = lp(hp(f, 30), 3500, order=2)
    f = eq(f, "lowshelf", 150, 2.0)
    f = loopify(f, 4.0)
    files.append(("SFX_Sea_Waves_Far_Loop", norm_lufs(f, -25, "integrated"), "远", True))
    return files


# ═════════════════════════ 第二梯队：机关的共用零件 ═════════════════════════
def seg(sid, start, dur, st=0.0, mono=True):
    """取一段素材并变调（变调连带变速：降调的石头更沉、更慢）。dur 是变调以后的长度。"""
    need = dur * 2 ** (st / 12) + 0.02
    x = load(sid, mono=mono, start=safe_start(sid, start, need), dur=need)
    x = resample_pitch(x, st)[: secs(dur)] if st else x[: secs(dur)]
    return fade(x, 0.002, min(0.02, dur / 4))      # 切口一律淡入淡出，免得咔哒


def sub_rumble(dur, f=70, depth=0.5, seed_=0):
    """很低的隆隆声：重石头移动时整座建筑传过来的振动。"""
    dsp.seed(seed_)
    x = hp(lp(noise(dur, "brown"), f, order=3), 22, order=2)
    m = np.interp(np.arange(secs(dur)), np.linspace(0, secs(dur), 12), 1 - depth + depth * dsp.RNG.random(12))
    return fade(x * m, 0.05, min(0.3, dur / 3))


def heavy_grind(dur, st=-5.0, seed_=0, src="844329", start=None, lo=40, hi=3200):
    """重石头磨石头：真实的石板门录音降调（更重），低通，加一层隆隆声。"""
    dsp.seed(seed_)
    need = dur * 2 ** (st / 12)
    lo_t, hi_t = {"844329": (5.2, 10.5), "352829": (0.4, 6.8)}.get(src, (0.5, 0.5))
    if start is None:
        start = dsp.RNG.uniform(lo_t, max(lo_t + 1e-3, hi_t - need))
    g = seg(src, start, dur, st)
    g = lp(hp(g, lo), hi)
    r = sub_rumble(dur, 90, 0.4, seed_ + 1)
    y = hp(unit(g) + 0.35 * unit(r), 25)
    return fade(y, 0.005, min(0.05, dur / 4))


def stone_thud(st=0.0, which=0, dur=1.0, lpf=2500):
    """石头落定的一下：真实的石头重击（vestibule-door 的石面重击、patchytherat 的石门关上）。"""
    srcs = [("669719", 0.65), ("669719", 1.85), ("669719", 3.15), ("669719", 4.45), ("669719", 5.80), ("530987", 0.02), ("530987", 1.22)]
    sid, t = srcs[which % len(srcs)]
    x = seg(sid, max(0, t - 0.02), dur, st)
    i = peak_at(x, 0.2)
    x = x[max(0, i - secs(0.004)):]
    return fade(lp(hp(x, 35), lpf), 0.002, min(0.3, len(x) / SR / 2))


def slam(st=-2.0, dur=1.0):
    """大石门砰地合上（PaceHeart）：很低、很厚。"""
    return fade(lp(seg("465807", 0.0, dur, st), 1800), 0.002, 0.25)


def clack(which=0, st=0.0, dur=0.4):
    """石头碰石头的脆响（xtra1）：做卡位、棘爪。"""
    ts = [0.05, 1.4, 2.35, 3.25, 4.25, 5.2, 6.2, 7.0, 8.1, 9.1]
    x = seg("858891", ts[which % len(ts)], dur + 0.3, st)
    i = int(np.argmax(np.abs(x[: secs(0.35)])))
    return fade(x[max(0, i - secs(0.003)): max(0, i - secs(0.003)) + secs(dur)], 0.001, dur / 2)


def lithophone(f, dur=1.4, seed_=0):
    """石磬：调过音的石条，用真实石头碰撞的瞬态去激发。"""
    dsp.seed(seed_)
    k = stone_knock(f, dur, bright=0.7, damp=0.85)
    c = hp(clack(seed_, 0, 0.12), 300) * 0.5
    return lp(mix((k, 0), (c, 0)), 6000)


def metal_slide(which=0, st=-6.0, dur=1.0):
    """青铜片滑过青铜（LordForklift 的金属滑动、Qat 的拔剑），降调后像大块的铜叶片。"""
    if which % 2 == 0:
        x = seg("448418", 0.25, dur, st)
    else:
        x = seg("107589", 0.03, dur, st)
    return fade(lp(hp(x, 120), 7000), 0.01, dur * 0.4)


def creak(st=-6.0, dur=2.0, start=0.6, src="637583"):
    """铜门轴的呻吟：真实的大铁门吱呀声降调（老铜门，不尖）。"""
    x = seg(src, start, dur, st)
    return lp(hp(x, 60), 5000)


def chain_tense(dur=0.8, st=-2.0, start=1.5):
    """铜链一紧（LePainMaudit 的重铁链）。"""
    x = seg("791907", start, dur, st)
    return fade(lp(hp(x, 120), 6000), 0.005, dur * 0.4)


def bolt(which=0, st=-2.0, dur=0.5):
    """门闩、卡子的一下（Alexbuk 的门闩录音里切出来）。"""
    x = hp(load("391794"), 80)
    ev = events(x, min_dist=0.6, post=0.5, prom_db=15)
    ev = sorted(ev, key=lambda e: -e[2])[:12]
    a, b, p = ev[which % len(ev)]
    y = x[secs(a):secs(a) + secs(dur * 2 ** (st / 12))]
    return fade(lp(resample_pitch(y, st), 7000), 0.002, dur / 2)


def water_gush(dur=1.2):
    return fade(hp(load("271668", start=0.0, dur=min(dur, 1.0)), 60), 0.005, 0.3)


STEP_NOTES = ["D3", "F3", "G3", "A3", "C4", "D4", "F4", "G4", "A4", "C5", "D5", "F5", "G5", "A5", "C6", "D6"]


# ═════════════════════════ 第二梯队 ═════════════════════════

@sound(14, "Sluice_Waterfall_Start", "水闸轮转动、瀑布开始流",
       "第一个机关。闸轮：真实的木轮转动（KVV_Audio）降调成大轮子，加上绞盘棘爪一格一格的咔哒（kyles 的滑轮绞盘），轴上很低的一声呻吟，最后石闸被拉开时“咚”地到位。"
       "瀑布开始流：先是一股水冲出来（HonorHunter 的水涌），再是从 30 米高处稀稀拉拉砸进水池的水（Breviceps 的倒水），然后真正的瀑布从低沉的闷响打开成整片的轰鸣（低通一路扫开），"
       "最后一秒和 10 的 Near 循环开头完全一样，能直接接上。另附一个关水闸、瀑布停下的版本。",
       "玩家按 E 开水闸：播 Sluice_Wheel_Turn（2.6 s）；它播到 2.2 s 左右（闸到位那一下）开始播 Waterfall_Start，"
       "Waterfall_Start 的最后 1 秒是等功率淡出：它播到 4.0 s 时启动 10 的 Near/Far 两条循环，Fade In 1 s、曲线选 Sin（Equal Power）。"
       "关水闸：Waterfall_Stop 开头 1 秒是等功率淡入，播它的同时让两条循环 Fade Out 1 s（同样的曲线）。", 2)
def b_sluice():
    dsp.seed(14)
    files = []
    # 闸轮：转 2.2 秒，到位
    wheel = seg("715478", 12, 2.6, -4)
    wheel = lp(hp(wheel, 60), 4000)
    wheel = shape(unit(wheel), [(0, 0), (0.15, 0.8), (1.9, 1), (2.25, 0.3), (2.6, 0)])
    ratchet = np.zeros(secs(2.6))
    pulls = [seg("454148", 0.22, 0.75, -5), seg("454148", 2.0, 1.15, -5)]
    ratchet = mix((unit(pulls[0]), 0.1, 0.7), (unit(pulls[1]), 0.9, 0.8), length=secs(2.6))
    ratchet = lp(ratchet, 6000)
    groan = creak(-9, 2.0, 0.8) * dsp.env_ar(secs(2.0), 0.5, 0.8)
    stop = stone_thud(-3, 1, 0.5)
    clunk = bolt(2, -5, 0.4)
    y = mix((wheel, 0, 0.55), (ratchet, 0, 0.5), (unit(groan), 0.1, 0.18), (unit(stop), 2.18, 0.9), (unit(clunk), 2.2, 0.45), length=secs(2.9))
    files.append(("SFX_Sluice_Wheel_Turn", norm_lufs(fade(y, 0.01, 0.2), -20), "闸轮"))
    # 瀑布开始流：5 秒。水从无到满，最后 1 秒等功率淡出，和 Near 循环交叉接上
    D = 5.0
    near = load("559203", mono=False, start=60, dur=D)
    spl = load("698306", mono=False, start=5, dur=D)
    bed = mix((hp(near, 35), 0, 1.0), (hp(spl, 300), 0, 0.45))
    bed = eq(eq(bed, "lowshelf", 180, 3.0), "highshelf", 9000, -2.0)
    full_level = bed.copy()
    t = np.arange(secs(D)) / SR
    ramp = np.clip((t - 0.7) / 2.3, 0, 1) ** 1.6                     # 0.7 s 起水，3.0 s 满
    tail = np.where(t > D - 1.0, np.cos((t - (D - 1.0)) / 1.0 * np.pi / 2), 1.0)
    full = bed * (ramp * tail)[:, None]
    fc = np.concatenate([np.geomspace(400, 16000, 60), np.full(40, 16000)])   # 前 3 秒从闷到全开
    swept = np.stack([sweep_filter(full[:, c], fc, None) for c in range(2)], axis=1)
    gush = to_stereo(unit(water_gush(1.0)), -0.1)
    pour = load("508178", mono=False, start=1.0, dur=3.0)
    pour = shape(hp(pour, 100), [(0, 0), (0.3, 1), (2.2, 0.7), (3.0, 0)])
    y = mix((swept, 0), (gush, 0.0, 0.35), (unit(pour) * 0.25, 0.5), length=secs(D))
    # 满水那一段和 Near 循环一样响
    y = norm_to_loop(y, full_level[secs(3.0):secs(4.0)], -21)
    files.append(("SFX_Waterfall_Start", fade(y, 0.01, 0.0), "瀑布开始流"))
    # 关水闸：轰鸣一路低通收掉，最后几滴
    stopb = load("559203", mono=False, start=60, dur=4.0)
    stopb = mix((hp(stopb, 35), 0, 1.0), (hp(load("698306", mono=False, start=5, dur=4.0), 300), 0, 0.45))
    stopb = np.stack([sweep_filter(stopb[:, c], 16000, 300) for c in range(2)], axis=1)
    stopb = shape(stopb, [(0, 1), (1.5, 0.6), (3.2, 0.05), (4.0, 0)])
    lvl_ref = stopb[secs(0.5):secs(1.0)].copy()
    t = np.arange(secs(4.0)) / SR
    stopb = stopb * np.where(t < 1.0, np.sin(t / 1.0 * np.pi / 2), 1.0)[:, None]   # 开头 1 秒等功率淡入，和循环交叉
    drips = sparkle(4.0, 6, env=[0, 0.3, 1, 0.6], pitch=-8, level=0.12, seed_=1414)
    y = mix((stopb, 0), (lp(drips, 5000), 0))
    files.append(("SFX_Waterfall_Stop", norm_to_loop(y, lvl_ref, -21) * db(1.5), "瀑布停下"))
    return files


def norm_to_loop(y, ref_seg, loop_lufs):
    """把 y 缩放到：ref_seg（y 里和循环一样的那段）的响度 = 循环的响度。"""
    g = db(loop_lufs - dsp.lufs(ref_seg, "integrated"))
    return y * g


@sound(15, "Steps_Rise_Settle", "台阶升起、落平",
       "屋顶环道的 16 级踏步。每一级到位时是一声“石磬”：调过音的石条（两端自由的石条的真实振动比例 1 : 2.76 : 5.40 : 8.93），用真实的石头碰撞激发，"
       "16 级按 d 小调五声从 D3 一路升到 D6——音高逐级变高，本身就是“快到了”的反馈；每级还带一点铜叶片擦过的亮声（光圈叶片跟着升起来）。"
       "落平是同一个音低八度、更闷、更轻。另有一条踏步移动时的石头摩擦循环。",
       "Rise_XX：第 XX 级升到顶（停住）那一刻播，单声道放在那一级上。Settle_XX：入夜后第 XX 级落平到底时播。"
       "Move_Loop：只要有踏步在动就循环播放，音量跟踏步的移动速度走（0 → 停）。", 2)
def b_steps():
    files = []
    for k, n in enumerate(STEP_NOTES):
        f = hz(n)
        dsp.seed(1500 + k)
        knock = lithophone(f, 1.6, 1500 + k)
        thud = stone_thud(-2 + k * 0.2, k, 0.4, lpf=1500)
        blade = metal_slide(k, -3 + k * 0.25, 0.35)
        grit = stone_grit(0.25, start=3 + k * 0.4, lo=400, hi=4000) * dsp.env_ar(secs(0.25), 0.002, 0.2)
        # 音高是主角：石磬在前，落定的闷响、叶片、砂粒都垫在下面
        y = mix((unit(knock), 0, 1.0), (unit(thud), 0, 0.28), (unit(blade), 0.0, 0.05), (unit(grit), 0, 0.06))
        files.append((f"SFX_Steps_Rise_{k + 1:02d}", norm_lufs(trim_tail(fade(y, 0.002, 0.3), -52, 0.2), -23), "升起"))
    for k, n in enumerate(STEP_NOTES):
        f = hz(n) / 2
        dsp.seed(1600 + k)
        knock = lp(lithophone(f, 1.4, 1600 + k), 2500)
        thud = stone_thud(-4, k + 3, 0.5, lpf=1200)
        y = mix((unit(knock), 0, 1.0), (unit(thud), 0, 0.5))
        files.append((f"SFX_Steps_Settle_{k + 1:02d}", norm_lufs(trim_tail(fade(y, 0.002, 0.3), -52, 0.2), -26), "落平"))
    mv = heavy_grind(6.5, st=-3, seed_=1599, src="352829")
    mv = lp(mv, 2500)
    files.append(("SFX_Steps_Move_Loop", norm_lufs(loopify(mv, 1.0), -26, "integrated"), "移动·循环", True))
    return files


@sound(16, "Lever_StoneSlab", "拉机关 A/B、石板滑动",
       "拉杆：手握铜把手、轴上一声短的呻吟、铜链“一紧”（LePainMaudit 的重铁链）、扳到底“咔”地卡住（Alexbuk 的门闩）。A 是拉下，B 是推回，用不同的素材段和顺序。"
       "石板滑动：一块大石板贴着外墙在滑轨上滑开 1.6 秒（真实的墓门石头摩擦，降调），起步一顿、到位一声闷响；两个版本给两块石板。",
       "Lever_Pull：拉 A；Lever_Push：推 B，放在拉杆上。Slab_Slide_01/02：两块石板各自开始滑的时候在石板上播（离得远，靠 UE 的衰减和混响就有“远处传来”的感觉）。", 2)
def b_lever():
    dsp.seed(16)
    files = []
    for name, cs, ch_t, bolt_i, order in [("Pull", 0.4, 1.4, 1, 0), ("Push", 1.1, 4.5, 4, 1)]:
        grip = clack(3 + order, 6, 0.15) * 0.25
        pivot = lp(creak(-4 + order, 0.9, cs, src="682776"), 3000) * dsp.env_ar(secs(0.9), 0.15, 0.5)
        chain = chain_tense(0.7, -2 - order, ch_t)
        lock = bolt(bolt_i, -3, 0.45)
        lv = lp(seg("696746", 0.0, 0.7, -4), 5000)
        y = mix((unit(grip), 0, 0.3), (unit(lv), 0.02, 0.35), (unit(pivot), 0.05, 0.16), (unit(chain), 0.35, 0.6), (unit(lock), 0.95, 0.9), length=secs(1.7))
        files.append((f"SFX_Lever_{name}", norm_lufs(fade(y, 0.003, 0.3), -21), "拉杆"))
    for k in range(2):
        dsp.seed(160 + k)
        D = 1.6
        scrape = seg("352829", 1.0 + 2.3 * k, D, -3 - k)
        scrape = lp(hp(scrape, 50), 3500)
        scrape = shape(unit(scrape), [(0, 0), (0.06, 1), (0.25, 0.7), (1.3, 0.85), (D, 0.15)])
        start = stone_thud(-1, 5, 0.3)
        end = stone_thud(-3 - k, 6 - k, 0.8)
        rum = sub_rumble(D + 0.6, 80, 0.3, 161 + k)
        y = mix((scrape, 0, 0.8), (unit(start), 0, 0.5), (unit(end), D - 0.03, 1.0), (unit(rum), 0, 0.25), length=secs(D + 0.8))
        files.append((f"SFX_Slab_Slide_{k + 1:02d}", norm_lufs(fade(y, 0.003, 0.3), -19), "石板滑动"))
    return files


def iris_blades(D, opening=True, seed_=0):
    """14 片铜叶片一片接一片滑过，声像绕着头顶转一圈。"""
    dsp.seed(seed_)
    out = np.zeros((secs(D), 2))
    for k in range(14):
        t = 0.25 + (D - 1.1) * (k / 13) ** (1.0 if opening else 0.8)
        b = metal_slide(k, dsp.RNG.uniform(-9, -6), dsp.RNG.uniform(0.5, 0.8))
        pan = np.sin(2 * np.pi * k / 14 + (0 if opening else np.pi))
        out = mix((out, 0), (to_stereo(unit(b) * dsp.RNG.uniform(0.5, 0.9), pan * 0.8), t), length=secs(D))
    return out


@sound(17, "Iris_Blades", "光圈叶片旋开",
       "天花板上的 14 片青铜叶片一片接一片旋开：每一片是真实的金属滑过金属（LordForklift、Qat 的录音）降调成大块铜片，声像绕着头顶转一圈；"
       "底下是转动的机构（真实的木轮转动，降得很低）；全开时铜叶片轻轻共振成一个和弦（D、A，铜盘的真实振动比例）。合拢是倒过来的顺序、最后一声更实。"
       "还有一条叶片滑动的循环，给开合时间不固定的时候用。",
       "Iris_Open / Iris_Close：开、合的完整版（3.5 s）。光圈半径跟着玩家的位置慢慢变时（日4 走圆眼光柱），改用 Iris_Move_Loop，"
       "音量跟半径的变化速度走，停下时补一个 Open 的最后 1 秒（或者只停循环）。立体声，放在圆眼中心（头顶）。", 2)
def b_iris():
    files = []
    for name, opening in [("Open", True), ("Close", False)]:
        D = 3.6
        bl = iris_blades(D, opening, 1700 + opening)
        mech = seg("715478", 30 + 5 * opening, D, -10)
        mech = lp(hp(mech, 40), 900) * dsp.env_ar(secs(D), 0.3, 1.0)
        ring = bronze_ring(hz("D3"), 2.5, 2.0, 0.6) + 0.6 * bronze_ring(hz("A3"), 2.5, 1.6, 0.5)
        ring = lp(ring, 5000)
        end = stone_thud(-6, 2, 0.5, lpf=1500) if not opening else clack(2, -10, 0.3)
        y = mix((bl, 0, 1.0), (to_stereo(unit(mech) * 0.35), 0), (widen(unit(ring) * 0.35), D - 1.3), (to_stereo(unit(end) * 0.5), D - 1.15), length=secs(D + 1.2))
        files.append((f"SFX_Iris_{name}", norm_lufs(fade(y, 0.01, 0.6), -21), "开合"))
    L = iris_blades(6.0, True, 1790)
    m = seg("715478", 40, 6.0, -10)
    L = mix((L, 0), (to_stereo(lp(hp(unit(m), 40), 900) * 0.35), 0))
    files.append(("SFX_Iris_Move_Loop", norm_lufs(loopify(L, 1.2), -24, "integrated"), "滑动·循环", True))
    return files


@sound(18, "Bridge_Gate", "桥门开、关",
       "屋顶细桥尽头的青铜桥门绕门柱转 1.4 秒。开：老铜门轴的低沉呻吟（真实的大铁门吱呀声降了 6 个半音，去掉尖的部分），铜门本身微微共振，转到位轻轻一顿。"
       "关：同样的呻吟更快，最后是厚重的合拢（铁门撞击 + 石门砰地合上的低频）和一声落闩——接住最后一缕光以后它再也不开，所以关门要像“定了”。",
       "Gate_Open：人走近桥尾、门开始转时播；Gate_Close：接住最后一缕光、门开始转回去时播（合拢那一下在 1.35 s）。单声道，放在门轴上。", 2)
def b_gate():
    dsp.seed(18)
    files = []
    D = 1.4
    g = creak(-6, D + 0.3, 0.7)
    g = shape(unit(g), [(0, 0), (0.08, 1), (D - 0.2, 0.8), (D + 0.3, 0)])
    body = bronze_ring(hz("A2"), 2.0, 1.2, 0.5)
    stop = stone_thud(-5, 4, 0.6, lpf=1500)
    y = mix((g, 0, 0.8), (unit(body), 0.02, 0.12), (unit(stop), D, 0.5), length=secs(D + 1.0))
    files.append(("SFX_Gate_Open", norm_lufs(fade(y, 0.005, 0.4), -20), "开"))
    g2 = creak(-5, D, 2.0)
    g2 = shape(unit(g2), [(0, 0), (0.06, 1), (D - 0.1, 0.9), (D, 0)])
    hit = seg("274767", 3.45, 1.4, -5)
    hit = lp(hit, 5000)
    i = int(np.argmax(np.abs(hit[: secs(0.6)])))
    hit = fade(hit[max(0, i - secs(0.003)):][: secs(0.45)], 0.001, 0.25)   # 只要第一下撞击，不要后面铁门的哐啷
    sl = slam(-3, 1.0)
    latch = bolt(0, -2, 0.45)
    ring = bronze_ring(hz("D2"), 3.0, 2.0, 0.5)
    y = mix((g2, 0, 0.7), (unit(hit), D - 0.05, 0.7), (unit(sl), D - 0.05, 0.9), (unit(ring), D - 0.05, 0.15), (unit(latch), D + 0.35, 0.6), length=secs(D + 2.2))
    files.append(("SFX_Gate_Close", norm_lufs(fade(y, 0.005, 0.6), -18), "关"))
    return files


@sound(19, "Statue_Turn", "转动雕像底座",
       "转一格：石像在石台座上转（真实的石板门摩擦，降调），旁边的绞盘咔哒咔哒（轮子转像的两倍：kyles 的绞盘棘爪），到格时石头卡位“咔”一声（xtra1 的石头碰石头，降调）。"
       "4 个版本轮着用。三相像（54° 一格，0.6 s）和天鹅（45° 一格，0.5 s）都用它。",
       "玩家按一次 E、像开始转向下一格时播；Random 不重复，音高 0.97–1.03。单声道，放在台座上。卡位那一下在 0.6 s；天鹅转得快一点，可以把音高调到 1.08。", 2)
def b_statue_turn():
    files = []
    for k in range(4):
        dsp.seed(1900 + k)
        D = 0.62
        gr = heavy_grind(D + 0.1, st=-4 - k * 0.7, seed_=1900 + k, hi=2800)
        gr = shape(gr, [(0, 0), (0.05, 1), (D - 0.1, 0.8), (D + 0.1, 0)])
        rt = seg("454148", 0.22 + 0.05 * k, D + 0.02, -3)
        rt = fade(lp(rt, 6500), 0.002, 0.03)
        det = clack(k * 2 + 1, -7, 0.35)
        thud = stone_thud(-3, k + 1, 0.4, lpf=1500)
        y = mix((gr, 0, 0.7), (unit(rt), 0.02, 0.35), (unit(det), D - 0.01, 0.7), (unit(thud), D - 0.01, 0.6), length=secs(D + 0.55))
        files.append((f"SFX_Statue_Turn_{k + 1:02d}", norm_lufs(fade(y, 0.003, 0.3), -21), "转一格"))
    return files


@sound(20, "Selene_MoonPhase", "塞勒涅怀里的月相持续音",
       "月5 唯一“找位置”的反馈。两层可以无缝循环的长音：Low 是一只真实的摩擦颂钵（hollandm 127 秒的长录音，变到 D4，下面叠低五度的 G3），一直都在、很轻；"
       "High 是两只摩擦水晶杯（A5、D6）加一点闪光，月光罩住月亮越多它越响。站满 1 秒时播 Lock：一声软的颂钵 + 往上收的水晶，接 25 的“亮起来”。",
       "人在月桥上、夜里时，Low、High 两条循环都在播（放在女神怀里的月亮上）：Low 音量 = 0.25 + 0.5 × sweep（被月光扫到的比例），"
       "High 音量 = lit（月光罩住月亮的比例，0–1），可以再把 High 的音高随 lit 从 0.985 推到 1.0（“对准”的感觉）。dwell 到 1 秒时播 Lock，两条循环 1 秒淡出。", 2)
def b_selene_drone():
    files = []
    D = 9.0
    a = seg("573805", 30, D, semis(546.5, hz("D4")))
    b = seg("573805", 60, D, semis(546.5, hz("G3")))
    low = hp(unit(a) + 0.55 * unit(b), 70)
    low = lp(low, 5000)
    files.append(("SFX_Selene_MoonDrone_Low_Loop", norm_lufs(widen(loopify(low, 2.0), 0.4), -27, "integrated"), "低层·循环", True))
    g1 = seg("419146", 1.0, D, semis(1074.0, hz("A5")))
    g2 = seg("418150", 1.0, D, semis(952.5, hz("D6")))
    hi = lp(hp(unit(g1) + 0.6 * unit(g2), 300), 7000)
    sp = sparkle(D, 10, pitch=8, level=0.06, seed_=2020)
    hi = mix((widen(hi, 0.6), 0), (sp, 0))
    files.append(("SFX_Selene_MoonDrone_High_Loop", norm_lufs(loopify(hi, 2.0), -28, "integrated"), "高层·循环", True))
    s = bowl_strike(hz("D4"), 2.5, soft=0.02)
    up = glass_swell(hz("A5"), 1.4, attack=0.9, release=0.4) + 0.7 * glass_swell(hz("D6"), 1.4, attack=1.1, release=0.3)
    y = mix((to_stereo(unit(s) * 0.7), 0), (widen(unit(up) * 0.5, 0.5), 0.1), length=secs(2.6))
    files.append(("SFX_Selene_MoonDrone_Lock", norm_lufs(fade(y, 0.01, 0.5), -24), "对准"))
    return files


@sound(21, "Statue_Push_Pull", "推动、拉出雕像",
       "拉出波吕丢刻斯：石像先“咔”地松动（石头碰撞降调），再从龛里被拖出来 1.6 秒（真实的重石板门摩擦，降 4 个半音），到位一声闷响。"
       "推：一条可以无缝循环的重石头拖地声（两段真实的石头摩擦叠起来，降 5 个半音，加一层隆隆声），配一个起步和一个停下。",
       "PullOut：拉出来时播（1.6 s 的动画）。推的时候：玩家推得动（v > 0.3）就播 Push_Start 再接 Push_Loop（Looping），"
       "音量和音高跟推的速度走（音高 0.9–1.05）；停下或推到卡斯托耳身边时停循环、播 Push_Stop。单声道，跟着雕像走。", 2)
def b_push():
    files = []
    dsp.seed(21)
    D = 1.6
    crack = clack(5, -9, 0.4)
    gr = heavy_grind(D + 0.2, st=-4, seed_=2101, hi=3000)
    gr = shape(gr, [(0, 0), (0.12, 1), (D - 0.2, 0.9), (D + 0.2, 0)])
    end = stone_thud(-5, 2, 0.8, lpf=1500)
    y = mix((unit(crack), 0, 0.7), (gr, 0.05, 0.8), (unit(end), D + 0.02, 0.9), length=secs(D + 0.9))
    files.append(("SFX_Statue_PullOut", norm_lufs(fade(y, 0.002, 0.3), -19), "拉出"))
    L = 6.5
    a = heavy_grind(L, st=-5, seed_=2110, src="352829", start=0.4, hi=3200)
    b = heavy_grind(L, st=-4, seed_=2111, src="844329", start=5.4, hi=2500)
    loop = loopify(unit(a) * 0.7 + unit(b) * 0.6, 1.5)
    files.append(("SFX_Statue_Push_Loop", norm_lufs(loop, -21, "integrated"), "推·循环", True))
    st_ = mix((unit(clack(6, -10, 0.3)), 0, 0.6), (shape(heavy_grind(0.6, -5, 2120), [(0, 0), (0.05, 1), (0.6, 1)]), 0.02, 0.7))
    files.append(("SFX_Statue_Push_Start", norm_lufs(fade(st_, 0.002, 0.1), -21), "推·起步"))
    sp_ = mix((shape(heavy_grind(0.4, -5, 2130), [(0, 1), (0.35, 0)]), 0, 0.6), (unit(stone_thud(-6, 3, 0.7, lpf=1400)), 0.25, 0.8))
    files.append(("SFX_Statue_Push_Stop", norm_lufs(fade(sp_, 0.02, 0.3), -21), "推·停下"))
    return files


def moon_chime_run(D, notes, pans, seed_, start=0.2, end_frac=0.75):
    """一串月光的显形音沿着一道弧铺过去。"""
    dsp.seed(seed_)
    out = np.zeros((secs(D), 2))
    n = len(notes)
    for k, (nt, p) in enumerate(zip(notes, pans)):
        t = start + (D * end_frac - start) * (k / max(1, n - 1)) ** 0.85
        s = bowl_strike(hz(nt), 1.6, soft=0.015)
        s = lp(s, 5000) * (0.5 + 0.5 * dsp.RNG.random())
        out = mix((out, 0), (to_stereo(unit(s) * 0.6, p), t), length=secs(D))
    return out


@sound(22, "Twins_MoonBridge", "双子亮起、月桥伸出",
       "双子并肩、一起亮：两只真实颂钵各一声（D4 和 A4，一人一个音，合起来是五度），木槌的硬起音抹掉，再各自长出摩擦颂钵的长音，像两尊像一起“醒”。"
       "月桥伸出：一道圆弧的月石从他们脚下铺到水庭东边——一串月石显形音沿着弧线从左铺到右、音一级级往上，下面是摩擦颂钵的长音和一点石头的细砂，最后落在 D 上。",
       "Twins_Light：两尊像同时亮起的那一刻，放在两尊像中间。MoonBridge_Extend：紧接着播，立体声，放在月桥中点（或者跟着桥头的显形前沿移动）。", 2)
def b_twins():
    files = []
    dsp.seed(22)
    a = bowl_strike(hz("D4"), 3.2, soft=0.015)
    b = bowl_strike(hz("A4"), 3.2, soft=0.015)
    ha = bowl_hum(hz("D4"), 3.2, start=12, attack=0.6, release=1.6)
    hb = bowl_hum(hz("A4"), 3.2, start=40, attack=0.8, release=1.5)
    y = mix((to_stereo(unit(a) * 0.6, -0.5), 0), (to_stereo(unit(b) * 0.6, 0.5), 0.09), (to_stereo(unit(ha) * 0.4, -0.4), 0), (to_stereo(unit(hb) * 0.35, 0.4), 0.05))
    files.append(("SFX_Twins_Light", norm_lufs(fade(y, 0.01, 0.6), -21), "双子亮起"))
    D = 4.0
    notes = ["A3", "C4", "D4", "F4", "G4", "A4", "C5", "D5"]
    run = moon_chime_run(D, notes, np.linspace(-0.85, 0.85, len(notes)), 2210)
    hum = bowl_hum(hz("D4"), D, start=20, attack=1.0, release=1.5)
    grit = grains(stone_grit(2.0, 4), 3.0, density=25, glen=(0.03, 0.08), pitch=3)
    grit = shape(lp(grit, 6000), [(0, 0), (0.4, 1), (2.6, 0.5), (3.0, 0)])
    sp = sparkle(D, 8, env=[0.1, 0.6, 1, 0.3], pitch=0, level=0.08, seed_=2211)
    y = mix((run, 0, 1.0), (widen(unit(hum) * 0.35, 0.5), 0), (grit * 0.12, 0.2), (sp, 0))
    files.append(("SFX_MoonBridge_Extend", norm_lufs(fade(y, 0.01, 0.8), -21), "月桥伸出"))
    return files


@sound(23, "SwanRelief_Sink", "天鹅浮雕下沉",
       "整面浮雕连同后面的墙往下沉 3 米、2.6 秒：真实的重石板门摩擦降 6 个半音（墙很重），再叠一层真实的重石门打开的摩擦，底下隆隆的振动，"
       "缝里落下的细沙（nicoproson 的沙子），2.6 秒时沉到底“咚”地落定（大石门合上的低频），最后一点尘土。",
       "天鹅解开、浮雕开始下沉时播，单声道，放在浮雕中心。", 2)
def b_swan():
    dsp.seed(23)
    D = 2.6
    a = heavy_grind(D + 0.3, st=-6, seed_=2301, hi=2500)
    b = seg("578491", 5.5, D + 0.3, -4)
    b = lp(hp(b, 40), 3000)
    gr = unit(a) * 0.75 + unit(b) * 0.45
    gr = shape(gr, [(0, 0), (0.15, 0.7), (0.8, 1), (D - 0.25, 1), (D + 0.05, 0.2), (D + 0.3, 0)])
    rum = sub_rumble(D + 1.5, 60, 0.3, 2302)
    rum = shape(rum, [(0, 0), (0.4, 1), (D, 1), (D + 1.5, 0)])
    sand = bp(load("627070", start=20, dur=D + 1.2), 800, 8000)
    sand = shape(sand, [(0, 0), (0.5, 0.6), (D, 1), (D + 1.2, 0)])
    boom = slam(-4, 1.2)
    y = mix((gr, 0, 0.8), (unit(rum), 0, 0.45), (unit(sand), 0, 0.12), (unit(boom), D, 1.0), length=secs(D + 1.6))
    return [("SFX_SwanRelief_Sink", norm_lufs(fade(y, 0.01, 0.5), -17), "下沉")]


@sound(24, "Stairs_Lower", "楼梯降下",
       "接住最后一缕光、回到桥头以后，另外半圈踏步一级接一级降成楼梯：12 块石头先后往下一沉、各自“咚”地落定（vestibule-door 的石面重击和石头落地，降调），"
       "从桥头沿着弧线一路过去（声像从右到左），间隔先快后慢，底下是整段的隆隆声。另附 4 个单级的版本，给程序逐级触发用。",
       "Stairs_Lower：楼梯开始降的那一刻播一次，立体声，放在楼梯中段。要逐级同步的话改用 Stairs_Lower_Step_01–04（单声道，放在那一级上，Random）。", 2)
def b_stairs():
    files = []
    dsp.seed(24)
    D = 5.0
    out = np.zeros((secs(D), 2))
    N = 12
    for k in range(N):
        t = 0.15 + 3.6 * (k / (N - 1)) ** 1.25
        g = shape(heavy_grind(0.45, st=-5 - 0.15 * k, seed_=2400 + k, hi=2500), [(0, 0), (0.05, 1), (0.4, 0.6), (0.45, 0)])
        th = stone_thud(-3 - 0.2 * k, k, 0.6, lpf=1600)
        one = mix((g, 0, 0.45), (unit(th), 0.38, 0.9))
        out = mix((out, 0), (to_stereo(one * (0.9 - 0.03 * k), 0.8 - 1.6 * k / (N - 1)), t), length=secs(D))
    rum = sub_rumble(D, 70, 0.4, 2420)
    rum = shape(rum, [(0, 0), (0.4, 1), (3.8, 1), (D, 0)])
    y = mix((out, 0), (to_stereo(unit(rum) * 0.3), 0))
    files.append(("SFX_Stairs_Lower", norm_lufs(fade(y, 0.01, 0.6), -18), "整段"))
    for k in range(4):
        g = shape(heavy_grind(0.45, st=-5, seed_=2440 + k, hi=2500), [(0, 0), (0.05, 1), (0.4, 0.6), (0.45, 0)])
        th = stone_thud(-3, k + 2, 0.6, lpf=1600)
        y = mix((g, 0, 0.45), (unit(th), 0.38, 0.9))
        files.append((f"SFX_Stairs_Lower_Step_{k + 1:02d}", norm_lufs(fade(y, 0.003, 0.3), -21), "单级"))
    return files


@sound(25, "Selene_Awaken_HalfBridge", "塞勒涅神像亮起、半桥伸出",
       "月光整个落进她怀里的月亮：低音区一声很深的颂钵（D3），20 的长音在这里“解决”——摩擦颂钵 D4、A4 一起长起来，最上面是水晶杯的 D6，"
       "像整座雕像慢慢亮透。半桥：一段石桥从池沿沿半径伸向水亭（2 秒，比雕像轻的石头摩擦），桥头搅动水面（真实的浪拍礁石里最轻的一段），到头轻轻一顿；"
       "按试听反馈比第一版轻了 4 dB、最低的隆隆声也去掉了一点。",
       "Selene_Awaken：dwell 满 1 秒、她亮起来时播（接在 20 的 Lock 后面），放在雕像上。HalfBridge_Extend：半桥开始伸出时播，放在池沿的桥头。", 2)
def b_selene_awaken():
    files = []
    dsp.seed(25)
    D = 4.5
    deep = bowl_strike(hz("D3"), D, soft=0.03)
    h1 = bowl_hum(hz("D4"), D, start=25, attack=1.2, release=2.0)
    h2 = bowl_hum(hz("A4"), D, start=50, attack=1.5, release=2.0)
    gl = glass_swell(hz("D6"), D - 0.6, attack=1.8, release=1.8)
    sp = sparkle(D, 10, env=[0, 0.4, 1, 0.5, 0.1], pitch=3, level=0.07, seed_=2501)
    y = mix((to_stereo(unit(deep) * 0.7), 0), (widen(unit(h1) * 0.4), 0.1), (widen(unit(h2) * 0.3), 0.3), (widen(unit(gl) * 0.18, 0.7), 0.6), (sp, 0.4))
    files.append(("SFX_Selene_Awaken", norm_lufs(fade(y, 0.01, 1.0), -20), "神像亮起"))
    D = 2.0
    gr = heavy_grind(D + 0.2, st=-2, seed_=2510, src="352829", hi=3500)
    gr = hp(shape(gr, [(0, 0), (0.1, 0.9), (D - 0.2, 0.8), (D + 0.2, 0)]), 70)    # 半桥比雕像轻：去掉一点最低的隆隆声
    wat = load("457956", start=40, dur=D + 0.8)
    wat = bp(wat, 300, 6000)
    wat = shape(wat, [(0, 0), (0.4, 1), (D, 0.8), (D + 0.8, 0)])
    end = stone_thud(-2, 4, 0.6, lpf=1800)
    y = mix((gr, 0, 0.7), (unit(wat), 0, 0.35), (unit(end), D, 0.45), length=secs(D + 1.0))
    files.append(("SFX_HalfBridge_Extend", norm_lufs(fade(y, 0.01, 0.4), -24), "半桥伸出"))   # 试听反馈：再轻一点（原来 -20）
    return files


@sound(26, "ShadowBridge_Join", "影桥接上",
       "屋顶细桥的月影在水面上挪过来，正好接上半桥的尽头、亮起来。水面轻轻的波光声（真实的浪拍礁石里最轻的一段，只留中高频），"
       "一对摩擦颂钵和水晶杯从差一点点（低 30 音分）滑到正好对上——“对齐了”——然后一起亮开。",
       "影桥 on 从 0 往 1 走时播一次（1.4 s 内接上），立体声，放在影桥中点。", 2)
def b_shadow():
    dsp.seed(26)
    D = 3.2
    def glide(x, cents_from):
        n = len(x)
        r = 2 ** (np.linspace(cents_from, 0, n) ** 1 / 1200)
        r[secs(1.2):] = 1.0
        r[: secs(1.2)] = 2 ** (np.linspace(cents_from, 0, secs(1.2)) / 1200)
        idx = np.cumsum(r)
        idx = idx[idx < n - 1]
        return np.interp(idx, np.arange(n), x)
    b1 = glide(bowl_hum(hz("D4"), D + 0.3, start=30, attack=0.5, release=1.4), -30)
    g1 = glide(glass_swell(hz("A5"), D + 0.3, attack=0.7, release=1.4), -30)
    bloom = bowl_strike(hz("A4"), 2.0, soft=0.03)
    wat = load("457956", mono=False, start=26, dur=D)
    wat = bp(wat, 600, 7000)
    wat = shape(wat, [(0, 0), (0.5, 1), (2.4, 0.6), (D, 0)])
    sp = sparkle(D, 10, env=[0.2, 0.6, 1, 0.3], pitch=5, level=0.08, seed_=2601)
    y = mix((widen(unit(b1) * 0.45), 0), (widen(unit(g1) * 0.3, 0.6), 0.1), (to_stereo(unit(bloom) * 0.4), 1.25), (unit(wat) * 0.2, 0), (sp, 0))
    return [("SFX_ShadowBridge_Join", norm_lufs(fade(y, 0.01, 0.8), -22), "接上")]


@sound(27, "Apple_Place", "放上金苹果",
       "结局动作。金苹果轻轻落进浑天仪的铜托：一声软的金属碰金属（HenKonen 的金属轻碰，低通抹软），铜托本身“嗡”一下（铜盘的真实振动比例）；"
       "接着苹果从金色变成月白、光一点点亮起来（0.5–3 秒）：颂钵 D4、水晶杯 A5 和 D6 慢慢长起来，最后停在一个很安静的 D 上。",
       "放上苹果那一刻播，放在小亭的浑天仪上。不要和结局音乐（13）抢：结局音乐最好在 3 秒以后进来。", 2)
def b_apple():
    dsp.seed(27)
    D = 6.0
    tink = seg("682154", 0.08, 1.2, -5)
    tink = fade(lp(tink, 4000), 0.001, 0.5)
    holder = bronze_ring(hz("D4"), 2.5, 1.8, 0.4)
    h = bowl_hum(hz("D4"), D - 0.5, start=35, attack=1.6, release=2.2)
    g1 = glass_swell(hz("A5"), D - 1.0, attack=2.0, release=2.2)
    g2 = glass_swell(hz("D6"), D - 1.4, attack=2.2, release=2.0)
    sp = sparkle(D, 12, env=[0, 0.3, 0.8, 1, 0.4, 0], pitch=4, level=0.06, seed_=2701)
    y = mix((to_stereo(unit(tink) * 0.55), 0), (to_stereo(unit(holder) * 0.25), 0.005), (widen(unit(h) * 0.35), 0.5),
            (widen(unit(g1) * 0.25, 0.6), 0.6), (widen(unit(g2) * 0.15, 0.7), 1.0), (sp, 0.5), length=secs(D))
    return [("SFX_Apple_Place", norm_lufs(fade(y, 0.002, 1.5), -21), "放上")]


def bronze_step(s, f0, seed_, metal=None, metal_gain=0.3):
    dsp.seed(seed_)
    s = cap(unit(s))
    ex = s[: secs(0.01)]
    ring = modal([f0 * r for r in BRONZE_PLATE[:6]], [0.22, 0.15, 0.1, 0.09, 0.07, 0.06], [1, 0.6, 0.45, 0.35, 0.25, 0.2], 0.5, detune=0.004)
    ring = lp(unit(ring), 5000)
    d = peak_at(s)
    parts = [(s, 0), (ring, d / SR, 0.22)]
    if metal is not None:
        parts.append((lp(unit(metal), 4000) * metal_gain, 0))
    y = mix(*parts)
    y = eq(y, "peak", 2500, -2, 1.0)
    y = dsp.limit(unit(y), -4.0)
    return fade(trim_tail(y, -50, 0.06), 0.0015, 0.06)


@sound(28, "Footstep_Bronze", "脚步：青铜",
       "凉鞋踩在厚青铜板上（环道、细桥、半桥）：和石头脚步同一双凉鞋，下面的“实”换成青铜——厚铜板的真实振动比例做的短共振（不是薄铁皮那种空响），"
       "叠一点真实的金属地面脚步（nate_asdfg、gristi 的录音，低通）。走 8 个、快走 6 个、落地 2 个。",
       "和石头脚步同一套触发，脚下是青铜（Physical Material = Bronze）时换这一组。", 2)
def b_foot_bronze():
    files = []
    walk_s, run_s = sandal_pool(), sandal_run_pool()
    mp = step_pool([("463811", 0, 3.6, 0.25), ("562195", 0, 3.1, 0.25), ("698697", 0, 10.3, 0.3)], hp_f=80, keep_db=10, post=0.3)
    dsp.seed(28)
    for k in range(8):
        f0 = dsp.RNG.uniform(180, 260)
        y = bronze_step(walk_s[(k * 3 + 1) % len(walk_s)], f0, 2800 + k, mp[k % len(mp)], 0.3)
        files.append((f"SFX_Footstep_Bronze_Walk_{k + 1:02d}", norm_lufs(y, -28), "走"))
    for k in range(6):
        f0 = dsp.RNG.uniform(200, 290)
        y = bronze_step(run_s[(k * 5 + 2) % len(run_s)], f0, 2850 + k, mp[(k + 3) % len(mp)], 0.35)
        files.append((f"SFX_Footstep_Bronze_Run_{k + 1:02d}", norm_lufs(y, -26), "快走"))
    for k in range(2):
        a = bronze_step(walk_s[(k * 7 + 3) % len(walk_s)], 170, 2880 + k, mp[(k + 1) % len(mp)], 0.5)
        b = bronze_step(walk_s[(k * 7 + 5) % len(walk_s)], 210, 2890 + k, None)
        y = mix((a, 0), (b, 0.022, 0.8))
        files.append((f"SFX_Land_Bronze_{k + 1:02d}", norm_lufs(y, -21), "落地"))
    return files


@sound(29, "UI", "界面：按钮悬停、确认、返回，开始游戏",
       "界面也用游戏里的材料：悬停是一把小锤在石头上轻轻一点（Shamewap 的录音，很短、很轻）；确认是一只小铜钵敲一下（FOSSarts），0.8 秒收住；"
       "返回是同一只钵、更低更闷、更短；开始游戏的第一声就是“确认”那一下（让它多响一会儿），接着水晶杯 D、A 慢慢亮起来，像走进光里（3.5 秒）。",
       "2D（不空间化），放到 UI 的 Sound Class。Hover 两个 Random；Confirm / Back 各一个；StartGame 在点“开始”时播，"
       "可以和第一声海浪（11）重叠。", 2)
def b_ui():
    files = []
    x = hp(load("389692"), 300)
    ev = sorted(events(x, min_dist=0.12, post=0.15, prom_db=12), key=lambda e: -e[2])
    for k in range(2):
        a, b, p = ev[3 + 4 * k]
        y = x[secs(a):secs(b)]
        i = int(np.argmax(np.abs(y)))
        y = fade(lp(y[max(0, i - secs(0.002)):][: secs(0.08)], 9000), 0.001, 0.04)
        files.append((f"SFX_UI_Hover_{k + 1:02d}", norm_lufs(to_stereo(y), -32), "悬停"))
    def brass(st, dur, lpf):
        y = seg("762646", 0.0, dur + 0.5, st)
        i = int(np.argmax(np.abs(y[: secs(0.6)])))
        y = y[max(0, i - secs(0.003)):][: secs(dur)]
        return fade(lp(hp(y, 150), lpf), 0.001, dur * 0.6)
    files.append(("SFX_UI_Confirm", norm_lufs(to_stereo(brass(semis(780.5, hz("A5")), 0.8, 9000)), -25), "确认"))
    files.append(("SFX_UI_Back", norm_lufs(to_stereo(brass(semis(780.5, hz("D5")), 0.5, 3500)), -27), "返回"))
    D = 3.6
    hit = brass(semis(780.5, hz("A5")), 2.5, 9000)      # 第一声和“确认”是同一下（A5），只是让它多响一会儿
    g1 = glass_swell(hz("D5"), D - 0.4, attack=1.0, release=1.6)
    g2 = glass_swell(hz("A5"), D - 0.6, attack=1.2, release=1.5)
    sp = sparkle(D, 9, env=[0, 0.5, 1, 0.3, 0], pitch=8, level=0.06, seed_=2901)
    y = mix((to_stereo(unit(hit) * 0.6), 0), (widen(unit(g1) * 0.35, 0.6), 0.2), (widen(unit(g2) * 0.25, 0.7), 0.4), (sp, 0.3), length=secs(D))
    files.append(("SFX_UI_StartGame", norm_lufs(fade(y, 0.001, 1.0), -22), "开始游戏"))
    return files


@sound(30, "LightPath_Reveal_Opening", "开场光路显形",
       "开场第一个“光”的声音：和 5 是同一套素材（摩擦水晶杯、被照亮的水雾、玻璃闪光），拉长到 4.5 秒，跟着光从门廊上方的窗一点点伸到岛上（约 3 秒）——"
       "低通一路打开，声像从远处（正前）慢慢铺开，闪光越来越多；光伸到岛上那一刻落在 D、A 上。",
       "开场往神殿迈第一步、光开始伸出来时播一次（灰盒 updateIsleGrow）。立体声；2D 播放也可以（这是开场的“标题音”）。", 2)
def b_opening():
    dsp.seed(30)
    D = 4.6
    a = glass_swell(hz("D5"), D, attack=1.3, release=1.4, start=1.5)
    b = glass_swell(hz("A5"), D - 0.3, attack=2.0, release=1.3, start=2.5)
    c = glass_swell(hz("D6"), D - 1.0, attack=1.8, release=1.2, start=3.5)
    tone = mix((a, 0, 1.0), (b, 0.2, 0.6), (c, 0.9, 0.35))
    tone = sweep_filter(tone, np.concatenate([np.geomspace(700, 9000, 60), np.full(40, 9000)]), None)
    st = widen(tone, 0.2, 0.013)
    # 声像慢慢铺开
    w = np.linspace(0.15, 1.0, len(st))[:, None]
    m = st.mean(axis=1, keepdims=True)
    st = m + (st - m) * w * 3
    mi = mist(D) * 0.08
    mi = shape(mi, [(0, 0), (1.0, 0.4), (3.0, 1), (D, 0)])
    sp = sparkle(D, 18, env=[0.4, 0.5, 0.7, 1, 0.4], pitch=9, level=0.1, seed_=3001)
    arrive = glass_tone(hz("A5"), 1.6, attack=0.02, t60=1.0) + 0.6 * glass_tone(hz("D5"), 1.6, attack=0.02, t60=1.1)
    y = mix((st, 0), (mi, 0), (sp, 0), (widen(lp(arrive, 6000) * 0.25), 3.0), length=secs(D))
    return [("SFX_LightPath_Reveal_Opening", norm_lufs(fade(y, 0.05, 0.8), -23), "开场")]



# 每一条的排序理由（照排期表）和它属于白天、夜里还是全程（试听页按这个上色）
REASONS = {
    3: "全程都在响，频率最高", 4: "踩光是核心操作，要让玩家一听就知道“脚下是光”", 5: "每束光出现都靠它提示“这里能走了”，全程反复出现",
    6: "夜里的核心反馈，月2 到月5 一直在用", 8: "光阶等关卡的基本操作", 9: "让玩家放心“没有死亡”", 10: "日1 的核心机关，又是贯穿全程的环境声",
    11: "开场第一声，殿外一直在", 14: "第一个机关，教会玩家“动机关会改变光”", 15: "日5、月1 的主体，音高逐级变化本身就是反馈",
    16: "日2 主线", 17: "日4 的视觉奇观，需要声音撑住", 18: "日5 进门、入夜关门，两个节点", 19: "月2、月3 都要用，转很多次",
    20: "月5 唯一的“找位置”反馈，没有它很难找", 21: "月4 要推很长一段", 22: "月4 的解谜奖励", 23: "月2 的解谜奖励", 24: "月1 入夜后第一条路",
    25: "月5 的解谜奖励", 26: "通往结局的最后一段路", 27: "结局动作", 28: "环道、细桥、半桥都会踩到", 29: "基础交互",
    30: "开场第一个“光”的声音，和第 5 条共用素材再加长",
}
WHEN = {3: "both", 4: "day", 5: "day", 6: "night", 8: "both", 9: "both", 10: "both", 11: "both", 14: "day", 15: "both", 16: "day",
        17: "day", 18: "day", 19: "both", 20: "night", 21: "night", 22: "night", 23: "night", 24: "night", 25: "night", 26: "night",
        27: "night", 28: "both", 29: "ui", 30: "day"}
# 试听页上“连着播”的按钮：组名 → (按钮文字, 间隔秒, 是否随机顺序)
SEQUENCES = {"走": ("走一段", 0.5, True), "快走": ("快走一段", 0.33, True), "升起": ("顺序播放 16 级", 0.42, False),
             "落平": ("顺序播放 16 级", 0.42, False), "单级": ("一级接一级", 0.55, True), "悬停": ("来回悬停", 0.18, True)}


def write_index(manifest):
    """试听页：模板里的 /*MANIFEST*/ 换成数据。仓库里的版本补上文档外壳，发布版本（_artifact.html）不要外壳。"""
    tpl = open(os.path.join(os.path.dirname(__file__), "index_template.html"), encoding="utf-8").read()
    data = dict(items=[dict(it, reason=REASONS.get(it["num"], ""), when=WHEN.get(it["num"], "both")) for it in manifest["items"]],
                sequences=SEQUENCES, credits=manifest["credits"])
    page = tpl.replace("/*MANIFEST*/null", json.dumps(data, ensure_ascii=False))
    shell = ('<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
             '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n')
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(shell + page + "\n</body>\n</html>\n")
    return page


README_HEAD = """# 音效 · 第一、第二梯队

日落回廊的音效：第一梯队里除了 1、2、7、12、13（时间和声、接光主题、主界面音乐、结局音乐，之后单独做）以外的全部，加上第二梯队全部（14–30）。
共 {n_items} 条、{n_files} 个文件。**试听：用浏览器打开 [index.html](index.html)**（按编号分组，可以切“殿内混响”听放进圆殿以后的样子）。

## 怎么做的

**要真实**，所以能用真实录音的地方都用真实录音：{n_src} 段 Freesound 上的 CC0 录音（凉鞋、石地面、石板门、铁链、铜钵、水晶杯、瀑布、海浪……，出处在最后），切、降调、叠层、滤波、对齐响度。
光、月光这些“现实里不发声”的东西，也用真实的材料来发声：

- **日光 = 玻璃**：摩擦的水晶杯（有真实的颤动）、玻璃轻碰的闪光、被照亮的水雾（瀑布录音里最高的那一段）。
- **月光 = 铜钵**：敲击、摩擦的颂钵，比日光低、冷；月石显形混一点石头的细砂，隐去混真实的流沙。
- **石头机关 = 真实的石板门摩擦**，降几个半音（越重降得越多），底下垫一层很低的隆隆声；落定用真实的石头重击。
- **会“发音”的石头和青铜**（升起的台阶、桥门、铜托）用模态合成：按真实物体的振动比例（两端自由的石条 1 : 2.76 : 5.40 : 8.93、厚铜盘）合成，再用真实的碰撞声去激发，所以起音还是真的。

**音高**：所有有音高的声音都在 d 小调五声（D F G A C）里，这几个音都在灰盒现有的时间和弦里（`CHORDS`），以后做时间和声时不会打架。
日光的音在 D5–D6，月光在 A3–A4，屋顶 16 级台阶从 D3 一级级升到 D6。

## 格式和用法（UE）

- 48 kHz、16 位 WAV，直接拖进 UE。**干声**（没有混响）：殿内的空间感交给 Audio Volume 的混响，或者用 [ir/IR_Temple_Rotunda.wav](ir/IR_Temple_Rotunda.wav)
  建一个 Convolution Reverb（合成的石头圆殿脉冲响应：早期反射按半径约 15 m 的圆墙，低频 4.2 s、高频 1.6 s 的尾巴）。
- 点声源（脚步、机关、月石……）是**单声道**，开 Spatialization；环境床（海浪、瀑布）、界面、几条要有宽度的（光路显形、光圈、月桥……）是**立体声**。
- **响度已经对齐过**，彼此之间的大小就是想要的混音比例，UE 里音量都先放 1.0 再微调：
  脚步 −28 LUFS（快走 −26），光路显形 −25，机关 −18 到 −21，界面 −25 到 −32；循环按整段响度：瀑布近 −21、海浪近 −22、远的更低。峰值都在 −1 dBFS 以下。
- 名字里带 `_Loop` 的是首尾无缝的循环，在 Sound Wave 上勾 Looping。
- 同一组有好几个文件的（`_01`、`_02`……）用 Sound Cue 的 Random 节点（勾“不重复”）。

## 每一条

"""

README_TAIL = """
## 重新生成

```
pip install numpy scipy soundfile
python audio/tools/fetch_sources.py   # 下载素材到 audio/_src（不进仓库；需要 curl、ffmpeg）
python audio/tools/build.py           # 全部重新生成；build.py 5 15 只生成这几条
```

`tools/dsp.py` 是小工具箱（滤波、模态合成、切脚步、无缝循环、响度），`tools/build.py` 里一条音效一个函数，参数都在里面（音高、长短、各层的比例），要改哪条就改哪个函数再跑一遍。
随机数都固定了种子，同样的素材生成的结果一样。这个文件（README）和 `manifest.json` 也是 build.py 生成的。

## 还没做

- 第一梯队的 1、2（时间和声）、7（接光主题）、12（主界面音乐）、13（结局音乐）。
- 第三、四梯队（31–58）。其中不少可以直接复用这里的素材：脚步（月石、月桥、影桥）用 4 的光路脚步换成 6 的颂钵；墙里楼梯的窗、石块用 16、23 的石头；碎片放入凹槽用 27。
- 这些声音是按频谱、波形、响度一条条检查过的，但还需要真人戴耳机在游戏里听一遍：哪条太响、太长、太“假”，告诉我改哪个函数的哪几个参数。

## 素材出处

全部是 Freesound 上的 CC0（公有领域）录音：可以商用、可以改，不需要署名。还是列出来，方便以后找回原始录音、换更高质量的版本（这里用的是 Freesound 的高质量试听版，约 192 kbps）。

| 编号 | 作者 | 名字 |
|---|---|---|
"""


def write_readme(manifest):
    items = manifest["items"]
    n_files = sum(len(it["files"]) for it in items)
    out = [README_HEAD.format(n_items=len(items), n_files=n_files, n_src=len(manifest["credits"]))]
    for it in items:
        tier = {1: "第一梯队", 2: "第二梯队"}[it["tier"]]
        out.append(f"### {it['num']}. {it['zh']}（{tier}）\n")
        out.append(f"**怎么做的**：{it['what']}\n")
        out.append(f"**UE 里怎么用**：{it['ue']}\n")
        groups = {}
        for f in it["files"]:
            groups.setdefault(f["group"], []).append(f)
        out.append("| 用途 | 文件 | 时长 | 声道 |\n|---|---|---|---|")
        for g, fs in groups.items():
            if len(fs) > 2:
                a, b = fs[0]["name"], fs[-1]["name"]
                durs = [f["dur"] for f in fs]
                out.append(f"| {g} | `{a}` … `{b[-2:]}`（{len(fs)} 个） | {min(durs):.2f}–{max(durs):.2f} s | {'单' if fs[0]['ch'] == 1 else '立体'} |")
            else:
                for f in fs:
                    loop = "（循环）" if f["loop"] else ""
                    out.append(f"| {g} | [`{f['name']}`]({f['path']}){loop} | {f['dur']:.2f} s | {'单' if f['ch'] == 1 else '立体'} |")
        out.append(f"\n文件夹：[{it['files'][0]['path'].rsplit('/', 1)[0]}/]({it['files'][0]['path'].rsplit('/', 1)[0]}/)\n")
    out.append(README_TAIL)
    for k, v in manifest["credits"].items():
        out.append(f"| [{k}]({v['url']}) | {v['user']} | {v['title']} |")
    open(os.path.join(ROOT, "README.md"), "w").write("\n".join(out) + "\n")


# ═════════════════════════ 输出 ═════════════════════════
def run(selected=None):
    os.makedirs(OUT, exist_ok=True)
    man_path = os.path.join(ROOT, "manifest.json")
    manifest = json.load(open(man_path)) if os.path.exists(man_path) else {"items": []}
    by_num = {it["num"]: it for it in manifest["items"]}
    for spec in REG:
        if selected and spec["num"] not in selected:
            continue
        folder = f"{spec['num']:02d}_{spec['key']}"
        d = os.path.join(OUT, folder)
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.endswith(".wav"):
                    os.remove(os.path.join(d, fn))
        files = []
        for f in spec["fn"]():
            name, x, group = f[0], f[1], f[2]
            loop = len(f) > 3 and f[3]
            path = os.path.join(d, name + ".wav")
            y = dsp.write(path, x, peak_db=-1.0)
            files.append(dict(path=f"sfx/{folder}/{name}.wav", name=name, group=group, loop=bool(loop),
                              ch=1 if y.ndim == 1 else 2, dur=round(len(y) / SR, 2),
                              lufs=round(dsp.lufs(y, "integrated" if loop else "max"), 1)))
        by_num[spec["num"]] = dict(num=spec["num"], tier=spec["tier"], key=spec["key"], zh=spec["zh"],
                                   what=spec["what"], ue=spec["ue"], files=files)
        print(f"{spec['num']:>3} {spec['zh']}: {len(files)} 个文件")
    manifest["items"] = [by_num[k] for k in sorted(by_num)]
    # 素材出处（只列 build.py 真正用到的，见 tools/sources.json）
    cr = json.load(open(os.path.join(os.path.dirname(__file__), "sources.json")))
    manifest["credits"] = {k: dict(title=v["title"], user=v["user"], url=v["url"]) for k, v in sorted(cr.items(), key=lambda kv: int(kv[0]))}
    json.dump(manifest, open(man_path, "w"), ensure_ascii=False, indent=1)
    write_readme(manifest)
    write_index(manifest)
    # 殿内混响的脉冲响应
    irp = os.path.join(ROOT, "ir", "IR_Temple_Rotunda.wav")
    if not os.path.exists(irp):
        dsp.write(irp, make_ir() * 0.5, peak_db=-1.0, bits=16)


if __name__ == "__main__":
    sel = [int(a) for a in sys.argv[1:]] or None
    run(sel)
