#!/usr/bin/env python3
"""raw/<id>.png(AI 생성 원본)를 template.json 규격 프레임으로 정규화해 norm/에 저장한다.

- prop      : 128x160, 앵커(64,104), footprint 바닥 꼭짓점 정렬. <id>.png(0도) + <id>_m.png(좌우 반전 = 90도)
- texture   : floor → 64x32 마름모 투영, wall → wall_x/wall_y 128x160 벽면 투영
- character : 48x64, 발(24,58). south/north 생성 + east/west 반전
검수용으로 norm/_qa/<id>.png(4배 확대 + footprint 표시)를 함께 만든다.
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / 'assets.json').read_text())
CHROMA = Path.home() / '.codex/skills/.system/imagegen/scripts/remove_chroma_key.py'
RAW, NORM, QA = HERE / 'raw', HERE / 'norm', HERE / 'norm' / '_qa'
INK = (58, 44, 70, 255)

# 소품이 footprint 마름모 너비 대비 차지하는 비율(시각적 크기). 없으면 0.9
FILL = {'desk': .98, 'sofa': .95, 'coffee': .96, 'whiteboard': .92, 'rug': 1.0, 'chair': .62, 'plant': .62,
        'bookshelf': .8, 'lamp': .42, 'table': .62, 'arcade': .74, 'catbed': .7, 'server': .72}
FLAT = {'rug'}  # 바닥에 붙는 평면 소품: bbox 중심을 footprint 중심에 맞춤


def load_rgba(a):
    src = RAW / f"{a['id']}.png"
    im = Image.open(src).convert('RGBA')
    if np.asarray(im)[..., 3].min() == 255:  # 투명 실패 → 크로마키 제거
        keyed = RAW / f"{a['id']}.keyed.png"
        subprocess.run([sys.executable, str(CHROMA), '--input', str(src), '--out', str(keyed), '--auto-key', 'border',
                        '--despill', '--force'], check=True, capture_output=True)
        im = Image.open(keyed).convert('RGBA')
    return im


def clean_alpha(im, keep=1):
    """알파 이진화 + 가장 큰 덩어리 keep개만 남긴다."""
    a = np.asarray(im).copy()
    mask = a[..., 3] >= 128
    lab, n = ndimage.label(mask)
    if n:
        sizes = ndimage.sum(mask, lab, range(1, n + 1))
        order = np.argsort(sizes)[::-1]
        big = sizes[order[0]]
        allowed = [i + 1 for i in order[:keep]] + [i + 1 for i in order[keep:] if sizes[i] > big * .02]
        mask = np.isin(lab, allowed)
    a[..., 3] = np.where(mask, 255, 0)
    return Image.fromarray(a), lab, mask


def pixelize(im, w, h, colors=48):
    """BOX 축소 → 알파 이진화 → 팔레트 축소(디더링 없음)."""
    arr = np.asarray(im).astype(np.float32)
    alpha = arr[..., 3:4] / 255
    pre = Image.fromarray(np.concatenate([arr[..., :3] * alpha, arr[..., 3:4]], -1).astype(np.uint8))
    small = np.asarray(pre.resize((w, h), Image.BOX)).astype(np.float32)
    a = small[..., 3:4] / 255
    rgb = np.where(a > 0, small[..., :3] / np.maximum(a, 1e-6), 0).clip(0, 255)
    mask = small[..., 3] >= 110
    rgb_im = Image.fromarray(rgb.astype(np.uint8)).quantize(colors, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).convert("RGB")
    out = np.dstack([np.asarray(rgb_im), np.where(mask, 255, 0).astype(np.uint8)])
    return Image.fromarray(out)


def bbox(im):
    return im.getchannel('A').getbbox()


def footprint(w, h):
    return [(64, 88), (64 + 32 * w, 88 + 16 * w), (64 + 32 * (w - h), 88 + 16 * (w + h)), (64 - 32 * h, 88 + 16 * h)]


def qa(img, name, poly=None, anchor=None, scale=4):
    big = Image.new('RGBA', img.size, (40, 32, 52, 255))
    big.alpha_composite(img)
    big = big.resize((img.width * scale, img.height * scale), Image.NEAREST)
    d = ImageDraw.Draw(big)
    if poly:
        d.polygon([(x * scale, y * scale) for x, y in poly], outline=(255, 80, 80, 255))
    if anchor:
        x, y = anchor
        d.ellipse([x * scale - 4, y * scale - 4, x * scale + 4, y * scale + 4], outline=(80, 255, 120, 255), width=2)
    big.save(QA / f'{name}.png')


def do_prop(a):
    w, h = a['fp']
    im, _, _ = clean_alpha(load_rgba(a))
    im = im.crop(bbox(im))
    if a.get('flip'):  # 생성 방향이 규칙과 반대면 좌우 반전으로 보정
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    fp = footprint(w, h)
    target_w = round((w + h) * 32 * FILL.get(a['id'], .9))
    tw, th = target_w, max(1, round(im.height * target_w / im.width))
    bottom = fp[2][1]
    if a['id'] in FLAT:  # 평면 소품은 footprint 마름모에 내접하는 2:1 타원으로 비율 고정
        tw, th = round((w + h) * 32 * .92), round((w + h) * 16 * .92)
    elif a['id'] not in FLAT and th > bottom - 2:  # 프레임 위로 넘치면 높이 기준으로 축소
        th = bottom - 2
        tw = round(im.width * th / im.height)
    sp = pixelize(im, tw, th)
    sb = bbox(sp)
    sp = sp.crop(sb)
    cx = 64 + 16 * (w - h)
    frame = Image.new('RGBA', (128, 160), (0, 0, 0, 0))
    if a['id'] in FLAT:
        cy = 88 + 8 * (w + h)
        pos = (round(cx - sp.width / 2), round(cy - sp.height / 2))
    else:
        pos = (round(cx - sp.width / 2), bottom - sp.height + 1)
    frame.alpha_composite(sp, (max(0, pos[0]), max(0, pos[1])))
    frame.save(NORM / f"{a['id']}.png")
    frame.transpose(Image.FLIP_LEFT_RIGHT).save(NORM / f"{a['id']}_m.png")
    qa(frame, a['id'], fp, (64, 104))
    clipped = pos[0] < 0 or pos[1] < 0 or pos[0] + sp.width > 128
    return f"{sp.width}x{sp.height} @ {pos}{' CLIPPED' if clipped else ''}"


def texel(a, size):
    im = Image.open(RAW / f"{a['id']}.png").convert('RGB')
    return np.asarray(im.resize(size, Image.BOX).quantize(16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB'))


def do_floor(a):
    tex = texel(a, (32, 32))
    out = np.zeros((32, 64, 4), np.uint8)
    for py in range(32):
        for px in range(64):
            dx, dy = (px + .5 - 32) / 32, (py + .5 - 16) / 16
            if abs(dx) + abs(dy) > 1.0001:
                continue
            gx, gy = (dx + dy) / 2 + .5, (dy - dx) / 2 + .5  # toGrid 역변환
            u, v = min(31, int(gx * 32)), min(31, int(gy * 32))
            out[py, px, :3] = tex[v, u]
            out[py, px, 3] = 255
    img = Image.fromarray(out)
    img.save(NORM / f"{a['id']}.png")
    tile = Image.new('RGBA', (64 * 4, 32 * 4), (40, 32, 52, 255))  # 반복 확인용 4x4
    for gy in range(4):
        for gx in range(4):
            tile.alpha_composite(img, ((gx - gy) * 32 + 96, (gx + gy) * 16))
    qa(tile, a['id'], scale=3)
    return '64x32 diamond'


def do_wall(a):
    H = 80
    src = Image.open(RAW / f"{a['id']}.png").convert('RGB')
    W = round(src.width * H / src.height)
    strip = np.asarray(src.resize((W, H), Image.BOX).quantize(24, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB'))
    c0 = (W - 32) // 2  # 가운데 열(창문이 있으면 창문 중심)

    def face(c, axis):
        x0, y0, slope, shade = (32, 104, -.5, 1.0) if axis == 'x' else (64, 88, .5, .9)
        out = np.zeros((160, 128, 4), np.uint8)
        for u in range(32):
            base = y0 + int(np.floor(u * slope)) if slope > 0 else y0 - int(np.ceil(u * .5))
            for v in range(H):
                y = base - H + v
                if 0 <= y < 160:
                    out[y, x0 + u, :3] = (strip[v, c + u] * shade).clip(0, 255)
                    out[y, x0 + u, 3] = 255
        return Image.fromarray(out)

    # _x/_y = 단일 칸(가운데 열). _x0~2/_y0~2 = 연속 3칸 세그먼트(긴 창문용).
    # 텍스처 왼쪽→오른쪽 순서: wall/y는 tx 증가 방향, wall/x는 ty 감소 방향과 같다.
    for axis in 'xy':
        face(c0, axis).save(NORM / f"{a['id']}_{axis}.png")
        for k in range(3):
            face(c0 + (k - 1) * 32, axis).save(NORM / f"{a['id']}_{axis}{k}.png")
    pair = Image.new('RGBA', (224, 208), (0, 0, 0, 0))
    for k in range(3):  # wall/y 3칸을 실제 배치처럼 이어 붙여 검수
        pair.alpha_composite(Image.open(NORM / f"{a['id']}_y{k}.png"), (k * 32, k * 16))
    qa(pair, a['id'], scale=3)
    return f'strip {W}x{H}, x/y faces + 3 segments'


def do_character(a):
    im, lab, mask = clean_alpha(load_rgba(a), keep=2)
    objs = sorted(ndimage.find_objects(ndimage.label(mask)[0]), key=lambda s: s[1].start)
    objs = sorted(objs, key=lambda s: (s[0].stop - s[0].start) * (s[1].stop - s[1].start), reverse=True)[:2]
    objs.sort(key=lambda s: s[1].start)
    out = {}
    for name, sl in zip(('south', 'north'), objs):
        crop = im.crop((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
        th = 54
        tw = max(1, round(crop.width * th / crop.height))
        sp = pixelize(crop, tw, th, colors=24)
        sp = sp.crop(bbox(sp))
        fr = Image.new('RGBA', (48, 64), (0, 0, 0, 0))
        fr.alpha_composite(sp, (round(24 - sp.width / 2), 58 - sp.height + 1))
        out[name] = fr
    out['east'] = out['south'].transpose(Image.FLIP_LEFT_RIGHT)
    out['west'] = out['north'].transpose(Image.FLIP_LEFT_RIGHT)
    sheet = Image.new('RGBA', (48 * 4, 64), (0, 0, 0, 0))
    for i, d in enumerate(('south', 'east', 'north', 'west')):
        out[d].save(NORM / f"{a['id']}_{d}.png")
        sheet.alpha_composite(out[d], (48 * i, 0))
    qa(sheet, a['id'], scale=4)
    return '48x64 x4 dirs'


def main():
    NORM.mkdir(exist_ok=True)
    QA.mkdir(exist_ok=True)
    ids = sys.argv[1:]
    for a in CFG['assets']:
        if ids and a['id'] not in ids:
            continue
        if not (RAW / f"{a['id']}.png").exists():
            print(f"{a['id']:12s} (raw 없음)")
            continue
        fn = {'prop': do_prop, 'character': do_character}.get(a['type']) or (do_floor if a['kind'] == 'floor' else do_wall)
        print(f"{a['id']:12s} {fn(a)}")


if __name__ == '__main__':
    main()
