# Phase 7-A · 비대칭 Office World 구조

2026-11-07 후속 지시를 우선 적용했습니다. **이번 단계는 맵·배치·동선·계단·충돌의 실제 구현이며 최종 원화 적용은 다음 단계**입니다. 기존 프로젝트/DB/인증/채팅/개인 집/게임/코인 구조를 재작성하지 않습니다.

복구 지점은 Git `4af9fc9`(직전 커밋035bbe5 포함)입니다. Git이 없던 NOBIS 폴더에만 초기화하고 기존 소스·설정으로 로컬 커밋을 만들었습니다. 비밀 환경·사용자 DB·의존성·백업은 커밋하지 않았습니다. 기존 별도 백업은 backups/before-phase7a-20261107.zip 및 .sqlite3입니다. DevNest에 Git 작업/소스 수정을 하지 않았습니다.

참조는 사용자가 지정했던 `../design/reference/nobis-office-target.png`입니다. 후속 이름 office-world-target.png는 별도로 없어 동일 파일을 `design/reference/office-world-target.png`에 참조용으로 보관했습니다. 최종 공간 배치는 후속 지시서의 상대 위치를 따릅니다. 그림 전체/그림에서 잘라낸 오브젝트를 게임 텍스처로 사용하지 않습니다.

## 기존 구현 분석과 재사용

- Phaser: frontend/src/game/scenes/OfficeScene.ts와HomeScene.ts가 WorldScene.ts를 공유합니다. 오피스는 하나의 Scene이고 개인 집만 별도 인스턴스입니다.
- 원래 맵은 shared/maps.json의36×28 직사각형과90개 가구/파티션,존은 zones.json의 여섯 동일 크기 사각형이었습니다.
- 좌표는 CoordinateSystem의64×32 아이소메트릭 타일입니다. 화면→카메라 월드 역변환(CameraSystem)→표면 타일(SurfaceCoordinates) 순서입니다.
- 기존 A* PathfindingSystem,속도/경로 추종 MovementSystem,오브젝트 접근 InteractionSystem을 재사용합니다. WASD/존 이동/순간이동 버튼을 추가하지 않습니다.
- WebSocket 위치는 기존 x/y·direction·zone 계약을 유지합니다. 서버가 실제 위치에서 zone을 계산하고 속도/장애물·층 경계/출입구를 검증합니다.
- 집 입장은 기존 bookshelf 오브젝트 접근→메뉴→room_enter입니다. 이 오브젝트 ID/상호작용과 개별 홈 데이터는 보존하고 오피스 내 위치만 변경했습니다.
- 카메라 줌/핀치/드래그/추적/전체 보기 로직은 유지하고 새 바닥 영역의 실제 투영 경계로 카메라 bounds를 계산합니다.

## 새 공간 배치

균등3×2 분할과 중앙 십자 통로를 제거했습니다. 전체 좌표 범위는58×54지만 **실제 바닥은1,150칸**이고 나머지는 이동 불가 void입니다. 다각형 방/중앙 홀/폭이 다른 연결로를 합쳐 하나의 연결 그래프를 구성합니다. 가구34개는 기존 상호작용 계약을 유지하고 출입구·계단과 앵커를 막지 않도록 배치합니다.

| 화면 위치 | 시각 공간 | 기존 존ID | 바닥 칸 | 높이(px) |
|---|---|---|---:|---:|
|좌측 상단|카페|cafe|107|24|
|상단 중앙|회의실|meeting|110|48|
|우측 상단|옥상 정원|vacation|73|72|
|좌측 중앙|집중 업무존|focus|124|0|
|중앙|중앙 라운지|lounge|241|0|
|우측 중앙|휴식 공간|lounge|74|24|
|좌측 하단|휴가 정원|vacation|115|0|
|하단 중앙|메인 입구|office|109|0|
|우측 하단|외근 · 테라스|outside|141|24|

중앙 라운지는241칸으로 가장 넓습니다. 옥상 정원은 vacation,우측 휴식 공간은 lounge의 시각 하위 공간입니다. 기존 주요6개 존ID와 말풍선/근무/채팅 규칙은 그대로입니다. 개인 집은 월드에 방을 그려 넣지 않고 기존 개별 인스턴스로 연결합니다.

[실제 배치도](phase7a-layout.svg)와 [브라우저 전체 화면](phase7a-asymmetric-overview.png)을 비교할 수 있습니다.

## 데이터 분리와 생성

```text
design/world/office-world-v2.json   수동 편집하는 원본: 다각형·높이·연결·가구ID
design/world/object-contracts.json 기존 가구/상호작용 계약 사본
infra/world/build-world.py         맵 생성기,DB 접근 없음
shared/maps.json                   WorldMap + WalkableMap + Obstacle + ObjectPlacement
shared/zones.json                  기존ID/규칙 + 비직사각형 cells 마스크
shared/world-layout.json           VisualLayer/하위공간/Connector/표면 높이
frontend/src/game/systems/         기존A* + Surface/Collision/Zone 확장
frontend/src/game/visual/          임시 바닥/벽/난간/계단 표시
backend/app/world.py               동일 공유 데이터의 서버 검증
```

원본 다각형은 화면의 상대 배치를 편집하기 쉬운 u=x-y,v=x+y 좌표입니다. 생성기는 이를 기존 논리 타일 x=(v+u)/2,y=(v-u)/2로 변환합니다. 런타임/UI에 방 좌표를 하드코딩하지 않습니다.

