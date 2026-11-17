> 최신 미니게임·Docker 결과는 [Phase 4 검증 기록](phase4-verification.md)을 확인하세요.

> 이 문서는 Phase 3.5 이전 검증 기록입니다. 현재 결과는 [Phase 3.5 검증 기록](phase35-verification.md)을 확인하세요.

# 멀티채널·채팅·관리자 검증 · 2026-11-06

## 실제 실행 결과

| 범위 | 결과 |
|---|---|
| FastAPI·SQLite·API·WebSocket·권한·CLI | **45개 통과** (기존 32 + 새 사회/권한 테스트 13) |
| 좌표·A*·이동·충돌·존·가구 배치 순수 모듈 | **13개 통과** |
| 실제 Chrome 브라우저 E2E | **8개 전체 통과** (기존 6 + 새 2, 약 2.8분) |
| TypeScript 검사·Vite production build | 통과 |

총 **66개 자동 테스트**입니다. 마지막 그룹 대화/귓속말 표시 보완 후 관련 브라우저 2시나리오를 다시 실행해 통과했고 서버 45개도 재실행했습니다. 브라우저 테스트마다 독립 임시 DB를 사용해 실제 개발 DB를 권한 부트스트랩하거나 수정하지 않습니다.

기존 단일 월드·여섯 존·클릭/터치·관람자·채팅 전용·개인 집·배치/회수/구매·실제 원본 DevNest 팝업 회귀가 포함됩니다. JavaScript pageerror 수집 시나리오에서 오류 0개를 확인했습니다. 탭 종료 때 Vite의 EPIPE/ECONNRESET 로그 및 의도된 HTTP 403은 발생할 수 있어 전체 로그 무오류라고 보고하지 않습니다.

## 추가 요구사항별 근거

| 요구 | 검증 근거 |
|---|---|
| 채널별 아바타 격리 | 다른 채널 snapshot/API 목록에 상대 아바타 없음, 실제 UI avatars 수/모델 목록 확인 |
| 위치 메시지 격리 | ch2 실제 이동 후 ch1의 WS에서 moved/zone_changed 부재 |
| 채널 이동/재접속 | 채널별 좌표·근무 상태 복원, 저장 채널 재접속, UI 채널 선택/인원 반영 |
| 정원 제한/원자성 | ch2 정원 1명에서 추가 이동 거부, 이전 메모리/DB 채널 유지. 접속 중 비활성화 거부 |
| 다른 채널 귓속말 | 실제 3브라우저: ch1→ch2 본문 수신, 발신자 기록·전달 상태 확인 |
| 잘못된 수신자 노출 차단 | 제3자의 WS/HTTP에 비밀 본문 없음, 중복/없는 닉네임 거부, ID 선택만 정확한 상대에게 전달 |
| 오프라인 귓속말 | stored 표시 → 같은 계정 재접속 기록 복원 → delivered 갱신 |
| 말풍선 ON/OFF | 사용자 설정 저장, 카페 공개 메시지 표시/교체/6초 후 숨김, OFF 비표시 |
| 집중 업무존 금지 | 실제 이동 후 공개 메시지는 채팅창에 남고 채팅 말풍선은 비표시 |
| 회의실 금지 | 같은 실제 브라우저 이동/공개 전송으로 비표시 확인 |
| 비공개/공지 제외 | 귓속말·카페/회의 그룹·관리자 공지가 chat_bubble을 만들지 않는 서버 테스트 |
| 전체 공지 | 다른 채널까지 수신, 채팅 전용에서도 상단 배너 표시 |
| 채널 공지/순서 | ch2만 수신, 두 전체 공지 큐 순서대로 닫기, 기록과 채팅 분리 |
| 일반 사용자 공지 차단 | 관리자 발송 API 403, 기존 chat announcements 쓰기도 거부 |
| 일반 사용자 관리자 차단 | 관리자 모든 기본 API 403, 실제 /admin 접근 거부 화면 |
| super_admin만 admin 임명 | admin의 admin 임명 거부, super의 임명 허용, 마지막 super 강등 거부 |
| 권한 변경 기록 | bootstrap/role_changed 감사 로그 서버·관리자 UI에서 확인 |
| 최초 bootstrap 보호 | CLI 2회 실행 거부 및 동시 요청 2개 중 1개만 성공/로그 1건 |
| 운영 모드 인증 | dev 로그인/키/기존 dev 세션 거부, CLI 비밀번호 계정 정상 로그인·관리자 조회 |
| 신고/모더레이션 | 신고 접수/처리·채팅 제한/해제·공개 메시지 삭제·계정 제한·세션 차단 |
| 실제 운영 CLI | create-user/list-users/set-password/migrate/backup/restore 호출 및 복원 DB 권한/계정 검증 |
| 단일 맵/DevNest 보존 | office 맵 파일은 변경 전과 바이트 동일, 원본 DevNest 이전 123개 파일 해시 모두 동일 |

