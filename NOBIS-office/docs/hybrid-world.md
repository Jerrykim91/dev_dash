# Hybrid World — Phase 7-A

## 기존 구현과 변경 경계

기존 OfficeScene은 shared/maps.json의 큰 비대칭 단일 맵을 렌더링했고 ZoneSystem이 타일 경계로 채팅 위치를 갱신했습니다. HomeScene은 scope 변경으로 별도 게임 인스턴스를 만들었습니다. 후자의 교체 흐름을 공용 룸에도 적용했습니다. A*·CoordinateSystem·MovementSystem·CollisionSystem·카메라 제스처 및 개인 집 카탈로그/소유권/배치는 유지합니다. 서버의 이동 유효성 검사에는 현재 룸 맵만 전달합니다.

## 계층과 데이터

World(nobis) → Channel(ch1, ch2, …) → Room Instance입니다. 공용 정의7개는 lobby/cafe/focus/lounge/garden/terrace/meeting이며 개인 집 home은 기존 HomeService를 재사용합니다. public:채널:타입, meeting:채널:회의대화ID, personal:소유자ID가 인스턴스 식별자입니다. 같은 채널과 인스턴스인 사용자만 위치/행동을 공유합니다.

| 룸 | 맵 크기 | 바닥 타일 | 용도 |
|---|---:|---:|---|
| 로비 |30×24|607|중앙 홀, 안내 데스크,6개 룸 입구,개인 집 입구|
| 카페 |19×21|244|카운터, 커피, 테이블|
| 집중 업무실 |38×36|712|15개 작업 구획, 구획마다3×3, 책상·의자|
| 라운지 |27×29|537|소파, 장식, 게임기|
| 휴식 정원 |28×28|402|기존 옥상 정원·휴식 공간 통합|
| 외근 테라스 |21×24|320|야외 가구와 난간|
| 회의실 |23×19|247|15좌석, 참석자 ACL, 동일 템플릿의 독립 회의|

각 수치는 가구가 차지한 칸을 포함한 바닥입니다. 모든 공용 룸의 출구는 가구와 최소5칸의 맨해튼 거리를 두고 바닥의 연결성을 유지하는 가장자리 위치에 배치합니다. 휴가 전용 맵은 없으며 ‘휴가 중’ 상태에서도 이동합니다. 개인 집은 기존 독립 맵/가구 데이터입니다. map_id/zone_id는 호환 계층으로 유지하되 좌표는 룸 안에서만 의미를 갖습니다.

RoomManager(backend/app/rooms.py)는 정의·인스턴스·입장 계획·정원·회의 참석권한·마지막 룸 복원·목록·집의 공통 메타데이터를 관리합니다. 개인 집 입장 권한/방문 승인은 기존 integration/HomeService가 검증합니다. room_access_policies 별도 테이블은 만들지 않고 기존 membership/방문 ACL과 access_policy 필드를 재사용합니다.

## 입장과 복귀

1. 입구 오브젝트 클릭/탭 → 기존 InteractionSystem이 접근 가능한 인접 타일까지 A* 경로를 계산합니다.
2. 도착하면 interact(object_id)를 전송합니다. 서버가 현재 룸 맵의 오브젝트인지, 실제 인접했는지, 정원·회의 참석권한을 확인합니다.
3. 검증이 통과하면 기존 룸에 left, 본인에 현재 룸 맵/사용자 snapshot, 새 룸에 joined를 보냅니다. 검증 실패는 기존 룸/좌표를 유지합니다.
4. React가 맵·플레이어·룸 식별자를 하나의 스토어 업데이트로 적용하고 이전 Phaser 인스턴스를 정리한 뒤 현재 룸 Scene 하나만 만듭니다. 개인 집 전환도 이전 룸 left와 본인 snapshot/대상 룸 scope_changed만 전송해 무관한 사용자의 이동을 취소하지 않습니다. 로딩 안내는 생성 완료 시 사라집니다.
5. 룸 출입문까지 걸어가 public_exit → 로비의 해당 입구 앞에 생성합니다. 개인 집 문은 마지막 공용 룸과 위치로 복귀합니다.

재접속은 저장된 룸의 현재 권한/정원/이동 가능 위치를 검사합니다. 회의가 종료되거나 권한이 사라졌으면 로비로 복귀합니다. 채널별 마지막 공용 룸을 따로 저장합니다. 중복 접속/채널 정원 처리는 기존 정책을 유지합니다. 서버가 보내는 world_revision에는 룸 인스턴스와 맵 해시가 들어갑니다. 같은 연결에서 같은 맵 재전송은 생략하며 새 연결에는 다시 보냅니다.

