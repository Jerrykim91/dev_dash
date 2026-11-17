# Phase 4 검증 기록 — 2026-11-06

기준 백업: `backups/before-phase4-20261106.zip` 및 SQLite 일관 백업. 기존 DevNest 기준 파일 123개, 가구 카탈로그·존 정의·캐릭터 생성 코드는 보존했습니다. 오피스 맵은 기존 라운지에 아케이드 오브젝트 한 개만 추가했습니다. 기존 계정·개인 집·가구·Coin·채팅을 삭제하거나 초기화하지 않았습니다.

## 구현 결과

- GameModule/Registry/Session/Result, 게임 로비·실제 두더지 보드·결과·보상·최근 기록
- 3×3, 실제 30초, 서버 HMAC 등장·수신 시각 판정·10점/명중·빈 칸0점·자동 종료
- 게임기까지 기존 A* 접근, 중앙 오버레이, 게임 중 월드 이동 차단과 게임 중 상태 동기화
- 서버 승인·활성 1세션·시작 멱등 요청·클릭 멱등 요청·구간당 명중1회·입력 속도 검사
- 기존 지갑/원장의 0/10/20/30 Coin 기본 보상·UTC 일일 상한·동시 정산·실패 롤백·감사
- /admin 게임 설정·보상·이용 현황·입력 거절 기록과 기존 RBAC
- v6 추가형 마이그레이션·SQLite pre-phase4 백업·PG 가져오기/전체 dump 연결
- 기존 Coin 내역에 ‘미니게임 보상’ 표시. 초기 HTTP 채널 목록이 더 최신 WS 접속 인원을 덮어쓰지 않도록 보완

## 자동 테스트

| 검증 | 명령/환경 | 실제 결과 |
|---|---|---|
| 전체 서버 | backend에서 `../.venv/bin/python -m pytest tests -q --tb=short`, 별도 PG 환경변수 포함 | **122 passed, 1 skipped** |
| 신규 게임 서버 | 같은 환경 `tests/test_games.py` | **26 passed**(SQLite13 + 실제PG13, 전체122에 포함) |
| 순수 시스템 | frontend에서 `npm test` | **20 passed** |
| 타입/번들 | frontend에서 `npm run build` | 성공, 큰 번들 경고 유지 |
| 전체 브라우저 | frontend에서 `npm run test:e2e` | **14 passed** |
| 추가 UI 회귀 | `npm run test:e2e -- ../tests/phase4.spec.ts --grep 'mobile touch\|delayed initial channel'` | **2 passed**(모바일 재검증1 + 새 채널 경합1) |
| 패키지 검사 | Vite6.4.5·Playwright1.55.1로 갱신 후 npm install/audit 및 Docker npm ci | 취약점 **0건** |

14개 전체 실행 후 새 채널 경합 테스트를 추가했습니다. 최종 전체15개를 한 번에 실행했다고 합산하지 않습니다. 14개 전체 + 추가1개 고유 항목을 확인했고, 모바일은 마지막 표시 변경 후 다시 통과했습니다. skip1은 SQLite 파라미터에 해당하지 않는 SQLite→PostgreSQL 가져오기이며 PG에서는 통과했습니다. native 서버 테스트는 Python3.14·Node22·macOS Chrome, Docker는 Linux ARM64·Python3.12입니다.

서버 테스트 DB는 `NOBIS_TEST_POSTGRES_URL`(전용 클러스터 DB 생성용) / `NOBIS_TEST_POSTGRES_APP_URL`(NOSUPERUSER/NOCREATEDB/NOCREATEROLE 앱 계정)으로 분리했습니다. 고유 테스트 DB만 생성/삭제했습니다. 브라우저 테스트도 실제 사용자 DB를 사용하지 않았습니다.

## 보안·정합성 실제 확인

