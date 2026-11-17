# Hybrid World 변경 파일

설계와 결과는 hybrid-world.md, hybrid-verification.md를 참조하세요. 기존 단일 맵은 Git 복구 지점과 archive 문서로 보존합니다.

## 서버·DB·실시간

- `backend/app/cli.py`
- `backend/app/database.py`
- `backend/app/db_transfer.py`
- `backend/app/games/api.py`
- `backend/app/main.py`
- `backend/app/repository.py`
- `backend/app/rooms.py`
- `backend/app/rooms_schema.py`
- `backend/app/services/work_status.py`
- `backend/app/websocket/hub.py`
- `backend/app/world.py`

## 맵 원본·생성기·공유 데이터

- `design/rooms/rooms.json`
- `design/world/build-asymmetric-archive.py`
- `design/world/office-world-v2.json`
- `infra/world/build-rooms.py`
- `infra/world/build-world.py`
- `shared/maps.json`
- `shared/rooms.json`
- `shared/zones.json`

## 프런트·렌더링

- `frontend/src/App.tsx`
- `frontend/src/components/ChannelManager.tsx`
- `frontend/src/components/ChatPanel.tsx`
- `frontend/src/components/GameWorld.tsx`
- `frontend/src/components/MeetingRoomLobby.tsx`
- `frontend/src/components/TopBar.tsx`
- `frontend/src/design/system.css`
- `frontend/src/design/tokens.json`
- `frontend/src/game/bridge.ts`
- `frontend/src/game/maps.ts`
- `frontend/src/game/scenes/WorldScene.ts`
- `frontend/src/game/systems/ZoneSystem.ts`
- `frontend/src/game/systems/surface.test.ts`
- `frontend/src/game/systems/systems.test.ts`
- `frontend/src/game/types.ts`
- `frontend/src/game/visual/ArchitectureVisual.ts`
- `frontend/src/game/visual/FloorVisual.ts`
- `frontend/src/game/visual/architecture-palette.json`
- `frontend/src/game/visual/visual.test.ts`
- `frontend/src/stores/officeStore.ts`
- `frontend/src/useOffice.ts`

## 검증

- `backend/tests/archive/README.md`
- `backend/tests/archive/test_every_walkable_tile_and_zone_connected.py.txt`
- `backend/tests/archive/test_partition_collision_and_doorway.py.txt`
- `backend/tests/archive/test_phase7a.py.txt`
- `backend/tests/archive/test_walking_boundary_changes_zone_and_channel_permissions.py.txt`
- `backend/tests/archive/test_world_sync.py.txt`
- `backend/tests/test_games.py`
- `backend/tests/test_hybrid.py`
- `backend/tests/test_phase2.py`
- `backend/tests/test_phase3.py`
- `backend/tests/test_phase35.py`
- `backend/tests/test_phase7a.py`
- `backend/tests/test_server.py`
- `backend/tests/test_social.py`
- `tests/archive/README.md`
- `tests/archive/capacity.spec.ts.txt`
- `tests/archive/office.spec.ts.txt`
- `tests/archive/phase7a.spec.ts.txt`
- `tests/hybrid.spec.ts`
- `tests/office.spec.ts`
- `tests/phase2.spec.ts`
- `tests/phase3.spec.ts`
- `tests/phase4.spec.ts`
- `tests/phase7.spec.ts`
- `tests/phase7a.spec.ts`
- `tests/room-fixture.ts`
- `tests/social.spec.ts`
- `tests/world-fixture.ts`

## 문서

- `README.md`
- `docs/architecture.md`
- `docs/history/before-hybrid-architecture.md`
- `docs/history/before-hybrid-implementation-plan.md`
- `docs/history/before-hybrid-storyboard.md`
- `docs/hybrid-changes.md`
- `docs/hybrid-performance.json`
- `docs/hybrid-verification.md`
- `docs/hybrid-world.md`
- `docs/implementation-plan.md`
- `docs/storyboard.md`

## 이미지·보존

새 최종 아트 제작은 제외했습니다. docs/hybrid-*.png는 실제 실행 캡처입니다. 이전 문서 이미지는 원본으로 복원하고 새 회귀 캡처는 Projects/캡처/NOBIS-Office_Hybrid_2026-11-07에 저장했습니다. DevNest123개 파일과 기존 사용자/경제 데이터11개 테이블은 유지했습니다.
