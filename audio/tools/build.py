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


def step_pool(specs, hp_f=90, keep_db=12, post=0.38, max_pre=0.03, min_crest=0.0, max_crest=26.0, keep=None):
    """从整段脚步录音里切出一步一步。specs: [(素材, 起, 止, 两步最小间隔)]；keep(step_feel) 为假的不要。"""
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
            if len(seg) > secs(0.08) and min_crest <= crest_db(seg) <= max_crest and (keep is None or keep(step_feel(seg))):
                out.append(seg)
    return out


def peak_at(x, within=0.2):
    m = np.abs(to_mono(x[: secs(within)]))
    return int(np.argmax(m))


def align_add(base, layer, gain, off=0.0, at=None):
    """把 layer 的峰（或 at 那个采样点）对齐到 base 的峰，再往后挪 off 秒，叠上去。"""
    d = peak_at(base) - (peak_at(layer) if at is None else at) + secs(off)
    if d >= 0:
        layer = np.concatenate([np.zeros(d), layer])
    else:
        layer = fade(layer[-d:], 0.002, 0.0)          # 切掉的头补个淡入，免得咔
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
    # 凉鞋拍地：按 soft_slap 挑软一点的（第一版专挑最尖的，听着硬）
    return step_pool([("734632", 10, 21, 0.3), ("119912", 0, 6, 0.3), ("119911", 0, 4.8, 0.3)], keep=lambda f: soft_slap(f))


def sandal_run_pool():
    return step_pool([("734632", 0, 10, 0.22), ("734632", 25, 35, 0.3)], post=0.3, keep=lambda f: soft_slap(f))


def stone_body_pool():
    return step_pool([("813622", 0, 6.7, 0.3)], hp_f=70, post=0.3)


def unit(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def cap(x, after_peak=0.17, fout=0.06):
    """一步只留峰后 after_peak 秒（凉鞋后面那一下拍脚跟不要，免得听成两步）。"""
    n = min(len(x), peak_at(x) + secs(after_peak))
    return fade(x[:n], 0.0, fout)


def match_level(x, ref, rel_db=0.0):
    """按整段的能量把 x 调到比 ref 高 rel_db（比按峰值对齐更接近耳朵听到的响）。"""
    return x * np.sqrt(np.sum(ref ** 2) / (np.sum(x ** 2) + 1e-20)) * db(rel_db)


def decay_after(x, i, t60):
    """第 i 个采样以后按指数收（t60 秒），以前不动。"""
    e = np.ones(len(x))
    e[i:] = expdecay(len(x) - i, t60)
    return x * e


def onset_at(x, frac=0.1):
    m = to_mono(x)
    env = np.sqrt(np.convolve(m ** 2, np.ones(48) / 48, mode="same"))
    return int(np.argmax(env > env.max() * frac))


def step_feel(x):
    """量一步听着多硬、多刺、多重（dB）：crest 前 100 ms 的峰值因数，attack 起音后 4 ms 对再后 40 ms 的能量，
    harsh 2.5–6 kHz 占的比例，low 250 Hz 以下占的比例；lead 是峰离开头几秒。"""
    m = to_mono(x)
    on = onset_at(m)
    a, b = m[on:on + secs(0.004)], m[on + secs(0.004):on + secs(0.044)]
    seg = m[on:on + secs(0.25)]
    X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 8192)) ** 2
    f = np.fft.rfftfreq(8192, 1 / SR)
    tot = np.sum(X[f >= 20]) + 1e-20

    def share(lo, hi):
        return 10 * np.log10(np.sum(X[(f >= lo) & (f < hi)]) / tot + 1e-12)
    return dict(crest=crest_db(m), attack=10 * np.log10((np.mean(a ** 2) + 1e-12) / (np.mean(b ** 2) + 1e-12)),
                harsh=share(2500, 6000), low=share(20, 250), lead=peak_at(m) / SR)


# 试听反馈第二轮：脚步“稍微有一点重、硬和刺耳”。比过两种改法（指标见 PR）：换更软的素材（B）和模拟更软的鞋底（C）。
# C 只把起音抹软了，刺耳的频段和低频几乎没动；B 三样都达标，留下 B：
# 大理石上赤脚落地的那一下领头，凉鞋拍地只挑不尖、不刺的，垫在后面；石头的“实”更轻、更短。


def soft_slap(f):
    # 凉鞋拍地的那一下：不要太尖、太刺，不要脚跟的闷“咚”，峰要在开头 40 ms 内（和脚落地对齐）
    return f["crest"] <= 22 and f["attack"] <= 6 and f["harsh"] <= -4.5 and f["low"] <= -6 and f["lead"] <= 0.04


def heel_pool():
    # 脚掌落在大理石上的那一下（ragamuffin 的大理石地面脚步）：软、圆；最尖的那几下不要
    return step_pool([("118985", 0, 7.3, 0.3)], post=0.3, max_crest=17)


_HEELS = None


def contact(sandal, k=0, run=False):
    """一只脚落地的“接触”那一下（单位峰值）。石头、光路、青铜、落地、回到落脚点都从这里出来：
    脚掌落在大理石上的“嗒”领头（软、圆），4 毫秒后凉鞋轻轻拍一下；凉鞋最刺耳的 3.8 kHz 一带压掉 7 dB。"""
    global _HEELS
    if _HEELS is None:
        _HEELS = heel_pool()
    h = resample_pitch(_HEELS[(k * 3 + run) % len(_HEELS)], 1.0 if run else 2.0)   # 往上挪一两个半音：步子轻一些
    h = cap(unit(lp(hp(h, 250 if run else 300), 5000)))
    i = peak_at(sandal)
    sl = eq(lp(hp(sandal, 200), 10000), "peak", 3800, -7.0, 0.8)
    sl = fade(decay_after(sl, i, 0.3 if run else 0.5)[: i + secs(0.17)], 0.0, 0.06)
    y = align_add(h, match_level(sl, h, -6.0 if run else -3.5), 1.0, off=0.004, at=i)
    return unit(y)


def footstep(sandal, body, body_gain, bright=0.0, low=0.0, k=0, run=False):
    c = contact(sandal, k, run)
    # 石头的“实”：轻一点、短一点，最低的那一截拿掉（女神走路，不是壮汉跺脚）
    b = lp(hp(unit(body), 140), 2200)
    b = b * expdecay(len(b), 0.12)
    y = align_add(c, b, body_gain)
    y = eq(y, "peak", 400, -2.5, 0.9)
    y = eq(y, "lowshelf", 160, low)
    y = eq(y, "highshelf", 7000, bright - 3.0)
    # 脚跟那一毫秒的尖峰削掉几 dB（录音里常见的处理），这样一组脚步的响度才对得齐
    y = dsp.limit(unit(y), -5.0)
    return fade(trim_tail(y), 0.0015, 0.03)


# ═════════════════════════ 第一梯队 ═════════════════════════

