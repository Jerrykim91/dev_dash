#!/usr/bin/env python3
"""v2 결과물(norm/) → 게임 아틀라스 + overrides.json (frontend/src/game/visual/overrides.json 형식).

- 가구: 회전 스키마 4-way-mirror. 0 = 앞 뷰, 90 = 앞 뷰 반전(WxH 교환), 180 = 뒤 뷰, 270 = 뒤 뷰 반전.
- 캐릭터: 기존 외형 칸 16개(서버 팔레트)에 프리셋 4종 × 4변형. east/west는 실행 중 반전(C5)이라 south/north만 넣는다.
- 바닥: 존별 타일셋.
출력: frontend/public/visual/aigen-v2-<hash>.png/.json, frontend/src/game/visual/overrides.json
"""
import hashlib, json, os, sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
FRONT = HERE.parents[3] / 'frontend'
# 그림 밀도(docs/visual-standard-v2.md §14): 2 = HD(그림 2px = 월드 1px). 아틀라스마다 scale(그림 1px의 월드 크기)을 적어 게임이 0.5배로 그린다
D = int(os.environ.get('NOBIS_DENSITY', '2'))
NORM = HERE / ('norm' if D == 1 else f'norm_d{D}')
SHEET = 2048  # 아틀라스 한 장의 한 변 한도(manifest.maxTextureSize)
PARTS = HERE.parent / 'parts' / 'export'
# 기존 캐릭터 아틀라스(nobis-avatar-0)와 같은 키로 등록 → 오버라이드 규칙상 그 아틀라스를 대체(외형 16칸을 모두 새 프레임으로 덮으므로 미사용).
# 텍스처 메모리 예산(24MB, visual.test.ts) 유지.
KEY = 'nobis-avatar-0'
EXTRA_KEY = 'nobis-aigen-{}'  # 2번째 장부터

# kind/W0xH0 → (회전 0 뷰, 회전 180 뷰). 회전 90/270은 각각의 반전
FURNITURE = {
    'desk/2x1': ('desk_work_r0', 'desk_work_r180'),
    'chair/1x1': ('chair_n', 'chair_s'),
    'sofa/2x1': ('sofa_s', 'sofa_n'),
    'sofa/1x1': ('armchair_s', 'armchair_n'),
    'plant/1x1': ('plant', 'plant'),
    # 묶음 1
    'desk/1x1': ('desk_small_s', 'desk_small_n'),
    'bookshelf/1x1': ('bookshelf_s', 'bookshelf_n'),
    'lamp/1x1': ('lamp', 'lamp'),
    'table/1x1': ('table_round', 'table_round'),
    'whiteboard/1x1': ('whiteboard_s', 'whiteboard_n'),
    'computer/1x1': ('computer_s', 'computer_n'),
    'coffee/1x1': ('coffee_s', 'coffee_n'),
    'arcade/1x1': ('arcade_s', 'arcade_n'),
    'bed/1x2': ('bed_long_s', 'bed_long_n'),
    'bed/1x1': ('daybed_s', 'daybed_n'),
    'rug/2x2': ('rug', 'rug'),
    'decoration/1x1': ('cat_bed', 'cat_bed'),
    'table/3x5': ('meeting_table', 'meeting_table'),  # 큰 가구: 게임이 칸 폭 띠로 잘라 깊이를 따로 준다(FurnitureVisual.sliceByFootprint)
}
# 로비 전용 물체(맵의 visual_asset) → 생성 그림
LOBBY_OBJECTS = {'bookshelf': 'home_portal', 'column': 'column'}
BIG = {'meeting_table'}  # 표준 128×160 프레임이 아닌 가구: 프레임에 기준점을 적고 여백을 자르지 않는다(띠 자르기)
TILESETS = {'focus': 'floor_stone', 'office': 'floor_stone', 'meeting': 'floor_meeting', 'cafe': 'floor_cafe',
            'lounge': 'floor_lounge', 'garden': 'floor_grass', 'outside': 'floor_deck', 'home': 'floor_wood'}
