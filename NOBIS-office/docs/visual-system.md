# NOBIS Office Visual System v1 · Phase 7

이번 버전은 기존 게임 로직 위에 적용한 **첫 코드 제작 픽셀 아트**입니다. 외부 에셋이나 기존 디자인 이미지 전체를 배경으로 사용하지 않았습니다. 최종 브랜드 원화 확정과 구별합니다. 캐릭터/가구는 독립 스프라이트이고 바닥·벽·오브젝트·이름표는 별도 레이어입니다.

## 디자인 토큰

원본은 `frontend/src/design/tokens.json`입니다. `colors`는 배경/표면/텍스트/강조/크림/성공/경고/오류/정보, `font`는 시스템 한글 본문과 모노스페이스 제목, `radius`와 `motion`은 공통 모서리와120/180/350ms 동작, `world`는 각 존의 시각 팔레트입니다. 기존 shared zones의 API 색/경계는 보존하며 신규 월드 렌더러만 world 팔레트를 적용합니다.

`tokens.css`는 같은 JSON에서 생성합니다. 기존 주요 UI CSS의 literal hex 색은 공통 변수로 정리했고 마지막에 `design/system.css`를 적용합니다. 로그인/헤더/사이드바/채팅/공지/프로필/그룹/상점/도감/개인 집/미니게임/출석/가챠/관리자가 공통 버튼·탭·표면·포커스·모달 스타일을 사용합니다. 데이터에 포함된 기존 아바타 팔레트/존 accent와 비상용 Legacy SVG/PlaceholderArt의 기존 색은 호환용으로 보존합니다.

한글 글꼴 파일은 새로 받지 않았습니다. OS 한글 시스템 폰트를 본문에 사용하고 제목은 시스템 모노스페이스를 우선합니다. 전용 한글 픽셀 폰트는 사용 권한을 확보한 뒤 별도 등록할 자료입니다.

## 디렉터리와 제작

```text
frontend/src/design/              tokens, 공통 스타일, PixelMark/Icon, 초상화, 로그인 장면
frontend/src/game/visual/         catalog, loader, 캐릭터/가구/바닥 렌더러
  manifest.json                  생성된 기본 에셋·프레임·피벗·애니메이션
  overrides.json                 수동 등록/교체(기본 {}, 생성기가 덮어쓰지 않음)
frontend/public/visual/           실제 해시 PNG 아틀라스와 Phaser JSON Hash
frontend/src/game/art/PlaceholderArt.ts 비상용 기존 도형
frontend/src/components/LegacyFurniturePreview.tsx 비상용 기존 썸네일
infra/visual/build-assets.cjs     네트워크 없이 Canvas로 만드는 원본 제작 스크립트
```

실제 적용본은 PNG3개(캐릭터1·가구2), JSON3개, 총788프레임입니다. 캐릭터640프레임, 가구148프레임(하단/상단74쌍)입니다. 원본 PNG 총348,932바이트, 최대1536×1280 또는1024×1600/1440입니다. 모두2048px 이하이며 RGBA 기준 아틀라스 메모리 산술 추정은20,316,160바이트입니다. 이 수치는 텍스트/프레임버퍼/드라이버 메모리를 포함한 GPU 실측값은 아닙니다.

```sh
# 프로젝트 루트, 기존 개발 의존성 설치 후
npm --prefix frontend run assets:build
npm --prefix frontend run test:visual
npm --prefix frontend run build
```

제작에는 로컬 Chrome과 기존 Playwright를 사용합니다. 기본 Chrome 경로는 macOS이며 다른 환경은 CHROME_BIN을 지정합니다. 생성기는 기존 맵/카탈로그를 읽기만 하고, shared/서버/충돌 데이터를 수정하지 않습니다. **일반 빌드/Docker 빌드는 생성기를 실행하지 않으며 이미 생성된 PNG/JSON을 패키징**합니다. 따라서 운영 서버에 Chrome이나 아트 제작 도구를 설치할 필요가 없습니다.

## 캐릭터 규격과 애니메이션

- 프레임48×64px, 발 픽셀(24,58), Phaser origin(0.5,0.90625), 표시 배율1.125.
- 2~3등신의 원본 코드 픽셀 아바타16개 외형. 피부/머리/옷을 프레임에서 그리며 전체 몸체 tint로 피부색을 바꾸지 않습니다.
- 기존 서버 palette16개를 같은 순서로 외형에 연결하고, 알 수 없는 palette는 사용자ID의 안정적 해시로 선택합니다. 네트워크의 기존 avatar.id 계약은 바꾸지 않고 렌더러 manifest.version을 별도로 둡니다.
- 방향은 기존 north/south/east/west를 그대로 사용합니다. 아이소메트릭 좌표나 이동 방향 계산을 바꾸지 않습니다.

