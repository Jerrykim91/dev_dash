# Phase 6 · Social Integration 검증 · 2026-11-06

첨부 Phase 6 지시서와 코인 가챠 정정을 함께 적용했습니다. 실제 코인 가챠의10~1000/10단위100개 확률은 보존했습니다. 경제 흐름은 **출석 → 티켓 → Coin 가챠 → 가구 상점 → 집 꾸미기**입니다. 과거 가구 가챠 기록은 보존하지만 신규 직접 아이템 지급과 가챠 전용 도감은 구현하지 않습니다.

## 구현과 접근 경로

- 소셜 → 친구와 활동 → 집 방문: private/friends/invite_only, 기본 private, 친구 모드도 소유자 승인 필요, 승인24시간, 소유자 포함1~5명 정원. 받은 요청 승인/거절, 방문 입장, 집 주인 내보내기, 방문 신고.
- 친구 프로필: 집 방문 요청·협동 게임 초대. 차단하면 집 권한을 회수하고 해당 두 사람의 협동 게임을 종료합니다.
- 집: 동일 scope의 아바타/위치/채팅/배치 공유, 다른 채널 사용자도 같은 집에서 동기화. 방문자에게는 배치 맵만 제공하며 소유자의 지갑/인벤토리/설정은 제공하지 않습니다. 가구 편집은 소유자만 가능합니다. 현재 모든 입장자의 위치를 배치 충돌 검사에 포함합니다. 변경 맵에 맞춰 일반 바닥 경로를 다시 계산하고 오브젝트 접근은 취소합니다.
- 복귀: 기본 원래 오피스 채널/좌표. 만석이면 빈 활성 채널, 전부 만석인 일반 퇴장은 재시도 안내. 권한 회수인데 복귀 자리가 없으면 연결을 종료하여 무단 체류를 방지합니다. 재접속은 권한/정원/충돌을 다시 검증합니다.
- 협동 게임:12장/6쌍, 두 장씩 번갈아 선택. 서버 보드/턴/revision/입력UUID/매칭/완료. 미공개 값은 참가자에게도 숨깁니다. 초대60초/게임5분/재접속 유예30초.
- 보상: 완료25 Coin/참가자, 최소10초, UTC 협동 일일100 및 기존 솔로와 합산300 상한. 기존 솔로 설정 상한도 유지합니다. 초대·수락·중도 종료 보상 없음. 최종 입력/세션/두 지갑/기존Coin원장/보상 참조는 단일 트랜잭션이며 오류 시 롤백 후 재시도합니다.
- 보유 가구 도감: 실제 catalog/inventory/placements/shop_purchases에서 수량·설치·최초 획득·경로·진행률을 조회합니다. 별도 collection_entries 원장을 중복 저장하지 않습니다.
- 직접 공유: 내 보유 가구/도감 진행률/완료 협동/솔로 결과 → 그룹 선택 → 서버 소유권 검증 미리보기 → 명시적 게시. 미리보기만으로 게시하지 않습니다.
- 알림: 기존 user_notifications에 방문/게임/코인 가챠를 통합하고 대상자별 WS 갱신·오프라인 저장을 유지합니다. 가챠 화면에는 누적 획득 Coin과 최신 잔액을 표시합니다.
- 관리자: 협동 게임·집 방문 메뉴에서 세션/거부 입력/지급 원장/방문 신고를 조회·처리합니다. 보드 정답과 개인 채팅을 운영 목록에 넣지 않습니다. 기존 공개 채팅 조회·삭제 경로에서도 personal 집 채팅을 제외했습니다.

## 실제 결과

| 검증 | 결과 |
|---|---|
| 전체 서버(SQLite + 일반 앱 역할 PostgreSQL17) | **190 passed, 1 skipped** |
| 최종 Phase 6 서버 집중 검증 | **16 passed**(양 DB) |
| 기존 포함 전체 Chrome | **21 passed** |
| 최종 신규 Chrome | **3 passed** |
| 실제 PostgreSQL 연결 신규 Chrome | **3 passed** |
| 순수 게임 시스템 | **20 passed** |
| TypeScript + Vite production build | **성공** |
| ARM64 Docker 운영 인증/API/WS | **통과** |
| 기존 Docker DB v7 → v9 업그레이드 | **통과**, 가구 영수증2건 유지 |
| Docker 컨테이너 재시작 | **통과**, 지갑/구매/코인 추첨/방문/게임 기록 집계 동일 |
| 최종 Docker Chrome | **통과**,2개 운영 계정 초대/수락/보드/취소/운영 메뉴 |
| 기존 native 데이터 | 기존 모든 테이블 행 수·Coin합계 보존, schema만9로 추가 |
| 기존 코인 확률 | DB 확률표 전체 행을 이전 백업과 비교하여 동일 |
| DevNest | 기존123개 파일 해시 동일 |

SQLite에서 PostgreSQL 전용 이전 테스트1건을 제외한 것이 전체 결과의 skip입니다. PG 환경 변수를 생략한 기본 pytest는 PG 사례를 추가 제외합니다. Full Chrome에는 이전 월드·클릭/터치·충돌·카메라·채팅·귓속말·그룹·집/상점·솔로 게임·Coin 가챠 회귀가 포함됩니다. 마지막 권한 보강은 집 대화를 관리자 공개 목록/삭제에 노출하지 않는지 양 DB에서 재검증했습니다.

