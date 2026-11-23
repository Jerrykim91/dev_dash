"""옷 갈아입기(파트 외형): 저장·방송·검증·재접속 유지·기본 외형 복귀 (docs/visual-standard-v2.md §15)."""
from test_server import client, login, auth  # noqa: F401
from test_phase2 import until, drain


def test_avatar_parts_broadcast_validate_persist_and_reset(client):
    a, b = login(client, 'Wearer'), login(client, 'Watcher')
    with client.websocket_connect('/ws') as wa, client.websocket_connect('/ws') as wb:
        auth(wa, a); auth(wb, b); drain(wa); drain(wb)
        wa.send_json({'type': 'avatar_parts', 'parts': {'hair': '1', 'top': 'hoodie', 'bottom': 'skirt'}})
        seen = until(wb, 'status')['player']
        assert seen['id'] == a['user']['id'] and seen['avatar']['parts'] == {'hair': '1', 'top': 'hoodie', 'bottom': 'skirt'}
        assert seen['avatar']['palette']  # 팔레트(완성 캐릭터 대체용)는 유지
        wa.send_json({'type': 'avatar_parts', 'parts': {'hair': '9', 'top': 'cape', 'bottom': 'skirt'}})
        assert until(wa, 'error')['message'] == '고를 수 없는 외형입니다.'
    # 다시 접속해도 유지
    with client.websocket_connect('/ws') as wa:
        snap = auth(wa, a)
        me = [p for p in snap['players'] if p['id'] == a['user']['id']][0]
        assert me['avatar']['parts'] == {'hair': '1', 'top': 'hoodie', 'bottom': 'skirt'}
        wa.send_json({'type': 'avatar_parts', 'parts': None})
        assert 'parts' not in until(wa, 'status')['player']['avatar']
    with client.websocket_connect('/ws') as wa:
        me = [p for p in auth(wa, a)['players'] if p['id'] == a['user']['id']][0]
        assert 'parts' not in me['avatar']
