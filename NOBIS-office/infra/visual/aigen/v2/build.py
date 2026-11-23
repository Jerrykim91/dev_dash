#!/usr/bin/env python3
"""표준 v2 빌드: raw/(AI 생성) → norm/(엔진 프레임) + qa.json/qa.md(게이트 결과) + 프리셋 색 교체.

가구  : 블록아웃 앵커를 그대로 옮겨 128x160(앵커 64,104)로 축소. 파트 마스크로 lower/upper 분리. 반전본(.m) 생성.
클립  : 셀(48x64, 발 24,58)마다 잘라 축소. 반전본은 엔진이 setFlipX로 처리하므로 미리보기용으로만 생성.
QA    : 각도(↗↘ vs 26.565°), 블록아웃 IoU, 측면 명암 대칭, 프레임 경계, 색 수 / 발 흔들림, 키, 프레임 간 색 일관성.
밀도  : NOBIS_DENSITY=2 → 같은 원본·같은 정합으로 2배 밀도(HD) 프레임을 norm_hd/에 만든다(축소 1/4, 게임에서 0.5배로 그림).
        QA 기준은 1배 빌드의 qa.json이 정본이므로 HD 빌드는 qa.json을 쓰지 않는다. docs/visual-standard-v2.md §14
"""
import colorsys, json, os, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from normalize import pixelize  # noqa: E402
from standard import ISO_DEG, QA, RAMPS, SIDE_SHADE_TOLERANCE  # noqa: E402

SPEC = json.loads((HERE / 'spec.json').read_text())
D = int(os.environ.get('NOBIS_DENSITY', '1'))  # 그림 밀도(1 = 표준 1px/월드px, 2 = HD)
RAW, BO, NORM = HERE / 'raw', HERE / 'blockout', HERE / ('norm' if D == 1 else f'norm_d{D}')
COLORS_FURN, COLORS_CLIP = (48, 32) if D == 1 else (48, 48)
CHROMA = Path.home() / '.codex/skills/.system/imagegen/scripts/remove_chroma_key.py'
ORGANIC = {'plant', 'rug', 'table_round', 'cat_bed', 'lamp'}  # 유기적·원형(블록아웃 박스와 원형 실루엣의 면적비 한계 π/4 등)
# 프리셋별 색 교체 대상(공통 팔레트 기준 실측). (색상 하한, 상한, 램프 그룹, 채도 하한, 명도 하한, 명도 상한)
# p3은 크림색 니트가 피부와 색상·채도·명도가 겹쳐 분리 불가 → 머리카락(채도 높고 어두움)을 교체
# p3: 색상 340~20°(빨강 축을 넘어감), 채도 > 0.35(피부 0.27~0.32 제외), 명도 0.28~0.90(외곽선 0.26 제외),
#     부츠가 같은 팔레트를 공유하므로 머리 영역(프레임 상단 26px) 픽셀만 교체
TOP_HUE = {'p0': (235, 300, 'top', .07, .40, 1.0),  # p0 명도 하한 0.40: 보라 기운의 짙은 회색 바지(명도 0.33)가 상의로 잡혀 색이 바뀌던 문제 'p1': (45, 140, 'top', .07, .30, 1.0),
           'p2': (225, 262, 'top', .07, .25, 1.0), 'p3': (340, 20, 'hair', .35, .28, .90)}
REGION = {'p3': 26}  # 색 교체를 프레임 상단 N px(머리)로 제한


# ---------- 공통 ----------
def load_raw(aid, size):
    src = RAW / f'{aid}.png'
    im = Image.open(src).convert('RGBA')
    if np.asarray(im)[..., 3].min() == 255:
        out = RAW / f'{aid}.keyed.png'
        subprocess.run([sys.executable, str(CHROMA), '--input', str(src), '--out', str(out), '--auto-key', 'border', '--despill', '--force'],
                       check=True, capture_output=True)
        im = Image.open(out).convert('RGBA')
    return im.resize(size, Image.LANCZOS)