서버 집중 검증은 private 거부, 승인/거절, 집 정원, 다른 오피스 채널 간 방문/위치/집 채팅, 방문자 편집 거부, 배치 전송, 강제 퇴장/차단, 접속 종료·권한 회수 후 재접속, 미공개 카드, 턴/중복/동시 선택, 중복 참가, 취소/연결 종료/상한, 재접속 후 협동 잠금, 솔로 조회와 상태 공존, DB 지급 오류 롤백/같은 요청 재시도, 보상 중복 방지, 코인 가챠 누적/상점 구매/도감/선택 공유/운영 권한을 확인했습니다. 무단 입장 시 소유자의 지갑/가구를 생성하지 않는 것도 확인했습니다.

브라우저는2탭 방문 승인→같은 집 아바타/집 채팅→소유자 배치 저장→방문자 내보내기→도감 미리보기/명시적 공유를 실행했습니다. 협동 테스트는 서버 원본 보드를 읽지 않고 **실제로 공개된 카드 값만 기억하여** 두 탭의 화면 버튼으로 완주했고 각25 Coin·중복 없음까지 확인했습니다. 모바일390px에서는 활동 메뉴/비공개 기본값/보유 도감과 팝업 가로 경계를 확인했습니다.

Docker는 격리 프로젝트 nobis-phase5-verify의 기존 PG/media 볼륨을 재사용하여 v7→v9 업그레이드를 검증했습니다. 기존 가구 영수증2건을 읽고, Coin-only5회/재시도→지갑 증가/인벤토리 불변→최저가 상점 구매→도감 경로 반영을 확인했습니다. 실제 WS2개로 공유 집/채팅/편집 거부/내보내기, 협동 초대/미공개 보드/잘못된 차례 거부/취소를 실행했습니다. backend/frontend 재시작 후 집계와 과거 기록이 유지됐습니다. 최종 빌드는 Chrome 운영 로그인2개로 보드와 운영 화면도 확인했습니다. DB+이미지 별도 저장소 복구 자체는 이전 Phase 5에서 검증한 절차를 유지하며 이번에는 추가 스키마 업그레이드·재시작 유지 여부를 검사했습니다.

## 실행

현재 개발 화면: `http://127.0.0.1:15173/`, API: `http://127.0.0.1:18000/health`.

```sh
# 프로젝트 루트, 설치가 필요한 경우
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
# 터미널1
cd backend
APP_ENV=development DEV_AUTH_ENABLED=true ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18000
# 별도 터미널2, 프로젝트 루트
API_TARGET=http://127.0.0.1:18000 npm --prefix frontend run dev -- --host 127.0.0.1 --port 15173
```

운영 Docker/PostgreSQL/마이그레이션/환경/DB+이미지 백업/복원/새 서버 이전은 README 명령을 유지했습니다. 기존 `.env`의 `/app/data`는 Docker 내부 경로이며 native 실행은 실제 `backend/data/nobis.sqlite3`를 사용합니다. 실제 CLI migrate 출력은 schema9입니다. 새 집 기본 정원 `HOME_MAX_OCCUPANTS=5`(1~5), 기존 소유자 설정은 보존합니다.

```sh
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

PG 검증용 URL/비밀번호는 환경으로만 전달하고 출력·커밋하지 않습니다. NOBIS_TEST_POSTGRES_URL은 DB 생성/삭제 가능한 **별도 테스트 서버**, NOBIS_TEST_POSTGRES_APP_URL은 일반 앱 역할, NOBIS_E2E_DATABASE_URL은 별도 테스트 DB를 지정합니다. Chrome 기본 경로는 macOS 설치 경로이며 CHROME_BIN으로 바꿀 수 있습니다. 브라우저 검증은15175/18002/18003 포트를 사용합니다.

## 화면·파일

[방문 중인 집](phase6-home-visit.png) · [협동 카드 보드](phase6-cooperative-board.png) · [완료/지급 결과](phase6-cooperative-result.png) · [가구 도감](phase6-collection.png) · [모바일 활동](phase6-mobile-activities.png) · [관리자 운영](phase6-admin-integration.png) · [코인 경제 흐름](phase6-gacha-economy.png)

[변경 파일](phase6-changes.md) · [검증 JSON](phase6-test-results.json). 동일 캡처와 gallery는 `Projects/캡처/NOBIS-Office_Phase6_2026-11-06`에 저장합니다.

## 남은 범위·제한

- 실제 iOS/Android 기기,15명 장시간/다중 집 부하, 실제 Raspberry Pi 성능, TLS/실제 도메인은 미검증입니다. macOS Chrome 모바일 에뮬레이션/실제 PG/Linux aarch64 Docker 검증과 구별합니다.
- Hub·연결별 정원·방송은 단일 backend worker 전제입니다. 다중 worker/호스트 전에는 분산 presence/잠금/메시지 전달 계층이 필요합니다.
- 집 스크린샷 공유·아바타 외형/의상·최종 픽셀 아트·음성/영상·외부 일정/SSO는 후속 범위입니다. 가챠 직접 아이템 지급/가챠 전용 도감은 정정 지시로 제외했습니다.
- 자동 플레이/다중 허위 계정 탐지를 별도로 구현하지 않았습니다. 입력/순서/소유권/재시도/최소 플레이 시간/지급 상한/유니크 원장을 적용합니다. 협동 보상 정책은 현재 코드의25/100/300값이며 별도 동적 운영 편집 UI는 추가하지 않았습니다.
- 최초 획득/이전 보유의 세부 원장은 과거 자료가 없는 경우 ‘기본 지급 또는 이전 보유’로 표시합니다. 상점 구매는 기존 영수증으로 구분합니다. 현재 보유품 기준이므로 별도 영구 수집 업적을 만들지 않습니다.
- 기존 Phaser 포함 번들 크기 경고와 native Python3.14의 FastAPI/Starlette deprecation 경고가 남습니다. 코드/테스트는 현재 설치 버전으로 통과했습니다.
