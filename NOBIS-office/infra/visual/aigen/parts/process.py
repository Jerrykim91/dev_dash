#!/usr/bin/env python3
"""파트 분리 시험 처리 (docs/visual-standard-v2.md §15).

  python3 process.py base      raw/base_<dir> → work/base_<dir>.png (템플릿 좌표로 정합, 투명 배경) = 옷 생성의 편집 대상
  python3 process.py layers    raw/top-*,bottom-* → work/<id>.png (기본 몸과 달라진 픽셀만 남긴 옷 레이어)
                               raw/heads → work/head_<style>_<dir>.png (머리 구 중심 기준 잘라 낸 머리 스프라이트)
  python3 process.py combos    기본 몸 + 하의 + 상의 + 머리를 고해상도에서 합성 → HD(96×128) 프레임 → out/

정합: 시트 전체 배율·이동(실루엣 IoU) 후, 칸마다 ±24px 이동을 다시 맞춘다(모델은 좌표를 정확히 지키지 않는다, sow 교훈).
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.signal import fftconvolve

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from normalize import pixelize  # noqa: E402
from template import FRAMES, frame_origin, BODY_S, HEAD_S  # noqa: E402

CHROMA = Path.home() / '.codex/skills/.system/imagegen/scripts/remove_chroma_key.py'
RAW, TPL, WORK, OUT = HERE / 'raw', HERE / 'template', HERE / 'work', HERE / 'out'
DIRS = ('south', 'north')
FW, FH = 48 * BODY_S, 64 * BODY_S          # 칸 안 프레임 크기(템플릿 픽셀)
HD = 2                                       # 그림 밀도
HEAD_SCALE = 1.08                            # v2 캐릭터와 머리 크기 맞춤(실측 폭 50 vs 45~48 HD px)
K = BODY_S // HD                             # 템플릿 3px = HD 1px


def load(name, size=(1536, 1024)):
    src = RAW / f'{name}.png'
    im = Image.open(src).convert('RGBA')
    if np.asarray(im)[..., 3].min() == 255:
        out = WORK / f'{name}.keyed.png'
        subprocess.run([sys.executable, str(CHROMA), '--input', str(src), '--out', str(out), '--auto-key', 'border', '--despill', '--force'],
                       check=True, capture_output=True)
        im = Image.open(out).convert('RGBA')
    if im.size != size:
        im = im.resize(size, Image.LANCZOS)
    a = np.asarray(im).copy()
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    return a


def iou(a, b):
    return (a & b).sum() / max((a | b).sum(), 1)


def shift(a, dx, dy):
    out = np.zeros_like(a)
    h, w = a.shape[:2]
    ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
    xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
    out[yd, xd] = a[ys, xs]
    return out


def register_sheet(a, target, scales=np.arange(.90, 1.101, .01)):
    """시트 전체: 배율 + 이동(IoU 최대)."""
    H, W = target.shape
    best = (-1, None)
    im = Image.fromarray(a)
    for sc in scales:
        r = np.asarray(im.resize((round(W * sc), round(H * sc)), Image.NEAREST))
        m = r[..., 3] > 0
        corr = fftconvolve(target.astype(float), m[::-1, ::-1].astype(float), mode='full')
        py, px = np.unravel_index(np.argmax(corr), corr.shape)
        dy, dx = int(py - (m.shape[0] - 1)), int(px - (m.shape[1] - 1))
        canvas = np.zeros((H, W, 4), np.uint8)
        y0, x0 = max(dy, 0), max(dx, 0)
        y1, x1 = min(dy + r.shape[0], H), min(dx + r.shape[1], W)
        canvas[y0:y1, x0:x1] = r[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
        v = iou(canvas[..., 3] > 0, target)
        if v > best[0]:
            best = (v, canvas, {'scale': round(float(sc), 2), 'dx': dx, 'dy': dy})
    return best[1], best[2], best[0]


def cell_boxes():
    """칸마다 이웃과 겹치지 않는 영역(프레임 원점 기준 ±여백)."""
    out = []
    for k in range(len(FRAMES)):
        fx, fy = frame_origin(k)
        out.append((fx - 9, fy - 60, fx + FW + 9, fy + FH + 60))
    return out


def register_cells(a, target, r=24):
    """칸마다 이동만 다시 맞춘다(시트 전체 정합 뒤 남은 개별 어긋남)."""
    out = np.zeros_like(a)
    moves = []
    for (x0, y0, x1, y1) in cell_boxes():
        y0, x0 = max(y0, 0), max(x0, 0)
        cell, tm = a[y0:y1, x0:x1], target[y0:y1, x0:x1]
        best = (-1, 0, 0)
        for dy in range(-r, r + 1, 2):
            for dx in range(-r, r + 1, 2):
                v = iou(shift(cell, dx, dy)[..., 3] > 0, tm)
                if v > best[0]:
                    best = (v, dx, dy)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], shift(cell, best[1], best[2]))
        moves.append([best[1], best[2], round(float(best[0]), 3)])
    return out, moves


def keep_figures(a, min_frac=.01):
    m = a[..., 3] > 0
    lab, n = ndimage.label(m)
    if n:
        sz = ndimage.sum(m, lab, range(1, n + 1))
        a = a.copy()
        a[..., 3] = np.where(np.isin(lab, [i + 1 for i in range(n) if sz[i] >= sz.max() * min_frac]), 255, 0)
    return a


def stage_base():
    rep = {}
    for d in DIRS:
        target = np.asarray(Image.open(TPL / f'body_{d}.png'))[..., 3] > 0
        a = keep_figures(load(f'base_{d}'))
        a, reg, v0 = register_sheet(a, target)
        a, moves = register_cells(a, target)
        Image.fromarray(a).save(WORK / f'base_{d}.png')
        rep[f'base_{d}'] = {'sheet': reg, 'iou_sheet': round(float(v0), 3), 'cells': moves,
                            'iou_cells_min': min(m[2] for m in moves)}
    return rep


# ---------- 레이어 ----------
UPPER = ('torso', 'arm', 'fore')            # 상의가 덮는 마네킹 파트(손은 팔 끝이라 함께 온다: 옷 시트에서도 기본 몸 그대로)
LOWER = ('leg', 'thigh', 'shin')


def nearest_part(d):
    """각 픽셀에서 가장 가까운 마네킹 파트 이름(템플릿 좌표). AI 실루엣이 몇 px 어긋나도 영역이 따라간다."""
    meta = json.loads((TPL / f'body_{d}.json').read_text())
    pm = np.asarray(Image.open(TPL / f'body_{d}.parts.png')).astype(int)
    names = {int(i): n for f in meta['frames'] for i, n in f['parts'].items()}
    _, (iy, ix) = ndimage.distance_transform_edt(pm == 0, return_indices=True)
    ids = pm[iy, ix]
    kind = np.zeros(pm.shape, np.uint8)  # 0 기타(머리), 1 상체, 2 하체
    for i, n in names.items():
        kind[ids == i] = 1 if n.startswith(UPPER) else 2 if n.startswith(LOWER) else 0
    return kind


def head_zone(d, grow=6):
    meta = json.loads((TPL / f'body_{d}.json').read_text())
    pm = np.asarray(Image.open(TPL / f'body_{d}.parts.png')).astype(int)
    ids = [int(i) for f in meta['frames'] for i, n in f['parts'].items() if n in ('head', 'face')]
    return ndimage.binary_dilation(np.isin(pm, ids), iterations=grow)


def below_heads(d):
    """칸마다 머리 중심보다 아래만 True(옷은 목 위로 뻗지 않는다)."""
    meta = json.loads((TPL / f'body_{d}.json').read_text())
    pm = np.asarray(Image.open(TPL / f'body_{d}.parts.png'))
    out = np.zeros(pm.shape, bool)
    for (x0, y0, x1, y1), f in zip(cell_boxes(), meta['frames']):
        out[int(f['head']['cy']):y1, max(x0, 0):x1] = True
    return out


def stage_layers():
    rep = {}
    for d in DIRS:
        base = np.asarray(Image.open(WORK / f'base_{d}.png'))
        bm = base[..., 3] > 0
        kind = nearest_part(d)
        for name in sorted(p.stem for p in RAW.glob(f'*_{d}.png') if p.stem.startswith(('top-', 'bottom-'))):
            part = name.split('-')[0]
            a = keep_figures(load(name))
            a, reg, v0 = register_sheet(a, bm)
            a, moves = register_cells(a, bm, r=12)
            m = a[..., 3] > 0
            # 경계 어긋남을 줄이려 둘 다 살짝 흐린 뒤 비교(안 바뀐 곳 중앙값 12~15, 가디건-회색 셔츠 차이 중앙값 52)
            sm = lambda x: ndimage.median_filter(x[..., :3].astype(int), size=(5, 5, 1))
            diff = np.abs(sm(a) - sm(base)).sum(-1)
            own = 1 if part == 'top' else 2
            # 내 영역: 조금만 바뀌어도 옷. 남의 영역·몸 밖: 크게 바뀌고(긴 밑단·치마) 내 영역의 옷과 이어진 덩어리만
            # 옷 색 모델: 확실히 바뀐 픽셀(차 > 80)로 옷 팔레트(16색)를 만들고, 내 영역의 픽셀이 그 자리 기본 몸 색보다
            # 옷 팔레트에 더 가까우면 옷(라벤더-회색처럼 차이가 작은 색도 잡힌다)
            strong = m & (kind == own) & (diff > 80)
            mine = m & (kind == own) & (diff > 30)
            if strong.sum() > 50:
                q = Image.fromarray(a[..., :3][strong].reshape(-1, 1, 3).astype(np.uint8)).quantize(16, method=Image.Quantize.MEDIANCUT)
                pal = np.array(q.getpalette()[:48]).reshape(-1, 3)
                ys, xs = np.nonzero(m & (kind == own))
                px = a[ys, xs, :3].astype(int)
                dG = np.abs(px[:, None, :] - pal[None]).sum(-1).min(1)
                dB = np.abs(px - base[ys, xs, :3].astype(int)).sum(-1)
                mine[ys, xs] |= dG * 1.2 < dB
            extra = m & (kind != 0) & (((kind != own) & (diff > 110)) | ~bm) & below_heads(d)
            changed = ndimage.binary_opening(mine | extra, iterations=2)
            lab, n = ndimage.label(changed)
            if n:
                sz = ndimage.sum(changed, lab, range(1, n + 1))
                core = ndimage.binary_opening(mine, iterations=2)
                touch = set(np.unique(lab[core])) - {0}
                changed = np.isin(lab, [i + 1 for i in range(n) if sz[i] >= 150 and (i + 1) in touch])
            take = ndimage.binary_fill_holes(changed) & m
            # 옷에 붙은 어두운 외곽선(기본 몸과 같은 색이라 차이로는 안 잡힘)
            lum = a[..., :3].astype(float) @ [.299, .587, .114]
            take |= ndimage.binary_dilation(take, iterations=4) & m & (lum < 95) & ((kind == own) | ~bm)
            take &= ~(head_zone(d) & ~changed)  # 민머리 턱 외곽선이 옷 레이어에 섞이지 않게
            layer = a.copy()
            layer[..., 3] = np.where(take, 255, 0)
            Image.fromarray(layer).save(WORK / f'{name}.png')
            rep[name] = {'sheet': reg, 'iou_sheet': round(float(v0), 3), 'iou_cells_min': min(x[2] for x in moves),
                         'layer_px': int(take.sum()), 'outside_base_px': int((take & ~bm).sum())}
    # 머리: 칸마다 구 중심 기준으로 잘라 낸다(머리카락 여유 1.45배)
    meta = json.loads((TPL / 'heads.json').read_text())
    target = np.asarray(Image.open(TPL / 'heads.png'))[..., 3] > 0
    a = keep_figures(load('heads'), min_frac=.05)
    a, reg, v0 = register_sheet(a, target)
    rep['heads'] = {'sheet': reg, 'iou_sheet': round(float(v0), 3)}
    for c in meta['cells']:
        cx, cy = c['center']
        R = int(c['radius_px'] * 1.45)
        x0, y0 = int(cx - R), int(cy - R)
        crop = a[max(y0, 0):int(cy + R), max(x0, 0):int(cx + R)].copy()
        crop = keep_figures(crop, min_frac=.2)
        Image.fromarray(crop).save(WORK / f"head_{c['style']}_{c['direction']}.png")
    return rep


# ---------- 합성 ----------
def head_sprite(style, d):
    """머리 스프라이트를 몸 배율로(12배 → 6배) 줄이고, 턱(뒷모습은 목덜미)이 구 아랫면에 닿도록 내릴 양(px, 몸 배율)도 반환.
    턱 = 폭이 최대 폭의 50% 이상인 마지막 줄(늘어진 포니테일·머리카락 끝은 제외). 치비는 목이 보이지 않아 턱이 옷깃에 바로 닿는다."""
    im = Image.open(WORK / f'head_{style}_{d}.png')
    a = np.asarray(im)[..., 3] > 0
    widths = a.sum(1)
    chin = int(np.nonzero(widths >= widths.max() * .5)[0].max()) - im.height // 2
    cell = [c for c in json.loads((TPL / 'heads.json').read_text())['cells'] if c['style'] == style and c['direction'] == d][0]
    t = np.asarray(Image.open(TPL / 'heads.png'))[..., 3] > 0
    cx, cy = map(int, cell['center'])
    col = t[:, cx - 40:cx + 40].any(1)
    sphere_bottom = int(np.nonzero(col[cy:cy + 300])[0].max())  # 템플릿에서 잰 구 아랫면(중심 기준)
    s0 = BODY_S / HEAD_S          # 머리 시트 → 몸 시트 배율
    s = s0 * HEAD_SCALE           # 머리만 조금 크게(중심 기준)
    return im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS), max(0.0, sphere_bottom * s0 - chin * s)


def compose(d, top, bottom, style):
    meta = json.loads((TPL / f'body_{d}.json').read_text())
    sheet = Image.open(WORK / f'base_{d}.png').copy()
    for layer in (f'bottom-{bottom}_{d}', f'top-{top}_{d}'):
        if (WORK / f'{layer}.png').exists():
            sheet.alpha_composite(Image.open(WORK / f'{layer}.png'))
    # 기본 몸의 민머리를 지운다(머리 스프라이트 밖으로 외곽선이 고리처럼 비치지 않게). 가장 가까운 파트가 머리인 픽셀
    arr = np.asarray(sheet).copy()
    arr[nearest_part(d) == 0, 3] = 0
    sheet = Image.fromarray(arr)
    hs, drop = head_sprite(style, d)
    a = np.asarray(hs).copy(); a[..., 3] = np.where(a[..., 3] >= 128, 255, 0); hs = Image.fromarray(a)
    frames = []
    for k, f in enumerate(meta['frames']):
        h = f['head']
        sheet.alpha_composite(hs, (round(h['cx'] - hs.width / 2), round(h['cy'] - hs.height / 2 + drop)))
    for k, f in enumerate(meta['frames']):
        fx, fy = f['origin']
        cell = sheet.crop((fx, fy, fx + FW, fy + FH))
        frames.append(pixelize(cell, 48 * HD, 64 * HD, 48))
    return frames


def stage_combos():
    OUT.mkdir(exist_ok=True)
    combos = [(t, b, s) for s in (0, 1) for t in ('cardigan', 'hoodie') for b in ('chino', 'skirt')]
    for d in DIRS:
        rows = []
        for t, b, s in combos:
            fr = compose(d, t, b, s)
            for k, im in enumerate(fr):
                im.save(OUT / f'{t}_{b}_h{s}_{d}_{k}.png')
            rows.append(fr)
        # 한눈에 보기: 줄 = 조합, 칸 = 10프레임, 2배 확대
        Z = 2
        sheet = Image.new('RGBA', (10 * 96 * Z + 9 * 8, len(rows) * 128 * Z + (len(rows) - 1) * 8), (200, 180, 160, 255))
        for r, fr in enumerate(rows):
            for k, im in enumerate(fr):
                sheet.alpha_composite(im.resize((96 * Z, 128 * Z), Image.NEAREST), (k * (96 * Z + 8), r * (128 * Z + 8)))
        sheet.save(OUT / f'combos_{d}.png')
    return {'combos': len(combos)}


# ---------- 실행 중 겹치기용 내보내기 ----------
EXPORT = HERE / 'export'
STATES = {'idle': [0, 1], 'walking': [2, 3, 4, 5], 'sitting': [6, 7], 'typing': [8, 9]}
LABELS = json.loads((HERE / 'spec.json').read_text())['labels']  # 화면 이름: make_spec.py의 TOPS/BOTTOMS/HAIR


def to_hd(im, w, h, cut=110, colors=48):
    """원본(템플릿 해상도) → HD: 3×3 평균(알파 곱) 후 알파 이진화. 옷 레이어는 cut을 낮춰 레이어 경계 틈을 막는다."""
    a = np.asarray(im).astype(np.float32)
    al = a[..., 3:4] / 255
    pre = Image.fromarray(np.concatenate([a[..., :3] * al, a[..., 3:4]], -1).astype(np.uint8)).resize((w, h), Image.BOX)
    b = np.asarray(pre).astype(np.float32)
    ba = b[..., 3:4] / 255
    rgb = np.where(ba > 0, b[..., :3] / np.maximum(ba, 1e-6), 0).clip(0, 255).astype(np.uint8)
    q = np.asarray(Image.fromarray(rgb).quantize(colors, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).convert('RGB'))
    return Image.fromarray(np.dstack([q, np.where(b[..., 3] >= cut, 255, 0).astype(np.uint8)]))


def stage_export():
    EXPORT.mkdir(exist_ok=True)
    for old in EXPORT.glob('*.png'):
        old.unlink()
    meta_out = {'frame': [48 * HD, 64 * HD], 'states': STATES, 'labels': LABELS, 'head': {}, 'anchors': {}}
    tops = sorted({p.stem.split('_')[0][4:] for p in WORK.glob('top-*_south.png')})
    bottoms = sorted({p.stem.split('_')[0][7:] for p in WORK.glob('bottom-*_south.png')})
    meta_out.update(tops=tops, bottoms=bottoms, hair=sorted(LABELS['hair']))
    for d in DIRS:
        meta = json.loads((TPL / f'body_{d}.json').read_text())
        base = np.asarray(Image.open(WORK / f'base_{d}.png')).copy()
        base[nearest_part(d) == 0, 3] = 0                      # 민머리 제거(머리 스프라이트가 덮는다)
        sheets = {'base': Image.fromarray(base)}
        def solid(path):
            # 레이어 안의 작은 구멍(아래 기본 셔츠가 비치는 점)을 메운다. 메운 픽셀 색은 옷 시트 자체 색(레이어는 알파만 깎은 시트)
            a = np.asarray(Image.open(path)).copy()
            m = a[..., 3] > 0
            m = ndimage.binary_fill_holes(ndimage.binary_closing(m, iterations=2)) | m
            a[..., 3] = np.where(m, 255, 0)
            return Image.fromarray(a)
        for t in tops:
            sheets[f'top-{t}'] = solid(WORK / f'top-{t}_{d}.png')
        for b in bottoms:
            sheets[f'bottom-{b}'] = solid(WORK / f'bottom-{b}_{d}.png')
        for name, sh in sheets.items():
            for k, f in enumerate(meta['frames']):
                fx, fy = f['origin']
                cell = sh.crop((fx, fy, fx + FW, fy + FH))
                to_hd(cell, 48 * HD, 64 * HD, cut=110 if name == 'base' else 70).save(EXPORT / f'{name}_{d}_{k}.png')
        anchors = {}
        for st in meta_out['hair']:
            hs, drop = head_sprite(int(st), d)
            a = np.asarray(hs).copy(); a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
            w, h = round(hs.width / K), round(hs.height / K)
            hd = np.asarray(to_hd(Image.fromarray(a), w, h)).copy()
            # 바깥 1px 테두리를 외곽선 색 하나로: AI 원본의 반투명 가장자리가 보라·자주 중간색 후광으로 남는 것을 막는다
            al = hd[..., 3] > 0
            ring = al & ~ndimage.binary_erosion(al)
            px = hd[ring][:, :3].astype(int)
            dark = px[px @ [.299, .587, .114] < 80]
            if len(dark):
                vals, cnt = np.unique(dark, axis=0, return_counts=True)
                hd[ring, :3] = vals[cnt.argmax()]
            Image.fromarray(hd).save(EXPORT / f'hair-{st}_{d}.png')
            # 머리 스프라이트 중심의 프레임 안 위치(HD px)
            anchors[st] = [[round((f['head']['cx'] - f['origin'][0]) / K, 2), round((f['head']['cy'] + drop - f['origin'][1]) / K, 2)] for f in meta['frames']]
        meta_out['anchors'][d] = anchors
    (EXPORT / 'parts.json').write_text(json.dumps(meta_out, indent=1, ensure_ascii=False))
    # 검증: 게임처럼 HD에서 최근접으로 겹친 결과 시트
    rows = []
    for t, b, st in [(t, b, s) for s in ('0', '1') for t in tops for b in bottoms]:
        fr = []
        for k in range(10):
            im = Image.open(EXPORT / f'base_south_{k}.png').copy()
            im.alpha_composite(Image.open(EXPORT / f'bottom-{b}_south_{k}.png'))
            im.alpha_composite(Image.open(EXPORT / f'top-{t}_south_{k}.png'))
            hd = Image.open(EXPORT / f'hair-{st}_south.png')
            cx, cy = meta_out['anchors']['south'][st][k]
            im.alpha_composite(hd, (round(cx - hd.width / 2), round(cy - hd.height / 2)))
            fr.append(im)
        rows.append(fr)
    Z = 2
    sheet = Image.new('RGBA', (10 * 96 * Z + 72, len(rows) * 128 * Z + (len(rows) - 1) * 8), (200, 180, 160, 255))
    for r, fr in enumerate(rows):
        for k, im in enumerate(fr):
            sheet.alpha_composite(im.resize((96 * Z, 128 * Z), Image.NEAREST), (k * (96 * Z + 8), r * (128 * Z + 8)))
    sheet.save(EXPORT / 'runtime_preview_south.png')
    return {'export': {'tops': tops, 'bottoms': bottoms, 'files': len(list(EXPORT.glob('*.png')))}}


if __name__ == '__main__':
    WORK.mkdir(exist_ok=True)
    stage = sys.argv[1]
    rep = {'base': stage_base, 'layers': stage_layers, 'combos': stage_combos, 'export': stage_export}[stage]()
    q = HERE / 'qa.json'
    old = json.loads(q.read_text()) if q.exists() else {}
    old.update(rep)
    q.write_text(json.dumps(old, indent=1, ensure_ascii=False))
    print(json.dumps(rep, ensure_ascii=False)[:1500])