def binarize(im, keep, min_frac=.02):
    a = np.asarray(im).copy()
    mask = a[..., 3] >= 128
    lab, n = ndimage.label(mask)
    if n:
        sizes = ndimage.sum(mask, lab, range(1, n + 1))
        order = np.argsort(sizes)[::-1]
        ok = [i + 1 for i in order[:keep]] + [i + 1 for i in order[keep:] if sizes[i] > sizes[order[0]] * min_frac]
        mask = np.isin(lab, ok)
    a[..., 3] = np.where(mask, 255, 0)
    return Image.fromarray(a), mask


def _j(o):
    return o.item() if hasattr(o, 'item') else str(o)


def iou(a, b):
    return float((a & b).sum() / max(1, (a | b).sum()))


def _angles(gray, sigma):
    from skimage.feature import canny
    from skimage.transform import probabilistic_hough_line
    lines = probabilistic_hough_line(canny(gray, sigma=sigma), threshold=10, line_length=50, line_gap=3, rng=1)
    res = {}
    for sign, name in ((1, 'up'), (-1, 'down')):
        v = []
        for (x0, y0), (x1, y1) in lines:
            if x1 == x0:
                continue
            ang = ((np.degrees(np.arctan2(-(y1 - y0), x1 - x0)) + 90) % 180) - 90
            if 15 < abs(ang) < 40 and np.sign(ang) == sign:
                v.append((abs(ang), np.hypot(x1 - x0, y1 - y0)))
        if v:
            v = np.array(v)
            res[name] = float(np.average(v[:, 0], weights=v[:, 1]))
    return res


def edge_angles(rgba):
    """내부 구조선(색 경계)과 실루엣(외곽선) 두 방식으로 측정한다.
    장식 사선(아케이드 무늬)은 내부 측정을, 얇은 다리(의자 별 다리)는 실루엣 측정을 오염시키므로
    둘 중 하나라도 2:1과 일치하면 기하가 맞는 것으로 본다."""
    a = np.asarray(rgba).astype(float)
    vis = a[..., 3] > 128
    return {'interior': _angles(np.where(vis, a[..., :3].mean(-1), 0), 2), 'silhouette': _angles(vis.astype(float) * 255, 1)}


def side_symmetry(rgba, parts, faces, erode=3):
    """파트별로 +y면(2)과 +x면(3)의 밝기 중앙값 비교(면 안쪽 영역, 손잡이 등 디테일 영향 배제) → 면적 가중 상대 차이."""
    a = np.asarray(rgba).astype(float)
    lum = (a[..., :3] @ [0.299, 0.587, 0.114])
    vis = a[..., 3] > 128
    diffs, weights = [], []
    for pid in np.unique(parts):
        if pid == 0:
            continue
        m2 = ndimage.binary_erosion((parts == pid) & (faces == 2) & vis, iterations=erode)
        m3 = ndimage.binary_erosion((parts == pid) & (faces == 3) & vis, iterations=erode)
        if m2.sum() > 300 and m3.sum() > 300:
            l2, l3 = np.median(lum[m2]), np.median(lum[m3])
            diffs.append(abs(l2 - l3) / max(1, (l2 + l3) / 2))
            weights.append(min(m2.sum(), m3.sum()))
    return float(np.average(diffs, weights=weights)) if diffs else None


def register(rgba, target_mask, scales=np.arange(.80, 1.21, .01)):
    """각도는 맞지만 위치·크기가 어긋난 생성물을 블록아웃 실루엣에 정합(확대+이동, IoU 최대화)."""
    from scipy.signal import fftconvolve
    W, H = rgba.size
    tm = target_mask.astype(float)
    best = (iou(np.asarray(rgba)[..., 3] > 128, target_mask), 1.0, 0, 0)
    for sc in scales:
        im = rgba.resize((round(W * sc), round(H * sc)), Image.LANCZOS)
        m = (np.asarray(im)[..., 3] > 128).astype(float)
        # 상관으로 최적 이동량 탐색
        corr = fftconvolve(tm, m[::-1, ::-1], mode='full')
        py, px = np.unravel_index(np.argmax(corr), corr.shape)
        dy, dx = py - (m.shape[0] - 1), px - (m.shape[1] - 1)
        canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        canvas.alpha_composite(im, (0, 0)) if False else canvas.paste(im, (int(dx), int(dy)), im)
        v = iou(np.asarray(canvas)[..., 3] > 128, target_mask)
        if v > best[0]:
            best = (v, float(sc), int(dx), int(dy), canvas)
    if len(best) == 5:
        return best[4], {'scale': round(best[1], 2), 'dx': best[2], 'dy': best[3]}
    return rgba, {'scale': 1.0, 'dx': 0, 'dy': 0}


