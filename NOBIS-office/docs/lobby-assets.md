# 로비 에셋 등록과 제작 — Phase 7-B

## 적용 범위

7-A의 RoomManager, 입구 ID, public_enter/meeting_lobby/개인 집 입장 이벤트를 그대로 재사용합니다. 로비 안에 다른 룸의 내부를 그리지 않습니다. 로비 맵은 design/rooms/rooms.json의 maps.lobby이며607개 바닥 타일과7개 입구를 유지합니다. 대기 소파·테이블·화분·램프·기둥11개를 추가했습니다. 중앙 시작점과 넓은 보행 홀을 비워 두고 서버/클라이언트가 같은 footprint를 사용합니다. DB 스키마는 v10 그대로이며 마이그레이션이나 초기화는 필요하지 않습니다.

## 실제 적용한 이미지

- 기존 자체 제작 visual/avatar-*.png:48×64px4방향 캐릭터와 기존 애니메이션.
- 기존 자체 제작 visual/furniture-*.png:소파·화분·램프·테이블·임시 안내 데스크. 같은 아틀라스를 재사용하며 새 사본을 로드하지 않습니다.
- 새 tiles 아틀라스128×32px:64×32 목재/석재 타일2개. 중앙 x11~18/y9~19는 석재, 나머지는 목재입니다.
- 새 architecture 아틀라스512×800px:7종 입구 각각 lower/upper, 벽2방향, 기둥 lower/upper. 총18개128×160 프레임입니다.

새 PNG는 infra/visual/build-lobby-assets.cjs가 직접 그린 프로젝트 내부용 **1차 코드 제작 픽셀 아트**입니다. 최종 일러스트가 공급된 상태가 아닙니다. 생성된 파일을 실제 Phaser texture로 로드하며 참조 이미지를 잘라 쓰거나 전체 배경으로 사용하지 않습니다. 라이선스와 출처는 asset-licenses.json에 추가했습니다. PNG2개 합계 약24KB, 추가 디코딩 메모리 약1.58MiB입니다.

## 폴더와 등록

frontend/public/assets/world/lobby/manifest.json이 편집 원본입니다. tiles/architecture에 내용 해시를 포함한PNG/JSON 아틀라스가 있습니다. furniture/effects의 README는 현재 기존 리소스 재사용 및 Graphics 조명 사용을 명시합니다. frontend/src/game/visual/lobby-manifest.generated.json은 빌드용 사본으로 직접 편집하지 않습니다.

```sh
# 프로젝트 코드 제작 아트를 다시 생성(사용자 제작 이미지가 있으면 먼저 백업)
npm --prefix frontend run assets:lobby
# 직접 등록한 manifest를 소스 사본에 동기화
npm --prefix frontend run assets:lobby:sync
# 맵의 오브젝트/footprint를 변경한 경우
python3 infra/world/build-rooms.py
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e -- lobby-assets.spec.ts hybrid.spec.ts phase35.spec.ts
```

npm dev/build도 manifest 동기화를 수행합니다. 실행 중 맵 생성기를 돌리면 Vite 갱신으로 현재 이동이 중단될 수 있으므로 맵 생성 후 테스트 서버를 실행합니다.

새 이미지는 투명 PNG로 준비하고 규격은 ASSET_SPEC.md를 따릅니다. atlas의 image/data 경로는 assets/world/lobby/로 시작하는 BASE_URL 상대 경로이며 최대2048px입니다. frames는 atlas/frame/rect를 등록합니다. objects의 `오브젝트 ID:에셋 키`가 실제 맵의 visual_asset과 연결됩니다. 예를 들어 portal-cafe→door/cafe는 door/cafe/lower와 door/cafe/upper를 사용합니다. 기존 가구는 visual_asset을 생략해 기존 kind/크기/회전 프레임을 재사용합니다.

