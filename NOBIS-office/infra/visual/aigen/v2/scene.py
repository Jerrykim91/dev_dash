#!/usr/bin/env python3
"""스타일 보드 v2 장면 합성: 엔진과 같은 좌표·앵커·깊이 규칙 v2로 norm/ 결과물을 배치한다.

검증 포인트
- 워크스테이션 4방향: (책상 앞/뒤 2장 + 반전) × (의자 앞/뒤 2장 + 반전) × (앉은 클립 south/north + 반전)
- 깊이: 가구 lower −0.15 < 앉은 캐릭터 +0.10 < upper +0.20, 서 있는 캐릭터 +1
- 프리셋 색 교체(p0 lavender 원본 / mint / sky 등)
출력: preview/styleboard.png(2배), preview/workstations.png(4방향 확대 4배)
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw
from standard import DEPTH

HERE = Path(__file__).resolve().parent
NORM, OUT = HERE / 'norm', HERE / 'preview'
W, H = 12, 11
BG = (36, 28, 48, 255)


def img(name, mirror=False):
    im = Image.open(NORM / f'{name}.png').convert('RGBA')
    return im.transpose(Image.FLIP_LEFT_RIGHT) if mirror else im


def world(x, y):
    return (x - y) * 32, (x + y) * 16


# 회전 스키마 4-way-mirror: facing → (그린 뷰, 반전 여부, footprint)
DESK = {'north': ('desk_r0', False, (2, 1)), 'west': ('desk_r0', True, (1, 2)),
        'south': ('desk_r180', False, (2, 1)), 'east': ('desk_r180', True, (1, 2))}   # facing = 앉는 사람이 보는 방향
CHAIR = {'north': ('chair_n', False), 'west': ('chair_n', True), 'south': ('chair_s', False), 'east': ('chair_s', True)}
SOFA = {'south': ('sofa_s', False, (2, 1)), 'east': ('sofa_s', True, (1, 2)), 'north': ('sofa_n', False, (2, 1)), 'west': ('sofa_n', True, (1, 2))}
CLIPDIR = {'south': ('s', False), 'east': ('s', True), 'north': ('n', False), 'west': ('n', True)}
# 워크스테이션 정의: 책상 원점 기준 좌석 오프셋(사람이 보는 방향별). 반전은 (dx,dy)→(dy,dx)
SEAT_OFFSET = {'north': (0, 1), 'west': (1, 0), 'south': (1, -1), 'east': (-1, 1)}


class Scene:
    def __init__(self):
        self.items = []

    def furniture(self, name, mirror, x, y, fp):
        cx, cy = x + (fp[0] - 1) / 2, y + (fp[1] - 1) / 2
        base = (cx + cy) * 100
        self.items.append((base + DEPTH['lower'], img(f"{name}{'.m' if mirror else ''}.lower"), x, y, (64, 104)))
        up = NORM / f"{name}{'.m' if mirror else ''}.upper.png"
        if up.exists():
            self.items.append((base + DEPTH['upper'], img(f"{name}{'.m' if mirror else ''}.upper"), x, y, (64, 104)))

    def chair(self, facing, x, y):
        n, m = CHAIR[facing]
        self.items.append(((x + y) * 100 + DEPTH['lower'], img(f'{n}{".m" if m else ""}.lower'), x, y, (64, 104)))
        self.items.append(((x + y) * 100 + DEPTH['upper'], img(f'{n}{".m" if m else ""}.upper'), x, y, (64, 104)))

    def avatar(self, preset, clip, facing, x, y, frame=0, seated=False):
        d, m = CLIPDIR[facing]
        self.items.append(((x + y) * 100 + (DEPTH['seated'] if seated else DEPTH['stand']),
                           img(f'{preset}_{clip}_{d}_{frame}', m), x, y, (24, 58)))

    def workstation(self, facing, dx, dy, preset):
        name, mirror, fp = DESK[facing]
        self.furniture(name, mirror, dx, dy, fp)
        ox, oy = SEAT_OFFSET[facing]
        self.chair(facing, dx + ox, dy + oy)
        self.avatar(preset, 'sittype', facing, dx + ox, dy + oy, seated=True)

    def render(self, size, origin):
        canvas = Image.new('RGBA', size, BG)
        ox, oy = origin
        stone, wood = img('floor_stone'), img('floor_wood')
        for ty in range(H):
            for tx in range(W):
                px, py = world(tx, ty)
                canvas.alpha_composite(wood if tx >= 7 and ty >= 5 else stone, (ox + px - 32, oy + py - 16))
        for ty in range(H):
            px, py = world(0, ty)
            canvas.alpha_composite(img('wall_plain_x'), (ox + px - 64, oy + py - 104))
        for tx in range(W):
            px, py = world(tx, 0)
            canvas.alpha_composite(img('wall_plain_y'), (ox + px - 64, oy + py - 104))
        for _, im, x, y, (ax, ay) in sorted(self.items, key=lambda t: t[0]):
            px, py = world(x, y)
            canvas.alpha_composite(im, (ox + px - ax, oy + py - ay))
        return canvas


def build():
    s = Scene()
    s.workstation('north', 2, 2, 'p0')
    s.workstation('west', 8, 1, 'p1')
    s.workstation('south', 2, 6, 'p1')
    s.workstation('east', 6, 5, 'p0-mint')
    name, m, fp = SOFA['south']
    s.furniture(name, m, 8, 6, fp)
    name, m, fp = SOFA['north']
    s.furniture(name, m, 8, 9, fp)
    name, m, fp = SOFA['east']
    s.furniture(name, m, 11, 7, fp)
    for x, y in ((11, 4), (0, 8), (5, 1), (6, 10)):
        s.furniture('plant', False, x, y, (1, 1))
    s.avatar('p0', 'idle', 'south', 4, 3)
    s.avatar('p1', 'walk', 'north', 10, 4, frame=0)
    s.avatar('p1', 'idle', 'east', 4, 8)
    s.avatar('p0-sky', 'walk', 'west', 9, 8, frame=2)
    s.avatar('p0-peach', 'idle', 'south', 3, 9)
    return s


def main():
    OUT.mkdir(exist_ok=True)
    s = build()
    ox, oy = H * 32 + 40, 120
    room = s.render(((W + H) * 32 + 80, (W + H) * 16 + 180), (ox, oy))
    room.resize((room.width * 2, room.height * 2), Image.NEAREST).save(OUT / 'styleboard.png')
    # 워크스테이션 4방향 확대
    crops = []
    for (fx, fy) in ((2, 2), (8, 1), (2, 6), (6, 5)):
        px, py = world(fx, fy)
        cx, cy = ox + px + 16, oy + py - 10
        crops.append(room.crop((cx - 90, cy - 80, cx + 90, cy + 60)))
    strip = Image.new('RGBA', (180 * 4 + 30, 140), BG)
    for k, c in enumerate(crops):
        strip.alpha_composite(c, (k * 190, 0))
    d = ImageDraw.Draw(strip)
    for k, t in enumerate(('north: view A', 'west: A mirrored', 'south: view B', 'east: B mirrored')):
        d.text((k * 190 + 4, 2), t, fill=(240, 230, 255, 255))
    strip.resize((strip.width * 3, strip.height * 3), Image.NEAREST).save(OUT / 'workstations.png')
    print('preview/styleboard.png', 'preview/workstations.png')


if __name__ == '__main__':
    main()