# 외형 16칸 = 프리셋 4종 × 4변형(옷 색, p3은 머리카락 색 — 크림 니트가 피부와 분리되지 않음)
WALLS = {'plain': 'wall_plain', 'cafe': 'wall_cafe', 'meeting': 'wall_meeting', 'railing': 'railing'}
DOORS = ['cafe', 'focus', 'meeting', 'lounge', 'garden', 'terrace', 'exit', 'exitcafe', 'exitmeeting', 'gate']  # exit* = 방 벽 테마별 출구, gate = 난간 방
PRESETS = ['p0', 'p0-mint', 'p0-peach', 'p0-sky', 'p1', 'p1-lavender', 'p1-peach', 'p1-sky',
           'p2', 'p2-lavender', 'p2-mint', 'p2-peach', 'p3', 'p3-black', 'p3-blonde', 'p3-rose']
STATES = {'idle': ('idle', 2), 'walking': ('walk', 4), 'typing': ('sittype', 2), 'sitting': ('sitidle', 2)}
# east·west는 아틀라스에 굽지 않고 실행 중 반전(C5, catalog.characterFrameDir) → 캐릭터 프레임 절반
DIRS = {'south': ('s', False), 'north': ('n', False)}


def collect():
    frames, alias = {}, {}
    blank = Image.new('RGBA', (128 * D, 160 * D), (0, 0, 0, 0))
    for key, (front, back) in FURNITURE.items():
        kind, size = key.split('/')
        w, h = map(int, size.split('x'))
        for rot, view, mirror in ((0, front, False), (90, front, True), (180, back, False), (270, back, True)):
            fw, fh = (h, w) if rot in (90, 270) else (w, h)
            for part in ('lower', 'upper'):
                src = NORM / f"{view}{'.m' if mirror else ''}.{part}.png"
                im = Image.open(src).convert('RGBA') if src.exists() else blank
                name = f"{view}{'.m' if mirror else ''}.{part}"
                if im.getbbox() is None:
                    name = 'blank'
                    im = blank
                frames.setdefault(name, im)
                alias[f'furniture/{kind}/{fw}x{fh}/{rot}/{part}'] = name
    # 건축: 벽(방 테마별)과 벽에 붙는 문. 프레임 128x160, 앵커 = 벽이 붙은 바닥 칸 중심
    for theme, src in WALLS.items():
        for axis in 'xy':
            name = f'wall/{theme}/{axis}'
            frames[name] = Image.open(NORM / f'{src}_{axis}.png').convert('RGBA')
            alias[f'architecture/{name}'] = name
    for theme in DOORS:
        for axis in 'xy':
            name = f'door/{theme}/{axis}'
            frames[name] = Image.open(NORM / f'door_{theme}_{axis}.png').convert('RGBA')
            alias[f'architecture/{name}'] = name
    for asset, view in LOBBY_OBJECTS.items():
        for part in ('lower', 'upper'):
            im = Image.open(NORM / f'{view}.{part}.png').convert('RGBA')
            name = f'{view}.{part}' if im.getbbox() else 'blank'
            frames.setdefault(name, im if im.getbbox() else blank)
            alias[f'lobby-object/{asset}/{part}'] = name
    alias['architecture/blank'] = 'blank'
    frames.setdefault('blank', blank)
    for zone, tex in TILESETS.items():
        frames.setdefault(f'floor/{tex}', Image.open(NORM / f'{tex}.png').convert('RGBA'))
    for v in range(16):
        preset = PRESETS[v]
        for state, (clip, n) in STATES.items():
            for d, (suffix, mirror) in DIRS.items():
                for i in range(n):
                    src = NORM / f'{preset}_{clip}_{suffix}_{i}.png'
                    name = f"{preset}/{clip}/{suffix}{'.m' if mirror else ''}/{i}"
                    if name not in frames:
                        im = Image.open(src).convert('RGBA')
                        frames[name] = im.transpose(Image.FLIP_LEFT_RIGHT) if mirror else im
                    alias[f'avatar/v{v}/{d}/{state}/{i}'] = name
    # 옷 갈아입기 파트(docs/visual-standard-v2.md §15): 기본 몸·상의·하의는 프레임마다, 머리는 방향마다 1장
    if PARTS.exists():
        meta = json.loads((PARTS / 'parts.json').read_text())
        for d, suffix in (('south', 'south'), ('north', 'north')):
            for k in range(10):
                frames[f'part/base/{d}/{k}'] = Image.open(PARTS / f'base_{suffix}_{k}.png').convert('RGBA')
                for t in meta['tops']:
                    frames[f'part/top/{t}/{d}/{k}'] = Image.open(PARTS / f'top-{t}_{suffix}_{k}.png').convert('RGBA')
                for b in meta['bottoms']:
                    frames[f'part/bottom/{b}/{d}/{k}'] = Image.open(PARTS / f'bottom-{b}_{suffix}_{k}.png').convert('RGBA')
            for h in meta['hair']:
                frames[f'part/hair/{h}/{d}'] = Image.open(PARTS / f'hair-{h}_{suffix}.png').convert('RGBA')
        for n in [n for n in frames if n.startswith('part/')]:
            alias[n] = n
    return frames, alias