| 상태 | 프레임 | fps | 전환 |
|---|---:|---:|---|
| idle | 2 | 1.2 | 정지 기본 |
| walking | 4 | 8 | 실제 이동 중, 다른 포즈보다 우선 |
| sitting | 2 | 1.5 | sitting/resting 액션 |
| typing | 2 | 5 | working/typing 액션 |

키는 `v0/south/walking/0` 형태입니다. 프레임명은 Phaser JSON Hash와 manifest.frames 양쪽에서 연결합니다. 발 기준점은 포즈마다 동일하며 충돌은 기존 그리드 좌표에만 의존합니다. 이름표/말풍선은 표시 크기·발 피벗에서 머리 위치를 계산하고 기존 화면 좌표 겹침 방지 시스템을 유지합니다. 동작 줄이기 설정에서는 포즈/방향의 첫 프레임으로 표시합니다.

## 캐릭터 이미지 교체

1. 새 PNG와 JSON Hash를 `frontend/public/visual/`에 추가합니다. PNG와 JSON 각각의 실제 내용 해시를 파일명에 넣습니다.
2. 같은 레이아웃/프레임명이라면 overrides.atlases에서 `nobis-avatar-0`의 image/data/width/height/bytes만 바꿉니다.
3. 크기·피벗이 다르면 overrides.avatar에 width/height/origin/scale/portrait를 등록합니다. **이동/충돌 코드는 수정하지 않습니다.**
4. 프레임 위치/이름이 다르면 overrides.frames의 `avatar/vN/방향/상태/인덱스` 항목에 atlas/실제frame명/rect를 등록합니다. 초상화 크롭도 이 rect를 사용합니다.
5. 애니메이션 설정을 바꿀 때는 avatar.animations에4개 필수 상태의 frames/fps를 모두 제공합니다. 현재 avatar 오버라이드는 얕은 병합이므로 animations 전체를 대체합니다.
6. test:visual → build → 브라우저에서 이동/정지/작업/앉기/이름표를 확인합니다.

```json
{
  "atlases": [{
    "key": "nobis-avatar-0",
    "image": "visual/avatar-실제PNG내용해시.png",
    "data": "visual/avatar-atlas-실제JSON내용해시.json",
    "width": 1536, "height": 1280, "bytes": 0
  }],
  "avatar": {"width":48,"height":64,"origin":{"x":0.5,"y":0.90625},"scale":1.125,
    "portrait":{"x":6,"y":0,"w":36,"h":34}}
}
```

예시 파일명과 bytes는 실제 자료로 대체합니다. 기존 key와 같은 atlas 등록은 그 atlas만 교체하며, 다른 key는 기존 목록에 추가됩니다. 생성기는 overrides.json을 덮어쓰지 않습니다. 프레임/이미지가 없으면 클립은 같은 외형의 idle, 그것도 없으면 기존 도형으로 대체합니다. 캐릭터 이동은 계속 동작합니다.

## 가구 등록·회전·미리보기

가구는 카탈로그의 item_id → asset_key → `kind/widthxheight/rotation/lower|upper`로 연결합니다. 예: `desk/2x1/0/lower`, 회전90도는 서버가 계산한 footprint대로 `desk/1x2/90/lower`입니다. 기존 카탈로그/보유 인스턴스/설치 좌표/rotation을 바꾸지 않습니다.

- 셀128×160, 발 기준 픽셀(64,104), origin(0.5,0.65).
- 하단/상단을 별도 이미지와 world depth로 배치합니다. 공통 ground anchor의 depth±0.15, 캐릭터는 기존 발 depth+1입니다. 전체 상단을 모든 캐릭터 위에 고정하지 않습니다.
- 상점/인벤토리/도감은 같은 아틀라스의 lower/upper를 SVG image로 조합합니다. previewBounds는 투명 여백을 뺀 썸네일 영역이며 월드 피벗/충돌을 바꾸지 않습니다.
- 회전0/90/180/270 등록을 지원합니다. v1 일부 대칭 가구는 반대 방향에서 같은 실루엣을 사용하며 정식 방향별 뒤/옆 디테일은 추후 다듬을 자료입니다.
- 유효/불가 배치 색상과 선택된 가구·회수/저장 로직은 기존 PlacementSystem을 그대로 사용합니다. ghost도 같은 에셋/rotation을 사용합니다. 설치·회수 연출은 FurnitureVisual의 alpha/scale/lifecycle에 추가할 수 있습니다.

