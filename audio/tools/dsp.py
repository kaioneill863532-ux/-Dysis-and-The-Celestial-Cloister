"""日落回廊音效的小工具箱：读素材、滤波、包络、模态合成（石、青铜、玻璃）、切脚步、做无缝循环、按响度归一、写 WAV。

全部用 numpy / scipy，单声道是一维数组，立体声是 (n, 2)。采样率固定 48 kHz。
"""
import os, json
import numpy as np
from scipy import signal
import soundfile as sf

SR = 48000
RNG = np.random.default_rng(20261006)
SRC_DIR = os.environ.get("DYSIS_SRC", os.path.join(os.path.dirname(__file__), "..", "_src"))


def seed(n):
    global RNG
    RNG = np.random.default_rng(n)


# ───────────────────────── 读、写 ─────────────────────────
_cache = {}


def load(sid, mono=True, start=0.0, dur=None):
    """读 Freesound 素材（已解码成 48k 浮点 WAV）。start/dur 秒。"""
    key = str(sid)
    if key not in _cache:
        x, sr = sf.read(os.path.join(SRC_DIR, f"{key}.wav"), dtype="float64", always_2d=True)
        assert sr == SR
        _cache[key] = x
    x = _cache[key]
    a = int(start * SR)
    b = len(x) if dur is None else min(len(x), a + int(dur * SR))
    x = x[a:b]
    if mono:
        return x.mean(axis=1).copy()
    return (x if x.shape[1] == 2 else np.repeat(x, 2, axis=1)).copy()


def limit(x, peak_db=-1.0, look=0.0015, release=0.06):
    """前瞻峰值限制：只削掉最前面那一两毫秒的尖，响度基本不动。"""
    lim = 10 ** (peak_db / 20)
    m = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    g = np.minimum(1.0, lim / (m + 1e-12))
    L = max(1, int(look * SR))
    # 前瞻：每一点取后面 L 个点里最小的增益，再往回平滑
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(g, size=2 * L + 1, origin=0)
    r = np.exp(-1 / (release * SR))
    out = np.empty_like(g)
    cur = 1.0
    for i, v in enumerate(g):
        cur = v if v < cur else r * cur + (1 - r) * v
        out[i] = cur
    out = np.convolve(out, np.ones(L) / L, mode="same")
    out = np.minimum(out, g * 1.0 + (1 - g) * 0)  # 不超过即时增益
    return x * (out if x.ndim == 1 else out[:, None])


def write(path, x, peak_db=-1.0, bits=16):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = np.asarray(x, dtype=np.float64)
    pk = np.max(np.abs(x)) + 1e-12
    lim = 10 ** (peak_db / 20)
    if pk > lim and pk < lim * 10 ** (8 / 20):
        x = limit(x, peak_db - 0.2)
        pk = np.max(np.abs(x)) + 1e-12
    if pk > lim:
        x = x * (lim / pk)
    sub = "PCM_16" if bits == 16 else "PCM_24"
    # 16 位加一点三角抖动，避免尾巴截断成颗粒
    if bits == 16:
        x = x + (RNG.random(x.shape) - RNG.random(x.shape)) / 32768.0
    sf.write(path, x, SR, subtype=sub)
    return x


def secs(t):
    return int(round(t * SR))


def silence(t, ch=1):
    return np.zeros(secs(t)) if ch == 1 else np.zeros((secs(t), 2))


def to_stereo(x, pan=0.0):
    if x.ndim == 2:
        return x
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def to_mono(x):
    return x if x.ndim == 1 else x.mean(axis=1)


def mix(*parts, length=None):
    """parts: (信号, 起点秒[, 增益]) ；自动补成同一声道数。"""
    ch = 2 if any(p[0].ndim == 2 for p in parts) else 1
    n = length if length is not None else max(secs(p[1]) + len(p[0]) for p in parts)
    out = np.zeros(n) if ch == 1 else np.zeros((n, 2))
    for p in parts:
        x, t0 = p[0], p[1]
        g = p[2] if len(p) > 2 else 1.0
        if ch == 2 and x.ndim == 1:
            x = to_stereo(x)
        a = secs(t0)
        if a >= n:
            continue
        b = min(n, a + len(x))
        out[a:b] += g * x[: b - a]
    return out


def db(v):
    return 10 ** (v / 20)


