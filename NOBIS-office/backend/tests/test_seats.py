"""좌석 시스템 (docs/visual-standard-v2.md §2.5, §7.2): 스냅·방향·점유 배타·일어서기·상태 변경·재접속."""
from test_server import client, login, auth, place  # noqa: F401 (fixture)
from test_phase2 import until, drain
from app.world import ROOM_DATA, walkable
from app.seats import derive_seats, FACING_TO_CHAIR_ROTATION


def own(ws, kind, user):
    """같은 방의 다른 사람 브로드캐스트는 건너뛰고 자기 플레이어 메시지만 받는다."""
    for _ in range(50):
        m = until(ws, kind)
        if m.get('player', {}).get('id') == user['user']['id']:
            return m
    raise AssertionError(f'missing own {kind}')


def seat(seat_id, room='focus'):
    return next(s for s in ROOM_DATA['maps'][room]['seats'] if s['id'] == seat_id)


def test_every_seat_has_walkable_approach_and_focus_desks_link_to_chairs():
    for room, m in ROOM_DATA['maps'].items():
        for s in m['seats']:
            assert walkable(room, s['approach']['x'], s['approach']['y']), (room, s)
            assert abs(s['approach']['x'] - s['tile']['x']) + abs(s['approach']['y'] - s['tile']['y']) == 1
    focus = ROOM_DATA['maps']['focus']['seats']
    assert len(focus) == 15 and all(s['facing'] == 'north' and s['work_surface_id'] for s in focus)
    meeting = ROOM_DATA['maps']['meeting']
    assert {s['facing'] for s in meeting['seats']} == {'north', 'south', 'east', 'west'}
    for o in meeting['objects']:
        if o['kind'] == 'chair':
            s = next(s for s in meeting['seats'] if s['object_id'] == o['id'])
            assert FACING_TO_CHAIR_ROTATION[s['facing']] == o['rotation']


def test_rotation_moves_seats_with_the_footprint():
    base = {'walkable_tiles': [{'x': x, 'y': y} for x in range(6) for y in range(6)], 'objects': []}
    for rot, tiles, facing in [(0, {(1, 1), (2, 1)}, 'south'), (90, {(1, 1), (1, 2)}, 'east'), (180, {(1, 1), (2, 1)}, 'north'), (270, {(1, 1), (1, 2)}, 'west')]:
        w, h = (1, 2) if rot in (90, 270) else (2, 1)
        m = {**base, 'objects': [{'id': 's', 'kind': 'sofa', 'x': 1, 'y': 1, 'width': w, 'height': h, 'rotation': rot}]}
        seats = derive_seats(m)
        assert {(s['tile']['x'], s['tile']['y']) for s in seats} == tiles and {s['facing'] for s in seats} == {facing}


def test_desk_seats_on_linked_chair_and_occupancy_is_exclusive(client):
    a, b = login(client, 'SeatA'), login(client, 'SeatB')
    ap = seat('chair#0')['approach']
    with client.websocket_connect('/ws') as wa, client.websocket_connect('/ws') as wb:
        auth(wa, a); auth(wb, b); drain(wa); drain(wb)
        place(a, ap['x'], ap['y'], 'focus'); place(b, ap['x'], ap['y'], 'focus')
        wa.send_json({'type': 'interact', 'object_id': 'desk-0'})
        p = own(wa, 'action', a)['player']
        assert (p['seat_id'], p['x'], p['y'], p['direction'], p['action']) == ('chair#0', 5, 5, 'north', 'working')
        wb.send_json({'type': 'interact', 'object_id': 'chair'})
        assert '다른 사람이 앉아 있어요' in until(wb, 'error')['message']
        # 상태를 바꿔도 앉은 채 유지
        wa.send_json({'type': 'status', 'work_status': 'meeting', 'message': ''})
        p = own(wa, 'status', a)['player']; assert p['seat_id'] == 'chair#0' and p['action'] == 'working'
        # stand → 진입 칸으로 교정, 좌석 해제 → B가 앉을 수 있음
        wa.send_json({'type': 'stand'})
        c = until(wa, 'correction'); assert (c['x'], c['y']) == (ap['x'], ap['y'])
        wb.send_json({'type': 'interact', 'object_id': 'chair'})
        assert own(wb, 'action', b)['player']['seat_id'] == 'chair#0'


def test_move_while_seated_stands_up_and_reconnect_restores_beside_the_chair(client):
    a = login(client, 'SeatC')
    ap = seat('chair#0')['approach']
    with client.websocket_connect('/ws') as ws:
        auth(ws, a); drain(ws); place(a, ap['x'], ap['y'], 'focus')
        ws.send_json({'type': 'interact', 'object_id': 'chair'}); assert until(ws, 'action')['player']['seat_id'] == 'chair#0'
        ws.send_json({'type': 'move', 'scope': 'office', 'zone': 'focus', 'x': ap['x'], 'y': ap['y'] + .3, 'direction': 'south', 'moving': True})
        c = until(ws, 'correction'); assert (c['x'], c['y']) == (ap['x'], ap['y'])
        ws.send_json({'type': 'interact', 'object_id': 'chair'}); assert until(ws, 'action')['player']['seat_id'] == 'chair#0'
    with client.websocket_connect('/ws') as ws:
        snapshot = auth(ws, a)
        p = next(p for p in snapshot['players'] if p['id'] == a['user']['id'])
        assert (p['x'], p['y']) == (ap['x'], ap['y']) and not p.get('seat_id')


def test_face_toward_object_without_seat():
    """의자 없는 책상 등: 선 채로 물체 중심을 바라본다(+x east, -x west, +y south, -y north)."""
    from app.main import face_toward
    me = {'x': 5, 'y': 5, 'direction': 'north'}
    assert face_toward(me, {'x': 6, 'y': 5}) == 'east'
    assert face_toward(me, {'x': 4, 'y': 5}) == 'west'
    assert face_toward(me, {'x': 5, 'y': 6}) == 'south'
    assert face_toward(me, {'x': 5, 'y': 3, 'width': 1, 'height': 2}) == 'north'
    assert face_toward(me, {'x': 5, 'y': 5}) == 'north'