def trim(frames):
    """가구·벽·문은 투명 여백을 잘라 담는다(텍스처 메모리 예산). 캐릭터는 실행 중 좌우 반전하므로 원래 크기 그대로.
    반환: 잘린 그림, 원래 크기 안에서의 오프셋·원래 크기 {name: (ox, oy, sw, sh)}."""
    out, src = {}, {}
    for name, im in frames.items():
        keep = (name.startswith('p') and '/' in name) or name.split('.')[0] in BIG  # 캐릭터·파트(p…/…)는 실행 중 반전, 큰 가구는 띠 자르기
        box = None if keep else im.getbbox()
        if box is None:
            box = (0, 0, im.width, im.height) if keep else (0, 0, 1, 1)
        out[name] = im.crop(box)
        src[name] = (box[0], box[1], im.width, im.height)
    return out, src


def pack(frames, width=SHEET, height=SHEET):
    """선반(shelf) 배치. 한 장이 차면 다음 장으로. 반환: [(sheet, {name: rect})]"""
    sheets, rects, x, y, row = [], {}, 0, 0, 0
    def close():
        sheet = Image.new('RGBA', (width, y + row), (0, 0, 0, 0))
        for name, (fx, fy, _, _) in rects.items():
            sheet.alpha_composite(frames[name], (fx, fy))
        sheets.append((sheet, dict(rects)))
    for name, im in sorted(frames.items(), key=lambda kv: (-kv[1].height, kv[0])):
        if x + im.width > width:
            x, y, row = 0, y + row, 0
        if y + im.height > height:
            close()
            rects, x, y, row = {}, 0, 0, 0
        rects[name] = (x, y, im.width, im.height)
        x += im.width
        row = max(row, im.height)
    close()
    return sheets


QA = json.loads((HERE / 'qa.json').read_text())


def origin(n):
    """큰 가구는 프레임 기준점(원점 칸 중심)을 비율로. 반전본(.m)은 x를 뒤집는다."""
    view = n.split('.')[0]
    if view not in BIG:
        return {}
    fw, fh, ax, ay = QA[view]['frame']
    x = ax / fw
    return {'origin': {'x': round(1 - x if '.m.' in n else x, 6), 'y': round(ay / fh, 6)}}