# ───────────────────────── 滤波 ─────────────────────────
def _sos(kind, f, order=2):
    nyq = SR / 2
    if kind in ("bandpass", "bandstop"):
        wn = [max(1, f[0]) / nyq, min(nyq * 0.999, f[1]) / nyq]
    else:
        wn = min(nyq * 0.999, max(1, f)) / nyq
    return signal.butter(order, wn, btype=kind, output="sos")


def _apply(sos, x):
    return signal.sosfilt(sos, x, axis=0)


def hp(x, f, order=2):
    return _apply(_sos("highpass", f, order), x)


def lp(x, f, order=2):
    return _apply(_sos("lowpass", f, order), x)


def bp(x, f1, f2, order=2):
    return _apply(_sos("bandpass", (f1, f2), order), x)


def _biquad(kind, f, gain_db=0.0, q=0.707):
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f / SR
    cw, sw = np.cos(w), np.sin(w)
    al = sw / (2 * q)
    if kind == "peak":
        b = [1 + al * A, -2 * cw, 1 - al * A]
        a = [1 + al / A, -2 * cw, 1 - al / A]
    elif kind == "lowshelf":
        sA = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) - (A - 1) * cw + sA), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sA)]
        a = [(A + 1) + (A - 1) * cw + sA, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sA]
    elif kind == "highshelf":
        sA = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * cw + sA), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sA)]
        a = [(A + 1) - (A - 1) * cw + sA, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sA]
    else:
        raise ValueError(kind)
    return np.array(b) / a[0], np.array(a) / a[0]


def eq(x, kind, f, gain_db, q=0.707):
    b, a = _biquad(kind, f, gain_db, q)
    return signal.lfilter(b, a, x, axis=0)


def sweep_filter(x, f0, f1, kind="lowpass", q=0.707, curve="exp", block=256):
    """随时间扫频的二阶滤波（逐块换系数，状态延续）。f0→f1 可以是数组（每块一个频率）。"""
    n = len(x)
    nb = (n + block - 1) // block
    if np.isscalar(f0):
        t = np.linspace(0, 1, nb)
        fs = f0 * (f1 / f0) ** t if curve == "exp" else f0 + (f1 - f0) * t
    else:
        fs = np.interp(np.linspace(0, 1, nb), np.linspace(0, 1, len(f0)), f0)
    y = np.zeros_like(x)
    zi = None
    for i in range(nb):
        f = float(np.clip(fs[i], 20, SR * 0.45))
        w = 2 * np.pi * f / SR
        cw, sw = np.cos(w), np.sin(w)
        al = sw / (2 * q)
        if kind == "lowpass":
            b = np.array([(1 - cw) / 2, 1 - cw, (1 - cw) / 2])
        elif kind == "highpass":
            b = np.array([(1 + cw) / 2, -(1 + cw), (1 + cw) / 2])
        else:  # bandpass，峰值 0 dB
            b = np.array([al, 0, -al])
        a = np.array([1 + al, -2 * cw, 1 - al])
        b, a = b / a[0], a / a[0]
        seg = x[i * block:(i + 1) * block]
        if zi is None:
            zi = np.zeros((2,) + seg.shape[1:])
        out, zi = signal.lfilter(b, a, seg, axis=0, zi=zi)
        y[i * block:(i + 1) * block] = out
    return y