| 항목 | 확인 방법 |
|---|---|
| 게임기 접근과 서버 시작 승인 | WS에서 게임기 인접 상호작용, 멀리서 시작403, 활성 두 세션409 |
| 임의 점수/보상 위조 | 실제 HTTP inputs/finish에 score/reward 추가 →422, 조기 finish409 |
| 명중 판정 | 현재/위조 challenge·다른 구간·빈 칸·종료 입력·중복 event·너무 빠른 클릭, 서버 점수 불변 검사 |
| 구간당 1회 | event_id 재사용/다른 event의 같은 구간과 DB 부분 UNIQUE 검사 |
| 소유권 | 타인의 state/input/finish/cancel404, 타인 기록 비노출 |
| 정산 1회 | 8개 동시 HTTP finish → 보상/결과/원장/감사 한 건 |
| 실패 롤백 | SQLite 실패 trigger + PG CHECK 실패 주입 → 세션 active·결과0·원장0·원잔액 보존 |
| 보상 구간 | 0/40/50/100/150점에 0/0/10/20/30 Coin, 기존 HomeService 거래와 일치 |
| 일일 상한/설정 | 남은 상한 일부 지급·한도 후0·게임 비활성·진행 중 보상표 스냅샷·설정 감사 |
| 관리자 권한 | user 조회/변경403, moderator 조회200/변경403, admin/super 설정 및 기록 |
| 월드 정지/복귀 | 게임 중 move 교정·집/채널/상호작용 거절, 새 WS 요청 채널로 우회도 거절, 종료 후 원래 위치 |
| 채팅/상태 | 동료 게임 중 표시·같은 연결에서 월드 채팅 수신·기존 귓속말/공지/초대 대화 회귀 |
| 재접속/기록 | 실제 브라우저 새로고침 활성 복구·30초 자동 정산, 서비스 재생성·만료 처리 |
| 모바일 | 390×844 실제 touch emulation, 한 탭 한 입력, 65px 이상 터치 영역, 스크롤 없음, 월드/채팅 복귀 |
| 기존 기능 | 여섯 연결 존·충돌·위치 동기화·채널 정원·권한·집·가구 배치/회전/회수·상점·DevNest 원본 새 탭 |

## 실제 Docker ARM64 검증

독립 Colima VM(2CPU·3GB), 별도 Compose 프로젝트 `nobis-phase4-verify`, HTTP `127.0.0.1:18080`, 별도 랜덤 암호 env/PG 볼륨을 사용했습니다. 기존 개발용 SQLite와 실제 사용자 지갑은 사용하지 않았습니다.

실행한 구성:

```sh
DOCKER_CONFIG=/private/tmp/nobis-phase4-docker-config docker --context colima-nobis-phase4 compose -p nobis-phase4-verify --env-file /private/tmp/nobis-phase4-compose.env -f compose.yaml config --quiet
DOCKER_CONFIG=/private/tmp/nobis-phase4-docker-config docker --context colima-nobis-phase4 compose -p nobis-phase4-verify --env-file /private/tmp/nobis-phase4-compose.env -f compose.yaml up --build -d --wait
```

위 임시 디렉터리/계정은 이번 검증용이며 장기 운영 기본값이 아닙니다. 운영 환경은 README의 `.env.production` 생성·Docker Engine 설치·실행 절차를 사용합니다.

