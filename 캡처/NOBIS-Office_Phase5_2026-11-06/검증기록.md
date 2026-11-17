# Phase 5 · Social + Attendance/Tickets/Gacha 검증

검증일: 2026-11-06, macOS ARM64 / Chrome / Node22 / native Python3.14 / PostgreSQL17 / Colima Linux aarch64. 첨부 Phase 5 소셜 지시서와 추가 무료 출석·가챠 지시서를 함께 구현했습니다. 아래 수치는 실제 실행 결과입니다.

## 실제 검증 결과

| 범위 | 결과 | 확인 내용 |
|---|---|---|
| 전체 서버 | **164 passed, 1 skipped** | SQLite와 실제 PostgreSQL의 일반 앱 역할. 기존 122건 + 신규 소셜/출석/가챠 42건 |
| SQLite → PostgreSQL 이전 보강 | **1 passed, 1 skipped** | 사진·그룹·출석·가챠 포함 이전, 원본 해시 보존, 비어 있지 않은 대상 거부. skip은 SQLite에서 PG 전용 테스트 제외 |
| 순수 게임 시스템 | **20 passed** | 기존 좌표/A*/이동/충돌/카메라/제스처 등 |
| 전체 Chrome 브라우저 | **18 passed** | 기존 15 + Phase 5 신규 3, 실제 UI/WS, SQLite 격리 DB |
| UI 수정 후 신규 Chrome | **3 passed** | 390px 팝업 가로 경계·사진·가챠 결과 스크롤 포함 |
| PostgreSQL 신규 Chrome | **3 passed** | 별도 PG DB에서 친구·그룹·사진·오프라인 알림·신고·출석·가챠·관리 UI |
| 프런트 빌드 | **성공** | TypeScript 검사 + Vite production build |
| ARM64 Docker API | **통과** | production 인증, 개발 로그인 403, 실제 PostgreSQL 및 media 볼륨 |
| Docker 저장/복구 | **통과** | DB+이미지 일관 백업, 별도 DB/볼륨 복원 비교, 전체 컨테이너 재생성, PostgreSQL/backend 재시작 |
| Docker Chrome | **통과** | 운영 로그인·연결된 월드·보존된 비공개 사진 피드·뽑기 영수증·대기 요청 결과 복구 |
| 기존 개발 DB | **보존** | 사용자16, 가구64, 배치48, 지갑8, 구매0, Coin원장9, 귓속말1, Coin합계8030 유지, schema7 |
| 기존 프로젝트/맵 | **보존** | DevNest 123개 파일 해시, shared의 maps/zones/personal-room/furniture-catalog 동일 |

테스트 전용 DB·브라우저 계정·Docker 프로젝트를 분리했습니다. 실서비스 사용자에게 테스트 티켓/가구를 지급하지 않았습니다. 예전 Phase 스크린샷은 백업 원본을 유지하고 새 화면은 phase5-*로 저장했습니다.

## 출석·가챠 보장 검증

- KST 23:59:59/00:00:00 날짜 경계, 같은 날 중복 지급 없음, 다음 날 연속/날짜 누락 리셋, 월별 달력, 누적 기록. 클라이언트 날짜 필드 거부.
- 출석 동시 8건에서 1회 지급. 티켓1장=1회, 5장=5회, 부족 거부, Coin 잔액 불변, 새 furniture_instances 지급, 동일 가구 중복 보유.
- 같은 요청키 동시 8건은 같은 영수증/인스턴스, 다른 요청키 동시 요청도 티켓 정합성/음수 방지. 사용자 간 영수증 접근 거부.
- 지급/출석 DB 실패를 SQLite trigger 및 PostgreSQL CHECK로 주입하여 티켓·가구·원장 전체 롤백 확인.
- 개별/등급 합계 10000 검증, 중복/미등록 아이템 거부. 확률표 변경 후 과거 영수증 v1 보존, 구버전으로 신규 뽑기 시 차감 없이 409.
- 관리자 외 확률/보상/무료 지급 변경 거부, 관리자 지급 재시도 중복 없음, 운영 감사/통계/잔액 부족 기록.
- SQLite/PG 서비스 재생성, Docker 재시작/컨테이너 재생성 후 기록 유지. 서버 secrets 난수의 가중 선택 경계 테스트이며 대규모 통계적 분포 검정과는 구별합니다.

## 소셜 보장 검증

친구 수락·거절·취소·삭제·중복/본인 요청 거부, 차단 후 관계/귓속말 제한; 프로필 privacy API/월드 마스킹; 그룹 역할·정원·가입 승인·퇴장·삭제 및 전역 관리자 권한 독립; 글/댓글 CRUD·반응 중복 방지; 그룹 외·탈퇴 사용자·나만 보기 접근 제한; PNG/JPEG/WebP 검증·잘못된 파일/크기/손상 거부·파일 정리; 다른 채널/오프라인 개인 알림·외부 소켓 미전달; 신고별 제한 검토·미디어 접근·숨김·감사; 페이지네이션·재시작 복원.