# ───────────────────────── 包络 ─────────────────────────
def env_ar(n, a, r, curve=3.0):
    """a、r 秒。起音正弦，释放按指数曲线。"""
    t = np.arange(n) / SR
    e = np.ones(n)
    na = max(1, secs(a))
    e[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    if r > 0:
        nr = min(n, secs(r))
        e[n - nr:] *= (np.linspace(1, 0, nr) ** curve)
    return e


def fade(x, fin=0.005, fout=0.02):
    x = x.copy()
    ni, no = min(len(x), secs(fin)), min(len(x), secs(fout))
    if ni:
        w = np.sin(np.linspace(0, np.pi / 2, ni)) ** 2
        x[:ni] *= w if x.ndim == 1 else w[:, None]
    if no:
        w = np.cos(np.linspace(0, np.pi / 2, no)) ** 2
        x[len(x) - no:] *= w if x.ndim == 1 else w[:, None]
    return x


def shape(x, pts):
    """分段线性增益包络：pts = [(秒, 增益), ...]。"""
    t = np.arange(len(x)) / SR
    g = np.interp(t, [p[0] for p in pts], [p[1] for p in pts])
    return x * (g if x.ndim == 1 else g[:, None])


def expdecay(n, t60):
    return np.exp(-6.91 * np.arange(n) / SR / max(1e-4, t60))


# ───────────────────────── 变调、伸缩 ─────────────────────────
def resample_pitch(x, semis):
    """变调连带变速（像磁带），适合短促的一次性声音。"""
    r = 2 ** (semis / 12)
    n = int(len(x) / r)
    if n < 2:
        return x[:1]
    return signal.resample_poly(x, 1000, int(round(1000 * r)), axis=0)[:n] if abs(r - 1) > 1e-6 else x.copy()


def stretch(x, factor, win=4096, hop=None):
    """相位声码器时间伸缩（不变调）。factor>1 变长。单声道。"""
    hop = hop or win // 4
    w = np.hanning(win)
    X = [np.fft.rfft(w * x[i:i + win]) for i in range(0, len(x) - win, hop)]
    if len(X) < 2:
        return x.copy()
    X = np.array(X)
    steps = np.arange(0, len(X) - 1, 1 / factor)
    phase = np.angle(X[0])
    omega = 2 * np.pi * hop * np.arange(win // 2 + 1) / win
    out = np.zeros(int(len(steps) * hop + win))
    for k, s in enumerate(steps):
        i = int(s)
        fr = s - i
        mag = (1 - fr) * np.abs(X[i]) + fr * np.abs(X[i + 1])
        dp = np.angle(X[i + 1]) - np.angle(X[i]) - omega
        dp -= 2 * np.pi * np.round(dp / (2 * np.pi))
        out[k * hop:k * hop + win] += w * np.fft.irfft(mag * np.exp(1j * phase))
        phase += omega + dp
    return out * (hop / (win * 0.375))


# ───────────────────────── 噪声、合成 ─────────────────────────
def noise(t, color="white"):
    n = secs(t)
    x = RNG.standard_normal(n)
    if color == "pink":
        X = np.fft.rfft(x)
        f = np.maximum(1, np.arange(len(X)))
        x = np.fft.irfft(X / np.sqrt(f), n)
    elif color == "brown":
        X = np.fft.rfft(x)
        f = np.maximum(1, np.arange(len(X)))
        x = np.fft.irfft(X / f, n)
    return x / (np.std(x) + 1e-12)


def modal(freqs, t60s, amps, dur, exc=None, detune=0.0, phase_rand=True):
    """一组带阻尼的正弦：真实敲击体（石条、铜盘、玻璃）的振动模式。
    exc：激励信号（短噪声、真实敲击的瞬态），与模态卷积，让起音更像真东西。"""
    n = secs(dur)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f, t60, a in zip(freqs, t60s, amps):
        if f >= SR * 0.45:
            continue
        f = f * (1 + detune * RNG.standard_normal())
        ph = RNG.random() * 2 * np.pi if phase_rand else 0
        y += a * np.sin(2 * np.pi * f * t + ph) * np.exp(-6.91 * t / t60)
    if exc is not None:
        y = signal.fftconvolve(y, exc)[:n]
    return y


def beating_modes(freqs, t60s, amps, dur, split=0.002):
    """每个模态拆成两根相距很近的频率（铜器、钵的“拍”）。"""
    f2, t2, a2 = [], [], []
    for f, t60, a in zip(freqs, t60s, amps):
        d = split * (0.5 + RNG.random())
        f2 += [f * (1 - d / 2), f * (1 + d / 2)]
        t2 += [t60, t60 * 0.9]
        a2 += [a * 0.55, a * 0.45]
    return modal(f2, t2, a2, dur)


# 真实物体的模态比例
STONE_BAR = [1.0, 2.756, 5.404, 8.933]          # 两端自由的石条（石磬）
BRONZE_PLATE = [1.0, 1.59, 2.14, 2.30, 2.65, 2.92, 3.16, 3.50, 3.60, 4.06]  # 厚圆盘
BOWL = [1.0, 2.71, 5.15, 8.43, 12.5]            # 钵、碗（颂钵测得的比例）
GLASS = [1.0, 2.32, 4.25, 6.63, 9.38]           # 高脚杯
BELL = [0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 2.67, 3.0, 4.0]  # 钟：hum、prime、小三度、五度、八度……


def stone_knock(f0, dur=1.2, bright=1.0, damp=1.0):
    """石磬式的石头敲击：有音高、很快收住。"""
    ratios = STONE_BAR
    t60 = [0.9 / damp, 0.35 / damp, 0.16 / damp, 0.08 / damp]
    amps = [1.0, 0.45 * bright, 0.22 * bright, 0.1 * bright]
    y = modal([f0 * r for r in ratios], t60, amps, dur, detune=0.002)
    click = hp(noise(0.012), 1500) * expdecay(secs(0.012), 0.006) * 0.6 * bright
    return mix((y, 0), (click, 0))


def bronze_ring(f0, dur=3.0, t60=2.0, bright=1.0, ratios=None):
    ratios = ratios or BRONZE_PLATE
    t60s = [t60 / (1 + 0.45 * i) for i in range(len(ratios))]
    amps = [(0.8 ** i) * (bright if i else 1) for i in range(len(ratios))]
    return beating_modes([f0 * r for r in ratios], t60s, amps, dur, split=0.003)


# ───────────────────────── 动态、空间 ─────────────────────────
def rms(x):
    return np.sqrt(np.mean(np.square(x)) + 1e-20)


def _kweight(x):
    # BS.1770 的 K 计权（48 kHz 系数）
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=0), axis=0)


