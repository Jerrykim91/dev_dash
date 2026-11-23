"""좌석 시스템 (docs/visual-standard-v2.md §2.5, §7.2 S2~S5).

- derive_seats(map): 맵 오브젝트 + shared/object-kinds.json → 좌석 목록(타일·방향·좌석 높이·진입 칸·연결 책상).
  서버가 맵 payload에 `seats`로 실어 보내고 클라이언트는 이것만 읽는다(로직 단일화).
- derive_rotation(map): 회전값이 없는 의자에 인접 책상/테이블 방향으로 회전을 부여(Pixel Agents 우선순위: 명시값 > 인접 책상).
- SeatRegistry: (채널, 룸 인스턴스)별 좌석 점유자 조회. 플레이어의 seat_id가 유일한 상태라 한 좌석 1명·한 사람 1좌석.
"""
import json
from pathlib import Path

KINDS = json.loads((Path(__file__).resolve().parents[2] / 'shared' / 'object-kinds.json').read_text())['kinds']
DIRS = {'north': (0, -1), 'south': (0, 1), 'east': (1, 0), 'west': (-1, 0)}
OPPOSITE = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}
MIRROR = {'north': 'west', 'west': 'north', 'south': 'east', 'east': 'south'}  # 아이소 좌우 반전 = x/y 축 교환
FACING_TO_CHAIR_ROTATION = {'north': 0, 'west': 90, 'south': 180, 'east': 270}
SURFACES = ('desk', 'table', 'computer')


def _size0(o):
    w, h = o.get('width', 1), o.get('height', 1)
    return (h, w) if o.get('rotation', 0) in (90, 270) else (w, h)


def kind_def(o):
    w0, h0 = _size0(o)
    return KINDS.get(f"{o['kind']}/{w0}x{h0}")


def rotate_tile(dx, dy, w0, h0, rotation):
    if rotation == 90:
        return dy, dx
    if rotation == 180:
        return w0 - 1 - dx, h0 - 1 - dy
    if rotation == 270:
        return h0 - 1 - dy, w0 - 1 - dx
    return dx, dy


def rotate_facing(facing, rotation):
    if rotation == 90:
        return MIRROR[facing]
    if rotation == 180:
        return OPPOSITE[facing]
    if rotation == 270:
        return MIRROR[OPPOSITE[facing]]
    return facing


def tiles_of(o):
    return {(o['x'] + dx, o['y'] + dy) for dx in range(o.get('width', 1)) for dy in range(o.get('height', 1))}


def _walkable_fn(m):
    floor = {(p['x'], p['y']) for p in m.get('walkable_tiles') or []}
    blocked = set()
    for o in m.get('objects', []):
        if o.get('blocking', True):
            blocked |= tiles_of(o)
    if floor:
        return lambda t: t in floor and t not in blocked
    return lambda t: 0 <= t[0] < m.get('width', 0) and 0 <= t[1] < m.get('height', 0) and t not in blocked


def derive_rotation(m):
    """회전값이 없는 의자에 인접한 책상/테이블 방향으로 회전을 부여한다. 변경한 의자 수를 돌려준다."""
    surfaces = [tiles_of(o) for o in m.get('objects', []) if o['kind'] in SURFACES]
    changed = 0
    for o in m.get('objects', []):
        if o['kind'] != 'chair' or o.get('rotation') is not None:
            continue
        hits = [f for f, (dx, dy) in DIRS.items() if any((o['x'] + dx, o['y'] + dy) in s for s in surfaces)]
        if len(hits) == 1:
            o['rotation'] = FACING_TO_CHAIR_ROTATION[hits[0]]
            changed += 1
    return changed


