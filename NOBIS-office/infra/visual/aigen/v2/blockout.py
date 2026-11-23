#!/usr/bin/env python3
"""표준 v2 블록아웃 라이브러리: 미터 치수 → 정확한 2:1 투영 가이드 + 파트/면 마스크.

출력(blockout/):
  <id>.png        생성 가이드 (위쪽 광원: 윗면 밝게, 측면 2개 같은 톤)
  <id>.parts.png  파트 인덱스 마스크(P 모드, 0=배경)
  <id>.faces.png  면 마스크(1=윗면, 2=+y면(좌하), 3=+x면(우하)) → 측면 대칭 QA
  <id>.json       앵커·배율·파트(이름, 레이어)·프레임 메타
가구: 캔버스 1024², 원점 타일 중심(0.5,0.5,0) → (512, 640).
캐릭터 스트립: 프레임(48x64)마다 셀 384x512, 발(24,58) → 셀 내 (192,464).
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
from standard import GEN_SCALE as S, SHADE, PX_PER_M

OUT = Path(__file__).resolve().parent / 'blockout'
OUTLINE = (60, 50, 70, 255)


# ---------- 투영·정렬 ----------
_S = S  # 현재 렌더 배율(큰 가구는 낮춤)


def proj(x, y, z, ox, oy):
    return (ox + (x - y) * 32 * _S, oy + ((x + y) * 16 - z * PX_PER_M) * _S)


def depth_order(parts, eps=1e-6):
    """아이소 박스 위상 정렬: 어느 축에서든 A.max <= B.min 이면 A가 뒤."""
    behind = lambda a, b: a[2][3] <= b[2][0] + eps or a[2][4] <= b[2][1] + eps or a[2][5] <= b[2][2] + eps
    n = len(parts)
    edges = {i: {j for j in range(n) if j != i and behind(parts[i], parts[j]) and not behind(parts[j], parts[i])} for i in range(n)}
    indeg = {i: 0 for i in range(n)}
    for i in edges:
        for j in edges[i]:
            indeg[j] += 1
    ready, out = sorted(i for i in range(n) if indeg[i] == 0), []
    while ready:
        i = ready.pop(0)
        out.append(i)
        for j in sorted(edges[i]):
            indeg[j] -= 1
            if indeg[j] == 0:
                ready.append(j)
        ready.sort()
    assert len(out) == n, 'cycle in depth order'
    return out


def sphere(name, layer, cx, cy, cz, r):
    """구 파트. 박스 자리에는 외접 박스를 넣어 깊이 정렬에 쓰고, 4번째 요소로 구 정보를 붙인다."""
    return (name, layer, (cx - r, cy - r, cz - r, cx + r, cy + r, cz + r), ('sphere', cx, cy, cz, r))


def _sphere_polys(cx, cy, cz, r, ox, oy):
    import numpy as np
    from scipy.spatial import ConvexHull
    u, v = np.meshgrid(np.linspace(0, 2 * np.pi, 48), np.linspace(0, np.pi, 24))
    xs, ys, zs = cx + r * np.cos(u) * np.sin(v), cy + r * np.sin(u) * np.sin(v), cz + r * np.cos(v)
    pts = np.array([proj(x, y, z, ox, oy) for x, y, z in zip(xs.ravel(), ys.ravel(), zs.ravel())])
    cap = np.array([proj(x, y, z, ox, oy) for x, y, z, vv in zip(xs.ravel(), ys.ravel(), zs.ravel(), v.ravel()) if vv < 1.0])
    hull = lambda p: [tuple(p[k]) for k in ConvexHull(p).vertices]
    return hull(pts), hull(cap)


def draw_parts(d, dm, df, parts, ox, oy, id_base=0):
    """parts: [(name, layer, (x0,y0,z0,x1,y1,z1)[, ('sphere', cx, cy, cz, r)])]"""
    order = depth_order(parts)
    order = [i for i in order if parts[i][0] != 'face'] + [i for i in order if parts[i][0] == 'face']  # 얼굴 방향 표시는 항상 머리 위에
    for i in order:
        name, layer, (x0, y0, z0, x1, y1, z1) = parts[i][:3]
        if len(parts[i]) > 3 and parts[i][3][0] == 'sphere':
            body, cap = _sphere_polys(*parts[i][3][1:], ox, oy)
            g, t = SHADE['side'], SHADE['top']
            d.polygon(body, fill=(g, g, g + 6, 255), outline=OUTLINE)
            d.polygon(cap, fill=(t, t, t + 6, 255))
            dm.polygon(body, fill=id_base + i + 1)
            df.polygon(body, fill=2)
            df.polygon(cap, fill=1)
            continue
        P = lambda x, y, z: proj(x, y, z, ox, oy)
        if len(parts[i]) > 3 and parts[i][3][0] == 'skew':
            # 기울어진 상자(평행육면체): 바닥 y범위 (yb0,yb1) → 윗면 y범위 (yt0,yt1). 팔다리를 엉덩이·어깨에서 비스듬히
            _, yb0, yb1, yt0, yt1 = parts[i][3]
            faces = [([P(x0, yt0, z1), P(x1, yt0, z1), P(x1, yt1, z1), P(x0, yt1, z1)], SHADE['top'], 1),
                     ([P(x0, yb1, z0), P(x1, yb1, z0), P(x1, yt1, z1), P(x0, yt1, z1)], SHADE['side'], 2),
                     ([P(x1, yb0, z0), P(x1, yb1, z0), P(x1, yt1, z1), P(x1, yt0, z1)], SHADE['side'], 3)]
            for poly, g, fid in faces:
                d.polygon(poly, fill=(g, g, g + 6, 255), outline=OUTLINE)
                dm.polygon(poly, fill=id_base + i + 1)
                df.polygon(poly, fill=fid)
            continue
        faces = [([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], SHADE['top'], 1),
                 ([P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)], SHADE['side'], 2),
                 ([P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)], SHADE['side'], 3)]
        for poly, g, fid in faces:
            d.polygon(poly, fill=(g, g, g + 6, 255), outline=OUTLINE)
            dm.polygon(poly, fill=id_base + i + 1)
            df.polygon(poly, fill=fid)


# ---------- 변환 ----------
def rot180(parts, w, h):
    out = []
    for p in parts:
        n, l, (x0, y0, z0, x1, y1, z1) = p[:3]
        q = (n, l, (w - x1, h - y1, z0, w - x0, h - y0, z1))
        if len(p) > 3 and p[3][0] == 'skew':
            _, yb0, yb1, yt0, yt1 = p[3]
            q = q + (('skew', h - yb1, h - yb0, h - yt1, h - yt0),)
        elif len(p) > 3:
            _, cx, cy, cz, r = p[3]
            q = q + (('sphere', w - cx, h - cy, cz, r),)
        out.append(q)
    return out


def translate(parts, dx=0, dy=0, dz=0):
    return [(n, l, (x0 + dx, y0 + dy, z0 + dz, x1 + dx, y1 + dy, z1 + dz)) for n, l, (x0, y0, z0, x1, y1, z1) in parts]


# ---------- 가구 (회전 0 = 사용면/앞면이 +y, 사용자는 north를 봄) ----------
def desk():
    return [('top', 'lower', (.04, .12, .70, 1.96, .92, .76)),
            ('leg', 'lower', (.08, .16, 0, .16, .88, .70)),
            ('cabinet', 'lower', (1.42, .16, 0, 1.92, .88, .70)),
            ('modesty', 'lower', (.16, .14, .25, 1.42, .20, .70)),
            ('mon_stand', 'lower', (.45, .30, .76, .55, .40, .92)),
            ('mon_screen', 'lower', (.18, .28, .92, .82, .34, 1.30)),
            ('keyboard', 'lower', (.25, .52, .76, .75, .68, .79)),
            ('books', 'lower', (1.30, .25, .76, 1.70, .45, .98))]


def desk_slot1():
    """작업 책상 2x1, 좌석 슬롯 = 두 번째 칸(x=1.5). 집중 업무실 데이터(의자 = 책상 원점 +1,+1)에 맞춤.
    모니터·키보드는 슬롯 정면, 서랍장은 반대쪽 끝(다리 공간 확보)."""
    return [('top', 'lower', (.04, .12, .70, 1.96, .92, .76)),
            ('leg', 'lower', (1.84, .16, 0, 1.92, .88, .70)),
            ('cabinet', 'lower', (.08, .16, 0, .58, .88, .70)),
            ('modesty', 'lower', (.58, .14, .25, 1.84, .20, .70)),
            ('mon_stand', 'lower', (1.45, .30, .76, 1.55, .40, .92)),
            ('mon_screen', 'lower', (1.18, .28, .92, 1.82, .34, 1.30)),
            ('keyboard', 'lower', (1.25, .52, .76, 1.75, .68, .79)),
            ('books', 'lower', (.25, .25, .76, .65, .45, .98))]


def armchair(facing):
    """1인용 암체어 1x1(맵의 1x1 소파). south: 앞면이 관찰자. north: 180°, 등받이 upper."""
    p = [('seat', 'lower', (.12, .30, .12, .88, .92, .345)),
         ('back', 'lower', (.12, .06, .12, .88, .30, .80)),
         ('arm_l', 'lower', (0, .06, .10, .14, .94, .58)),
         ('arm_r', 'lower', (.86, .06, .10, 1.0, .94, .58))]
    if facing == 'north':
        p = [(n, 'upper' if n == 'back' else l, b) for n, l, b in rot180(p, 1, 1)]
    return p


def chair(facing):
    """facing north: 등받이가 +y(관찰자 쪽) → upper. south: 180° 회전, 등받이가 뒤 → lower."""
    p = [('base_x', 'lower', (.10, .46, 0, .90, .54, .05)), ('base_y', 'lower', (.46, .10, 0, .54, .90, .05)),
         ('post', 'lower', (.46, .46, .05, .54, .54, .31)),
         ('seat', 'lower', (.20, .22, .31, .80, .78, .375)),
         ('back_bar', 'lower', (.46, .76, .31, .54, .84, .48)),
         ('back', 'upper', (.24, .74, .46, .76, .82, .92))]
    if facing == 'south':
        p = [(n, 'lower', b) for n, _, b in rot180(p, 1, 1)]
    return p


def sofa(facing):
    """2x1 소파. facing south(앞면이 관찰자): 등받이 -y. north: 180°, 등받이 +y → upper."""
    p = [('seat', 'lower', (.08, .30, .12, 1.92, .92, .345)),
         ('back', 'lower', (.08, .06, .12, 1.92, .30, .80)),
         ('arm_l', 'lower', (0, .06, .10, .18, .94, .60)),
         ('arm_r', 'lower', (1.82, .06, .10, 2.0, .94, .60))]
    if facing == 'north':
        p = [(n, 'upper' if n == 'back' else l, b) for n, l, b in rot180(p, 2, 1)]
    return p


def plant():
    return [('pot', 'lower', (.30, .30, 0, .70, .70, .34)),
            ('foliage', 'lower', (.14, .14, .34, .86, .86, 1.30))]


# ---------- 마네킹 (south 기준 → north는 180°) ----------
def _mann_base(head=0, torso=.58, legs=.44, hw=.27, tw=.28, td=.20):
    """치수(m). hw=구 머리 반지름. 기본값: 전신 53.9px, 머리 39.4%(지름 약 21px), 다리/몸통 0.76(치비) — 수치 탐색으로 보정."""
    c = .5
    return dict(head=head, torso=torso, legs=legs, hw=hw, tw=tw, td=td, c=c)


def mannequin_stand(stride=0.0, arm=0.0, bob=0.0, m=None):
    m = m or _mann_base()
    c, L, T, H = m['c'], m['legs'], m['torso'], m['head']
    tw, td, hw = m['tw'], m['td'], m['hw']
    lw = tw / 2 - .02
    return [
        ('leg_l', 'body', (c - tw / 2, c - .06 + stride, 0, c - tw / 2 + lw, c + .06 + stride, L + bob)),
        ('leg_r', 'body', (c + tw / 2 - lw, c - .06 - stride, 0, c + tw / 2, c + .06 - stride, L + bob)),
        ('torso', 'body', (c - tw / 2, c - td / 2, L + bob, c + tw / 2, c + td / 2, L + T + bob)),
        ('arm_l', 'body', (c - tw / 2 - .07, c - .05 - arm, L + .05 + bob, c - tw / 2, c + .05 - arm, L + T - .02 + bob)),
        ('arm_r', 'body', (c + tw / 2, c - .05 + arm, L + .05 + bob, c + tw / 2 + .07, c + .05 + arm, L + T - .02 + bob)),
        sphere('head', 'body', c, c, L + T + hw * .85 + bob, hw),
        ('face', 'body', (c - .05, c + hw * .92, L + T + hw * .7 + bob, c + .05, c + hw * .92 + .03, L + T + hw * .95 + bob)),
    ]


def mannequin_walk(stride=0.0, arm=0.0, bob=0.0, m=None):
    """걷기: 다리는 엉덩이에서, 팔은 어깨에서 비스듬히 뻗는다(상자를 통째로 앞뒤로 옮기면 다리가 몸에서 떨어져 보임).
    stride = 발끝의 앞뒤 거리(m), arm = 손의 앞뒤 거리(m). 다리와 반대쪽 팔이 앞으로."""
    m = m or _mann_base()
    c, L, T = m['c'], m['legs'], m['torso']
    tw, td, hw = m['tw'], m['td'], m['hw']
    lw = tw / 2 - .02
    hip = L + bob
    xl, xr = c - tw / 2 + lw / 2, c + tw / 2 - lw / 2
    parts = [p for p in mannequin_stand(bob=bob, m=m) if not p[0].startswith(('leg_', 'arm_'))]
    sz = L + T - .06 + bob

    def rod(name, top, bottom, t):
        # 엉덩이·어깨(top)에서 발·손(bottom)까지 기울어진 상자 하나(마디선 없음)
        z0, z1 = bottom[2] - t / 2, top[2]
        yb0, yb1, yt0, yt1 = bottom[1] - t / 2, bottom[1] + t / 2, top[1] - t / 2, top[1] + t / 2
        box = (top[0] - t / 2, min(yb0, yt0), z0, top[0] + t / 2, max(yb1, yt1), z1)
        return [(name, 'body', box, ('skew', yb0, yb1, yt0, yt1))]
    parts += rod('leg_l', (xl, c, hip + .02), (xl, c + stride, lw / 2), lw)
    parts += rod('leg_r', (xr, c, hip + .02), (xr, c - stride, lw / 2), lw)
    parts += rod('arm_l', (c - tw / 2 - .035, c, sz), (c - tw / 2 - .035, c - arm, L + .08 + bob), .07)
    parts += rod('arm_r', (c + tw / 2 + .035, c, sz), (c + tw / 2 + .035, c + arm, L + .08 + bob), .07)
    return parts


def mannequin_sit_type(phase=0, m=None):
    """south를 보고 표준 좌석(0.375m)에 앉아 타이핑. phase로 손 높이 1cm 교대."""
    m = m or _mann_base()
    c, T, H, tw, td, hw = m['c'], m['torso'], m['head'], m['tw'], m['td'], m['hw']
    seat = .375
    a, b = (.01, 0) if phase == 0 else (0, .01)
    lw = tw / 2 - .02
    return [
        ('thigh_l', 'body', (c - tw / 2, c - .05, seat, c - tw / 2 + lw, c + .30, seat + .07)),
        ('thigh_r', 'body', (c + tw / 2 - lw, c - .05, seat, c + tw / 2, c + .30, seat + .07)),
        ('shin_l', 'body', (c - tw / 2, c + .24, .05, c - tw / 2 + lw, c + .34, seat)),
        ('shin_r', 'body', (c + tw / 2 - lw, c + .24, .05, c + tw / 2, c + .34, seat)),
        ('torso', 'body', (c - tw / 2, c - td / 2 - .06, seat + .07, c + tw / 2, c + td / 2 - .06, seat + .07 + T)),
        ('arm_l', 'body', (c - tw / 2 - .07, c - .05, seat + .25 + a, c - tw / 2, c + .42, seat + .33 + a)),
        ('arm_r', 'body', (c + tw / 2, c - .05, seat + .25 + b, c + tw / 2 + .07, c + .42, seat + .33 + b)),
        sphere('head', 'body', c, c - .06, seat + .07 + T + hw * .85, hw),
        ('face', 'body', (c - .05, c - .06 + hw * .92, seat + .07 + T + hw * .7, c + .05, c - .06 + hw * .92 + .03, seat + .07 + T + hw * .95)),
    ]


def mannequin_sit_idle(phase=0, m=None):
    """south를 보고 표준 좌석에 앉아 쉬는 자세: 손은 허벅지 위, phase로 몸 1cm 들썩임."""
    p = mannequin_sit_type(0, m)
    m = m or _mann_base()
    c, tw, seat, b = m['c'], m['tw'], .375, (.012 if phase else 0)
    out = []
    for n, l, box, *rest in p:
        if n in ('arm_l', 'arm_r'):
            x0 = c - tw / 2 - .07 if n == 'arm_l' else c + tw / 2
            out.append((n, l, (x0, c - .04, seat + .22 + b, x0 + .07, c + .04, seat + .52 + b)))          # 위팔(세로)
            out.append(('fore' + n[3:], l, (x0, c - .02, seat + .14, x0 + .07, c + .24, seat + .21)))   # 아래팔(무릎 위)
            continue
        elif n not in ('thigh_l', 'thigh_r', 'shin_l', 'shin_r'):
            box = (box[0], box[1], box[2] + b, box[3], box[4], box[5] + b)
            if rest:
                _, cx, cy, cz, r = rest[0]
                rest = [('sphere', cx, cy, cz + b, r)]
        out.append((n, l, box, *rest))
    return out


def facing(parts, f):
    """south 그대로, north는 180° 회전하고 얼굴 표시(face)를 뺀다(뒷모습)."""
    return parts if f == 'south' else [p for p in rot180(parts, 1, 1) if p[0] != 'face']


CLIPS = {
    'idle': lambda f: [facing(mannequin_stand(bob=0), f), facing(mannequin_stand(bob=.015), f)],
    # 걷기(2026-11-23 수정): 다리·팔을 엉덩이·어깨에서 회전. 보폭 발끝 ±0.16m, 손 ±0.10m, 지나가는 자세 0.02m 위로
    'walk': lambda f: [facing(mannequin_walk(.16, .10), f), facing(mannequin_walk(0, 0, .02), f),
                       facing(mannequin_walk(-.16, -.10), f), facing(mannequin_walk(0, 0, .02), f)],
    'sit.type': lambda f: [facing(mannequin_sit_type(0), f), facing(mannequin_sit_type(1), f)],
    'sit.idle': lambda f: [facing(mannequin_sit_idle(0), f), facing(mannequin_sit_idle(1), f)],
    'turnaround': lambda f: [mannequin_stand(), facing(mannequin_stand(), 'north')],
}


# ---------- 묶음 1 가구 ----------
def desk_small():
    """1x1 보조 책상(안내 데스크·테라스): 노트북 화면이 +y."""
    return [('top', 'lower', (.05, .12, .70, .95, .92, .76)), ('side_l', 'lower', (.08, .16, 0, .14, .88, .70)),
            ('side_r', 'lower', (.86, .16, 0, .92, .88, .70)), ('modesty', 'lower', (.14, .14, .25, .86, .20, .70)),
            ('laptop', 'lower', (.30, .42, .76, .70, .70, .78)), ('screen', 'lower', (.30, .36, .78, .70, .42, 1.02))]


def bookshelf():
    p = [('back', 'lower', (.08, .30, 0, .92, .36, 1.80)), ('side_l', 'lower', (.08, .36, 0, .14, .92, 1.80)),
         ('side_r', 'lower', (.86, .36, 0, .92, .92, 1.80))]
    for i, z in enumerate((0, .60, 1.20, 1.74)):
        p.append((f'shelf{i}', 'lower', (.14, .36, z, .86, .92, z + .06)))
    for i, z in enumerate((.06, .66, 1.26)):
        p.append((f'books{i}', 'lower', (.18, .42, z, .80, .86, z + .40)))
    return p


def lamp():
    return [('base', 'lower', (.36, .36, 0, .64, .64, .04)), ('pole', 'lower', (.47, .47, .04, .53, .53, 1.35)),
            ('shade', 'lower', (.30, .30, 1.30, .70, .70, 1.65))]


def table_round():
    return [('base', 'lower', (.35, .35, 0, .65, .65, .04)), ('post', 'lower', (.46, .46, .04, .54, .54, .70)),
            ('top', 'lower', (.12, .12, .70, .88, .88, .75))]


def meeting_table():
    """3x5 회의 테이블(대칭). 큰 가구라 생성 배율 4, 게임에서는 타일 단위로 분할."""
    return [('top', 'lower', (.15, .15, .70, 2.85, 4.85, .76)), ('ped_a', 'lower', (.9, .9, 0, 2.1, 1.3, .70)),
            ('ped_b', 'lower', (.9, 3.7, 0, 2.1, 4.1, .70))]


def whiteboard():
    return [('foot_l', 'lower', (.08, .30, 0, .18, .70, .05)), ('foot_r', 'lower', (.82, .30, 0, .92, .70, .05)),
            ('post_l', 'lower', (.10, .46, .05, .16, .54, 1.75)), ('post_r', 'lower', (.84, .46, .05, .90, .54, 1.75)),
            ('board', 'lower', (.16, .47, .60, .84, .53, 1.70)), ('tray', 'lower', (.20, .53, .60, .80, .60, .64))]


def computer():
    return [('stand', 'lower', (.15, .20, 0, .85, .80, .70)), ('foot', 'lower', (.45, .50, .70, .55, .58, .80)),
            ('monitor', 'lower', (.22, .44, .80, .78, .50, 1.15)), ('keyboard', 'lower', (.28, .60, .70, .72, .74, .72))]


def coffee():
    return [('counter', 'lower', (.05, .15, 0, .95, .92, .90)), ('machine', 'lower', (.18, .25, .90, .60, .62, 1.32)),
            ('grinder', 'lower', (.66, .30, .90, .84, .50, 1.22)), ('cups', 'lower', (.64, .62, .90, .86, .80, .98))]


def arcade():
    return [('cabinet', 'lower', (.15, .20, 0, .85, .80, 1.55)), ('marquee', 'lower', (.15, .20, 1.55, .85, .45, 1.78)),
            ('panel', 'lower', (.15, .80, .85, .85, .98, .95)), ('screen', 'lower', (.22, .80, 1.0, .78, .82, 1.45))]


def bed_long():
    """침대 1x2: 머리판이 -y 끝, 발치가 +y(관찰자)."""
    return [('headboard', 'lower', (.05, 0, 0, .95, .12, 1.0)), ('frame', 'lower', (.05, .12, 0, .95, 1.95, .35)),
            ('mattress', 'lower', (.08, .15, .35, .92, 1.92, .50)), ('pillow', 'lower', (.20, .20, .50, .80, .48, .60)),
            ('blanket', 'lower', (.08, .80, .50, .92, 1.92, .56))]


def daybed():
    """1x1 데이베드(개인 방 기본 침대): 등받이가 -y."""
    return [('back', 'lower', (.05, .05, .12, .95, .20, .75)), ('base', 'lower', (.05, .05, 0, .95, .95, .35)),
            ('mattress', 'lower', (.08, .20, .35, .92, .92, .48)), ('pillow', 'lower', (.20, .22, .48, .80, .40, .58))]


def rug():
    return [('rug', 'lower', (.05, .05, 0, 1.95, 1.95, .02))]


def cat_bed():
    return [('cushion', 'lower', (.20, .20, 0, .80, .80, .15)), sphere('cat', 'lower', .5, .5, .24, .17)]


def home_portal():
    """로비의 개인 집 입구: 도어매트 위에 선 독립형 문틀과 문(문면이 +y = 좌하를 본다)."""
    return [('mat', 'lower', (.12, .30, 0, .88, .80, .03)),
            ('post_l', 'lower', (.14, .46, 0, .24, .56, 2.05)), ('post_r', 'lower', (.76, .46, 0, .86, .56, 2.05)),
            ('lintel', 'lower', (.10, .44, 2.05, .90, .58, 2.20)),
            ('door', 'lower', (.24, .48, .03, .76, .54, 2.05)),
            ('sign', 'lower', (.30, .54, 1.62, .70, .56, 1.86))]


def column():
    # 높이 2.3m: 2.5m면 블록아웃 캔버스 위 끝에 닿아 생성 그림의 장식 머리가 잘린다
    return [('shaft', 'lower', (.30, .30, 0, .70, .70, 2.20)), ('capital', 'lower', (.25, .25, 2.20, .75, .75, 2.30)),
            ('plinth', 'lower', (.25, .25, 0, .75, .75, .10))]


FURNITURE = {
    'desk_r0': (desk, (2, 1)), 'desk_r180': (lambda: rot180(desk(), 2, 1), (2, 1)),
    'chair_n': (lambda: chair('north'), (1, 1)), 'chair_s': (lambda: chair('south'), (1, 1)),
    'sofa_s': (lambda: sofa('south'), (2, 1)), 'sofa_n': (lambda: sofa('north'), (2, 1)),
    'plant': (plant, (1, 1)),
    'desk_s1_r0': (desk_slot1, (2, 1)), 'desk_s1_r180': (lambda: rot180(desk_slot1(), 2, 1), (2, 1)),
    'armchair_s': (lambda: armchair('south'), (1, 1)), 'armchair_n': (lambda: armchair('north'), (1, 1)),
    'desk_small_s': (desk_small, (1, 1)), 'desk_small_n': (lambda: rot180(desk_small(), 1, 1), (1, 1)),
    'bookshelf_s': (bookshelf, (1, 1)), 'bookshelf_n': (lambda: rot180(bookshelf(), 1, 1), (1, 1)),
    'lamp': (lamp, (1, 1)), 'table_round': (table_round, (1, 1)),
    'meeting_table': (meeting_table, (3, 5), 4),
    'whiteboard_s': (whiteboard, (1, 1)), 'whiteboard_n': (lambda: rot180(whiteboard(), 1, 1), (1, 1)),
    'computer_s': (computer, (1, 1)), 'computer_n': (lambda: rot180(computer(), 1, 1), (1, 1)),
    'coffee_s': (coffee, (1, 1)), 'coffee_n': (lambda: rot180(coffee(), 1, 1), (1, 1)),
    'arcade_s': (arcade, (1, 1)), 'arcade_n': (lambda: rot180(arcade(), 1, 1), (1, 1)),
    'bed_long_s': (bed_long, (1, 2)), 'bed_long_n': (lambda: rot180(bed_long(), 1, 2), (1, 2)),
    'daybed_s': (daybed, (1, 1)), 'daybed_n': (lambda: rot180(daybed(), 1, 1), (1, 1)),
    'rug': (rug, (2, 2)), 'cat_bed': (cat_bed, (1, 1)), 'column': (column, (1, 1)), 'home_portal': (home_portal, (1, 1)),
    'm_lay_s': (lambda: lay_parts(), (1, 2)), 'm_lay_n': (lambda: rot180(lay_parts(), 1, 2), (1, 2)),
}


# ---------- 묶음 2: 동작 포즈 (south 기준, +y = 정면) ----------
def limb(name, a, b, t=.075, steps=3):
    """두 점을 잇는 팔·다리를 작은 박스 steps개로 근사(대각선도 가늘게 유지)."""
    out = []
    for k in range(steps):
        p0 = [a[i] + (b[i] - a[i]) * k / steps for i in range(3)]
        p1 = [a[i] + (b[i] - a[i]) * (k + 1) / steps for i in range(3)]
        lo = [min(p0[i], p1[i]) - t / 2 for i in range(3)]
        hi = [max(p0[i], p1[i]) + t / 2 for i in range(3)]
        out.append((f'{name}{k}', 'body', (*lo, *hi)))
    return out


def arm(name, shoulder, hand):
    elbow = [shoulder[0] + (hand[0] - shoulder[0]) * .45, shoulder[1] + (hand[1] - shoulder[1]) * .45, min(shoulder[2], hand[2]) + abs(shoulder[2] - hand[2]) * .35]
    return limb(name + '_up', shoulder, elbow) + limb(name + '_fore', elbow, hand)


def pose(sit=False, left=None, right=None, bob=0.0, head=(0, 0, 0), lean=0.0, props=(), legs_out=False):
    """치비 마네킹에 손 위치(left/right: (dx, dy, z), c 기준)를 지정. None이면 몸 옆에 내림."""
    m = _mann_base()
    c, T, r, tw, td = m['c'], m['torso'], m['hw'], m['tw'], m['td']
    if sit:
        base = [p for p in mannequin_sit_type(0) if not p[0].startswith(('arm_', 'head', 'face', 'torso'))]
        hip, ty = .375 + .07, c - .06 - lean
        if legs_out:
            base = [p for p in base if not p[0].startswith('shin')] + [('shin_l', 'body', (c - tw / 2, c + .30, .30, c - .02, c + .62, .40)),
                                                                        ('shin_r', 'body', (c + .02, c + .30, .30, c + tw / 2, c + .62, .40))]
    else:
        L = m['legs']
        base = [p for p in mannequin_stand(bob=bob) if p[0].startswith('leg')]
        hip, ty = L + bob, c
    top = hip + T
    parts = base + [('torso', 'body', (c - tw / 2, ty - td / 2, hip, c + tw / 2, ty + td / 2, top))]
    sh_z = top - .05
    shoulders = {'l': (c - tw / 2 - .04, ty, sh_z), 'r': (c + tw / 2 + .04, ty, sh_z)}
    for side, hand in (('l', left), ('r', right)):
        sx, sy, sz = shoulders[side]
        target = (sx, sy, hip + .06) if hand is None else (c + hand[0], ty + hand[1], hand[2] + (bob if not sit else 0))
        parts += arm('arm_' + side, (sx, sy, sz), target)
    hx, hy, hz = head
    parts.append(sphere('head', 'body', c + hx, ty + hy, top + r * .85 + hz, r))
    parts.append(('face', 'body', (c + hx - .05, ty + hy + r * .92, top + r * .7 + hz, c + hx + .05, ty + hy + r * .92 + .03, top + r * .95 + hz)))
    for name, box in props:
        parts.append((name, 'body', box))
    return parts


def cup_at(c, y, z):
    return ('cup', (c - .04, y - .04, z - .03, c + .04, y + .04, z + .07))


_c = .5
_shz = lambda sit: (.445 if sit else .44) + .58  # 앉음/서 있음 어깨 기준 높이
POSES = {
    # 앉은 동작
    'sit.talk': lambda: [pose(True, right=(.22, .22, .80)), pose(True, right=(.24, .26, .92))],
    'sit.relax': lambda: [pose(True, left=(-.30, .05, .58), right=(.30, .05, .58), lean=.08, head=(0, -.08, -.02), legs_out=True)],
    'sit.drink': lambda: [pose(True, right=(.14, .22, .58), props=[cup_at(_c + .14, _c + .16, .62)]),
                          pose(True, right=(.12, .24, .82), props=[cup_at(_c + .12, _c + .18, .86)]),
                          pose(True, right=(.06, .22, 1.08), props=[cup_at(_c + .06, _c + .20, 1.10)])],
    # 서 있는 동작
    'stand.drink': lambda: [pose(right=(.16, .14, .58), props=[cup_at(_c + .16, _c + .14, .60)]),
                            pose(right=(.13, .18, .82), props=[cup_at(_c + .13, _c + .18, .84)]),
                            pose(right=(.06, .20, 1.10), props=[cup_at(_c + .06, _c + .20, 1.12)])],
    'stand.read': lambda: [pose(left=(-.12, .22, .82), right=(.12, .22, .82), props=[('book', (_c - .14, _c + .20, .80, _c + .14, _c + .26, .98))]),
                           pose(left=(-.12, .22, .80), right=(.12, .22, .80), head=(0, .02, -.02), props=[('book', (_c - .14, _c + .20, .78, _c + .14, _c + .26, .96))])],
    'stand.present': lambda: [pose(right=(.36, .24, 1.25)), pose(right=(.38, .28, 1.12))],
    'stand.play': lambda: [pose(left=(-.10, .28, .78), right=(.10, .28, .78)), pose(left=(-.12, .30, .80), right=(.08, .30, .76))],
}
for _sit, _tag in ((False, 'stand'), (True, 'sit')):
    POSES[f'gesture.wave.{_tag}'] = (lambda sit: lambda: [pose(sit, right=(.30, .14, 1.66 if not sit else 1.60)), pose(sit, right=(.40, .14, 1.60 if not sit else 1.54)), pose(sit, right=(.24, .14, 1.66 if not sit else 1.60))])(_sit)  # 손이 머리 뒤에 가리지 않게 높고 앞쪽
    POSES[f'gesture.nod.{_tag}'] = (lambda sit: lambda: [pose(sit), pose(sit, head=(0, .05, -.04))])(_sit)
    POSES[f'gesture.clap.{_tag}'] = (lambda sit: lambda: [pose(sit, left=(-.20, .24, .86), right=(.20, .24, .86)), pose(sit, left=(-.04, .26, .88), right=(.04, .26, .88)), pose(sit, left=(-.20, .24, .86), right=(.20, .24, .86))])(_sit)
    POSES[f'gesture.cheer.{_tag}'] = (lambda sit: lambda: [pose(sit, left=(-.22, .05, .70), right=(.22, .05, .70)), pose(sit, left=(-.30, 0, 1.55 if not sit else 1.50), right=(.30, 0, 1.55 if not sit else 1.50), bob=0 if sit else .06), pose(sit, left=(-.28, 0, 1.52 if not sit else 1.47), right=(.28, 0, 1.52 if not sit else 1.47), bob=0 if sit else .03)])(_sit)
    POSES[f'gesture.thumbsup.{_tag}'] = (lambda sit: lambda: [pose(sit, right=(.16, .30, .92), props=[('thumb', (_c + .14, _c + .30, .96, _c + .19, _c + .35, 1.06))]), pose(sit, right=(.16, .32, .96), props=[('thumb', (_c + .14, _c + .32, 1.00, _c + .19, _c + .37, 1.10))])])(_sit)


def lay_parts():
    """침대 1x2(머리판 -y)에 누운 마네킹. 침대와 같은 앵커·프레임(128x160)으로 그려 침대 위에 그대로 겹친다."""
    c, z = .5, .52
    return [('legs', 'body', (c - .14, 1.05, z, c + .14, 1.80, z + .16)), ('torso', 'body', (c - .16, .45, z, c + .16, 1.05, z + .20)),
            ('arm_l', 'body', (c - .24, .55, z, c - .16, 1.00, z + .10)), ('arm_r', 'body', (c + .16, .55, z, c + .24, 1.00, z + .10)),
            sphere('head', 'body', c, .30, z + .18, .22)]


# ---------- 렌더 ----------
def _canvas(size):
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    pm, fm = Image.new('P', size, 0), Image.new('P', size, 0)
    return img, pm, fm, ImageDraw.Draw(img), ImageDraw.Draw(pm), ImageDraw.Draw(fm)


def _save(name, img, pm, fm, meta):
    OUT.mkdir(exist_ok=True)
    img.save(OUT / f'{name}.png')
    pal = [0, 0, 0] + [c for i in range(1, 256) for c in ((i * 53) % 256, (i * 97) % 256, (i * 151) % 256)]
    pm.putpalette(pal)
    fm.putpalette(pal)
    pm.save(OUT / f'{name}.parts.png')
    fm.save(OUT / f'{name}.faces.png')
    (OUT / f'{name}.json').write_text(json.dumps(meta, indent=1, ensure_ascii=False))


def render_furniture(name):
    global _S
    fn, fp, *rest = FURNITURE[name]
    scale = rest[0] if rest else S
    parts = fn()
    img, pm, fm, d, dm, df = _canvas((1024, 1024))
    if scale == S:
        ax, ay = 512, 640  # 표준 가구(≤2x2): 128x160 프레임과 같은 배치
    else:
        # 큰 가구: footprint+높이의 1x 외곽을 캔버스 중앙에. 앵커 = 원점 타일 중심
        w, h = fp
        zmax = max(b[5] for _, _, b, *_ in parts)
        xmin, xmax, ymin, ymax = -32 * h, 32 * w, -16 - zmax * PX_PER_M, (w + h - 1) * 16
        ax, ay = 512 - scale * (xmin + xmax) / 2, 512 - scale * (ymin + ymax) / 2
    _S = scale
    try:
        draw_parts(d, dm, df, parts, ax, ay - 16 * scale)
    finally:
        _S = S
    _save(name, img, pm, fm, {'kind': 'furniture', 'scale': scale, 'anchor': [ax, ay], 'footprint': fp,
                              'parts': [{'id': i + 1, 'name': p[0], 'layer': p[1]} for i, p in enumerate(parts)]})


def render_clip(name, frames, canvas=(1536, 1024)):
    cw, ch = 48 * S, 64 * S
    img, pm, fm, d, dm, df = _canvas(canvas)
    x0, y0 = (canvas[0] - cw * len(frames)) // 2, (canvas[1] - ch) // 2
    for k, parts in enumerate(frames):
        fx, fy = x0 + k * cw + 24 * S, y0 + 58 * S
        draw_parts(d, dm, df, parts, fx, fy - 16 * S, id_base=k * 20)
    _save(name, img, pm, fm, {'kind': 'clip', 'scale': S, 'cell': [48, 64], 'foot': [24, 58], 'frames': len(frames),
                              'origin': [x0, y0], 'canvas': list(canvas)})


def all_targets():
    t = {n: ('f', n) for n in FURNITURE}
    for clip in ('idle', 'walk', 'sit.type', 'sit.idle'):
        for f in ('south', 'north'):
            t[f'm_{clip}_{f}'] = ('c', clip, f)
    for clip in POSES:
        for f in ('south', 'north'):
            t[f'm_{clip}_{f}'] = ('p', clip, f)
    t['m_turnaround'] = ('c', 'turnaround', 'south')
    return t


if __name__ == '__main__':
    targets = all_targets()
    for n in (sys.argv[1:] or targets):
        t = targets[n]
        if t[0] == 'f':
            render_furniture(n)
        elif t[0] == 'p':
            render_clip(n, [facing(fr, t[2]) for fr in POSES[t[1]]()], canvas=(1536, 1024))
        else:
            render_clip(n, CLIPS[t[1]](t[2]), canvas=(1536, 1024))
        print('blockout', n)