def lufs(x, mode="integrated"):
    """integrated：带门限的整段响度（循环、长声）；max：400 ms 窗口里最响的一段（一次性短声）。"""
    x = x if x.ndim == 2 else x[:, None]
    y = _kweight(x)
    win, hop = secs(0.4), secs(0.1)
    if len(y) < win:
        y = np.pad(y, ((0, win - len(y)), (0, 0)))
    ms = np.array([np.sum(np.mean(np.square(y[i:i + win]), axis=0)) for i in range(0, len(y) - win + 1, hop)])
    L = -0.691 + 10 * np.log10(ms + 1e-20)
    if mode == "max":
        return float(L.max())
    g = ms[L > -70]
    if not len(g):
        return -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g2 = ms[(L > -70) & (L > rel)]
    return float(-0.691 + 10 * np.log10(g2.mean()))


def norm_lufs(x, target, mode="max"):
    return x * db(target - lufs(x, mode))


def norm_peak(x, peak_db=-1.0):
    return x * (db(peak_db) / (np.max(np.abs(x)) + 1e-12))


def soft_clip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


def compress(x, thresh_db=-18, ratio=3.0, attack=0.005, release=0.12):
    m = to_mono(np.abs(x))
    a, r = np.exp(-1 / (attack * SR)), np.exp(-1 / (release * SR))
    env = np.zeros_like(m)
    e = 0.0
    for i, v in enumerate(m):
        e = a * e + (1 - a) * v if v > e else r * e + (1 - r) * v
        env[i] = e
    ldb = 20 * np.log10(env + 1e-9)
    gr = np.where(ldb > thresh_db, (thresh_db - ldb) * (1 - 1 / ratio), 0.0)
    g = db(gr)
    return x * (g if x.ndim == 1 else g[:, None])


def make_ir(t60_low=4.2, t60_high=1.6, dur=5.0, predelay=0.012, er=True, width=1.0, seed_=7):
    """合成一个石头圆殿的脉冲响应：早期反射（半径约 15 m 的圆墙、地面、楼板）+ 随频率变短的指数尾巴。"""
    rng = np.random.default_rng(seed_)
    n = secs(dur)
    out = np.zeros((n, 2))
    bands = [(20, 250, t60_low), (250, 1000, t60_low * 0.85), (1000, 4000, (t60_low + t60_high) / 2), (4000, 20000, t60_high)]
    for ch in range(2):
        tail = np.zeros(n)
        for f1, f2, t60 in bands:
            nz = rng.standard_normal(n)
            nz = bp(nz, f1, min(f2, 23000), order=3)
            tail += nz * np.exp(-6.91 * np.arange(n) / SR / t60)
        # 尾巴慢慢长出来（扩散）
        tail *= 1 - np.exp(-np.arange(n) / (0.025 * SR))
        out[:, ch] = tail
    if width < 1:
        m = out.mean(axis=1, keepdims=True)
        out = m + (out - m) * width
    if er:
        # 圆墙、地面、楼板的早期反射：往返 20–95 ms
        for k in range(18):
            t = predelay + rng.uniform(0.008, 0.095)
            g = 0.55 * np.exp(-t / 0.06) * rng.uniform(0.5, 1)
            i = secs(t)
            out[i, rng.integers(0, 2)] += g * 6
            out[min(n - 1, i + rng.integers(1, 40)), rng.integers(0, 2)] += g * 4
    pd = secs(predelay)
    out = np.vstack([np.zeros((pd, 2)), out])[:n]
    return out / np.sqrt(np.sum(out ** 2) / 2)