새 가구의 논리 footprint/가격/소유권 추가는 별도 기능 작업입니다. **이미지 교체에는 그 값을 수정하지 않습니다.** overrides.frames에 기존 logical key의 lower/upper를 새 atlas frame에 연결하고, 필요한 경우 furniture.previewBounds에 각 `kind/widthxheight/rotation`의 크롭을 등록합니다. 알 수 없는 가구/이미지 누락은 기존 도형/Legacy 썸네일을 사용합니다.

## 바닥·벽·타일셋

기본 바닥은 FloorVisual의 코드 픽셀 패턴이며, world 토큰으로 집중/카페/라운지/회의/휴가/외근과 개인 집을 구분합니다. 후면 벽은 시각 레이어만 추가합니다. 원래 벽/파티션 장애물과 단일 Office Scene을 유지하며 새로운 이동 차단 칸은 만들지 않습니다.

새 타일셋을 확보한 경우 overrides.atlases에 별도 key를 추가하고, tilesets의 존ID를 frame에 연결합니다. 권장 프레임64×32 투명 다이아몬드, origin(0.5,0.5)이며 렌더러가 기존 CoordinateSystem의64×32에 맞춥니다. 셀/존/클릭 좌표는 바뀌지 않습니다.

```json
{
  "atlases":[{"key":"office-floor","image":"visual/실제해시.png","data":"visual/실제해시.json","width":256,"height":128,"bytes":0}],
  "tilesets":{"focus":{"atlas":"office-floor","frame":"focus-floor","rect":{"x":0,"y":0,"w":64,"h":32}}}
}
```

현재 출하 아트에는 별도 이미지 타일셋이 없으므로 기본 코드 패턴을 사용합니다. 선택 등록 경로는 준비했고, 실물 타일셋의 아트 검수는 확보 후 필요합니다. 타일 프레임이 없으면 코드 패턴으로 대체합니다.

## 레이어·입력·동작

`catalog.visualLayers`: 벽-1002, 바닥-1000, 바닥장식-990, 존 캡션-900, 러그-850, 이동경로-800, 목적지-700, 효과100000, 배치미리보기100001, 레이블100010. 가구/캐릭터는 기존 world 좌표의 발 깊이로 정렬합니다. PNG는 시각 범위만 바꾸고 기존 hit 영역·그리드 충돌·A*·MovementSystem·CameraSystem은 보존합니다. 다른 사용자 클릭은 기존 프로필 동작입니다.

클릭 가능 물체는 hover 강조와 짧은 상호작용 반응을 사용합니다. 모달 진입/종료180ms, 공지/결과는 공통 짧은 동작을 사용하며 기존 가챠 결과 건너뛰기 버튼을 유지합니다. prefers-reduced-motion에서는 비필수 CSS 동작을 중지하고 캐릭터 정지 프레임을 사용합니다. 공개 채팅 말풍선과 상태 메시지는 기존 권한/금지 존/겹침 처리 정책을 유지합니다.

## 성능·배포·라이선스

아틀라스는 Scene texture cache를 확인하여 중복 큐잉하지 않습니다. 애니메이션은 외형/방향/상태가 달라질 때만 다시 선택합니다. UI 미리보기는 같은 PNG URL과 브라우저 캐시를 공유합니다. 기존 scope 전환 시 Phaser Game을 재생성하는 구조는 유지하므로 GPU 업로드는 새 인스턴스에서 다시 필요합니다. 채팅 전용 모드는 기존 loop.sleep/wake를 유지합니다.

public/visual 파일은 Vite dist/visual로 복사되고 Nginx가 실제 파일만 제공합니다. 없는 파일에 index.html을 반환하지 않으며, 내용 해시 파일에1년 immutable 캐시를 붙입니다. PNG/JSON/manifest를 한 프런트 빌드로 배포합니다. Docker Compose/PostgreSQL/데이터/미디어 볼륨과 별개이며 이 Phase에는 DB 마이그레이션이 없습니다.

원본 제작/라이선스 상태는 manifest.license와 [asset-licenses.json](asset-licenses.json)에 기록합니다. 외부 유료·보호 에셋을 복사하지 않았습니다. 별도 외부 배포 라이선스는 지정하지 않았으며 프로젝트 내부 적용본입니다. 새 에셋을 받을 때 출처·제작자·권한/라이선스·고지문·원본 위치를 같은 장부에 추가합니다.

아직 필요한 자료는 정식 브랜드 캐릭터 원화/방향별 보강, chatting/drinking/meeting/celebrating 전용 클립, 일부 가구의 완성된 뒤/측면, 라이선스를 확보한 한글 픽셀 폰트, 정식 이미지 타일셋·특수 효과입니다. 현재 v1 적용본과 대체 경로는 실제 동작하며 이 자료들이 있다고 가정하지 않습니다.