# HD 빌드는 1배 빌드가 찾은 정합값(qa.json)을 그대로 쓴다(같은 원본 → 같은 정합, 탐색 시간 절약)
KNOWN_REG = {k: v['registration'] for k, v in json.loads((HERE / 'qa.json').read_text()).items()
             if not k.startswith('_') and isinstance(v, dict) and v.get('registration')} if D > 1 and (HERE / 'qa.json').exists() else {}


def register_for(aid, rgba, target_mask, scales=np.arange(.80, 1.21, .01)):
    r = KNOWN_REG.get(aid)
    if r is None:
        return register(rgba, target_mask, scales)
    W, H = rgba.size
    im = rgba.resize((round(W * r['scale']), round(H * r['scale'])), Image.LANCZOS)
    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    canvas.paste(im, (int(r['dx']), int(r['dy'])), im)
    return canvas, dict(r)


def equalize_sides(rgba, parts, faces, erode=3):
    """결정 1(위쪽 광원·측면 대칭)을 결정적으로 보장: 파트마다 +y면/+x면 밝기 중앙값을 둘의 평균으로 맞춘다."""
    a = np.asarray(rgba).astype(float)
    lum = a[..., :3] @ [0.299, 0.587, 0.114]
    vis = a[..., 3] > 128
    for pid in np.unique(parts):
        if pid == 0:
            continue
        regions = [(parts == pid) & (faces == f) & vis for f in (2, 3)]
        cores = [ndimage.binary_erosion(r, iterations=erode) for r in regions]
        if min(c.sum() for c in cores) < 300:
            continue
        meds = [np.median(lum[c]) for c in cores]
        target = sum(meds) / 2
        for r, m in zip(regions, meds):
            if m > 1:
                a[r, :3] = (a[r, :3] * (target / m)).clip(0, 255)
    return Image.fromarray(a.astype(np.uint8))


def to_frame(img, anchor, s=8, frame=(128, 160), at=(64, 104), resample=Image.NEAREST):
    big = Image.new(img.mode, (frame[0] * s, frame[1] * s), 0 if img.mode in ('P', 'L') else (0, 0, 0, 0))
    big.paste(img, (round(at[0] * s - anchor[0]), round(at[1] * s - anchor[1])))
    return big