def main():
    frames, alias = collect()
    frames, src = trim(frames)
    out = FRONT / 'public' / 'visual'
    for old in out.glob('aigen-v2-*'):
        old.unlink()
    atlases, where = [], {}
    for i, (sheet, rects) in enumerate(pack(frames)):
        key = KEY if i == 0 else EXTRA_KEY.format(i)
        tmp = out / '_aigen.png'
        sheet.save(tmp, optimize=True)
        png = out / f"aigen-v2-{hashlib.sha256(tmp.read_bytes()).hexdigest()[:12]}.png"
        tmp.replace(png)
        data = {'frames': {n: {'frame': dict(zip('xywh', r)), 'rotated': False,
                               'trimmed': (r[2], r[3]) != src[n][2:],
                               'spriteSourceSize': {'x': src[n][0], 'y': src[n][1], 'w': r[2], 'h': r[3]},
                               'sourceSize': {'w': src[n][2], 'h': src[n][3]}}
                           for n, r in rects.items()},
                'meta': {'image': png.name, 'size': {'w': sheet.width, 'h': sheet.height}, 'scale': '1'}}
        raw = json.dumps(data).encode()
        js = out / f"aigen-v2-atlas-{hashlib.sha256(raw).hexdigest()[:12]}.json"
        js.write_bytes(raw)
        atlases.append({'key': key, 'image': f'visual/{png.name}', 'data': f'visual/{js.name}',
                        'width': sheet.width, 'height': sheet.height, 'bytes': png.stat().st_size, 'scale': 1 / D})
        where.update({n: (key, r) for n, r in rects.items()})
        print(f'{key}: {png.name} {sheet.size} {png.stat().st_size // 1024}KB, frames={len(rects)}')
    # rect = 원래(잘리기 전) 크기의 논리 프레임(그림 픽셀). 실제 위치는 아틀라스 JSON의 frame/spriteSourceSize
    # rect = 잘리기 전 프레임의 원점이 놓일 아틀라스 좌표와 원래 크기, trim = 그 안에서 실제 그림이 있는 상자(SVG 미리보기 잘라내기용)
    vf = lambda n: {'atlas': where[n][0], 'frame': n,
                    'rect': {'x': where[n][1][0] - src[n][0], 'y': where[n][1][1] - src[n][1], 'w': src[n][2], 'h': src[n][3]},
                    'trim': {'x': src[n][0], 'y': src[n][1], 'w': where[n][1][2], 'h': where[n][1][3]}, **origin(n)}
    overrides = {
        'atlases': atlases,
        'frames': {k: vf(v) for k, v in sorted(alias.items())},
        'tilesets': {z: vf(f'floor/{t}') for z, t in TILESETS.items()},
        # 결정 5: 캐릭터 축척 1.0(월드 기준). HD 그림은 1/D로 그려 같은 월드 크기
        'avatar': {'scale': 1 / D, 'width': 48 * D, 'height': 64 * D},
    }
    if PARTS.exists():
        meta = json.loads((PARTS / 'parts.json').read_text())
        overrides['parts'] = {k: meta[k] for k in ('states', 'anchors', 'tops', 'bottoms', 'hair', 'labels')}
        # 서버 검증 목록(백엔드는 이 파일에 있는 id만 받는다)
        lists = {'hair': meta['hair'], 'top': meta['tops'], 'bottom': meta['bottoms']}
        shared = {k: [{'id': i, 'label': meta['labels'][k][i]} for i in v] for k, v in lists.items()}
        (HERE.parents[3] / 'shared' / 'avatar-parts.json').write_text(json.dumps(shared, ensure_ascii=False, indent=1) + '\n')
    (FRONT / 'src' / 'game' / 'visual' / 'overrides.json').write_text(json.dumps(overrides, indent=1, ensure_ascii=False) + '\n')
    print(f'frames={len(frames)}, keys={len(alias)}, memory={sum(a["width"] * a["height"] * 4 for a in atlases) / 2**20:.1f}MB')


if __name__ == '__main__':
    sys.exit(main())