@sound(3, "Footstep_Stone", "脚步：石头/大理石",
       "皮凉鞋踩在大理石上。领头的是真实的大理石地面上脚掌落地的那一下（ragamuffin 的录音，软、圆），4 毫秒后是凉鞋轻轻一拍"
       "（Vrymaa、ftpalad 的录音里只挑不尖、不刺的），最下面垫一点真实的石地面脚步的“实”（SecureSubset，去掉最低的一截、很短）。"
       "第二版按试听反馈改轻、改软：比第一版刺耳的 2.5–6 kHz 少 3.6 dB、起音软了约 10 dB、250 Hz 以下少 4 dB。走 10 个、快走 8 个、蹭地 4 个，响度都对齐。",
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
        y = footstep(s, b, db(dsp.RNG.uniform(-10, -8)), low=-1.0, k=k)
        files.append((f"SFX_Footstep_Stone_Walk_{k + 1:02d}", norm_lufs(y, -28), "走"))
    order = dsp.RNG.permutation(len(run_s))
    for k in range(8):
        s = run_s[order[k % len(run_s)]]
        b = resample_pitch(body[(k + 2) % len(body)], dsp.RNG.uniform(-1.0, 1.5))
        y = footstep(s, b, db(dsp.RNG.uniform(-9, -7)), low=-0.5, k=k, run=True)
        files.append((f"SFX_Footstep_Stone_Run_{k + 1:02d}", norm_lufs(y, -26), "快走"))
    # 蹭地：赤脚/凉鞋在石面上转身、停步时的擦声（SpliceSound 的瓷砖擦地录音）
    sc = step_pool([("197404", 0, 29, 0.3)], hp_f=120, keep_db=8, post=0.45)
    for k in range(4):
        y = trim_tail(eq(sc[(3 * k + 1) % len(sc)], "highshelf", 6000, -2))
        files.append((f"SFX_Footstep_Stone_Scuff_{k + 1:02d}", norm_lufs(y, -31), "蹭地"))
    return files


def light_step(s, f, level_glass, t60, seed_):
    dsp.seed(seed_)
    s = hp(cap(contact(s, seed_), 0.15), 320, order=2)     # 光没有分量：低频比石头脚步拿得更干净
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
       "脚下是光：和石头脚步同一个“接触”（脚掌落地 + 轻轻的凉鞋，第二版一起改软了），去掉石头的“实”（低频全拿掉，光没有分量），每一步激起一点水晶的余振——"
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
       "落地：两只脚前后差 15–30 毫秒落下，石地面的“实”比走路重一点，最后衣料落定一下。另有落在光上的版本：没有石头的重量，脚下一声水晶。"
       "第二版跟着脚步一起改轻、改软，起跳里刺耳的那一段也收了一点。",
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
        y = eq(eq(y, "peak", 3500, -4.0, 0.8), "highshelf", 6500, -3.0)   # 和脚步一起：刺耳的那一段收一点
        files.append((f"SFX_Jump_{k + 1:02d}", norm_lufs(fade(y, 0.002, 0.08), -26), "起跳"))
    for k in range(4):
        a = walk_s[(k * 4 + 1) % len(walk_s)]
        b = walk_s[(k * 4 + 6) % len(walk_s)]
        bod = resample_pitch(body[(k + 1) % len(body)], -2.0)
        fa = footstep(a, bod, db(-6), low=0.5, k=k)
        fb = footstep(b, body[(k + 3) % len(body)], db(-9), low=0.0, k=k + 5)
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
        step = hp(contact(walk_s[7], 7), 200) * 0.45 * np.max(np.abs(walk_s[7]))
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


def lever(order, lock_t=0.95, D=1.7, pivot_dur=0.9, lock_at_peak=False):
    """拉杆的一下：手握把手、轴上一声短的呻吟、铜链“一紧”、扳到底“咔”地卡住。order 0 = 拉下，1 = 推回。
    lock_at_peak：让“咔”的峰（而不是那一小段的开头）正好落在 lock_t。"""
    cs, ch_t, bolt_i = [(0.4, 1.4, 1), (1.1, 4.5, 4)][order]
    grip = clack(3 + order, 6, 0.15) * 0.25
    pivot = lp(creak(-4 + order, pivot_dur, cs, src="682776"), 3000) * dsp.env_ar(secs(pivot_dur), 0.15, 0.5)
    chain = chain_tense(0.7, -2 - order, ch_t)
    lock = bolt(bolt_i, -3, 0.45)
    if lock_at_peak:
        lock_t -= peak_at(lock, 0.45) / SR
    lv = lp(seg("696746", 0.0, 0.7, -4), 5000)
    y = mix((unit(grip), 0, 0.3), (unit(lv), 0.02, 0.35), (unit(pivot), 0.05, 0.16), (unit(chain), 0.35, 0.6), (unit(lock), lock_t, 0.9), length=secs(D))
    return fade(y, 0.003, 0.3)


def slab_slide(k, D=1.6, st=None, start=None, start_gain=0.5, end_gain=1.0, end_st=None, rum_gain=0.25, tail=0.8):
    """一块大石板在滑轨上滑过去（真实的墓门石头摩擦，降调），起步一顿、到位一声闷响。k 换素材段和音高。"""
    dsp.seed(160 + k)
    scrape = seg("352829", 1.0 + 2.3 * k if start is None else start, D, (-3 - k) if st is None else st)
    scrape = lp(hp(scrape, 50), 3500)
    scrape = shape(unit(scrape), [(0, 0), (0.06, 1), (0.25, 0.7), (D - 0.3, 0.85), (D, 0.15)])
    st0 = stone_thud(-1, 5, 0.3)
    end = stone_thud((-3 - k) if end_st is None else end_st, 6 - k, 0.8)
    rum = sub_rumble(D + 0.6, 80, 0.3, 161 + k)
    y = mix((scrape, 0, 0.8), (unit(st0), 0, start_gain), (unit(end), D - 0.03, end_gain), (unit(rum), 0, rum_gain), length=secs(D + tail))
    return fade(y, 0.003, 0.3)


@sound(16, "Lever_StoneSlab", "拉机关 A/B、石板滑动",
       "拉杆：手握铜把手、轴上一声短的呻吟、铜链“一紧”（LePainMaudit 的重铁链）、扳到底“咔”地卡住（Alexbuk 的门闩）。拉下和推回用不同的素材段和顺序。"
       "石板滑动：一块大石板贴着外墙在滑轨上滑开 1.6 秒（真实的墓门石头摩擦，降调），起步一顿、到位一声闷响；两个版本给两块石板。",
       "A、B 两个机关现在合成了同一个拉杆：拉下播 Lever_Pull，推回播 Lever_Push，放在拉杆上。"
       "Slab_Slide_01/02：两块石板各自开始滑的时候在石板上播（离得远，靠 UE 的衰减和混响就有“远处传来”的感觉）。", 2)
def b_lever():
    dsp.seed(16)
    files = [("SFX_Lever_Pull", norm_lufs(lever(0), -21), "拉杆"), ("SFX_Lever_Push", norm_lufs(lever(1), -21), "拉杆")]
    for k in range(2):
        files.append((f"SFX_Slab_Slide_{k + 1:02d}", norm_lufs(slab_slide(k), -19), "石板滑动"))
    return files


def iris_slides(D, opening=True, n=5, seed_=0, thuds=True):
    """光圈：几块石板一样的叶片先后滑开（和 16 的石板滑动同一套做法），声像绕着头顶走半圈。"""
    out = np.zeros((secs(D), 2))
    for j in range(n):
        t = (D - 2.2) * j / max(1, n - 1)
        L = 1.5 + 0.1 * (j % 3)
        last = j == n - 1
        y = slab_slide(j % 2, D=L, st=-4 - 0.5 * (j % 3) - (0 if opening else 0.5), start=0.6 + 1.1 * j,
                       start_gain=0.25 if thuds and j == 0 else 0.0,
                       end_gain=(0.9 if last else 0.3) if thuds else 0.0, end_st=(-3 if opening else -5) if last else -2,
                       rum_gain=0.18, tail=0.8 if last else 0.4)
        pan = 0.7 * np.cos(np.pi * j / max(1, n - 1) + (0 if opening else np.pi))
        out = mix((out, 0), (to_stereo(y * (0.75 + 0.25 * last), pan), t), length=secs(D))
    return out


@sound(17, "Iris_Blades", "光圈叶片旋开",
       "天花板上的光圈一片片旋开。第二版按试听反馈（第一版的金属叶片太像磨刀）整个换成 16 的石板滑动：几块石板一样的叶片先后滑开，"
       "每块都是真实的墓门石头摩擦（降调）、起步轻轻一顿，前面几片落定得轻，最后一片“咚”地到位；声像在头顶走半圈。合拢是反方向走、最后一声更沉。"
       "还有一条只有摩擦、没有落定的循环，给开合时间不固定的时候用。不再有任何金属摩擦和铜的和弦。",
       "Iris_Open / Iris_Close：开、合的完整版（约 4 s，最后一片在 3.4 s 左右落定）。光圈半径跟着玩家的位置慢慢变时（日4 走圆眼光柱），改用 Iris_Move_Loop，"
       "音量跟半径的变化速度走，停下时停循环（要的话补一个 16 的 Slab_Slide 的最后 0.8 秒当落定）。立体声，放在圆眼中心（头顶）。", 2)
def b_iris():
    files = []
    for name, opening in [("Open", True), ("Close", False)]:
        y = iris_slides(4.2, opening, 5, 1700 + opening)
        files.append((f"SFX_Iris_{name}", norm_lufs(fade(y, 0.01, 0.5), -21), "开合"))
    L = iris_slides(7.0, True, 6, 1790, thuds=False)
    L = shape(L, [(0, 1), (7.0, 1)])
    files.append(("SFX_Iris_Move_Loop", norm_lufs(loopify(L[secs(0.6):secs(6.8)], 1.5), -24, "integrated"), "滑动·循环", True))
    return files


@sound(18, "Bridge_Gate", "桥门开、关",
       "屋顶细桥尽头的桥门绕门柱转 1.4 秒。第二版按试听反馈（桥门以后不一定是青铜）改用 16 的拉杆声音：开门是“拉下”那一套、关门是“推回”那一套，"
       "轴上的呻吟拉长到门转的时间，扳到底“咔”地卡住那一下挪到门转完的时刻（1.37 s）。去掉了第一版里青铜门的共振和铁门的撞击。",
       "Gate_Open：人走近桥尾、门开始转时播；Gate_Close：接住最后一缕光、门开始转回去时播。卡住那一下都在 1.37 s。单声道，放在门轴上。", 2)
def b_gate():
    dsp.seed(18)
    return [("SFX_Gate_Open", norm_lufs(lever(0, lock_t=1.37, D=2.1, pivot_dur=1.35, lock_at_peak=True), -21), "开"),
            ("SFX_Gate_Close", norm_lufs(lever(1, lock_t=1.37, D=2.1, pivot_dur=1.35, lock_at_peak=True), -20), "关")]


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


def stone_block(k, st0=-5.0, dk=0.15, thud_t=0.38, lpf=1600, seed0=2400):
    """一块石头往下一沉（或被推出去）：短的摩擦，最后“咚”地落定。"""
    g = shape(heavy_grind(0.45, st=st0 - dk * k, seed_=seed0 + k, hi=2500), [(0, 0), (0.05, 1), (0.4, 0.6), (0.45, 0)])
    th = stone_thud(-3 - 0.2 * k if dk else -3, k, 0.6, lpf=lpf)
    return mix((g, 0, 0.45), (unit(th), thud_t, 0.9))


def stairs_cascade(D, times, pans, gains, seed0=2400, rumble=(70, 0.4, 2420, 3.8), st0=-5.0, dk=0.15):
    """一串石头先后落定（屋顶的楼梯、墙里的楼梯共用）。"""
    out = np.zeros((secs(D), 2))
    for k, (t, p, g) in enumerate(zip(times, pans, gains)):
        out = mix((out, 0), (to_stereo(stone_block(k, st0, dk, seed0=seed0) * g, p), t), length=secs(D))
    f, depth, seed_, hold = rumble
    rum = shape(sub_rumble(D, f, depth, seed_), [(0, 0), (0.4, 1), (hold, 1), (D, 0)])
    return mix((out, 0), (to_stereo(unit(rum) * 0.3), 0))


@sound(24, "Stairs_Lower", "楼梯降下",
       "接住最后一缕光、回到桥头以后，另外半圈踏步一级接一级降成楼梯：12 块石头先后往下一沉、各自“咚”地落定（vestibule-door 的石面重击和石头落地，降调），"
       "从桥头沿着弧线一路过去（声像从右到左），间隔先快后慢，底下是整段的隆隆声。"
       "按试听反馈，单级的版本去掉了，只用整段；另外用同一套做法给墙里的两段楼梯显现各做了一段：窗里堵着的石块从上往下一块块被推出去，"
       "接着下门的封石沉下去、最后落定，比屋顶那段短、闷一点（在墙里面）。",
       "Stairs_Lower：楼梯开始降的那一刻播一次，立体声，放在楼梯中段。WallStairs_Reveal_TS：月2 天鹅解开、TS 楼梯上门打开时播（3 扇窗）；"
       "WallStairs_Reveal_TR：月3 月亮浮雕隐去、TR 楼梯上门打开时播（2 扇窗）。都放在那段楼梯的中段。", 2)
def b_stairs():
    dsp.seed(24)
    N = 12
    times = [0.15 + 3.6 * (k / (N - 1)) ** 1.25 for k in range(N)]
    pans = [0.8 - 1.6 * k / (N - 1) for k in range(N)]
    gains = [0.9 - 0.03 * k for k in range(N)]
    y = stairs_cascade(5.0, times, pans, gains)
    files = [("SFX_Stairs_Lower", norm_lufs(fade(y, 0.01, 0.6), -18), "整段")]
    for name, windows, seed0 in [("TS", 3, 2460), ("TR", 2, 2480)]:
        # 窗里的石块：从上往下，0.25 s 一块；封石：从一开始就往下沉，约 2.2 s 落定
        t_w = [0.1 + 0.25 * k for k in range(windows)]
        pans_w = [0.5 - 0.5 * k for k in range(windows)]
        D = 3.4
        y = stairs_cascade(D, t_w, pans_w, [0.7] * windows, seed0=seed0, rumble=(60, 0.4, seed0 + 9, 2.4), st0=-4.0, dk=0.4)
        seal = shape(heavy_grind(2.2, st=-6, seed_=seed0 + 7, hi=2200), [(0, 0), (0.2, 0.8), (1.9, 1), (2.2, 0.4)])
        land = stone_thud(-4, windows + 2, 0.9, lpf=1400)
        y = mix((y, 0), (to_stereo(seal * 0.5, -0.2), 0.05), (to_stereo(unit(land) * 0.95, -0.2), 2.2), length=secs(D))
        y = eq(lp(y, 2400), "peak", 320, 2.0, 0.8)           # 在墙里面：闷一点、腔一点
        files.append((f"SFX_WallStairs_Reveal_{name}", norm_lufs(fade(y, 0.01, 0.5), -19.5), "墙里楼梯显现"))
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


@sound(27, "Apple_Place", "放上金苹果、取下金苹果",
       "放上（结局动作）：金苹果轻轻落进浑天仪的铜托：一声软的金属碰金属（HenKonen 的金属轻碰，低通抹软），铜托本身“嗡”一下（铜盘的真实振动比例）；"
       "接着苹果从金色变成月白、光一点点亮起来（0.5–3 秒）：颂钵 D4、水晶杯 A5 和 D6 慢慢长起来，最后停在一个很安静的 D 上。"
       "取下（第二版新加）：在屋顶的浑天仪上把发光的金苹果拿起来、接住最后一缕阳光。是“放上”的反面：同一下金属轻碰更轻、更低（金苹果离开铜托），"
       "铜托空了“嗡”一下，然后是暖的日光——水晶杯 D5、A5 很快亮起来再慢慢收住，几颗闪光；不到 3 秒，给以后的接光主题（7）留出位置。",
       "Apple_Place：放上苹果那一刻播，放在小亭的浑天仪上；结局音乐（13）最好在 3 秒以后进来。"
       "Apple_Take：在屋顶浑天仪前按 E“取下金苹果”（灰盒 catchLight）那一刻播，放在浑天仪上；接光主题（7）做好以后可以在 0.3 s 左右叠进来。", 2)
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
    files = [("SFX_Apple_Place", norm_lufs(fade(y, 0.002, 1.5), -21), "放上")]
    # 取下：金苹果离开屋顶浑天仪的铜托，接住最后一缕阳光
    dsp.seed(2702)
    D = 2.9
    lift = fade(lp(seg("682154", 0.08, 0.9, -8), 3000), 0.001, 0.4)
    empty = bronze_ring(hz("A4"), 1.8, 1.2, 0.35)
    w1 = glass_swell(hz("D5"), D - 0.2, attack=0.25, release=1.6, start=2.0)
    w2 = glass_swell(hz("A5"), D - 0.4, attack=0.4, release=1.5, start=3.0)
    sp = sparkle(D, 7, env=[0.3, 1, 0.6, 0.2, 0], pitch=6, level=0.06, seed_=2703)
    y = mix((to_stereo(unit(lift) * 0.4), 0), (to_stereo(unit(empty) * 0.2), 0.03), (widen(unit(w1) * 0.4, 0.6), 0.02),
            (widen(unit(w2) * 0.28, 0.7), 0.12), (sp, 0.1), length=secs(D))
    files.append(("SFX_Apple_Take", norm_lufs(fade(y, 0.002, 0.8), -22.5), "取下"))
    return files


def bronze_step(s, f0, seed_, metal=None, metal_gain=0.3):
    dsp.seed(seed_)
    s = cap(contact(s, seed_))
    ring = modal([f0 * r for r in BRONZE_PLATE[:6]], [0.18, 0.13, 0.1, 0.09, 0.07, 0.06], [0.7, 0.6, 0.45, 0.35, 0.25, 0.2], 0.5, detune=0.004)
    ring = lp(unit(ring), 5000)
    d = peak_at(s)
    parts = [(s, 0), (ring, d / SR, 0.18)]
    if metal is not None:
        parts.append((lp(hp(unit(metal), 200), 4000) * metal_gain, 0))   # 金属地面的身体：最低的那截拿掉，不发闷
    y = mix(*parts)
    y = eq(y, "peak", 2500, -2, 1.0)
    y = dsp.limit(unit(y), -4.0)
    return fade(trim_tail(y, -50, 0.06), 0.0015, 0.06)


@sound(28, "Footstep_Bronze", "脚步：青铜",
       "凉鞋踩在厚青铜板上（环道、细桥、半桥）：和石头脚步同一个“接触”，下面的“实”换成青铜——厚铜板的真实振动比例做的短共振（不是薄铁皮那种空响），"
       "叠一点真实的金属地面脚步（nate_asdfg、gristi 的录音，低通）。第二版跟着脚步改软，铜板的音往上挪、最低的一截拿掉（250 Hz 以下少 7 dB）。走 8 个、快走 6 个、落地 2 个。",
       "和石头脚步同一套触发，脚下是青铜（Physical Material = Bronze）时换这一组。", 2)
def b_foot_bronze():
    files = []
    walk_s, run_s = sandal_pool(), sandal_run_pool()
    mp = step_pool([("463811", 0, 3.6, 0.25), ("562195", 0, 3.1, 0.25), ("698697", 0, 10.3, 0.3)], hp_f=80, keep_db=10, post=0.3)
    dsp.seed(28)
    for k in range(8):
        f0 = dsp.RNG.uniform(230, 320)
        y = bronze_step(walk_s[(k * 3 + 1) % len(walk_s)], f0, 2800 + k, mp[k % len(mp)], 0.3)
        files.append((f"SFX_Footstep_Bronze_Walk_{k + 1:02d}", norm_lufs(y, -28), "走"))
    for k in range(6):
        f0 = dsp.RNG.uniform(250, 340)
        y = bronze_step(run_s[(k * 5 + 2) % len(run_s)], f0, 2850 + k, mp[(k + 3) % len(mp)], 0.3)
        files.append((f"SFX_Footstep_Bronze_Run_{k + 1:02d}", norm_lufs(y, -26), "快走"))
    for k in range(2):
        a = bronze_step(walk_s[(k * 7 + 3) % len(walk_s)], 220, 2880 + k, mp[(k + 1) % len(mp)], 0.4)
        b = bronze_step(walk_s[(k * 7 + 5) % len(walk_s)], 260, 2890 + k, None)
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



# ═════════════════════════ 第三、四梯队：共用零件 ═════════════════════════
def brass_strike(f, dur, lpf=9000):
    """小铜钵敲一下（FOSSarts），变到目标音高（按它的基音 780.5 Hz 算）。"""
    y = seg("762646", 0.0, dur + 0.5, semis(780.5, f))
    i = int(np.argmax(np.abs(y[: secs(0.6)])))
    y = y[max(0, i - secs(0.003)):][: secs(dur)]
    return fade(lp(hp(y, 150), lpf), 0.001, dur * 0.6)


def decayed(x, t60):
    """按 x 自己的长度乘一条指数衰减（有的素材变调以后比要的短一点）。"""
    return x * expdecay(len(x), t60)


def note(inst, n, dur=1.6, seed_=0):
    """一个音：glass 敲水晶杯、bowl 颂钵、stone 石磬、brass 小铜钵。"""
    f = hz(n) if isinstance(n, str) else n
    if inst == "glass":
        return glass_tone(f, dur, attack=0.003, t60=dur * 0.6, start=1.0 + (seed_ % 5))
    if inst == "bowl":
        return lp(bowl_strike(f, dur, soft=0.008), 5000)
    if inst == "stone":
        return lithophone(f, dur, seed_)
    return brass_strike(f, dur)


def phrase(D, notes, seed_=0):
    """一串音：[(时间, 乐器, 音名, 力度, 声像[, 长度])]，立体声。"""
    out = np.zeros((secs(D), 2))
    for k, n in enumerate(notes):
        t, inst, nm, v, pan = n[:5]
        dur = n[5] if len(n) > 5 else 1.6
        x = unit(note(inst, nm, dur, seed_ + k)) * v
        out = mix((out, 0), (to_stereo(x, pan), t), length=secs(D))
    return out


def bend(x, cents0, cents1):
    """音高从 cents0 滑到 cents1（变调连带变速，很短的音听不出来变速）。"""
    n = len(x)
    r = 2 ** (np.linspace(cents0, cents1, n) / 1200)
    idx = np.cumsum(r)
    idx = idx[idx < n - 1]
    return np.interp(idx, np.arange(n), x)


def ring_step(s, ring, seed_, ring_db=-14, hp_f=260):
    """一步 + 脚下材质的共振（月石、影桥）。"""
    c = hp(cap(contact(s, seed_), 0.15), hp_f)
    d = peak_at(c)
    y = mix((c, 0), (unit(ring), d / SR + 0.002, db(ring_db)))
    y = dsp.limit(unit(y), -4.0)
    return fade(trim_tail(y, -50, 0.08), 0.0015, 0.08)


def loop_bed(sid, start, dur, xfade=2.5, hp_f=40, lp_f=None):
    x = hp(load(sid, mono=False, start=start, dur=dur), hp_f)
    if lp_f:
        x = lp(x, lp_f)
    return loopify(x, xfade)


# ═════════════════════════ 第三梯队 ═════════════════════════

@sound(31, "Apple_Hold", "捧着金苹果",
       "整个夜里捧在手里的那点暖：摩擦颂钵的低音（F4）垫底，上面一只摩擦水晶杯（A5 或 C6，一阵换一只）——F、A、C 是一个大三和弦，比月光那一套暖。"
       "像海浪一样一阵一阵：每一阵慢慢涌上来（约 3.5 秒）、再慢慢退下去，退到很轻以后下一阵才来；四阵的间隔、大小都不一样，30 秒无缝循环，听久了也不吵。",
       "接住最后一缕光以后一直循环到放下苹果（Looping），2D 跟着玩家，音量很低；放上苹果时 2 秒淡出，接 27 的 Apple_Place。", 3)
def b_apple_hold():
    dsp.seed(31)
    L = 30.0

    def swell(n, rise, fall, curve=1.2):
        t = np.arange(n) / SR
        up = np.sin(np.pi / 2 * np.clip(t / rise, 0, 1)) ** 2
        down = np.cos(np.pi / 2 * np.clip((t - rise) / fall, 0, 1)) ** (2 * curve)
        return np.where(t < rise, up, down)

    # (开始, 涌上来, 退下去, 这一阵多大, 上面那只水晶杯, 颂钵从录音哪里取)
    waves = [(0.0, 3.6, 6.4, 1.0, "A5", 4), (7.6, 3.2, 5.8, 0.85, "C6", 14), (14.4, 3.8, 6.6, 1.1, "A5", 22), (22.2, 3.4, 6.2, 1.3, "C6", 30)]
    parts = []
    for k, (t0, rise, fall, g, gn, bst) in enumerate(waves):
        D = rise + fall
        e = swell(secs(D), rise, fall)
        lo = lp(unit(bowl_hum(hz("F4"), D, start=bst, attack=0.05, release=0.05)), 2500)
        hi = unit(glass_swell(hz(gn), D, attack=0.05, release=0.05, start=0.5 + k * 0.7, src="419146" if gn == "A5" else "418150"))
        parts.append((widen(lo * e * 0.55 * g, 0.4), t0))
        parts.append((widen(hi * e * (0.2 if gn == "A5" else 0.13) * g, 0.6), t0 + 0.4))
    y = mix(*parts, length=secs(L + 10))
    y = y[: secs(L)] + np.pad(y[secs(L):], ((0, secs(L) - (len(y) - secs(L))), (0, 0)))   # 过了 30 秒的尾巴绕回开头：首尾天然接上
    y = lp(y, 4500)
    return [("SFX_Apple_Hold_Loop", norm_lufs(y, -34.5, "integrated"), "捧着·循环", True)]


@sound(32, "Footstep_Moon_Shadow", "脚步：月石、月桥、影桥",
       "夜里的两种特殊路面。月石（月桥也是月石做的）：和石头脚步同一个“接触”，脚下激起一点颂钵的余振（模态合成的钵 + 真实的颂钵敲击，月光的低音区 A3–A4），"
       "比光路的水晶低、冷。影桥（水面上的月影）：同一个接触，脚下是一小下真实的水波拍岸（TheyLook_Here），上面一点很轻的高音颂钵。",
       "和石头脚步同一套触发：脚下是月石、月桥时用 Moonstone，影桥（Zone shadowbr）用ShadowBridge。Random 不重复。", 3)
def b_foot_moon():
    files = []
    walk_s, run_s = sandal_pool(), sandal_run_pool()
    notes = [hz(n) for n in MOON_NOTES]
    for k in range(8):
        dsp.seed(3200 + k)
        f = notes[(k * 2) % len(notes)]
        ring = mix((unit(modal([f * r for r in BOWL], [0.6, 0.25, 0.12, 0.07, 0.05], [1, 0.3, 0.12, 0.05, 0.02], 1.0)), 0, 0.5),
                   (unit(bowl_strike(f, 1.0, soft=0.004)), 0, 0.7))
        y = ring_step(walk_s[(k * 3 + 2) % len(walk_s)], lp(ring, 5000) * expdecay(len(ring), 0.55), 3200 + k, -14)
        files.append((f"SFX_Footstep_Moonstone_Walk_{k + 1:02d}", norm_lufs(y, -29), "月石·走"))
    for k in range(6):
        dsp.seed(3220 + k)
        f = notes[(k * 2 + 1) % len(notes)]
        ring = unit(bowl_strike(f, 0.8, soft=0.004))
        y = ring_step(run_s[(k * 3 + 1) % len(run_s)], lp(ring, 5000) * expdecay(len(ring), 0.4), 3220 + k, -15)
        files.append((f"SFX_Footstep_Moonstone_Run_{k + 1:02d}", norm_lufs(y, -27), "月石·快走"))
    laps = hp(load("866205"), 250)
    ev = [e for e in events(laps, min_dist=0.6, post=0.35, prom_db=14)]
    lapsl = [trim_tail(laps[secs(a):secs(b)], -40) for a, b, p in ev]
    for k in range(8):
        dsp.seed(3240 + k)
        w = lapsl[(k * 3) % len(lapsl)]
        hi = unit(bowl_strike(hz("A5") * 2 ** (dsp.RNG.choice([0, 3, 5]) / 12), 0.6, soft=0.004)) * 0.25
        ring = mix((unit(w), 0), (hi, 0.01))
        y = ring_step(walk_s[(k * 5 + 1) % len(walk_s)], ring, 3240 + k, -10, hp_f=300)
        files.append((f"SFX_Footstep_ShadowBridge_Walk_{k + 1:02d}", norm_lufs(y, -29), "影桥·走"))
    for k in range(6):
        dsp.seed(3260 + k)
        w = lapsl[(k * 5 + 2) % len(lapsl)]
        y = ring_step(run_s[(k * 5 + 3) % len(run_s)], unit(w), 3260 + k, -11, hp_f=300)
        files.append((f"SFX_Footstep_ShadowBridge_Run_{k + 1:02d}", norm_lufs(y, -27), "影桥·快走"))
    return files


@sound(33, "Shard_Pickup", "拾取碎片 ×3",
       "三片碎片各有自己的材料：日之碎片（正四面体，火）是小铜钵一声（和“确认”同一只）接着三只水晶杯很快往上走（D5、A5、D6），暖、亮；"
       "月之碎片（正二十面体，水）是两声颂钵（D4、A4）和几滴往下落的玻璃水珠；虹之碎片（正八面体，气）是七只水晶杯一口气从低到高（七种颜色），带一点被照亮的水雾。"
       "都在 3 秒以内，最后落在一个长一点的音上，给“获得感”。",
       "拿到碎片的那一刻播，2D（不空间化）。三片各用各的。", 3)
def b_shard_pickup():
    dsp.seed(33)
    files = []
    sun = phrase(3.0, [(0, "brass", "A5", 0.7, 0, 2.2), (0.12, "glass", "D5", 0.55, -0.3), (0.24, "glass", "A5", 0.55, 0.0), (0.36, "glass", "D6", 0.6, 0.3, 2.2)], 3300)
    sun = mix((sun, 0), (sparkle(3.0, 8, env=[0.2, 1, 0.5, 0], pitch=9, level=0.08, seed_=3301), 0.3))
    files.append(("SFX_Shard_Pickup_Sun", norm_lufs(fade(sun, 0.001, 0.8), -20), "日之碎片"))
    moon = phrase(3.0, [(0, "bowl", "D4", 0.7, -0.2, 2.6), (0.18, "bowl", "A4", 0.6, 0.2, 2.6)], 3310)
    drops = sparkle(3.0, 6, env=[0.3, 1, 0.6, 0.2], pitch=-4, level=0.12, seed_=3311)
    moon = mix((moon, 0), (lp(drops, 6000), 0.35), (widen(unit(bowl_hum(hz("D4"), 2.6, start=20, attack=0.3, release=1.6)) * 0.3), 0.1))
    files.append(("SFX_Shard_Pickup_Moon", norm_lufs(fade(moon, 0.001, 0.8), -20), "月之碎片"))
    seven = ["D5", "F5", "G5", "A5", "C6", "D6", "F6"]
    rb = phrase(3.2, [(0.07 * k, "glass", n, 0.5 + 0.03 * k, -0.8 + 1.6 * k / 6, 2.4 if k == 6 else 1.4) for k, n in enumerate(seven)], 3320)
    rb = mix((rb, 0), (shape(mist(3.2) * 0.07, [(0, 0), (0.4, 1), (3.2, 0)]), 0), (sparkle(3.2, 10, env=[0.5, 1, 0.4, 0], pitch=8, level=0.08, seed_=3321), 0.2))
    files.append(("SFX_Shard_Pickup_Rainbow", norm_lufs(fade(rb, 0.001, 0.8), -20), "虹之碎片"))
    return files


# 关卡标题：白天往上走（台阶、水晶），夜里往下走（颂钵），结尾的音一关比一关高（白天）/低（夜里）
TITLE_PHRASES = [
    ("Prologue", "序 · 登殿", [(0, "glass", "D5", 0.6, -0.2, 2.6), (0.45, "glass", "A5", 0.55, 0.2, 2.8)]),
    ("Day1", "日1", [(0, "stone", "D4", 0.6, -0.3), (0.3, "stone", "F4", 0.5, 0), (0.6, "glass", "A5", 0.55, 0.3, 2.4)]),
    ("Day2", "日2", [(0, "stone", "F4", 0.6, -0.3), (0.3, "stone", "G4", 0.5, 0), (0.6, "glass", "C6", 0.55, 0.3, 2.4)]),
    ("Day3", "日3", [(0, "stone", "G4", 0.6, -0.3), (0.25, "stone", "A4", 0.5, -0.1), (0.5, "stone", "C5", 0.5, 0.1), (0.8, "glass", "D6", 0.55, 0.3, 2.4)]),
    ("Day4", "日4", [(0, "stone", "A4", 0.6, -0.3), (0.25, "stone", "C5", 0.5, -0.1), (0.5, "stone", "D5", 0.5, 0.1), (0.8, "glass", "F6", 0.5, 0.3, 2.4)]),
    ("Day5", "日5", [(0, "stone", "C5", 0.6, -0.3), (0.22, "stone", "D5", 0.5, -0.1), (0.44, "stone", "F5", 0.5, 0.1), (0.7, "brass", "A5", 0.5, 0, 2.6), (0.72, "glass", "D6", 0.5, 0.3, 2.6)]),
    ("Dusk", "日落之后 · 入夜", [(0, "glass", "D6", 0.55, 0.3, 1.8), (0.35, "glass", "A5", 0.5, 0.1, 1.8), (0.75, "bowl", "D4", 0.7, -0.2, 3.2)]),
    ("Night1", "月1", [(0, "bowl", "A4", 0.6, 0.3, 2.2), (0.4, "bowl", "D4", 0.6, -0.2, 2.8)]),
    ("Night2", "月2", [(0, "bowl", "A4", 0.6, 0.3, 2.0), (0.35, "bowl", "G4", 0.5, 0, 2.0), (0.7, "bowl", "C4", 0.6, -0.2, 2.8)]),
    ("Night3", "月3", [(0, "bowl", "G4", 0.6, 0.3, 2.0), (0.35, "bowl", "F4", 0.5, 0, 2.0), (0.7, "bowl", "A3", 0.6, -0.2, 2.8)]),
    ("Night4", "月4", [(0, "bowl", "F4", 0.6, 0.3, 2.0), (0.3, "bowl", "D4", 0.5, 0.1, 2.0), (0.6, "bowl", "C4", 0.5, -0.1, 2.0), (0.9, "bowl", "G3", 0.6, -0.2, 2.8)]),
    ("Night5", "月5", [(0, "bowl", "D4", 0.6, 0.3, 2.0), (0.3, "bowl", "C4", 0.5, 0.1, 2.0), (0.6, "bowl", "A3", 0.5, -0.1, 2.0), (0.95, "bowl", "D3", 0.7, -0.2, 3.4), (1.0, "glass", "A5", 0.25, 0.2, 2.6)]),
]


@sound(35, "Level_Title", "关卡标题短乐句",
       "每关标题出现时的一句短乐句（2–4 秒），用游戏里已有的“乐器”：白天是石磬（屋顶台阶那种调过音的石头）一级级往上、最后落在一只水晶杯上；"
       "夜里是颂钵一声声往下。白天一关比一关结束得高（日1 落在 A5，日5 落在铜钵和 D6），夜里一关比一关结束得低（月1 落在 D4，月5 落到 D3）——跟着太阳往上爬、跟着月亮往下走。"
       "序是两只水晶杯的空五度；“日落之后 · 入夜”是水晶往下交给颂钵。全部在 d 小调五声里。",
       "关卡标题出现时播（灰盒 showTitle），2D。文件名对应：Prologue=序，Day1–5=日1–日5，Dusk=日落之后·入夜，Night1–5=月1–月5。", 3)
def b_titles():
    files = []
    for k, (key, zh, notes) in enumerate(TITLE_PHRASES):
        D = max(t for t, *_ in notes) + 3.4
        y = phrase(D, notes, 3500 + 10 * k)
        files.append((f"SFX_Title_{key}", norm_lufs(fade(y, 0.001, 1.0), -22), "标题"))
    return files


@sound(36, "UI_Prompt", "互动提示出现、提示文字出现",
       "提示出现：一颗很小的玻璃闪光（真实的玻璃轻碰）加一点很短的高音水晶，很轻；提示文字出现：一口很轻的“气”（被照亮的水雾那一段）托着一只很远的水晶杯，像一行字从光里浮出来。"
       "两样都轻到不打扰，但不看屏幕也能听见“有东西可以按了”。",
       "Prompt_Appear：互动提示（按 E）从无到有的那一刻；Text_Appear：提示文字（toast）出现时。2D，各两个 Random。同一秒里只播一个。", 3)
def b_ui_prompt():
    dsp.seed(36)
    files = []
    pool = tinkles()
    for k in range(2):
        g = resample_pitch(pool[(k * 7 + 3) % len(pool)], 5 + 2 * k)
        t = decayed(note("glass", ["D6", "A5"][k], 0.5, 3600 + k), 0.3)
        y = mix((to_stereo(lp(unit(g), 9000) * 0.5), 0), (to_stereo(unit(t) * 0.35), 0.005))
        files.append((f"SFX_UI_Prompt_Appear_{k + 1:02d}", norm_lufs(fade(y, 0.001, 0.15), -31), "提示出现"))
    for k in range(2):
        air = shape(mist(0.6) * 1.0, [(0, 0), (0.12, 1), (0.6, 0)])
        t = glass_swell(hz(["A5", "F5"][k]), 0.7, attack=0.08, release=0.5, start=2 + k)
        y = mix((air, 0, 0.6), (widen(unit(t) * 0.35, 0.6), 0.03))
        files.append((f"SFX_UI_Text_Appear_{k + 1:02d}", norm_lufs(fade(y, 0.005, 0.25), -33), "文字出现"))
    return files


@sound(37, "UI_Dialogue_Advance", "对话推进音",
       "翻到下一句：一把小锤在石头上轻轻一点（Shamewap 的录音，比“悬停”低、更圆），后面跟一点很短的颂钵余音。三个版本轮着用，听很多次也不烦。",
       "对话框翻页/下一句时播，2D，Random 不重复。", 3)
def b_dialogue_advance():
    dsp.seed(37)
    x = hp(load("389692"), 200)
    ev = sorted(events(x, min_dist=0.12, post=0.15, prom_db=12), key=lambda e: -e[2])
    files = []
    for k in range(3):
        a, b, p = ev[1 + 3 * k]
        y = x[secs(a):secs(b)]
        i = int(np.argmax(np.abs(y)))
        y = lp(resample_pitch(y[max(0, i - secs(0.002)):][: secs(0.1)], -4), 6000)
        r = decayed(bowl_strike(hz(["A4", "D5", "G4"][k]), 0.5, soft=0.003), 0.25)
        y = mix((unit(y), 0, 0.7), (unit(lp(r, 4000)), 0.004, 0.18))
        files.append((f"SFX_UI_Dialogue_Next_{k + 1:02d}", norm_lufs(to_stereo(fade(y, 0.001, 0.12)), -30), "下一句"))
    return files


@sound(38, "Roof_Wind", "海风",
       "屋顶的高度感：真实的海边悬崖小路上的强风（bruno.auzet），有一阵一阵的起伏，去掉最低的隆隆声，22 秒无缝循环。",
       "屋顶（和四层外沿）循环播放，2D 或很大的衰减半径；越高越响，进殿以后用 Audio Volume 压低 10–15 dB、低通到 600 Hz。和 11 的远处海浪叠着用。", 3)
def b_roof_wind():
    y = loop_bed("706471", 60, 22, 3.0, hp_f=70, lp_f=9000)
    return [("SFX_Roof_Wind_Loop", norm_lufs(y, -25, "integrated"), "海风·循环", True)]


@sound(39, "Interior_RoomTone", "殿内空间底噪",
       "殿里“安静”的声音：不是真的没声音，而是一座大石头圆殿里的空气——很轻的粉噪声经过圆殿的脉冲响应（和 ir/ 里给 UE 的是同一个），"
       "墙外的海隔着石墙只剩最低的一层（bruno.auzet 的崖上听海，低通到 350 Hz），殿里的瀑布在远处只剩闷闷的一点（低通到 250 Hz）。20 秒无缝循环，很轻。",
       "殿内的 Audio Volume 里一直循环（2D）；出殿 2 秒淡出、换成 11 的海浪。瀑布没开的时候（日1 开闸前）也可以用，瀑布那一层很低。", 3)
def b_room_tone():
    dsp.seed(39)
    D = 22
    ir = make_ir()
    pn = np.stack([noise(D, "pink"), noise(D, "pink")], axis=1) * 0.02
    air = np.stack([signal_fftconvolve(pn[:, c], ir[:, c])[: secs(D)] for c in range(2)], axis=1)
    air = lp(hp(air, 60), 3000)
    sea = lp(hp(load("525029", mono=False, start=90, dur=D), 30), 350)
    fall = lp(hp(load("559203", mono=False, start=100, dur=D), 30), 250)
    y = mix((unit(air) * 0.5, 0), (unit(sea) * 0.7, 0), (unit(fall) * 0.35, 0))
    return [("SFX_Interior_RoomTone_Loop", norm_lufs(loopify(y, 3.0), -38, "integrated"), "殿内·循环", True)]


def signal_fftconvolve(a, b):
    from scipy.signal import fftconvolve
    return fftconvolve(a, b)


@sound(40, "Pool_Water", "水池水面",
       "水庭的黑石镜池：真实的轻轻拍着岩岸的水（TheyLook_Here），一下一下、很稀，20 秒无缝循环。"
       "原录音里有几下水泡的“咕噜”带着音高、会滑音，听起来像猫叫、像人说话——把这些有音高的细线从频谱里压掉了，水声本身不动。",
       "放在水池边几处（或池心，衰减半径约 3–15 m），Looping。夜里潮水涨起来时可以把音量提高 3 dB。", 3)
def b_pool():
    y = loopify(dsp.detone(hp(load("866205", mono=False, start=0, dur=22), 70)), 2.0)
    return [("SFX_Pool_Water_Loop", norm_lufs(y, -28, "integrated"), "水面·循环", True)]


@sound(41, "Swan_Transform", "女神像变天鹅",
       "月光照满女神像，她变成天鹅：月光的颂钵长音（D4）和水晶杯（A5）慢慢亮起来，中间一对大翅膀展开、扇了几下（Lsoundaccount 的真实扇翅声），羽毛落定。"
       "另有反过来的一条：月光离开，天鹅收起翅膀、变回女神像。",
       "Swan_Transform：天鹅形态从 0 往 1 走时播（SWAN.form），放在女神像上；Swan_Revert：从 1 往 0 走时播。", 3)
def b_swan_transform():
    dsp.seed(41)
    files = []
    D = 3.8
    hum = bowl_hum(hz("D4"), D, start=40, attack=0.8, release=1.6)
    gl = glass_swell(hz("A5"), D - 0.4, attack=1.0, release=1.4)
    flaps = lp(hp(seg("753219", 3.0, 2.4), 120), 7000)
    flaps = shape(unit(flaps), [(0, 0), (0.2, 0.6), (1.0, 1), (2.0, 0.6), (2.4, 0)])
    cl = cloth_pool()
    rustle = lp(unit(cl[2]), 6000) * 0.3
    y = mix((widen(unit(hum) * 0.45), 0), (widen(unit(gl) * 0.3, 0.6), 0.2), (to_stereo(flaps * 0.7), 0.7), (to_stereo(rustle), 3.0), length=secs(D + 0.4))
    files.append(("SFX_Swan_Transform", norm_lufs(fade(y, 0.01, 0.8), -21), "变天鹅"))
    D = 2.8
    hum = moon_vanish(hz("A4"), D, 4101, dust=0.4)
    fold = lp(hp(seg("753219", 8.0, 1.2), 120), 6000)
    fold = shape(unit(fold), [(0, 0), (0.1, 0.8), (0.8, 0.5), (1.2, 0)])
    y = mix((to_stereo(unit(hum) * 0.5), 0), (to_stereo(fold * 0.6), 0.1), (to_stereo(lp(unit(cl[5]), 6000) * 0.25), 1.2), length=secs(D))
    files.append(("SFX_Swan_Revert", norm_lufs(fade(y, 0.01, 0.6), -23), "变回女神像"))
    return files


def vary_rate(x, r0, r1):
    """播放速度从 r0 慢慢变到 r1（像轮子越转越快：音高和速度一起升）。"""
    n = len(x)
    r = np.linspace(r0, r1, n)
    idx = np.cumsum(r)
    idx = idx[idx < n - 1]
    return np.interp(idx, np.arange(n), x)


@sound(42, "Armillary_Spin", "浑天仪开始自转",
       "结局里浑天仪自己转起来——“时间交出去了”：只有平滑的转动声（真实的木轮转动降调），从很慢、很轻开始，速度和音高一路往上滑，转顺了以后接一条持续转动的循环。"
       "没有颂钵、水晶杯，也没有一格一格的轴承声和金属刮擦。",
       "Armillary_Start：浑天仪开始自转时播（放在小亭的浑天仪上，约 6.5 s）；它的最后 1 秒和 Armillary_Spin_Loop 交叉接上（Loop Fade In 1 s），一直转到结局画面。", 3)
def b_armillary():
    dsp.seed(42)
    files = []
    D = 6.5
    whirr = vary_rate(lp(hp(seg("715478", 20, D + 0.3, -6), 50), 1400), 0.45, 1.0)[: secs(D)]
    whirr = shape(unit(whirr), [(0, 0), (1.5, 0.3), (4.5, 0.8), (D, 1)])
    files.append(("SFX_Armillary_Start", norm_lufs(fade(widen(whirr, 0.3), 0.01, 1.0), -24), "开始自转"))
    L = 16.0
    w = lp(hp(seg("715478", 44, L, -6), 50), 1400)
    files.append(("SFX_Armillary_Spin_Loop", norm_lufs(loopify(widen(w, 0.3)[secs(0.5):], 2.0), -27, "integrated"), "持续转动·循环", True))
    return files


@sound(43, "Day_Birds", "白天鸟鸣",
       "海中央的白天：没有成片的鸟叫，只是隔一阵远处有一只海鸥叫几声（Ambientsoundapp），偶尔一只燕子掠过（SamuelGremaud）。"
       "32 秒里只有四声，中间是空的（下面垫着 11 的海浪），低频去掉（和海浪不打架）。",
       "开场的岛上和殿外的白天循环（2D 或大衰减半径），和 11 的海浪叠着用；日5 太阳落下去时 5–10 秒淡出。", 3)
def b_birds():
    dsp.seed(43)
    L = 32.0
    gull = hp(load("537854", mono=False), 500)
    sw = hp(load("543683"), 800)

    def call(x, a, b, fin=0.25, fout=0.4):
        return fade(x[secs(a):secs(b)], fin, fout)
    # (第几秒, 哪一声, 多大)：海鸥是原录音里的远处叫声（立体声原样），燕子放在右边一点
    calls = [(1.5, call(gull, 1.0, 2.4), 0.5), (9.0, to_stereo(call(sw, 1.05, 1.75, 0.005, 0.15), 0.5), 0.3),
             (15.5, call(gull, 11.0, 12.6), 0.42), (24.0, call(gull, 19.0, 20.6), 0.36)]
    y = mix(*[(unit(x) * g, t) for t, x, g in calls], length=secs(L))
    return [("SFX_Day_Birds_Loop", norm_lufs(y, -33, "integrated"), "鸟鸣·循环", True)]


@sound(44, "Footstep_Water_Wet", "脚步：浅水、湿石",
       "浅水：真实的踩水脚步（aglinder、ChristopherJngs 的录音），一步一步切出来，只留一次水花。湿石：和石头脚步同一个“接触”，下面叠一层真实的赤脚踩湿瓷砖（SpliceSound）的“湿”声，石头的“实”换成更软的一点。",
       "和石头脚步同一套触发：脚下是浅水（潮沟、水庭边的浅水）用 Water，湿的石面（瀑布、水闸石台附近）用 WetStone。Random 不重复。", 3)
def b_foot_water():
    files = []
    dsp.seed(44)
    wp = step_pool([("265582", 0, 52.8, 0.35)], hp_f=100, keep_db=10, post=0.5, max_crest=32)
    wr = step_pool([("861369", 0, 8.9, 0.3)], hp_f=100, keep_db=10, post=0.45, max_crest=32)
    def splash(x, after):
        x = x[max(0, onset_at(x, 0.15) - secs(0.005)):]                 # 从脚碰到水的那一下开始（和脚落地对齐）
        x = eq(eq(cap(x, after, 0.1), "peak", 3500, -4.0, 0.8), "highshelf", 7000, -3.0)   # 和石头脚步一样收一点刺耳的高频
        return fade(trim_tail(dsp.limit(unit(x), -4.0)), 0.0015, 0.1)
    for k in range(8):
        files.append((f"SFX_Footstep_Water_Walk_{k + 1:02d}", norm_lufs(splash(wp[(k * 3 + 1) % len(wp)], 0.35), -26), "浅水·走"))
    for k in range(4):
        files.append((f"SFX_Footstep_Water_Run_{k + 1:02d}", norm_lufs(splash(wr[(k * 2 + 1) % len(wr)], 0.3), -24), "浅水·快走"))
    walk_s, body = sandal_pool(), stone_body_pool()
    wet = step_pool([("338106", 0, 18.7, 0.3)], hp_f=120, keep_db=10, post=0.3)
    for k in range(8):
        c = footstep(walk_s[(k * 3 + 4) % len(walk_s)], body[k % len(body)], db(-14), low=-2.0, k=k)
        w = cap(unit(wet[(k * 2) % len(wet)]), 0.2)
        y = align_add(c, match_level(lp(hp(w, 250), 9000), c, -4.0), 1.0, off=0.006)
        y = eq(y, "lowshelf", 200, -3.0)                                  # 湿石不比干石头更沉
        y = fade(trim_tail(dsp.limit(unit(y), -4.0)), 0.0015, 0.05)
        files.append((f"SFX_Footstep_WetStone_Walk_{k + 1:02d}", norm_lufs(y, -28), "湿石·走"))
    return files


@sound(45, "Waterfall_Hole", "瀑布水帘透开",
       "镜子反射的月光打到瀑布上，那一块水帘透开：瀑布那一块的轰鸣变薄（低频一路被抽掉，只剩细的水声），上面是月光的颂钵（A4）和水晶（D6）轻轻亮起来、几颗水珠的闪光。"
       "另有合上的一条（月光离开，那一块又变回厚水帘）。",
       "Hole_Open：瀑布上透开那一块从 0 往 1 走时（FALLHOLE.k），放在透开处；Hole_Close：从 1 往 0 走时。瀑布的循环照常播，这两条叠在上面。", 3)
def b_waterfall_hole():
    dsp.seed(45)
    files = []
    D = 2.8
    w = hp(load("559203", mono=False, start=120, dur=D), 40)
    thin = np.stack([sweep_filter(w[:, c], 150, 2500, kind="highpass") for c in range(2)], axis=1)
    thin = shape(thin, [(0, 0), (0.3, 0.8), (1.6, 0.6), (D, 0)])
    hum = bowl_hum(hz("A4"), D, start=50, attack=0.5, release=1.2)
    g = glass_swell(hz("D6"), D - 0.3, attack=0.6, release=1.2)
    sp = sparkle(D, 8, env=[0.3, 1, 0.6, 0.1], pitch=-2, level=0.09, seed_=4501)
    y = mix((thin * 0.35, 0), (widen(unit(hum) * 0.4), 0.05), (widen(unit(g) * 0.22, 0.6), 0.2), (sp, 0.1), length=secs(D))
    files.append(("SFX_Waterfall_Hole_Open", norm_lufs(fade(y, 0.02, 0.6), -24), "透开"))
    D = 1.8
    w = hp(load("559203", mono=False, start=140, dur=D), 40)
    thick = np.stack([sweep_filter(w[:, c], 2500, 150, kind="highpass") for c in range(2)], axis=1)
    thick = shape(thick, [(0, 0), (0.2, 0.6), (1.4, 0.5), (D, 0)])
    hum = moon_vanish(hz("A4"), D, 4502, dust=0.2)
    y = mix((thick * 0.35, 0), (to_stereo(unit(hum) * 0.35), 0), length=secs(D))
    files.append(("SFX_Waterfall_Hole_Close", norm_lufs(fade(y, 0.02, 0.5), -26), "合上"))
    return files


# ═════════════════════════ 第四梯队 ═════════════════════════
SEVEN = ["D5", "F5", "G5", "A5", "C6", "D6", "F6"]          # 红橙黄绿蓝靛紫：颜色的频率越高，音越高


@sound(46, "Rainbow_Bridge_IrisRelief", "彩虹桥出现、伊莉丝浮雕醒来",
       "伊莉丝浮雕醒来：浮雕上沿的铜唇里流下一层细水帘（真实的小水流，kyles），刻在浮雕上的那圈虹亮起来——三只水晶杯（D5、A5、D6）慢慢长起来。"
       "彩虹桥出现：七只水晶杯从低到高（红到紫），声像从浮雕这边一路拱到对面窗台（左到右），下面是被照亮的水雾和闪光，最后七色一起停在一个长音上。",
       "IrisRelief_Awaken：影子的头落进人形、虹醒过来时，放在浮雕上；RainbowBridge_Appear：虹桥开始从浮雕上走下来时播，立体声，放在虹桥中点。", 4)
def b_rainbow_bridge():
    dsp.seed(46)
    files = []
    D = 3.2
    trickle = shape(lp(hp(load("454340", start=10, dur=D), 300), 7000), [(0, 0), (0.6, 1), (2.4, 0.8), (D, 0)])
    ch = mix((glass_swell(hz("D5"), D, attack=0.8, release=1.2), 0, 0.6), (glass_swell(hz("A5"), D - 0.2, attack=1.0, release=1.2), 0.15, 0.45),
             (glass_swell(hz("D6"), D - 0.5, attack=1.0, release=1.0), 0.4, 0.3), length=secs(D))
    y = mix((to_stereo(unit(trickle) * 0.3), 0), (widen(unit(ch) * 0.6, 0.6), 0))
    files.append(("SFX_IrisRelief_Awaken", norm_lufs(fade(y, 0.02, 0.6), -23), "浮雕醒来"))
    D = 4.2
    arc = phrase(D, [(0.15 + 0.3 * k, "glass", n, 0.45, -0.85 + 1.7 * k / 6, 2.6) for k, n in enumerate(SEVEN)], 4600)
    held = mix(*[(glass_swell(hz(n), 1.8, attack=0.3, release=1.2, start=1.0 + k % 4), 2.3, 0.12) for k, n in enumerate(SEVEN[::2])], length=secs(D))
    y = mix((arc, 0), (widen(unit(held) * 0.35, 0.7), 0), (shape(mist(D) * 0.08, [(0, 0), (1.0, 1), (D, 0)]), 0),
            (sparkle(D, 14, env=[0.2, 0.6, 1, 0.5, 0], pitch=9, level=0.08, seed_=4601), 0))
    files.append(("SFX_RainbowBridge_Appear", norm_lufs(fade(y, 0.01, 0.8), -21), "彩虹桥出现"))
    return files


@sound(47, "Prism_Turn", "棱镜转台转一格（7 个音高）",
       "转棱镜的铜轮转一格：轮子“咔”一声（真实的石头碰撞 + 金属轻碰，很小），接着一只水晶杯响一下——七格七个音，从红（D5）到紫（F6），颜色的频率越高音越高。"
       "第六格是靛色（D6），也就是落进塞勒涅眼睛的那一色。",
       "转到第几格播第几个（_1_Red … _7_Violet）。棱镜在窗下石沿上，单声道放在棱镜上。", 4)
def b_prism():
    dsp.seed(47)
    names = ["Red", "Orange", "Yellow", "Green", "Blue", "Indigo", "Violet"]
    files = []
    for k, (n, nm) in enumerate(zip(SEVEN, names)):
        click = mix((unit(clack(k, 8, 0.12)) * 0.4, 0), (unit(fade(lp(seg("682154", 0.08, 0.15, 3), 6000), 0.001, 0.08)) * 0.3, 0.003))
        t = note("glass", n, 1.4, 4700 + k)
        y = mix((lp(click, 7000), 0), (unit(t) * 0.6, 0.03))
        files.append((f"SFX_Prism_Turn_{k + 1}_{nm}", norm_lufs(fade(y, 0.001, 0.4), -24), "转一格"))
    return files


@sound(48, "Selene_Eyes", "塞勒涅眼睛点亮",
       "靛色的光落进塞勒涅浮雕的青金石眼睛：先是一声很亮的水晶“叮”（D6，像宝石里点着了光），接着月亮的颂钵（D4）低低地应一声，摩擦颂钵 A4 慢慢亮起来，几颗闪光。",
       "眼睛亮起来那一刻播，放在浮雕的眼睛上；对话在这条播到 2 秒左右以后再开始。", 4)
def b_selene_eyes():
    dsp.seed(48)
    D = 3.8
    ping = note("glass", "D6", 2.2, 4800)
    low = bowl_strike(hz("D4"), 3.2, soft=0.02)
    hum = bowl_hum(hz("A4"), D - 0.3, start=55, attack=0.9, release=1.5)
    y = mix((to_stereo(unit(ping) * 0.55, 0.1), 0), (to_stereo(unit(low) * 0.5, -0.1), 0.15), (widen(unit(hum) * 0.3), 0.3),
            (sparkle(D, 8, env=[1, 0.6, 0.3, 0], pitch=10, level=0.06, seed_=4801), 0), length=secs(D))
    return [("SFX_Selene_Eyes_Light", norm_lufs(fade(y, 0.001, 0.8), -21), "眼睛点亮")]


@sound(49, "Rainbow_Small_Mechs", "窗下石沿伸出、虹之龛铜门、棱镜铜柱升起",
       "彩虹支线的三个小机关：窗下石沿伸出（16 的石板滑动，更短、更轻：0.9 m 的石沿从墙里滑出来）；虹之龛的两扇小铜门（两声小的门轴吱呀，一前一后，最后轻轻一靠）；"
       "托着棱镜的铜柱从石沿里升起来（轻的石头摩擦，升到顶一声小的铜响）。",
       "Sill_Ledge_Extend：虹桥快落到对岸、石沿开始伸出时；Niche_Doors_Open：打开虹之龛；Prism_Column_Rise：铜柱开始升起时。都放在机关上，单声道。", 4)
def b_rainbow_mechs():
    dsp.seed(49)
    files = []
    y = slab_slide(1, D=1.0, st=-1.5, start_gain=0.3, end_gain=0.6, end_st=-1, rum_gain=0.1, tail=0.5)
    files.append(("SFX_Sill_Ledge_Extend", norm_lufs(y, -22), "石沿伸出"))
    c1 = lp(creak(2, 0.55, 0.8, src="682776"), 5000) * dsp.env_ar(secs(0.55), 0.05, 0.3)
    c2 = lp(creak(3, 0.5, 1.6, src="682776"), 5000) * dsp.env_ar(secs(0.5), 0.05, 0.3)
    stop = clack(4, -3, 0.25)
    y = mix((unit(c1) * 0.4, 0), (unit(c2) * 0.35, 0.14), (unit(stop) * 0.35, 0.62), length=secs(1.2))
    files.append(("SFX_Niche_Doors_Open", norm_lufs(fade(y, 0.003, 0.3), -24), "虹之龛铜门"))
    gr = shape(heavy_grind(1.0, st=-1, seed_=4901, hi=3000), [(0, 0), (0.1, 0.7), (0.85, 0.7), (1.0, 0)])
    ring = bronze_ring(hz("A4"), 1.2, 0.8, 0.3)
    y = mix((gr * 0.5, 0), (unit(clack(2, -2, 0.2)) * 0.4, 0.95), (unit(ring) * 0.2, 0.97), length=secs(2.0))
    files.append(("SFX_Prism_Column_Rise", norm_lufs(fade(y, 0.003, 0.4), -23), "铜柱升起"))
    return files


@sound(50, "Mirror_SunNiche", "三相像镜子醒来、日之龛开盖",
       "三相像醒来（日相）：石像在台座上轻轻一动（短的石头摩擦），铜镜迎着太阳亮起来——两只水晶杯（D5、A5）很快亮起来，铜镜本身轻轻一声共振。"
       "日之龛开盖：铜匣的盖子绕后沿翻开（一声短的门轴吱呀、盖子靠住的一下），里面的光一下透出来（水晶杯 A5），碎片升起时几颗闪光往上走。",
       "Mirror_Awaken：三相像变成日相时（灰盒 updateMirrors 里 form 变成 sun），放在像上；SunNiche_Open：打开日之龛时，放在铜匣上。", 4)
def b_mirror_niche():
    dsp.seed(50)
    files = []
    D = 2.8
    shift = shape(heavy_grind(0.6, st=-2, seed_=5001, hi=2500), [(0, 0), (0.1, 1), (0.6, 0)])
    g1 = glass_swell(hz("D5"), D, attack=0.35, release=1.4)
    g2 = glass_swell(hz("A5"), D - 0.2, attack=0.45, release=1.3)
    shine = bronze_ring(hz("D5"), 2.0, 1.4, 0.4)
    y = mix((to_stereo(shift * 0.3), 0), (widen(unit(g1) * 0.45, 0.6), 0.1), (widen(unit(g2) * 0.3, 0.6), 0.2), (to_stereo(unit(shine) * 0.12), 0.25), length=secs(D))
    files.append(("SFX_Mirror_Awaken", norm_lufs(fade(y, 0.01, 0.7), -22), "镜子醒来"))
    D = 2.9
    hinge = lp(creak(0, 0.8, 1.0, src="682776"), 4000) * dsp.env_ar(secs(0.8), 0.05, 0.4)
    thunk = clack(6, -6, 0.3)
    light = glass_swell(hz("A5"), D - 0.6, attack=0.3, release=1.3)
    sp = sparkle(D - 1.0, 9, env=[0.2, 1, 0.8, 0.2], pitch=4, level=0.08, seed_=5002)
    y = mix((to_stereo(unit(hinge) * 0.35), 0), (to_stereo(unit(thunk) * 0.4), 0.95), (widen(unit(light) * 0.4, 0.6), 0.6), (sp, 1.0), length=secs(D))
    files.append(("SFX_SunNiche_Open", norm_lufs(fade(y, 0.003, 0.7), -22), "日之龛开盖"))
    return files


@sound(52, "Dodecahedron_Stars", "正十二面体与星座亮起",
       "三片碎片合成正十二面体（柏拉图说它是宇宙的形状）：很深的一声颂钵（D3）托底，水晶杯 D5、A5、D6、F6 一层层长上去；"
       "星座一颗一颗亮起来——三十多颗玻璃闪光从中间往两边散开，越来越多。6.5 秒。",
       "正十二面体合成、星座开始亮时播，2D 或放在合成的位置（立体声）。", 4)
def b_dodecahedron():
    dsp.seed(52)
    D = 6.5
    deep = bowl_strike(hz("D3"), D, soft=0.03)
    layers = [(glass_swell(hz(n), D - t, attack=1.2, release=1.8, start=1.0 + k), t, 0.35 - 0.05 * k) for k, (n, t) in enumerate([("D5", 0.3), ("A5", 0.9), ("D6", 1.5), ("F6", 2.1)])]
    stars = np.zeros((secs(D), 2))
    pool = tinkles()
    for k in range(34):
        t = 1.2 + 4.6 * (k / 34) ** 0.8 + dsp.RNG.uniform(-0.1, 0.1)
        g = lp(resample_pitch(pool[dsp.RNG.integers(len(pool))], dsp.RNG.uniform(4, 12)), 11000)
        pan = np.clip(dsp.RNG.normal(0, 0.15 + 0.6 * k / 34), -1, 1)
        stars = mix((stars, 0), (to_stereo(unit(g) * dsp.RNG.uniform(0.15, 0.35), pan), t), length=secs(D))
    y = mix((to_stereo(unit(deep) * 0.6), 0), *[(widen(unit(x) * v, 0.6), t) for x, t, v in layers], (stars * 0.5, 0),
            (shape(mist(D) * 0.06, [(0, 0), (2.0, 1), (D, 0)]), 0), length=secs(D))
    return [("SFX_Dodecahedron_Stars", norm_lufs(fade(y, 0.002, 1.2), -19), "亮起")]


@sound(53, "RainbowGate_Rainbow", "虹门彩虹",
       "屋顶虹门里的那道小彩虹：背对夕阳穿过虹门时，三只水晶杯（F5、A5、C6）很轻地亮一下，带一点被照亮的水雾——比 46 的彩虹桥小得多，只是一个细节。",
       "穿过虹门、彩虹出现时播（每次经过最多播一次），放在虹门上，很轻。", 4)
def b_rainbow_gate():
    dsp.seed(53)
    D = 3.0
    ch = mix((glass_swell(hz("F5"), D, attack=0.5, release=1.3, start=1.5), 0, 0.5), (glass_swell(hz("A5"), D - 0.2, attack=0.6, release=1.2, start=2.5), 0.1, 0.4),
             (glass_swell(hz("C6"), D - 0.4, attack=0.7, release=1.1, start=3.5), 0.2, 0.3), length=secs(D))
    y = mix((widen(unit(ch) * 0.5, 0.6), 0), (shape(mist(D) * 0.06, [(0, 0), (0.6, 1), (D, 0)]), 0), (sparkle(D, 5, pitch=9, level=0.05, seed_=5301), 0.2))
    return [("SFX_RainbowGate_Rainbow", norm_lufs(fade(y, 0.02, 0.7), -27), "虹门彩虹")]


@sound(54, "WallStairs_Windows", "墙里楼梯的窗打开",
       "墙里楼梯朝外的小窗里堵着的石块，一块一块被推出去：每块是 24 里墙里楼梯显现用的同一种石块（短的摩擦 + 落定），一样闷一点（在墙里面）。三个版本。",
       "要逐扇同步的话（灰盒 TUNWIN：从上往下 0.25 s 一块），每块开始动时播一个，Random；已经用了 24 的 WallStairs_Reveal 就不用再播这个。", 4)
def b_wall_windows():
    files = []
    for k in range(3):
        y = stone_block(k, st0=-4.0, dk=0.4, seed0=5400)
        y = eq(lp(y, 2400), "peak", 320, 2.0, 0.8)
        files.append((f"SFX_WallStairs_Window_{k + 1:02d}", norm_lufs(fade(y, 0.003, 0.3), -22), "一扇窗"))
    return files


@sound(55, "Ambience_Layers", "氛围层：水雾",
       "水雾：瀑布录音里最高的那一段细嘶声（开闸以后中庭里的雾），很轻地起伏，无缝循环。",
       "Mist_Loop：开闸以后中庭里一直在（和雾的浓度一起淡入淡出）。", 4)
def b_ambience_layers():
    dsp.seed(55)
    m = mist(18)
    t = np.arange(len(m)) / SR
    m = m * (0.8 + 0.2 * np.sin(2 * np.pi * t / 7.0))[:, None]
    return [("SFX_Mist_Loop", norm_lufs(loopify(m, 2.0), -36, "integrated"), "水雾·循环", True)]


def voice_syllable(inst, f, dur, rise, seed_):
    """一个“音节”：一个乐器音截短、起音像说话（6 ms），音高在音节里滑一点（说话的抑扬）。"""
    dsp.seed(seed_)
    if inst == "glass":
        x = glass_tone(f, dur + 0.1, attack=0.006, t60=dur * 1.5, start=1.0 + seed_ % 5)
    elif inst == "bowl":
        x = lp(bowl_hum(f, dur + 0.1, start=10 + seed_ % 40, attack=0.02, release=dur * 0.5), 4000)
    else:
        x = lithophone(f, dur + 0.1, seed_)
    x = bend(unit(x), 0, rise)[: secs(dur)]
    x = x * dsp.env_ar(len(x), 0.006, dur * 0.45, curve=1.5)
    return fade(x, 0.002, 0.02)


@sound(56, "Selene_SleepTalk", "塞勒涅梦话",
       "塞勒涅在梦里说话：她的“声音”是一只摩擦颂钵（月神，低、慢、柔），很慢、很含糊——几个音节拖长、音高往下滑，中间停很久，最后一声很轻的叹气（一小口带通的气声）。两段。",
       "彩虹支线里靠近她的浮雕、她还没醒的时候，隔一会儿随机播一段（放在浮雕上，很轻）。", 4)
def b_sleep_talk():
    files = []
    for k in range(2):
        dsp.seed(5600 + k)
        parts, t = [], 0.1
        for j in range(dsp.RNG.integers(3, 6)):
            n = ["D4", "F4", "A3", "C4", "G3"][dsp.RNG.integers(5)]
            dur = dsp.RNG.uniform(0.25, 0.5)
            s = voice_syllable("bowl", hz(n), dur, dsp.RNG.uniform(-120, -40), 5610 + 10 * k + j)
            parts.append((to_stereo(s * dsp.RNG.uniform(0.5, 0.9), dsp.RNG.uniform(-0.2, 0.2)), t))
            t += dur + dsp.RNG.uniform(0.15, 0.6)
        sigh = shape(bp(noise(0.9, "pink"), 300, 1500) * 0.3, [(0, 0), (0.25, 1), (0.9, 0)])
        parts.append((to_stereo(sigh), t + 0.2))
        y = mix(*parts, length=secs(t + 1.3))
        files.append((f"SFX_Selene_SleepTalk_{k + 1:02d}", norm_lufs(fade(y, 0.01, 0.4), -28), "梦话"))
    return files


@sound(57, "UI_Shard_Hover", "界面：碰到已获得的日月虹碎片",
       "鼠标碰到界面里已经拿到的碎片时，那片碎片轻轻响一下，和 33 拾取时同一种材料，只是小得多：日是一只很短的水晶杯（D6），月是一声很短的颂钵（A5），虹是三只水晶杯一闪（D6、F6、A6）。",
       "2D，放到 UI 的 Sound Class；同一片碎片 0.3 秒内只播一次。", 4)
def b_ui_shard_hover():
    dsp.seed(57)
    files = []
    sun = decayed(note("glass", "D6", 0.45, 5700), 0.3)
    moon = decayed(lp(bowl_strike(hz("A5"), 0.5, soft=0.004), 6000), 0.3)
    rb = mix(*[(unit(decayed(note("glass", n, 0.4, 5710 + k), 0.22)) * 0.5, 0.035 * k) for k, n in enumerate(["D6", "F6", "A6"])])
    for name, x in [("Sun", sun), ("Moon", moon), ("Rainbow", rb)]:
        files.append((f"SFX_UI_Shard_Hover_{name}", norm_lufs(to_stereo(fade(unit(x), 0.001, 0.12)), -30), "悬停"))
    return files


# 每一条的排序理由（照排期表）和它属于白天、夜里还是全程（试听页按这个上色）
REASONS = {
    3: "全程都在响，频率最高", 4: "踩光是核心操作，要让玩家一听就知道“脚下是光”", 5: "每束光出现都靠它提示“这里能走了”，全程反复出现",
    6: "夜里的核心反馈，月2 到月5 一直在用", 8: "光阶等关卡的基本操作", 9: "让玩家放心“没有死亡”", 10: "日1 的核心机关，又是贯穿全程的环境声",
    11: "开场第一声，殿外一直在", 14: "第一个机关，教会玩家“动机关会改变光”", 15: "日5、月1 的主体，音高逐级变化本身就是反馈",
    16: "日2 主线", 17: "日4 的视觉奇观，需要声音撑住", 18: "日5 进门、入夜关门，两个节点", 19: "月2、月3 都要用，转很多次",
    20: "月5 唯一的“找位置”反馈，没有它很难找", 21: "月4 要推很长一段", 22: "月4 的解谜奖励", 23: "月2 的解谜奖励", 24: "月1 入夜后第一条路",
    25: "月5 的解谜奖励", 26: "通往结局的最后一段路", 27: "结局动作；取下是接光那一下", 28: "环道、细桥、半桥都会踩到", 29: "基础交互",
    30: "开场第一个“光”的声音，和第 5 条共用素材再加长",
    31: "整个夜里一直在，给冷色的夜一点温度", 32: "区分夜里的特殊路面", 33: "支线奖励，但很需要“获得感”", 35: "每关一次，节奏感",
    36: "不看屏幕也知道有东西能交互", 37: "不配音时的替代方案", 38: "屋顶的高度感", 39: "区分殿内外", 40: "水庭的氛围",
    41: "月2 的奇观", 42: "结局“时间交出去了”的声音表现", 43: "开场画面生动", 44: "局部材质", 45: "月5 的细节",
    46: "彩虹支线", 47: "彩虹支线", 48: "彩虹支线的奖励", 49: "彩虹支线的小机关", 50: "日3 支线",
    52: "集齐碎片的额外内容", 53: "日5 的小细节", 54: "月2 的小细节", 55: "氛围层", 56: "彩虹支线里的彩蛋", 57: "界面小音效",
}
WHEN = {3: "both", 4: "day", 5: "day", 6: "night", 8: "both", 9: "both", 10: "both", 11: "both", 14: "day", 15: "both", 16: "day",
        17: "day", 18: "day", 19: "both", 20: "night", 21: "night", 22: "night", 23: "night", 24: "night", 25: "night", 26: "night",
        27: "both", 28: "both", 29: "ui", 30: "day", 31: "night", 32: "night", 33: "both", 35: "both", 36: "ui", 37: "ui",
        38: "both", 39: "both", 40: "both", 41: "night", 42: "night", 43: "day", 44: "both", 45: "night", 46: "day", 47: "day",
        48: "day", 49: "day", 50: "day", 52: "both", 53: "day", 54: "night", 55: "both", 56: "day", 57: "ui"}
# 试听页上“连着播”的按钮：组名 → (按钮文字, 间隔秒, 是否随机顺序)
SEQUENCES = {"走": ("走一段", 0.5, True), "快走": ("快走一段", 0.33, True), "升起": ("顺序播放 16 级", 0.42, False),
             "落平": ("顺序播放 16 级", 0.42, False), "悬停": ("来回悬停", 0.18, True),
             "月石·走": ("走一段", 0.5, True), "月石·快走": ("快走一段", 0.33, True), "影桥·走": ("走一段", 0.5, True), "影桥·快走": ("快走一段", 0.33, True),
             "浅水·走": ("走一段", 0.55, True), "浅水·快走": ("快走一段", 0.36, True), "湿石·走": ("走一段", 0.5, True),
             "标题": ("按关卡顺序", 3.6, False), "转一格": ("转一圈", 0.6, False), "一扇窗": ("一扇接一扇", 0.25, False)}


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


README_HEAD = """# 音效 · 第一到第四梯队

日落回廊的音效：第一梯队里除了 1、2、7、12、13（时间和声、接光主题、主界面音乐、结局音乐，之后单独做）以外的全部，第二梯队全部（14–30），第三、四梯队除了 34（岛影逼近）、51（碎片放入凹槽：现在结局自动检测）和 58（对话配音）以外的全部。
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
- 第三梯队的 34（岛影逼近）。
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
        tier = {1: "第一梯队", 2: "第二梯队", 3: "第三梯队", 4: "第四梯队"}[it["tier"]]
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