관련 테스트: backend/tests/test_social.py, 기존 backend/tests/test_server.py·test_phase2.py·test_phase3.py, frontend/src/game/systems/systems.test.ts, tests/social.spec.ts 및 기존 office.spec.ts·phase2.spec.ts·phase3.spec.ts.

## 데이터와 실제 서버

수정 전 백업: `backups/before-multichannel-20261106.zip`. 추가형 v4 스키마 및 기존 presence/session 컬럼을 적용했습니다. 개발 DB에서 v2/v3/v4와 초기 ch1 정원 15, `.pre-multichannel.bak` 생성을 확인했습니다. 기존 사용자·집·코인·대화방·세션 기록을 삭제하지 않았습니다. production은 기존 dev-kind 세션을 인증 수단으로 받아들이지 않습니다.

기존 DevNest는 수정하지 않았고 소셜 그룹/활동/사진/영상 기능을 구현한 것처럼 표시하지 않습니다. 실제 개발 DB의 최초 super_admin을 임의 계정에 지정하지 않습니다. 운영자가 CLI list-users/create-user와 bootstrap-admin으로 계정 ID를 선택하는 절차는 README에 있습니다.

실제 사용 주소 http://127.0.0.1:15173/ 에서 새 테스트 계정 두 개로 채널 선택 UI·귓속말 수신·말풍선 설정 저장·일반 사용자의 /admin 거부를 별도 확인했습니다. 이 확인의 pageerror는 0개였습니다. 초기 채널은 1개입니다. 추가 채널 생성은 /admin의 채널 관리 기능으로 검증했습니다. 관리자 경로 자체는 정적 앱에 포함되어도 권한 있는 서버 응답 전에는 메뉴를 렌더링하지 않습니다.

## 검증 한계/남은 작업

- macOS ARM64 / Node 22.16.0 / Python 3.14.6 / 설치된 Chrome에서 실행했습니다.
- Docker 엔진과 Pi 실기기가 없어 Debian 설치·Compose 기동·ARM64 운영·여러 채널 전체 서버 부하는 미검증입니다. 채널별 기능 정원 검사는 전체 서버 성능 측정이 아닙니다. 기존 ARM64 검사 스크립트는 Docker 부재로 실행을 완료할 수 없습니다.
- README의 shell 블록 14개는 bash -n 구문 검사와 실제 CLI --help 대조를 통과했습니다. Docker/PostgreSQL 설치 명령은 공식 문서와 대조했으며 여기서 새 Linux 서버를 실제 설치하지 않았습니다. 현재 앱 DB는 SQLite입니다. PostgreSQL 어댑터/데이터 변환은 미구현이며 PostgreSQL 준비/백업/복원 명령을 현재 앱 연결 명령으로 안내하지 않습니다.
- 가구/캐릭터는 임시 에셋이며 Phaser 번들 약 1.77MB 경고와 Python deprecation 경고가 남습니다.
- 다중 worker/클러스터 상태 공유, 자율 회원가입·복구·SSO/MFA, 소셜 그룹/기록/미디어, 게임 보상·실제 결제·거래·방문·공동 편집·외부 Google 연결은 미구현입니다.

화면: [관리자 로그](admin-audit.png), [채팅 전용 채널 공지](multichannel-toast.png), [채팅 말풍선](chat-bubble.png), [실제 로컬 실행](multichannel-live.png). 명령/설정: [README](../README.md). 설계: [architecture](architecture.md).
