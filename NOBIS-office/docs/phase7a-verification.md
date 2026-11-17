# Phase 7-A · 비대칭 월드 검증

2026-11-07 후속 지시 기준입니다. 최종 원화 적용은 다음 단계이고 이번에는 실제 맵 구조·이동 가능 영역·출입구·계단·충돌을 변경했습니다.

## 결과

- 균등6분할과 십자 통로를 제거하고,크기가 다른9개 다각형 공간과 가장 넓은 중앙 라운지241칸을 구성했습니다.
- 좌표 범위58×54 중 바닥1,150칸(가구 제외 이동1116칸),연결 경로13개,출입구16edge,실제 계단8edge,높이0/24/48/72px입니다.
- 카페/회의실/집중/라운지/휴가/외근6개 존ID와 규칙은 유지합니다. 옥상 정원·우측 휴식 공간은 각각 vacation/lounge의 시각 하위 공간입니다.
- 기존 비파티션 오브젝트34개와 상호작용 계약을 모두 유지하고 위치를 재배치했습니다. 기존 파티션 격자는 명시적 닫힌 경계와 실제 바닥/void 경계로 대체했습니다.
- [기존 코드 분석·변경 구조·존/연결·에셋 규격](phase7a-world-design.md),[실제 배치도](phase7a-layout.svg),[전체 변경 파일](phase7a-changes.md).

## 검증 결과

| 검사 | 결과 | 내용 |
|---|---|---|
| 단위 검사 |30 통과|전체1116개 이동 셀 연결,모든 존/상호작용 접근,계단 양방향·닫힌 edge·void·표면 역변환,기존 A*/이동/가구 검사|
| 전체 Chrome |27 통과,8.6분|데스크톱/390px 모바일,신규 Phase7-A3개+기존24개|
| 전체 백엔드 |192 통과,1 조건부 생략|격리SQLite와실제PostgreSQL17,SQLite에서PG 전용 가져오기 검사의 생략|
| TypeScript/Vite |성공|새 구조를 포함한 정적 빌드|
| 맵 생성 |성공/재실행 동일|생성된3개JSON SHA256 불변,DB 접근 없음|
| ARM64 Docker |성공|기존 검증 볼륨 유지,세 서비스 healthy,backend aarch64/v2/바닥1150 확인|
| 실제 Nginx Chrome |성공|로그인/캔버스/새 존315칸 lounge 마스크/코인확률/관리자,페이지 예외 없음|
| 정적 파일 |성공|기존 아틀라스PNG/JSON6개200+immutable,없는이미지404|

신규 브라우저 검사는 카페→회의실→카페→라운지→외근→라운지→휴가 실제 클릭 이동 중 장애물/계단 이외 높이 변경/Scene 교체가 없는지 관찰합니다. 다른 브라우저의 위치·존 동기화와 월드 채팅도 검증합니다. 모바일은 터치 이동 후 기존 책장 접근으로 개인 집에 입장합니다. 채팅 접기 후 실제 canvas가 넓어지고 그 크기에서 클릭 목적지에 도착하는지 확인합니다.

기존 회귀에는 자동 존 채널 갱신,귓속말/카페·회의 ACL/말풍선 제한/공지,집 입퇴장·가구구매/회전/설치/회수/새로고침 복원,관리자,친구·그룹·소셜 사진/권한·집 방문·협동,미니게임/보상,출석1회/티켓/1회·5회 코인 가챠와 인벤토리 무변경을 포함합니다.

기존 시나리오가 사용하던 옛 맵 좌표는 tests/world-fixture.ts에서 같은 존/오브젝트의 새 실제 좌표로 해석하고,개인 집 좌표는 변경하지 않습니다. 새 Phase7-A 검사는 현재 맵/존 데이터를 직접 사용합니다. 이 변환은 테스트 전용이며 프로덕션에 옛 좌표 순간이동 기능을 추가하지 않습니다. 서버 검증 데이터도 실제 새 위치에 맞췄습니다.

## 보존·복구

Git복구 지점4af9fc9(앞선035bbe5 포함)을 만들었습니다. 비밀환경/사용자DB/의존성/백업은 Git에 넣지 않았습니다. 원래 소스/SQLite 사본도 backups/before-phase7a-20261107.zip/.sqlite3에 있습니다.

기존 CoordinateSystem/PathfindingSystem/MovementSystem/InteractionSystem/CameraSystem/GestureSystem6개 모듈과 개인 집 맵·가구 카탈로그가 시작 전 SHA256과 같습니다. DevNest123개 파일 SHA256도 동일합니다. 백엔드 기능 소스는 world.py의 이동/존 해석만 확장했고 인증/DB/경제/권한 서비스는 변경하지 않았습니다.

기존 개발SQLite의 사용자 수·지갑·가구인스턴스·배치·코인거래·가챠확률 테이블은 백업과 같습니다. 스키마v9,10~1,000Coin 확률표를 유지합니다. 이전 위치가 새 맵에서 무효이면 기존 안전 복귀 검증으로 입구spawn에 배치하며 계정/재화/가구 데이터를 초기화하지 않습니다.

이전 단계의 docs PNG64개와Phase7 성능JSON은 원본 백업에서 복구했습니다. 현재 증거는 phase7a-asymmetric 접두사로 저장합니다. 초기 균등맵 기반 중간 미리보기는 backups/phase7a-superseded-previews에 보존하고 최종 캡처와 구분했습니다.

## 실행과 남은 작업

로컬 NOBIS 프런트15173/백엔드18000은 실행 중이며 마지막 확인HTTP200입니다. 기존 환경/SQLite 경로를 보존해 백엔드를 재시작했습니다. 검증용 Compose·PostgreSQL·ARM64 VM은 종료하고 데이터 볼륨은 유지했습니다. 최종 운영 서버로 이전하지 않았습니다. 실행/설치/백업 명령은 [README](../README.md)를 따릅니다.

새 최종 픽셀 아트는 적용하지 않았습니다. 기존 Phase7 아바타/가구3아틀라스와 코드 타일/벽/계단을 사용합니다. 다음 교체 위치는 FloorVisual.ts/ArchitectureVisual.ts/FurnitureVisual.ts/CharacterVisual.ts와manifest/overrides입니다. [필요 이미지·피벗·규격](phase7a-world-design.md)에 정리했습니다.

Raspberry Pi 실기기/15명 부하와 겹쳐 걷는 다층 교량은 검증/구현 범위가 아닙니다. Vite 대형JS 청크 경고와 기존 Python/FastAPI deprecation 경고가 남아 있습니다. [성능 원자료](phase7a-performance.json)는 개발Chrome 전경 단일 아바타 측정으로 서버/Pi 부하 검증이 아닙니다. [기계 판독 결과](phase7a-test-results.json).

## 화면

[전체 새 월드](phase7a-asymmetric-overview.png) · [채팅을 접은 넓은 월드](phase7a-asymmetric-wide.png) · [모바일](phase7a-asymmetric-mobile.png)

[개인 집](phase7a-asymmetric-home.png) · [꾸미기](phase7a-asymmetric-home-editor.png) · [소셜](phase7a-asymmetric-social.png) · [미니게임](phase7a-asymmetric-arcade.png) · [코인 가챠](phase7a-asymmetric-coin-gacha.png) · [관리자](phase7a-asymmetric-admin.png)

[Docker 실제 화면](phase7a-asymmetric-docker-office.png) · [Docker 코인 확률](phase7a-asymmetric-docker-gacha.png) · [Docker 관리자](phase7a-asymmetric-docker-admin.png)

캡처 폴더: `../캡처/NOBIS-Office_Phase7A_2026-11-07/index.html`.