# ---------- 가구 ----------
def build_furniture(a):
    aid = a['id']
    meta = json.loads((BO / f"{Path(a['guide']).stem}.json").read_text())
    bo = Image.open(BO / f"{Path(a['guide']).stem}.png")
    parts = np.asarray(Image.open(BO / f"{Path(a['guide']).stem}.parts.png"))
    faces = np.asarray(Image.open(BO / f"{Path(a['guide']).stem}.faces.png"))
    raw = load_raw(aid, bo.size)
    raw, mask = binarize(raw, keep=1)
    bmask = np.asarray(bo)[..., 3] > 0
    q = {'iou_raw': round(iou(mask, bmask), 3)}
    raw, q['registration'] = register_for(aid, raw, bmask)
    q['iou'] = round(iou(np.asarray(raw)[..., 3] > 128, bmask), 3)
    ang = edge_angles(raw)
    errs = {k: max(abs(v - ISO_DEG) for v in m.values()) for k, m in ang.items() if m}
    q['angle'] = {k: {d: round(v, 1) for d, v in m.items()} for k, m in ang.items()}
    q['angle_err'] = round(min(errs.values()), 1) if errs else None
    before = side_symmetry(raw, parts, faces)
    raw = equalize_sides(raw, parts, faces)
    after = side_symmetry(raw, parts, faces)
    q['side_asym_raw'] = round(before, 3) if before is not None else None
    q['side_asym'] = round(after, 3) if after is not None else None
    S, (fw, fh), at = meta['scale'], (128, 160), (64, 104)
    if S != 8:  # 큰 가구(3x5 등): footprint+높이를 덮는 프레임. 게임에서는 타일 단위로 분할(엔진 작업)
        w, h = meta['footprint']
        zmax_px = 40 + 8
        at = (32 * h + 8, zmax_px)
        fw, fh = 32 * (w + h) + 16, zmax_px + (w + h - 1) * 16 + 8
    q['frame'] = [fw, fh, *at]
    big = to_frame(raw, meta['anchor'], s=S, frame=(fw, fh), at=at, resample=Image.LANCZOS)
    frame = pixelize(big, fw * D, fh * D, COLORS_FURN)
    up_ids = [p['id'] for p in meta['parts'] if p['layer'] == 'upper']
    pm = np.asarray(to_frame(Image.fromarray(parts), meta['anchor'], s=S, frame=(fw, fh), at=at))
    up = np.isin(pm, up_ids).reshape(fh * D, S // D, fw * D, S // D).mean(axis=(1, 3)) > .3
    up = ndimage.binary_dilation(up, iterations=D) if up.any() else up
    f = np.asarray(frame)
    lower, upper = f.copy(), f.copy()
    lower[..., 3] = np.where(up, 0, f[..., 3])
    upper[..., 3] = np.where(up, f[..., 3], 0)
    for suffix, arr in (('lower', lower), ('upper', upper)):
        Image.fromarray(arr).save(NORM / f'{aid}.{suffix}.png')
        Image.fromarray(np.fliplr(arr)).save(NORM / f'{aid}.m.{suffix}.png')
    al = f[..., 3] > 0
    q['clipped'] = bool(al[0].any() or al[:, 0].any() or al[:, -1].any() or al[-1].any())
    q['colors'] = int(len(np.unique(f[al][:, :3], axis=0)))
    q['upper_px'] = int((upper[..., 3] > 0).sum())
    organic = aid in ORGANIC or '_lay_' in aid  # 누운 캐릭터는 가구 경로로 빌드하지만 각도 검사 대상 아님
    q['pass'] = {
        'iou': q['iou'] >= (QA['iou_min_organic'] if organic else QA['iou_min']),
        'angle': True if organic or q['angle_err'] is None else q['angle_err'] <= QA['angle_tol_deg'],
        'symmetry': q['side_asym'] is None or q['side_asym'] <= SIDE_SHADE_TOLERANCE,
        'bounds': not q['clipped'], 'colors': q['colors'] <= QA['max_colors']}
    return q


# ---------- 클립 ----------
def skin_ratio(fr):
    """머리 영역(위쪽 22px)의 피부색 비율. 앞모습은 얼굴이 보여 높고 뒷모습은 낮다(프리셋마다 절대값은 다름)."""
    a = np.asarray(fr).astype(float)
    al = a[..., 3] > 0
    ys = np.nonzero(al.any(1))[0]
    head = al.copy()
    head[ys.min() + 22 * D:] = False
    px = a[head][:, :3] / 255
    if not len(px):
        return 0.0
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in px])
    return float(((hsv[:, 0] * 360 >= 8) & (hsv[:, 0] * 360 <= 40) & (hsv[:, 1] > .12) & (hsv[:, 1] < .55) & (hsv[:, 2] > .72)).mean())