이미지를 교체할 때 발 pivot과128×160 프레임을 유지하면 이동 코드를 수정할 필요가 없습니다. 충돌 크기는 PNG 크기에서 추론하지 않고 맵 width/height만 변경합니다. 파일 내용이 바뀌면 파일명에 SHA256의 앞12자리를 넣고 manifest를 갱신합니다. 기존 hashed 파일의 바이트를 덮어쓰지 않습니다. 새 아틀라스와 manifest를 동기화·빌드한 뒤 배포합니다. 현재 이미지 경로가 누락되면 기존 타일/가구 Graphics 또는 기존 가구 아틀라스로 돌아갑니다.

## 새 룸 입구

maps.lobby.objects에 충돌 footprint와 입구를 추가하고 interaction.kind=public_enter/room_type을 지정합니다. defs/maps에는 기존7-A 규칙의 룸 정의와 독립 맵을 등록합니다. visual_asset에 manifest objects의 ID를 지정합니다. 좌측 존 메뉴를 추가하거나 클릭 즉시 순간이동시키지 않습니다. 기존 InteractionSystem이 접근 경로를 찾고 서버가 인접성·정원·권한을 검증합니다. 회의실은 meeting_lobby와 기존 참석자 ACL을 사용합니다.

## 렌더링과 카메라

LobbyCatalog는 순수 설정과 프레임 조회, AssetLoader는 현재 룸의 아틀라스 로드/오류 집계, FloorVisual은 개별 타일, LobbyVisual은 개별 후면 벽/바닥 간접 조명, FurnitureVisual은 하단/상단, CharacterVisual은 기존 발 기준 캐릭터를 담당합니다. 이름표/입구 표지는 Overlay에 유지합니다. 벽은 바닥 외곽에만 그려 기존 이동 영역을 가로막지 않습니다. 기둥과 가구는 실제 맵 오브젝트입니다.

기본 확대는 로비 전용 데스크톱0.85/모바일1.05입니다. 휠/핀치 최소0.55, 최대1.8이며 기존 경계 제한과 추적을 유지합니다. 사용자가 선택한 ‘전체 보기’는 예외적으로 현재 로비 전체가 맞는 fit 배율을 사용합니다. 기본 화면이 축소된 전체 월드로 시작하지 않습니다. 다른 룸은 각자의 기존 카메라/맵을 사용합니다.

## 아직 없는 최종 이미지와 제작 순서

1. 로비 바닥과 벽의 최종 목재/석재 질감, 모서리 캡·몰딩.
2. 안내 데스크 전용 스프라이트, 벽면 안내판/장식.
3. 카페/집중/유리 회의실/라운지/정원 아치/테라스/개인 집 입구의 최종 테마 원화.
4. 로비 소파·테이블·화분·기둥의 최종 통일된 가구 원화.
5. PNG 조명·반짝임/식물 효과(현재 간접 조명은 Graphics).

이 항목들은 완성했다고 보고하지 않습니다. 우선 현재128×160/64×32의 동일 pivot 규격으로 제작한 뒤 manifest의 같은 ID로 교체합니다. 캐릭터 최종 디자인은 이번 범위 밖이며 기존 자체 제작 리소스를 유지합니다.

## 배포와 ARM64

기존 Docker/PostgreSQL 설치·백업/복구/새 서버 이전 지침은 README를 유지합니다. 현재 PC는 최종 운영 서버가 아닙니다. Docker build는 manifest 동기화 스크립트와 public 파일을 포함합니다. Nginx는 /assets/world/의 없는 파일을404로 반환하며 해시PNG/JSON만1년 immutable, 일반 manifest는 재검증합니다. 이미지 렌더링은 브라우저 GPU/클라이언트 CPU 비용이고 FastAPI의 서버 비용과 다릅니다. 새 로비 아틀라스는 로비에서만 로드하며 최대2048px를 검증합니다. Raspberry Pi 실기기15브라우저 부하는 별도 대상입니다.