```sh
python3 infra/world/build-world.py
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

생성기는 다각형을4방향 타일로 변환하고 방 사이 연결로를 만듭니다. 가구가 통행 가능한 모서리/출입구를 고립시키는 후보는 배치하지 않습니다. 수동으로 생성 JSON만 변경하면 다음 생성 때 덮어쓰므로 원본 정의를 수정하세요. 기존 사용자 DB·지갑·가구 인스턴스에 접근하거나 초기화하지 않습니다.

## 존·충돌·계단

존의 bounding tiles는 호환/표시 정보이고 실제 경계는 cells 마스크입니다. 옥상 정원처럼 떨어진 같은 존 하위 영역도 같은ID로 처리합니다. 클라이언트 ZoneSystem과 서버 zone_at이 같은 마스크를 사용합니다.

- WalkableMap: 실제 바닥 셀만 이동 가능. 밖/빈 공간은 불가.
- Obstacle: 기존 가구 footprint. 경로에서 제외합니다.
- closed_edges: 방/층 사이 닫힌 벽·난간. 같은 높이여도 통과 불가.
- Connector: 실제 복도 경로13개, 출입구 경계16개와 높이 변경 계단8개. 출입구/계단만 닫힌 경계를 개방합니다.
- Surface:0/24/48/72px. 지정된 계단의 논리 이웃 edge에서만 높이가 변합니다. 계단4단은 바로 그 edge를 그립니다.
- A*는 기존 알고리즘으로 CollisionSystem.neighbors를 탐색합니다. 재클릭 취소·가장 가까운 접근 가능 지점·가구 접근을 유지합니다.
- 서버 valid_move는 유한 좌표/속도/보간 샘플 검사에 바닥 마스크·closed edge·계단 검사를 적용합니다. 클라이언트가 높이/존을 임의 결정하지 않습니다.
- 캐릭터는 논리 위치를 보간한 뒤 높이를 적용하고 발 위치로 깊이를 정렬합니다. floor picking은 가려진 지면보다 앞 표면을 선택하고 계단의 투영도 별도로 역변환합니다.

현재 타일 하나에 지면 높이 하나입니다. 같은 x/y에 겹친 교량 두 층은 이번 모델의 범위가 아니며 미래에는 node/level 구분과 프로토콜 검토가 필요합니다. 서로 연결되지 않은 층 사이 순간이동을 만들지 않습니다.

기존 저장 위치가 새 맵에서 유효하지 않으면 기존 서버의 재접속/집 복귀 검증을 통해 메인 입구의 안전한 spawn으로 복귀합니다. 유효한 저장 위치는 유지하면서 zone을 재계산합니다. 계정·집 꾸미기·재화 DB를 이동시키거나 삭제하지 않습니다.

## 렌더링과 다음 에셋 교체

새 최종 픽셀 아트는 적용하지 않았습니다. 기존 Phase7 캐릭터/가구 PNG3개·JSON3개는 호환용 임시 아트로 유지합니다. 바닥은 코드 색/타일,벽·유리·난간·계단은 실제 논리 경계를 그리는 코드 도형입니다. 배경 이미지 한 장으로 대체하지 않습니다.

| 파일 | 다음 작업 |
|---|---|
| game/visual/FloorVisual.ts | 목재/석재/정원 타일셋,계속 같은 walkable 셀 사용 |
| game/visual/ArchitectureVisual.ts | 경계별 벽/난간/계단 이미지,닫힌 edge/계단 개방을 유지 |
| game/visual/FurnitureVisual.ts | 기존 asset_key/footprint에 방향별 가구 lower/upper 연결 |
| game/visual/CharacterVisual.ts | 발 pivot/4방향/idle-walk-sit-type 유지하며 최종 스프라이트 교체 |
| game/visual/catalog.ts 및 overrides.json | 실제 확보한 PNG/JSON·프레임·피벗 등록 |
| design/tokens.json,system.css | 최종 색/공통 UI 조정 |

필요 이미지 규격은 바닥64×32,가구128×160(기존발64,104),캐릭터48×64(발24,58)를 시작점으로 합니다. 벽/유리/난간은 바닥 edge 방향별 앞뒤 조각,계단은24/48/72 높이 연결에 대응하는 타일 모듈·상하단,나무/조명은 독립 발 pivot으로 제작합니다. 아틀라스는2048px 이하/내용 해시 파일명,기존 asset-licenses.json에 출처/권한을 기록합니다. 실제 원화 크기를 바꿀 때는 manifest의pivot/rect/scale만 조정하고 충돌 데이터를 그림으로 추정하지 않습니다.

## UI와 검증

서비스 메뉴/친구·접속자는 좌측,존 버튼은 없습니다. 채팅 접기 상태를 로컬에 저장하고 소켓/수신은 유지합니다. 실제 캔버스/입력 배율까지 같이 리사이즈하며 채팅 전용 모드는 접힘과 관계없이 채팅을 보여 주고 렌더링을 멈춥니다. 모바일은 월드/채팅 전환과 터치 이동을 유지합니다.

[실행 결과·기능 회귀·변경 파일](phase7a-verification.md)을 참조하세요. 실제 검증 결과와 아직 검증하지 않은 환경을 구분합니다.