def build_clip(a):
    aid = a['id']
    stem = Path(a['guide']).stem
    meta = json.loads((BO / f'{stem}.json').read_text())
    bo = np.asarray(Image.open(BO / f'{stem}.png'))[..., 3] > 0
    S, (x0, y0), n = meta['scale'], meta['origin'], meta['frames']
    cw, ch = 48 * S, 64 * S
    raw = load_raw(aid, tuple(meta['canvas']))
    raw, mask = binarize(raw, keep=n)
    frames, q = [], {'frames': n}
    # 스트립 전체를 마네킹 실루엣에 정합(프레임 간 움직임은 보존). 프리셋·클립 간 키 편차 제거
    raw, q['registration'] = register_for(aid, raw, bo, scales=np.arange(.86, 1.15, .01))
    mask = np.asarray(raw)[..., 3] > 128
    ious, bottoms, cxs, heights, bo_heights, bo_bottoms = [], [], [], [], [], []
    for k in range(n):
        box = (x0 + k * cw, y0, x0 + (k + 1) * cw, y0 + ch)
        cell = raw.crop(box)
        fr = pixelize(cell, 48 * D, 64 * D, COLORS_CLIP)
        frames.append(fr)
        fr.save(NORM / f'{aid}_{k}.png')
        cm, bm = mask[y0:y0 + ch, box[0]:box[2]], bo[y0:y0 + ch, box[0]:box[2]]
        ious.append(iou(cm, bm))
        fa = np.asarray(fr)[..., 3] > 0
        ys, xs = np.nonzero(fa)
        bottoms.append(int(ys.max()) / D)
        cxs.append(float(xs.mean()) / D)
        heights.append((int(ys.max() - ys.min() + 1)) / D)
        by = np.nonzero(bm.any(1))[0]
        bo_heights.append((by.max() - by.min() + 1) / S)
        bo_bottoms.append(by.max() / S)
    hist = [np.histogramdd((np.asarray(f)[np.asarray(f)[..., 3] > 0][:, :3] // 32), bins=8, range=[(0, 8)] * 3)[0].ravel() for f in frames]
    sim = min(float(h1 @ h2 / (np.linalg.norm(h1) * np.linalg.norm(h2))) for h1 in hist for h2 in hist)
    q.update(iou_min=round(min(ious), 3), foot_jitter=round(max(abs(b - m) for b, m in zip(bottoms, bo_bottoms)), 1), cx_jitter=round(max(cxs) - min(cxs), 1),
             height=heights, mannequin_height=[round(h, 1) for h in bo_heights], color_sim_min=round(sim, 3))
    standing = any(t in aid for t in ('idle', 'walk'))
    q['height_err'] = round(max(h - b for h, b in zip(heights, bo_heights)), 1)
    # 방향 검사: 클립 안에서 한 프레임만 머리 피부색 비율이 튀면 앞/뒤가 뒤집힌 것(끄덕이기는 고개를 숙여 정상 변화).
    # 색 일관성(color_sim_min)은 소품·팔 동작으로 오탐이 많아 참고 지표로만 남긴다(묶음 2: 31건 중 실제 결함 1건).
    ratios = [skin_ratio(f) for f in frames]
    q['skin_ratio'] = [round(r, 3) for r in ratios]
    flip = len(ratios) > 1 and 'nod' not in aid and max(ratios) - float(np.median(ratios)) > .10
    q['pass'] = {'iou': q['iou_min'] >= QA['iou_min_organic'], 'foot': q['foot_jitter'] <= QA['foot_jitter_px'] + 1,
                 'height': (-1 <= q['height_err'] <= QA['hair_allowance_px']) if standing else True,
                 'direction': not flip}
    sheet = Image.new('RGBA', (48 * D * n, 64 * D), (0, 0, 0, 0))
    for k, fr in enumerate(frames):
        sheet.alpha_composite(fr, (48 * D * k, 0))
    sheet.save(NORM / f'{aid}.sheet.png')
    return q


# ---------- 바닥·벽 (텍스처 투영, 위쪽 광원 → 두 벽면 같은 톤) ----------
def build_floor(src, name):
    # 바닥 무늬는 2배 밀도에서도 1배 텍셀(32)로 투영한다: 텍셀을 더 잘게 하면 나무결·이음선이 1px 줄무늬로 촘촘해져 지글거린다
    T = 32
    tex = np.asarray(Image.open(src).convert('RGB').resize((T, T), Image.BOX)
                     .quantize(16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB'))
    out = np.zeros((32 * D, 64 * D, 4), np.uint8)
    for py in range(32 * D):
        for px in range(64 * D):
            dx, dy = (px + .5 - 32 * D) / (32 * D), (py + .5 - 16 * D) / (16 * D)
            if abs(dx) + abs(dy) > 1.0001:
                continue
            gx, gy = (dx + dy) / 2 + .5, (dy - dx) / 2 + .5
            out[py, px, :3], out[py, px, 3] = tex[min(T - 1, int(gy * T)), min(T - 1, int(gx * T))], 255
    Image.fromarray(out).save(NORM / f'{name}.png')


def build_wall(src, name, H=80, shade=.95, segments=True):
    """정면 텍스처 → 벽면 투영. 위쪽 광원이라 두 벽면 같은 톤(shade). 투명(난간)은 알파 유지.
    segments=True면 단일 칸(_x/_y)과 연속 3칸(_x0..2)을, 문은 가운데 한 칸만 만든다."""
    s = Image.open(src).convert('RGBA')
    H *= D
    W = round(s.width * H / s.height)
    small = s.resize((W, H), Image.BOX)
    a = np.asarray(small)[..., 3]
    rgb = np.asarray(small.convert('RGB').quantize(24, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB'))
    alpha = np.where(a >= 128, 255, 0) if a.min() < 255 else np.full(a.shape, 255)
    U = 32 * D  # 벽 한 칸 폭
    c0 = (W - U) // 2

    def face(c, axis):
        x0, y0, slope = (32 * D, 104 * D, -.5) if axis == 'x' else (64 * D, 88 * D, .5)
        out = np.zeros((160 * D, 128 * D, 4), np.uint8)
        for u in range(U):
            base = y0 + int(np.floor(u * slope)) if slope > 0 else y0 - int(np.ceil(u * .5))
            for v in range(H):
                y = base - H + v
                out[y, x0 + u, :3], out[y, x0 + u, 3] = (rgb[v, c + u] * shade).clip(0, 255), alpha[v, c + u]
        return Image.fromarray(out)

    for axis in 'xy':
        face(c0, axis).save(NORM / f'{name}_{axis}.png')
        if segments:
            for k in range(3):
                face(c0 + (k - 1) * U, axis).save(NORM / f'{name}_{axis}{k}.png')
    return {'strip': [W, H], 'transparent': bool(a.min() < 255)}


# ---------- 프리셋 색 교체 ----------
def hex2rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)


def recolor(preset, n_colors=28):
    """결정 2(프리셋 + 팔레트 램프 교체): 프리셋 전 프레임에 공통 인덱스 팔레트를 씌우고,
    의상 색 항목만 밝기 순서대로 목표 램프에 매핑한다. 외곽선(명도 0.30 이하)은 건드리지 않는다."""
    lo, hi, group, smin, vmin, vmax = TOP_HUE[preset]
    files = sorted(f for f in NORM.glob(f'{preset}_*_[0-9].png'))
    if not files:
        return []
    frames = [Image.open(f).convert('RGBA') for f in files]
    mosaic = Image.new('RGB', (48 * D * len(frames), 64 * D), (0, 0, 0))
    for i, f in enumerate(frames):
        mosaic.paste(f.convert('RGB'), (48 * D * i, 0), f)
    opaque = np.concatenate([np.asarray(f)[np.asarray(f)[..., 3] > 0][:, :3] for f in frames])
    sample = Image.fromarray(opaque.reshape(1, -1, 3).astype(np.uint8))
    pal_img = sample.quantize(n_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(pal_img.getpalette()[:n_colors * 3]).reshape(-1, 3)
    # 1) 공통 팔레트로 모든 프레임 재매핑(프레임 간 색 일관성)
    indexed = []
    for f, path in zip(frames, files):
        a = np.asarray(f)
        rgb = Image.fromarray(a[..., :3]).quantize(palette=pal_img, dither=Image.Dither.NONE)
        idx = np.asarray(rgb)
        out = np.dstack([pal[idx], a[..., 3]]).astype(np.uint8)
        Image.fromarray(out).save(path)
        indexed.append((path, idx, a[..., 3]))
    # 2) 의상 항목 찾기
    hsv = np.array([colorsys.rgb_to_hsv(*(c / 255)) for c in pal])
    in_hue = (lambda h: lo <= h <= hi) if lo <= hi else (lambda h: h >= lo or h <= hi)
    garment = [i for i, (h, sat, v) in enumerate(hsv) if in_hue(h * 360) and sat > smin and vmin < v <= vmax]
    if not garment:
        return []
    garment.sort(key=lambda i: -(pal[i] @ [0.299, 0.587, 0.114]))  # 밝음→어두움
    out_names = []
    for ramp_name, ramp in RAMPS[group].items():
        cols = [hex2rgb(c) for c in ramp]
        newpal = pal.copy().astype(float)
        for rank, i in enumerate(garment):
            newpal[i] = cols[min(3, int(rank * 4 / len(garment)))]
        for path, idx, alpha in indexed:
            rgb = newpal[idx]
            if preset in REGION:  # 머리 영역 밖(부츠 등)은 원래 색 유지
                ys = np.nonzero((alpha > 0).any(1))[0]
                keep = np.zeros(idx.shape, bool)
                if len(ys):
                    keep[ys.min() + REGION[preset] * D:] = True
                rgb = np.where(keep[..., None], pal[idx], rgb)
            Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8)).save(
                path.with_name(path.name.replace(preset + '_', f'{preset}-{ramp_name}_')))
        out_names.append(ramp_name)
    return out_names


def main():
    NORM.mkdir(exist_ok=True)
    ids = sys.argv[1:]
    recolor_only = ids == ['--recolor']
    if recolor_only:
        ids = ['__none__']
    report = json.loads((HERE / 'qa.json').read_text()) if (HERE / 'qa.json').exists() and D == 1 else {}
    for a in SPEC['assets']:
        if ids and a['id'] not in ids or not (RAW / f"{a['id']}.png").exists():
            continue
        if a['type'] == 'gprop':
            report[a['id']] = build_furniture(a)
        elif a['type'] == 'gclip' and a['id'] != 'p1_turn':
            report[a['id']] = build_clip(a)
        elif a['type'] == 'texture':
            src = RAW / f"{a['id']}.png"
            if a['id'].startswith('floor'):
                build_floor(src, a['id'])
            elif a['id'].startswith('door_'):
                report[a['id']] = {'kind': 'door', **build_wall(src, a['id'], segments=False), 'pass': {'built': True}}
            else:
                report[a['id']] = {'kind': 'wall', **build_wall(src, a['id']), 'pass': {'built': True}}
        print(a['id'], json.dumps(report.get(a['id'], {}).get('pass', 'built'), ensure_ascii=False, default=_j))
    if not recolor_only:
        build_floor(HERE.parent / 'raw' / 'floor_stone.png', 'floor_stone')
        build_wall(HERE.parent / 'raw' / 'wall_plain.png', 'wall_plain')
    for p in ([] if os.environ.get('NOBIS_SKIP_RECOLOR') else TOP_HUE):  # 병렬 빌드는 끝난 뒤 --recolor 한 번
        r = recolor(p)
        if r:
            report.setdefault('_recolor', {})[p] = r
    if D == 1:  # QA 정본은 1배 빌드
        (HERE / 'qa.json').write_text(json.dumps(report, indent=1, ensure_ascii=False, default=_j))
        write_md(report)


def write_md(report):
    rows = ['| 에셋 | 결과 | 지표 |', '|---|---|---|']
    for k, q in report.items():
        if k.startswith('_'):
            continue
        ok = all(q['pass'].values())
        fails = [n for n, v in q['pass'].items() if not v]
        if q.get('kind') in ('wall', 'door'):
            m = f"{q['kind']} 투영, 띠 {q['strip']}, 투명 {q['transparent']}"
        elif 'iou' in q:
            m = f"IoU {q.get('iou_raw')}→{q['iou']} (정합 {q.get('registration')}), 각도 {q.get('angle')}, 측면차 {q.get('side_asym_raw')}→{q.get('side_asym')}, 색 {q['colors']}, upper {q['upper_px']}px"
        else:
            m = f"정합 {q.get('registration')}, IoU≥{q['iou_min']}, 발 오차 {q['foot_jitter']}px, 중심x {q['cx_jitter']}px, 키 {q['height']} (마네킹 {q['mannequin_height']}), 색일관 {q['color_sim_min']}"
        rows.append(f"| {k} | {'✅' if ok else '❌ ' + ', '.join(fails)} | {m} |")
    (HERE / 'qa.md').write_text('# 스타일 보드 v2 QA\n\n' + '\n'.join(rows) + '\n')


if __name__ == '__main__':
    main()