- backend/frontend/postgres 실제 빌드·기동·health 통과. backend 컨테이너 `platform.machine() = aarch64`.
- **운영 모드** 비밀번호 계정 생성, 초기 Coin **0** 확인. 개발 로그인 없이 접속.
- Nginx `/ws`로 로그인·연결된 맵 경로 보행·게임 시작. 실제 시간 30초를 두 번 사용하여 각각 **380점/38명중/30 Coin**. 잔액 **0→30→60**, 중복 finish 후에도60.
- 같은 기존 shop API의40 Coin 화분 구매 → 잔액 **20**, 인벤토리 증가.
- 실제 빌드한 배포 화면에서 비밀번호 로그인·게임기 접근·30초 마우스 플레이·30 Coin 정산 → **20→50**. 개인 집에 입장해 기존 상점 UI에서40 Coin 화분 구매 → **10**, 인벤토리 증가, pageerror0. 운영 번들에 개발용 `__NOBIS_GAME__` 노출 없음.
- pg_dump custom 백업을 새 DB에 pg_restore하여 계정·게임 결과·원장·지갑·가구 수 비교 일치.
- postgres/backend/frontend restart 후 일치. `down`(볼륨 삭제 옵션 없음) → `up`으로 컨테이너 재생성 후에도 일치.
- 저장 비교 시점 값: users1 / game_sessions2 / game_results2 / game_rewards2 / coin_transactions4 / wallet20 / furniture9 / schema6. 이후 추가 브라우저 플레이·취소·구매 검증은 별도 진행했습니다.
- PostgreSQL 호스트5432 미노출, 내부 data 네트워크 사용. 정상 health의 database=postgresql 확인.

따라서 Docker 실행은 이번 Phase에서 실제 검증했습니다. Raspberry Pi4 실기기·외부 도메인/TLS·다중 서버 클러스터를 검증했다고 주장하지 않습니다. 테스트 전용 스택은 검증 후 정지하며, 사용자 개발 화면은 기존 SQLite로 계속 실행합니다.

## 발견·수정 및 테스트 조정

- 초기 채널 HTTP 응답이 WS snapshot보다 늦게 도착하여 채널 인원0을 표시할 수 있었습니다. 더 최신 소켓 목록을 받은 뒤에는 초기 응답을 버리고, 지연 응답 회귀를 통과했습니다.
- 기존 Coin 내역의 기본 분기가 게임 보상을 가구 구매로 표시할 수 있어 명시적 보상 종류 표시를 추가했습니다.
- 게임 중 WS 재접속에 새 channel_id를 넣어 이동 제한을 우회하는 경로도 서버에서 거절하도록 보완했습니다.
- 첫 브라우저 테스트의 채팅 확인은 이동 후 현재 존 탭에 남아 월드 메시지를 보지 못했습니다. 기존 전달 범위를 바꾸지 않고 테스트에서 월드 탭을 선택하여 전체14개를 재실행해 통과했습니다. 이 실패 때문에 선행 보상 기록이 없던 후속 관리자 확인도 함께 통과했습니다.
- 배포 화면 smoke script는 시작 요청 후 보드 생성 대기가 빠져 조기 종료됐고 상품명 선택자도 실제 이름과 달랐습니다. 보드 대기/이름을 맞춘 뒤 전체 실제 플레이→개인 집→가구 구매가 통과했습니다.
- 빌드에서 이전 Vite/Playwright 개발 의존성 경고를 확인해 최소 보안 버전으로 갱신하고 다시 빌드·검증했습니다.

## 남은 범위

- 카드 짝 맞추기·코인 모으기는 준비 중이며 실행 불가입니다. 대전·랭킹 보상·시즌·결제·거래소·소셜 피드·업무 성과 보상·최종 아트는 추가하지 않았습니다.
- 유효 목표를 자동으로 누르는 봇을 사람과 구분하는 탐지는 없습니다. 점수/시간/세션/중복/상한 검증과 구별합니다.
- 일일 상한은 UTC 기준입니다. 다른 게임을 추가할 때 개별 입력 계약·전체 게임 보상 정책을 함께 검토해야 합니다.
- 실제 iOS Safari/Android,15명 동시 게임·다중 채널 장시간 부하, Pi4 발열/메모리/저장장치 내구성, 운영 TLS·계정 복구·백업 보관 정책은 미검증/미확정입니다.
- 큰 프런트엔드 번들 경고와 native Python3.14의 기존 FastAPI/Starlette deprecation 경고가 있습니다. Docker/전체 이미지 CVE 스캔을 npm audit 결과로 대체하지 않습니다.
- 실시간 Hub는 기존 단일 worker 구조를 유지합니다.
