# Hybrid World 검증 — 2026-11-07

## 변경과 복구 지점

작업 전 Git e59fa65 및 backups/before-office-capacity-20261107.zip을 보존했습니다. 현재 개발 DB 적용 전 SQLite backup API로 backups/before-hybrid-world-20261107.sqlite3를 만들었습니다. v10 자체 마이그레이션도 최초 적용 전에 .pre-hybrid.bak를 생성합니다. 사용자 DB를 초기화하지 않았습니다.

맵·이동·룸 설계는 [hybrid-world.md](hybrid-world.md), 전체 변경 목록은 [hybrid-changes.md](hybrid-changes.md)를 참조하세요. 이전 단일 맵만을 전제로 한 검사 원문은 tests/archive와 backend/tests/archive에 보존했고, 독립 룸 연결·권한·현재 룸만 렌더링하는 검사로 대체했습니다.

## 검증 범위

| 항목 | 근거 |
|---|---|
| 로비→카페 실제 보행/퇴장→해당 로비 입구 | hybrid.spec.ts 두 브라우저 |
| 같은 룸 위치 동기화/다른 룸 아바타 미표시 | hybrid.spec.ts, test_hybrid.py |
| 업무실15개 작업 구획(각9칸),15인 별도 착석 | surface.test.ts, test_hybrid.py(실제15개 WebSocket) |
| 모든 룸 이동 가능 타일/오브젝트 접근 연결 | systems.test.ts, surface.test.ts, test_hybrid.py |
| 회의실15좌석, 참석자 ACL, 종료 후 퇴거 | hybrid.spec.ts, test_hybrid.py |
| 채널, 귓속말, 공지, 룸 채팅, 말풍선 제한 | social.spec.ts, phase2.spec.ts, test_social.py, test_hybrid.py |
| 개인 집/방문/가구 저장/상점/재접속 | phase3.spec.ts, phase6.spec.ts, test_phase3.py, test_phase6.py |
| 티켓→10~1000코인→상점, 중복 요청/롤백 | phase5.spec.ts, test_collectibles.py |
| 미니게임·협동 보상·관리자 | phase4.spec.ts, phase6.spec.ts, test_games.py |
| 모바일 터치, 핀치·카메라, 채팅 전용 모드 | hybrid.spec.ts, phase35.spec.ts, phase7.spec.ts |
| 기존 SQLite→PostgreSQL 이전 | test_phase35.py(실제 룸 정의/인스턴스/접속 행 포함) |
| 다른 사용자의 집 입장이 내 보행을 중단하지 않음 | test_hybrid.py의 불필요한 snapshot 전파 방지 검사 |

## 실행 환경과 결과

macOS ARM64, Node22, 로컬 Python3.14/실제 PostgreSQL17, Chrome headless입니다. Docker는 별도 검증 VM의 aarch64에서 Python3.12 + PostgreSQL17 + Nginx를 사용했습니다. 이 PC는 최종 운영 서버가 아닙니다.

- 프런트 독립 모듈 테스트:33개 통과.
- 최종 출입구 데이터 변경 후 서버 룸 검사:SQLite/PostgreSQL 합계15개 재검증 통과(회의 종료 직후 채팅/기록 접근 즉시 차단 포함).
- TypeScript 및 Vite production build:통과.
- 서버 전체 회귀:199개 통과,1개 제외(SQLite 경로에서는 PostgreSQL import 검사를 제외하며 실제 PostgreSQL 경로에서 별도 통과).
- 브라우저 전체25개 시나리오 통과(최종 출입구 데이터, 5.5분).
- ARM64 Docker:PostgreSQL·backend·frontend 실행, production 인증/로비/코인 확률 UI/관리자/정적 아틀라스6개 immutable 캐시/누락 에셋404 확인. CLI migrate가 schema_version10과 postgresql을 반환했습니다.
- Docker 기존 데이터 유지:사용자3명,가구 인스턴스23개,지갑2개,기존 추첨3건. 새 공용 로비 인스턴스와 room_presence 저장 확인. 검증 컨테이너/VM/격리 PostgreSQL은 종료하고 볼륨과 데이터는 보존했습니다.
- 개발 DB 마이그레이션 전후:기존 데이터11개 테이블 행 내용 해시 동일(사용자·개인 집·가구·지갑·코인 원장·구매·출석·티켓·가챠). 기존 사용자19명 유지.
- DevNest:기존123개 파일 해시 동일.

브라우저 중간 실행에서 맵 생성기의 파일 갱신이 진행 중인 이동을 중단한 경우가 있어, 최종 실행에서는 소스/맵 생성과 브라우저 검증을 순차 수행했습니다. 서버에서는 개인 집 이동 시 전 사용자 snapshot을 보내던 코드를 관련 룸 이벤트로 바꿔 다른 사용자 보행이 취소될 가능성을 제거했습니다. 의자의 과도한 클릭 영역이 책상을 덮는 문제도 줄였습니다. 정원 출구는 식물과 떨어진 가장자리로 옮겨 가려짐을 없앴습니다. A* 알고리즘/충돌 footprint는 유지했습니다.

## 남은 범위와 제한

최종 픽셀 아트·캐릭터 최종 디자인·외부 캘린더 연동·분산 서버·신규 게임/소셜은 제외했습니다. 기존 자체 제작 아틀라스와 임시 타일을 사용합니다. 대형 회의 테이블은 명시적 placeholder입니다. 필요한 이미지와 교체 파일은 hybrid-world.md에 있습니다.

Vite 빌드는 성공하지만 Phaser를 포함한 초기 JS 청크가 약2MB(gzip 약476KB)라 크기 경고가 남습니다. 실제 Raspberry Pi 하드웨어 및15대 브라우저의 성능 부하는 검증하지 않았습니다. 15인 검사는 서버 WebSocket 동시 연결과 착석 검증이며, 브라우저 회귀는2~3개 탭과390px 모바일 뷰포트입니다. 다중 worker나 클러스터는 지원하지 않습니다. Python3.14에서 FastAPI/Starlette deprecation 경고가 있으며 Docker Python3.12 실행은 별도 확인했습니다.

## 실행

README의 로컬 개발 및 Docker/PostgreSQL 설치·백업/복구 절차를 유지합니다. 개발 화면은 http://127.0.0.1:15173, API health는 http://127.0.0.1:18000/health입니다. 이전 맵 탭이 열려 있다면 새로고침해 현재 맵을 받습니다. 룸 데이터가 없는 이전 단일 맵 위치는 첫 접속에 로비 시작점으로 복귀하며 이후에는 채널별 마지막 룸을 복원합니다.

캡처: Projects/캡처/NOBIS-Office_Hybrid_2026-11-07(주요12장 및 회귀 검증). 이전 문서 이미지 원본은 보존했습니다. 새 성능 샘플은 hybrid-performance.json이며 단일 브라우저/아바타 기준입니다.