def convolve(x, ir, wet=0.3, dry=1.0):
    xs = to_stereo(x)
    y = np.stack([signal.fftconvolve(xs[:, c], ir[:, c]) for c in range(2)], axis=1)
    y = y * wet
    y[: len(xs)] += dry * xs
    return y


def pan_sweep(x, p0, p1):
    x = to_mono(x)
    p = np.linspace(p0, p1, len(x))
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def widen(x, amount=0.6, delay=0.011):
    """单声道做出宽度：Haas + 互补梳状。"""
    x = to_mono(x)
    d = secs(delay)
    y = np.concatenate([np.zeros(d), x])[: len(x)]
    side = (x - y) * 0.5 * amount
    return np.stack([x + side, x - side], axis=1)


# ───────────────────────── 素材整理 ─────────────────────────
def denoise(x, noise_clip=None, amount=1.0, floor=0.08, n_fft=2048):
    """谱减法去底噪。noise_clip：一段只有底噪的素材。"""
    def stft(v):
        return signal.stft(v, SR, nperseg=n_fft, noverlap=n_fft * 3 // 4)
    mono = x.ndim == 1
    xs = x[:, None] if mono else x
    nc = noise_clip if noise_clip is not None else None
    out = np.zeros_like(xs)
    for c in range(xs.shape[1]):
        f, t, Z = stft(xs[:, c])
        if nc is None:
            mag = np.abs(Z)
            prof = np.percentile(mag, 12, axis=1, keepdims=True)
        else:
            ncc = nc if nc.ndim == 1 else nc[:, min(c, nc.shape[1] - 1)]
            _, _, N = stft(ncc)
            prof = np.mean(np.abs(N), axis=1, keepdims=True)
        mag = np.abs(Z)
        g = np.maximum(floor, 1 - amount * prof / (mag + 1e-12))
        # 时间方向平滑一下增益，避免“水声”
        g = signal.lfilter([0.5], [1, -0.5], g, axis=1)
        _, y = signal.istft(Z * g, SR, nperseg=n_fft, noverlap=n_fft * 3 // 4)
        out[:, c] = y[: len(xs)] if len(y) >= len(xs) else np.pad(y, (0, len(xs) - len(y)))
    return out[:, 0] if mono else out


def detone(x, thresh_db=7.0, lo=150, hi=6000, n_fft=2048, width=10, hold=5):
    """去掉噪声类录音里“有音高的细线”（水泡咕噜声听起来像猫叫、人声），宽带的水声不动。
    每帧用频率方向的中值当底，高出底 thresh_db 且在时间上持续几帧的窄峰压回到底的水平。"""
    from scipy.ndimage import median_filter, maximum_filter, uniform_filter1d
    hop = n_fft // 4
    mono = x.ndim == 1
    xs = x[:, None] if mono else x
    f, _, Zm = signal.stft(xs.mean(axis=1), SR, nperseg=n_fft, noverlap=n_fft - hop)
    P = np.abs(Zm) ** 2 + 1e-20
    floor = median_filter(P, size=(2 * width + 1, 1), mode="nearest")
    R = maximum_filter(P / floor, size=(5, 1))                 # 频率方向放宽两格：滑音也算同一条线
    R = np.exp(uniform_filter1d(np.log(R), hold, axis=1))      # 时间方向要持续（随机的噪声尖峰会被平均掉）
    band = ((f > lo) & (f < hi))[:, None]
    over = np.where(band, R / 10 ** (thresh_db / 10), 1.0)
    g = np.where(over > 1, np.minimum(1.0, np.sqrt(2.0 * floor / P)), 1.0)
    g = np.minimum(g, uniform_filter1d(g, 3, axis=1))
    out = np.zeros_like(xs)
    for c in range(xs.shape[1]):
        _, _, Z = signal.stft(xs[:, c], SR, nperseg=n_fft, noverlap=n_fft - hop)
        _, y = signal.istft(Z * g, SR, nperseg=n_fft, noverlap=n_fft - hop)
        out[:, c] = y[: len(xs)] if len(y) >= len(xs) else np.pad(y, (0, len(xs) - len(y)))
    return out[:, 0] if mono else out


def onsets(x, thresh_db=-30, min_gap=0.18, hop=0.004):
    """很简单的起音检测：能量包络的上升沿。返回秒。"""
    m = to_mono(x)
    h = secs(hop)
    e = np.array([np.sqrt(np.mean(m[i:i + h] ** 2)) for i in range(0, len(m) - h, h)])
    edb = 20 * np.log10(e + 1e-9)
    ref = np.percentile(edb, 99)
    flux = np.diff(edb, prepend=edb[0])
    res, last = [], -1e9
    for i in range(1, len(e)):
        t = i * hop
        if edb[i] > ref + thresh_db and flux[i] > 6 and t - last > min_gap:
            # 往回找到真正起点
            j = i
            while j > 0 and edb[j - 1] < edb[j] and edb[j - 1] > ref + thresh_db - 25:
                j -= 1
            res.append(j * hop)
            last = t
    return res


def slice_hits(x, ons, pre=0.008, maxlen=0.6, tail_db=-48):
    """按起音切出单个声音：结尾在能量掉到峰值以下 tail_db 处或下一个起音前。"""
    out = []
    m = to_mono(x)
    for k, t in enumerate(ons):
        a = max(0, secs(t - pre))
        nxt = secs(ons[k + 1] - 0.01) if k + 1 < len(ons) else len(m)
        b = min(len(m), a + secs(maxlen), nxt)
        seg = x[a:b]
        mm = to_mono(seg)
        pk = np.max(np.abs(mm)) + 1e-12
        env = np.convolve(np.abs(mm), np.ones(secs(0.01)) / secs(0.01), mode="same")
        idx = np.where(env > pk * db(tail_db))[0]
        end = idx[-1] + secs(0.02) if len(idx) else len(seg)
        seg = seg[: min(len(seg), end)]
        out.append(fade(seg, 0.002, min(0.04, len(seg) / SR / 3)))
    return out


def loopify(x, xfade=2.0):
    """把一段素材做成首尾无缝的循环：结尾一段等功率交叉淡入开头。"""
    n = secs(xfade)
    body = x[: len(x) - n].copy()
    tail = x[len(x) - n:]
    w = np.linspace(0, 1, n)
    fi, fo = np.sin(w * np.pi / 2), np.cos(w * np.pi / 2)
    if x.ndim == 2:
        fi, fo = fi[:, None], fo[:, None]
    body[:n] = body[:n] * fi + tail * fo
    return body


def grains(src, dur, density=40, glen=(0.03, 0.12), pitch=0.0, spread=0.0, env=None, pan=0.0):
    """粒子化：从 src 里随机取小片段撒到时间线上（碎石、粉末、闪光）。"""
    n = secs(dur)
    out = np.zeros((n, 2))
    m = to_mono(src)
    count = int(density * dur)
    for _ in range(count):
        L = secs(RNG.uniform(*glen))
        if L >= len(m):
            continue
        a = RNG.integers(0, len(m) - L)
        g = m[a:a + L] * np.hanning(L)
        if pitch or spread:
            g = resample_pitch(g, pitch + spread * RNG.standard_normal())
        t = RNG.integers(0, max(1, n - len(g)))
        amp = 1.0 if env is None else float(np.interp(t / n, np.linspace(0, 1, len(env)), env))
        p = np.clip(pan + RNG.uniform(-0.7, 0.7), -1, 1)
        out[t:t + len(g)] += to_stereo(g * amp, p)
    return out


def credits():
    p = os.path.join(SRC_DIR, "credits.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def events(x, min_dist=0.25, pre_db=-30, max_pre=0.14, post=0.35, prom_db=12, smooth=0.02, gap=0.012):
    """找“整步”事件：平滑能量包络的峰（相距至少 min_dist），往前找到能量升起的地方（最多 max_pre 秒），往后取 post 秒。
    返回 [(起点秒, 终点秒, 峰值 dB)]。"""
    m = to_mono(x)
    k = secs(smooth)
    env = np.sqrt(np.convolve(m ** 2, np.ones(k) / k, mode="same")) + 1e-9
    edb = 20 * np.log10(env)
    pk, _ = signal.find_peaks(edb, distance=secs(min_dist), prominence=prom_db)
    starts = []
    for p in pk:
        a = p
        lim = max(0, p - secs(max_pre))
        while a > lim and edb[a] > edb[p] + pre_db:
            a -= 1
        starts.append(a)
    res = []
    for k, p in enumerate(pk):
        b = min(len(m), p + secs(post))
        if k + 1 < len(pk):
            b = min(b, starts[k + 1] - secs(gap))   # 不吃进下一步
        res.append((starts[k] / SR, b / SR, float(edb[p])))
    return res