브라우저는 4개 탭에서 친구 요청 → 비공개 그룹 → 사진 게시 → 댓글/하트 → 외부 사용자 API/사진403 → 나만 보기 제외 → 다른 채널/오프라인 알림 → 신고/관리자 숨김까지 실행했습니다. 모바일390px에서는 사진 업로드·공개 설정·출석 달력·터치 뽑기·채팅 모드와 소켓 유지, 팝업 경계를 확인했습니다.

## Docker 저장 검증 상세

테스트 프로젝트 `nobis-phase5-verify`, PostgreSQL 내부 네트워크(호스트 DB 포트 미노출), 사용자 권한 UID10001 media 파일 생성. production 임시 계정3개, 사진1개/기록1개, 출석1개, 뽑기2건/획득6개, schema7을 생성했습니다. 쓰기를 멈춘 DB dump와 media tar를 다른 DB 및 새 media 볼륨으로 복원해 테이블 집계와 실제 이미지 SHA256을 비교했습니다. `down`(볼륨 유지) → `up --wait`, PostgreSQL/backend 재시작 후 집계·인증·그룹 ACL·사진 해시·당시 확률표가 동일했습니다. 최종 UI 수정으로 다시 빌드한 컨테이너에 Chrome으로 로그인해 보존된 화면과 대기 요청 영수증 복구도 확인했습니다. 원본/운영 DB에는 테스트하지 않았습니다.

## 실행·확인

프로젝트 루트에서:

```sh
.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
# 별도 터미널1
cd backend
APP_ENV=development DEV_AUTH_ENABLED=true ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18000
# 별도 터미널2, 프로젝트 루트
API_TARGET=http://127.0.0.1:18000 npm --prefix frontend run dev -- --host 127.0.0.1 --port 15173
```

브라우저 `http://127.0.0.1:15173/` → 상단 소셜/티켓 아이콘. 관리자 운영은 `/admin`에서 실제 권한 계정으로 확인합니다. DB/티켓/파일 정리/백업·복구/Docker 실행 명령은 README Phase 5 절에 있습니다.

```sh
# 프로젝트 루트
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

기본 pytest는 PostgreSQL URL 미설정 시 PG 사례를 추가 skip합니다. 실제 PG 전체 검증은 별도 테스트용 `NOBIS_TEST_POSTGRES_URL`(DB 생성/삭제 가능)와 `NOBIS_TEST_POSTGRES_APP_URL`(일반 앱 역할)을 환경으로 제공했습니다. `NOBIS_E2E_DATABASE_URL`도 별도 테스트 DB만 사용합니다. 테스트는 실제 Chrome 설치 경로/CHROME_BIN과 로컬 서버 포트15175/18002/18003을 필요로 합니다. 테스트 이미지 픽스처는 `tests/fixtures/social-upload.png`에 포함했습니다.

## 캡처·변경 파일

- [월드와 상단 진입점](phase5-office.png)
- [그룹 피드](phase5-group-feed.png), [Docker 보존된 사진](phase5-docker-feed.png)
- [가챠 결과 복구](phase5-docker-gacha-recovered.png), [뽑기 기록](phase5-docker-history.png)
- [소셜 신고 관리자](phase5-admin-social.png), [출석·가챠 관리자](phase5-admin-collectibles.png)
- [모바일 사진 공유](phase5-mobile-social.png), [모바일 출석](phase5-mobile-attendance.png)
- [생성·수정 파일](phase5-changes.md), [검증 결과 JSON](phase5-test-results.json)

동일 캡처와 index.html을 `Projects/캡처/NOBIS-Office_Phase5_2026-11-06`에도 저장합니다.

## 남은 범위와 발견한 제한

- 실제 iOS Safari/Android 기기·15명 장시간 그룹/미디어 부하·실제 Raspberry Pi 성능은 미검증입니다. Chrome 모바일 에뮬레이션과 Linux ARM64 Docker 결과로 구분합니다.
- 기존 단일 프로세스 Hub/레이트리밋 구조입니다. 다중 worker 배포 전 공유 presence·알림 전달 계층이 필요합니다.
- 기존 Phaser 포함 약1.84MB 번들 경고와 Python3.14의 FastAPI/Starlette deprecation 경고가 남습니다. 테스트 실패는 없습니다.
- 직접 ID 초대를 구현했으며 초대 링크·소유권 이전·외부 SNS·영상·최종 캐릭터/가구/맵 디자인·결제·거래는 구현하지 않았습니다. 다른 사람 집 방문은 기존 후속 범위입니다.
- 백업 보유 기간/자동 일정·실제 운영 TLS/도메인·계정 자율 가입/복구/SSO는 운영 결정이 필요합니다. 기본 로컬 media 파일 저장은 quota/정리 명령을 제공하며 외부 객체 저장소는 후속 확장점입니다.
- 프로필 위치 비공개가 공용 월드에 표시되는 아바타 좌표를 숨기지는 않습니다. 이미 다운로드한 이미지 사본은 권한 회수로 삭제할 수 없습니다. 신고 숨김 자료와 과거 백업의 보관 정책을 별도로 정해야 합니다.
