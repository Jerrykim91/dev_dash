#!/usr/bin/env python3
"""파트 분리 시험(docs/visual-standard-v2.md §15): 잠긴 지오메트리 템플릿 시트 만들기 (sow 방식).

몸 시트(방향별 1장, 1536×1024, 5×2칸, 마네킹 6배):
  칸 순서 = idle0 idle1 walk0 walk1 walk2 / walk3 sitidle0 sitidle1 sittype0 sittype1
  프레임(월드 48×64) 원점은 3의 배수 → 6배 원본 3px = HD(2배 밀도) 1px 격자에 정확히 맞는다.
머리 시트(1장, 1536×1024, 4×2칸, 머리 구 12배): 칸 (열, 줄) = 스타일 (줄*2 + 열//2), 방향 = 열%2 (0 앞, 1 뒤).
출력 template/: <name>.png(가이드), <name>.parts.png(파트 id), <name>.json(칸·발·머리 중심·파트 이름)
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'v2'))
import blockout as B  # noqa: E402

OUT = HERE / 'template'
BODY_S, HEAD_S = 6, 12
CANVAS = (1536, 1024)
FRAMES = [('idle', 0), ('idle', 1), ('walk', 0), ('walk', 1), ('walk', 2),
          ('walk', 3), ('sit.idle', 0), ('sit.idle', 1), ('sit.type', 0), ('sit.type', 1)]
CELL_W, CELL_H, X0, Y0 = 306, 510, 12, 66   # 원점 (12 + 306c, 66 + 510r): 모두 3의 배수


def frame_origin(k):
    c, r = k % 5, k // 5
    return X0 + c * CELL_W, Y0 + r * CELL_H


def body(direction):
    img, pm, fm, d, dm, df = B._canvas(CANVAS)
    clips = {name: B.CLIPS[name](direction) for name in ('idle', 'walk', 'sit.idle', 'sit.type')}
    B._S = BODY_S
    meta = {'kind': 'body', 'direction': direction, 'scale': BODY_S, 'cell': [48, 64], 'foot': [24, 58], 'frames': []}
    try:
        for k, (clip, i) in enumerate(FRAMES):
            parts = clips[clip][i]
            fx, fy = frame_origin(k)
            foot = (fx + 24 * BODY_S, fy + 58 * BODY_S)
            B.draw_parts(d, dm, df, parts, foot[0], foot[1] - 16 * BODY_S, id_base=k * 20)
            names = {k * 20 + j + 1: p[0] for j, p in enumerate(parts)}
            meta['frames'].append({'clip': clip, 'i': i, 'origin': [fx, fy], 'foot': list(foot), 'parts': names})
    finally:
        B._S = B.S
    # 머리 중심·반지름: 파트 마스크의 head 영역에서 측정(투영 수식 대신 실제 그림 기준)
    pa = np.asarray(pm)
    for f in meta['frames']:
        hid = [i for i, n in f['parts'].items() if n == 'head'][0]
        ys, xs = np.nonzero(pa == hid)
        f['head'] = {'cx': float((xs.min() + xs.max() + 1) / 2), 'cy': float((ys.min() + ys.max() + 1) / 2),
                     'w': int(xs.max() - xs.min() + 1), 'h': int(ys.max() - ys.min() + 1)}
    return img, pm, meta


def heads():
    """머리만(구 + 얼굴 방향 표시). 칸 가운데에 머리 중심."""
    img, pm, fm, d, dm, df = B._canvas(CANVAS)
    B._S = HEAD_S
    meta = {'kind': 'head', 'scale': HEAD_S, 'cells': []}
    cw, ch = CANVAS[0] // 4, CANVAS[1] // 2
    try:
        for row in range(2):
            for col in range(4):
                direction = 'south' if col % 2 == 0 else 'north'
                parts = [p for p in B.facing(B.mannequin_stand(), direction) if p[0] in ('head', 'face')]
                cx, cy, cz, r = parts[0][3][1:]
                # 머리 중심이 칸 가운데에 오도록 투영 원점 계산
                hx, hy = B.proj(cx, cy, cz, 0, 0)
                ox, oy = col * cw + cw / 2 - hx, row * ch + ch / 2 - hy
                B.draw_parts(d, dm, df, parts, ox, oy, id_base=(row * 4 + col) * 4)
                meta['cells'].append({'style': row * 2 + col // 2, 'direction': direction,
                                      'center': [col * cw + cw / 2, row * ch + ch / 2], 'radius_px': r * B.PX_PER_M * HEAD_S})
    finally:
        B._S = B.S
    return img, pm, meta


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    for direction in ('south', 'north'):
        img, pm, meta = body(direction)
        img.save(OUT / f'body_{direction}.png'); Image.fromarray(np.asarray(pm).astype(np.uint8), 'L').save(OUT / f'body_{direction}.parts.png')  # P를 팔레트 없이 저장하면 번호가 뭉개진다
        (OUT / f'body_{direction}.json').write_text(json.dumps(meta, indent=1))
    img, pm, meta = heads()
    img.save(OUT / 'heads.png'); Image.fromarray(np.asarray(pm).astype(np.uint8), 'L').save(OUT / 'heads.parts.png')
    (OUT / 'heads.json').write_text(json.dumps(meta, indent=1))
    print('ok')