def derive_seats(m):
    walkable = _walkable_fn(m)
    by_id = {o['id']: o for o in m.get('objects', [])}
    linked = {w['chair_id']: w for w in m.get('workstations') or []}
    seats = []
    for o in m.get('objects', []):
        d = kind_def(o)
        if not d or not d.get('seats'):
            continue
        w0, h0 = _size0(o)
        rot = o.get('rotation', 0) or 0
        for i, s in enumerate(d['seats']):
            dx, dy = rotate_tile(*s['tile'], w0, h0, rot)
            tile = (o['x'] + dx, o['y'] + dy)
            facing = rotate_facing(s['facing'], rot)
            approach = None
            ws = linked.get(o['id'])
            if ws and ws.get('approach'):
                approach = (ws['approach']['x'], ws['approach']['y'])
            if approach is None:
                for f in (facing, OPPOSITE[facing], MIRROR[facing], OPPOSITE[MIRROR[facing]]):
                    c = (tile[0] + DIRS[f][0], tile[1] + DIRS[f][1])
                    if walkable(c):
                        approach = c
                        break
            if approach is None:
                continue
            front = (tile[0] + DIRS[facing][0], tile[1] + DIRS[facing][1])
            surface = ws['desk_id'] if ws else next((x['id'] for x in m.get('objects', []) if x['kind'] in SURFACES and front in tiles_of(x)), None)
            seats.append({'id': f"{o['id']}#{i}", 'object_id': o['id'], 'tile': {'x': tile[0], 'y': tile[1]}, 'facing': facing,
                          'sit_height': s.get('sitHeight', 12), 'approach': {'x': approach[0], 'y': approach[1]},
                          'work_surface_id': surface if surface in by_id else None})
    return seats


def derive_wall_axis(m):
    """벽에 붙는 문: 문 칸의 -x 이웃이 바닥이 아니면 좌상 벽('x'), -y 이웃이 아니면 우상 벽('y'). 클라이언트가 해당 벽면용 문 그림을 쓴다."""
    floor = {(p['x'], p['y']) for p in m.get('walkable_tiles') or []}
    if not floor:
        return
    for o in m.get('objects', []):
        if o['kind'] == 'door' and 'wall_axis' not in o:
            x, y = o['x'], o['y']
            o['wall_axis'] = 'x' if (x - 1, y) not in floor else 'y' if (x, y - 1) not in floor else None


def with_seats(m):
    """맵 payload 전처리: 의자 회전·좌석·문 벽 방향."""
    if m is not None and 'seats' not in m:
        derive_rotation(m)
        m['seats'] = derive_seats(m)
        derive_wall_axis(m)
    return m


def space_of(player):
    return f"{player.get('channel_id', 'ch1')}|{player.get('room_instance_id') or player.get('scope', 'office')}"


class SeatRegistry:
    """점유자는 접속 중인 플레이어의 seat_id에서 계산한다(별도 상태 없음 → 연결 종료·전환 시 어긋남 없음)."""
    def __init__(self, players):
        self.players = players  # () -> 접속 중 플레이어 dict 목록

    def holder(self, player, seat_id):
        sp = space_of(player)
        return next((q['id'] for q in self.players() if q.get('seat_id') == seat_id and space_of(q) == sp), None)


def pick_seat(m, obj, player, registry):
    """상호작용 대상 오브젝트(의자·소파·연결된 책상)에서 앉을 좌석을 고른다.
    플레이어가 서 있는 칸이 진입 칸인 빈 좌석을 우선하고, 없으면 좌석 칸이 1.5 이내(대각선 인접 포함)인 빈 좌석."""
    import math
    seats = [s for s in m.get('seats', []) if s['object_id'] == obj['id'] or s.get('work_surface_id') == obj['id']]
    if not seats:
        return None, None
    free = [s for s in seats if registry.holder(player, s['id']) in (None, player['id'])]
    if not free:
        return None, 'occupied'
    pos = (player['x'], player['y'])
    at_approach = [s for s in free if math.hypot(pos[0] - s['approach']['x'], pos[1] - s['approach']['y']) < .3]
    near = sorted(free, key=lambda s: math.hypot(pos[0] - s['tile']['x'], pos[1] - s['tile']['y']))
    # 대각선으로 붙은 빈자리(2인 소파의 옆자리 등)도 허용: 1.5 이내
    seat = (at_approach or [s for s in near if math.hypot(pos[0] - s['tile']['x'], pos[1] - s['tile']['y']) <= 1.5] or [None])[0]
    return seat, (None if seat else 'far')