## 채팅과 개인정보

월드 채팅은 서비스 전체, 채널 채팅은 해당 채널 전체입니다. UI의 기존 ‘현재 존’ 탭은 같은 룸 채팅입니다. 회의실 룸 채팅은 인스턴스별 독립 키를 사용합니다. 초대 대화방은 기존 membership ACL을 별도로 검증합니다. 다른 룸/채널 귓속말은 directory의 user_id를 사용합니다. 초대 사용자 목록도 좌표 없는 directory를 사용합니다.

위치·행동·오브젝트 효과·말풍선은 같은 룸으로만 전송합니다. 다른 룸의 위치를 마스킹한 플레이어를 보내지 않습니다. 인원 집계는 숫자만 전달합니다. 말풍선은 설정이 켜진 일반 공용 룸에서만 표시하고 집중 업무실·회의실·개인 집·귓속말·초대 대화는 제외합니다. 공지·소셜 알림은 기존 전달 정책대로 룸 전환과 무관하게 유지합니다.

## 맵·에셋 등록

`design/rooms/rooms.json`의 definitions에 room_type, room_id, map_id, zone_id, access_policy, max_occupancy, spawn_point, exit_point, portal_id, lobby_return을 등록합니다. maps의 해당 키에 width/height, tile 크기, walkable_tiles, blocked/objects, spawn/exit를 작성합니다. 로비 objects에는 public_enter 목적 룸을 설정합니다. 회의실 입구는 meeting_lobby, 내부 출구는 public_exit입니다. 생성기는 `python3 infra/world/build-rooms.py`입니다. `build-world.py`도 같은 생성기로 연결됩니다.

충돌은 타일/가구 footprint, 렌더링은 asset_key와 발 위치로 분리합니다. 독립 룸은 현재 평면 맵이며 룸 사이에 계단 그래프는 필요하지 않습니다. 향후 한 룸 안 높이를 추가하면 기존 surface/connector와 충돌 데이터를 함께 검증해야 합니다. 건축 팔레트는 architecture-palette.json에 별도로 두며 이전 shared/world-layout.json은 런타임에서 읽지 않습니다.

에셋은 frontend/public/visual 및 frontend/src/game/visual/manifest.json을 사용합니다. 실제 교체 지점은 FloorVisual.ts, ArchitectureVisual.ts, FurnitureVisual.ts, CharacterVisual.ts와 manifest입니다. 상세 프레임/라이선스는 visual-system.md를 참고하세요. 이번 작업에 새로운 최종 이미지 에셋은 없습니다. 기존 자체 제작 아틀라스를 재사용하고 대형 회의 테이블은 placeholder로 표시합니다.

필요한 최종 에셋: 로비 출입구6종과 안내 데스크, 룸별 바닥/벽/난간, 카페 카운터/커피, 15석 업무실용 책상·의자·모니터·파티션, 대형 회의 테이블·화이트보드, 정원 수목·조명, 테라스 장식, 캐릭터4방향 idle/walk/sit/type. 발 기준 pivot, 시각 크기와 footprint를 분리하고 기존64×32 타일 투영 비율을 유지합니다. 이미지 한 장을 맵 배경으로 쓰지 않습니다.

## DB와 배포

v10은 기존 테이블 삭제 없이4개 테이블을 추가합니다. 정의는 서버 시작 시 소스에 맞게 갱신하며 인스턴스는 실제 입장 시 생성합니다. room_presence는(user_id,channel_id) 키와 room_instances FK를 사용합니다. 개인 집 데이터는 기존 personal_homes/가구 테이블에 유지합니다. SQLite→PostgreSQL import-sqlite도 새 FK 순서를 포함합니다.

서버1프로세스가 룸 전체를 관리합니다. 기존 Docker Compose의 backend/frontend/postgres3서비스·기존 볼륨을 사용하며 룸별 Docker는 만들지 않습니다. 운영 이전/pg_dump·pg_restore/SQLite 백업·이미지 볼륨 복원은 README의 기존 절차를 따릅니다. 코인 가챠 확률과 사용자 데이터는 변경하지 않습니다. 이전 단일 맵의 좌표만 첫 접속에 로비로 안전 복귀합니다.
