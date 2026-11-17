# NOBIS Office — Phase 7-A · Hybrid World

공용 로비에서 캐릭터가 입구까지 걸어가 **독립된 룸**에 들어가는 메타버스 오피스입니다. React/TypeScript/Vite/Phaser 3 + FastAPI/WebSocket + PostgreSQL 17(또는 기존 SQLite)을 사용합니다. 최종 픽셀 아트는 이번 단계에 포함하지 않습니다. 현재 구조와 변경 사항은 [Hybrid World 설계](docs/hybrid-world.md), [검증 기록](docs/hybrid-verification.md)을 확인하세요. 이전 Phase 문서는 당시 구현의 기록입니다.

## 실행 방법 — 현재 Mac

터미널에서 아래 한 줄을 실행하세요. 백엔드와 프런트엔드 중 꺼져 있는 서버를 자동으로 켭니다.

```bash
/Users/hyowonkim/Desktop/Demo/Projects/NOBIS-office/start-frontend.command
```

[노비스 오피스 접속](http://127.0.0.1:15173) → 개발용 닉네임 입력 → **오피스 입장하기**. 실행한 터미널은 켜 두고, 종료하려면 `Ctrl+C`를 누릅니다. 이미 다른 터미널에서 실행 중인 서버는 그대로 재사용합니다.

더블클릭 실행, 재실행, `npm` 오류와 서버 연결 오류 해결은 **[실행 가이드 README-RUN.md](README-RUN.md)**에 정리했습니다. 다른 PC의 설치 및 Docker·PostgreSQL 운영 안내는 아래 기존 절차를 따르세요.

## 구조와 조작

```text
frontend/src/          React 화면·스토어·Phaser
  components/         사이드바, 채팅, 관리자, 집 꾸미기
  game/scenes/        OfficeScene, 개인 집 HomeScene
  game/systems/       좌표·A*·이동·충돌·상호작용·카메라·제스처·레이블
backend/app/          FastAPI·인증·WebSocket·repository·HomeService·SocialService
  database.py         PostgreSQL 어댑터와 추가형 v10 마이그레이션
  db_transfer.py      읽기 전용 SQLite 원본 → 빈 PostgreSQL 이전
  cli.py              계정·최초 관리자·마이그레이션·SQLite 백업
shared/               맵·존·가구 카탈로그(그림과 충돌 데이터 분리)
infra/                비밀 환경 생성·DB 초기화·ARM64 검증
compose.yaml          운영 PostgreSQL 구성(docker-compose.yml과 동일)
docker-compose.dev.yml 개발 PostgreSQL 구성
docker-compose.sqlite.yml 기존 SQLite 볼륨 보존 구성
docs/                 설계·스토리보드·구현 순서·검증 기록
```

- 바닥 클릭/탭: A* 이동. 드래그: 카메라 탐색. 휠/두 손가락 핀치: 줌. ‘전체 보기’와 ‘내 캐릭터’는 카메라만 변경합니다. WASD·존 이동 드롭다운·좌측 존 버튼은 없습니다.
- 기본 사이드바는 좁은 아이콘입니다. 데스크톱 호버/키보드 포커스로 펼치거나 상단 ☰로 고정하며 고정 상태를 저장합니다. 모바일 ☰는 서비스 메뉴를 덮어 엽니다.
- 모바일 하단 ‘월드/채팅’: 캔버스와 채팅을 별도 화면으로 표시합니다. 채팅 모드에서도 소켓·공지·귓속말은 유지하며 게임 렌더링은 멈춥니다.
- 채널 → 공용 로비/카페/집중 업무실/라운지/휴식 정원/외근 테라스/참석자 전용 회의실입니다. 현재 룸 하나만 렌더링하며 같은 채널·같은 룸의 아바타만 수신합니다. 채널 정원은 최대15명입니다. 업무실은15개 3×3 개인 작업 구획, 회의실은15개 좌석을 갖췄습니다. 휴가는 별도 공간 대신 상태 메시지로 표시합니다.
- 로비의 **개인 집 입구** 클릭 → 접근 → ‘내 방 · 작업실 입장’. 다른 룸에서 사이드바의 내 방을 누르면 출구→로비 입구까지 걸어갑니다. 개인 집 출입문은 이전 공용 룸·위치로 돌아갑니다. 미니게임 메뉴도 라운지 게임기까지 실제로 걸어갑니다.
- 집 꾸미기: 인벤토리 → 바닥/좌표 선택 → 회전 → 배치 확정 → 배치 저장. 회수하면 미설치 인벤토리로 복귀합니다. 미리보기 중에는 보행 입력을 막습니다. 서버가 소유권·revision·중복 설치·벽·가구·입구·통로·캐릭터 충돌을 검사합니다.
- 집 상점: 구매 확인 → 서버 잔액 차감+아이템 지급+거래 기록을 한 트랜잭션으로 확정합니다. request_id 재전송은 같은 영수증을 반환합니다. 개발 계정만 최초 1,000 Coin, 운영 계정은 0 Coin입니다. 실제 결제는 없습니다.

## 채팅·권한

| 종류 | 전달 범위 |
|---|---|
| 월드 | 모든 월드 채널의 사용자 |
| 채널 | 같은 채널, 모든 룸 |
| 현재 존(룸) | 같은 채널·같은 룸 인스턴스 |
| 초대 카페/회의 대화방 | 수락한 membership ACL, 서버 검증 |
| @닉네임 귓속말 | 발신자·선택한 수신자만, 다른 채널/오프라인 포함 |
| 공지 | 관리자 지정 전체/특정 채널, 일반 채팅과 별도 저장·토스트 큐 |

닉네임은 고유 키가 아닙니다. 자동완성에서 내부 user_id를 선택합니다. 선택 없는 중복 닉네임/존재하지 않는 수신자는 거부하며 오프라인 귓속말은 저장 후 재접속 때 전달합니다. ‘전달됨’은 읽음 확인이 아닙니다.

설정의 공개 채팅 말풍선은 기본 OFF이며 6초만 표시합니다. 집중 업무존·회의실·개인 집·귓속말·초대 대화·공지는 제외합니다. 고정 상태 메시지와 닉네임은 별도입니다. 화면 좌표로 레이블을 정렬하고 경계/겹침을 보정하며 공간이 모자라면 낮은 우선순위 레이블을 숨깁니다. HTML로 렌더링하지 않습니다.

| 역할 | 서버가 허용하는 범위 |
|---|---|
| user | 월드·채팅·내 집 |
| moderator | 신고, 공개 메시지 삭제, 하위 사용자 채팅 제한 |
| admin | 위 기능 + 공지·채널·하위 계정 관리·user/moderator 변경·감사 로그 |
| super_admin | 위 기능 + 관리자 임명/해제·시스템 설정 |

최초 관리자 지정은 CLI 전용·1회입니다. 마지막 super_admin 해제는 거부합니다. 운영자도 비공개 대화 본문을 우회 조회하지 못합니다. 대시보드는 DB의 실제 집계와 계정 생성 출처(개발/운영자/기존 미분류)를 구분합니다. 감사 로그는 이름·행동·KST로 표시하고 UTC 원본 JSON은 펼쳐봅니다. UI role 조작은 권한을 부여하지 않습니다.

## 로컬 개발 설치

Node.js 22+, Python 3.12+, macOS/Linux에서 프로젝트 루트 기준:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
```

터미널 1(SQLite 유지):

```sh
cd backend
APP_ENV=development DEV_AUTH_ENABLED=true ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18000
```

터미널 2:

```sh
API_TARGET=http://127.0.0.1:18000 npm --prefix frontend run dev -- --host 127.0.0.1 --port 15173
```

macOS에서는 프로젝트의 `start-frontend.command`를 실행하거나 더블클릭해도 프런트엔드가 시작됩니다. 프로젝트 `.tools/node`에 설치된 Node.js를 우선 사용하고, 없으면 PATH의 npm을 사용합니다. 이 파일은 백엔드와 프런트엔드를 확인하고 꺼져 있는 서버만 자동 실행합니다. 이미 실행 중인 서버는 재사용하며, 이 실행 파일이 시작한 서버만 Ctrl+C로 함께 종료합니다. `.tools`는 로컬 런타임 폴더로 Git에 포함하지 않습니다.

`http://127.0.0.1:15173/`, `http://127.0.0.1:18000/health`. 다른 포트를 쓰면 `ALLOWED_ORIGINS`도 프런트 주소에 맞춥니다. 기본 DB는 backend/data/nobis.sqlite3입니다. DATABASE_URL이 있으면 DATABASE_PATH보다 우선합니다. 로컬 PostgreSQL은 DATABASE_URL을 환경으로 주입하고 같은 명령을 사용합니다. 비밀번호/DSN을 출력·커밋하지 않습니다.

## Docker Engine / Compose 설치

아래 명령은 새 **64비트 Ubuntu 또는 Debian 호스트**에 해당합니다. 현재 macOS에서 이 apt 명령을 실행하지 않았습니다. 기존 Docker와 충돌하는 패키지가 있다면 공식 문서의 교체 절차를 먼저 적용합니다.

Ubuntu 저장소 등록 ([공식 설치 문서](https://docs.docker.com/engine/install/ubuntu/)):

```sh
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

Debian 저장소 등록 ([공식 설치 문서](https://docs.docker.com/engine/install/debian/)):

```sh
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $(. /etc/os-release && echo "$VERSION_CODENAME")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

해당 OS 저장소 등록 후 공통 설치:

```sh
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
```

아래 `docker` 명령은 Docker 사용 권한이 있는 터미널에서 실행합니다. 권한이 없으면 `sudo docker`를 사용합니다.

## PostgreSQL 초기화·최초 실행

프로젝트 루트에서 실행합니다. 생성기는 기존 env를 덮어쓰지 않으며 mode 600·각각 다른 랜덤 DB 암호를 만듭니다.

```sh
python3 infra/init-env.py --output .env.production
# 공개 DevNest가 있으면 위 명령에 --devnest-url https://실제-대시보드-도메인/ 추가
chmod 600 .env.production
docker compose --env-file .env.production -f compose.yaml config --quiet
docker compose --env-file .env.production -f compose.yaml up -d --wait postgres
docker compose --env-file .env.production -f compose.yaml build backend frontend
docker compose --env-file .env.production -f compose.yaml run --rm backend python -m app.cli migrate
docker compose --env-file .env.production -f compose.yaml up -d --wait
curl --fail http://127.0.0.1:8080/health
```

기본 서비스 이름은 **postgres / backend / frontend**입니다. backend는 비슈퍼유저 `nobis`로 접속합니다. postgres는 내부 data 네트워크에만 있으며 호스트 5432 포트를 열지 않습니다. 데이터는 `nobis-postgres-data` 이름의 Compose 관리 볼륨입니다. `down`은 보존하지만 **down -v는 데이터를 삭제하므로 사용하지 않습니다**. 초기화 스크립트는 새 볼륨에서 한 번만 실행됩니다. 이미 만든 볼륨에 env 암호만 변경하면 접속이 깨지며 DB 역할 암호도 함께 변경해야 합니다.

기본 HTTP 바인딩은 127.0.0.1:8080, 플랫폼은 linux/arm64입니다. x86 서버는 `.env.production`의 DOCKER_PLATFORM=linux/amd64로 바꿉니다. 포트 충돌은 HTTP_PORT를 변경합니다. 외부 공개 시 실제 HTTPS 리버스 프록시 도메인을 ALLOWED_ORIGINS에 정확히 등록하고 내부 주소/포트와 HTTP_BIND를 배치 구조에 맞춥니다. 이 저장소는 TLS 인증서 발급을 수행하지 않습니다. Backend는 단일 worker를 유지해야 채널 정원이 정확합니다.

개발 Compose는 별도 `nobis-dev-postgres-data` 볼륨을 사용합니다:

```sh
python3 infra/init-env.py --development --output .env.development
docker compose --env-file .env.development -f docker-compose.dev.yml up --build -d --wait
```

개발 화면은 127.0.0.1:5173, 개발 인증은 development에서만 가능합니다. 운영 설정과 개발 env를 섞지 않습니다.

## 최초 관리자·비밀번호 계정

```sh
docker compose --env-file .env.production -f compose.yaml exec backend python -m app.cli create-user --nickname operator
docker compose --env-file .env.production -f compose.yaml exec backend python -m app.cli list-users
# 출력의 실제 user_id를 대입
NOBIS_USER_ID='위에서 확인한 사용자 ID'
docker compose --env-file .env.production -f compose.yaml exec backend python -m app.cli bootstrap-admin --user-id "$NOBIS_USER_ID"
```

create-user는 비밀번호를 숨김 입력받습니다. 로그인 화면 ‘기존 계정으로 로그인’에서 user_id와 비밀번호로 접속합니다. 관리자 승격/해제는 super_admin 로그인 후 **/admin → 권한 관리**에서 수행합니다. CLI가 웹 API의 권한 검사를 우회하는 임의 승격 명령을 제공하지 않습니다.

기존 사용자 집·잔액을 유지하며 비밀번호 설정 및 세션 회수:

```sh
docker compose --env-file .env.production -f compose.yaml exec backend python -m app.cli set-password --user-id "$NOBIS_USER_ID"
```

비밀번호는 PBKDF2-SHA256 600,000회 해시, 세션은 해시로 저장합니다. password 세션 유효기간은 24시간입니다. 운영 모드는 개발 로그인·개발 세션·개발 관리자 키를 거부합니다. 공개 가입/비밀번호 찾기/SSO/MFA는 후속 범위입니다. 자동화는 CLI의 --password-env에 비밀번호 **환경변수 이름**만 전달할 수 있습니다.

## 재시작·상태·로그

```sh
docker compose --env-file .env.production -f compose.yaml ps
docker compose --env-file .env.production -f compose.yaml logs --tail=100 backend frontend postgres
docker compose --env-file .env.production -f compose.yaml restart backend frontend
docker compose --env-file .env.production -f compose.yaml up -d --wait
```

재접속은 지수 백오프, 중복 계정 연결은 이전 소켓을 4001로 닫습니다. 최신 유효 세션만 남으며 원래 위치·상태를 복구합니다. 가득 찬 채널은 다른 활성 채널을 선택합니다. 비활성 저장 채널은 기본 채널의 별도 저장 위치 또는 spawn으로 복귀합니다. DB 장애 시 health 503/WS 1013으로 재시도를 유도하며 비밀번호 포함 DSN을 응답하지 않습니다.

## PostgreSQL 백업·복원

백업에는 계정·개인 메시지가 포함되므로 접근을 제한합니다. DB와 앱 버전·env를 함께 관리하고 백업 복원 점검을 정기적으로 수행합니다.

```sh
mkdir -p backups
umask 077
NOBIS_BACKUP="backups/nobis-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose --env-file .env.production -f compose.yaml exec -T postgres sh -c 'export PGPASSWORD="$NOBIS_DB_PASSWORD"; exec pg_dump -h 127.0.0.1 -U "$NOBIS_DB_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl' > "$NOBIS_BACKUP"
test -s "$NOBIS_BACKUP"
```

복원은 검증된 백업 경로를 지정하고 현재 데이터를 먼저 백업합니다. `--clean`이 기존 DB 내용을 교체하므로 앱을 정지하고 수행합니다:

```sh
NOBIS_RESTORE='backups/복원할-실제-백업.dump'
docker compose --env-file .env.production -f compose.yaml stop backend frontend
docker compose --env-file .env.production -f compose.yaml exec -T postgres sh -c 'export PGPASSWORD="$NOBIS_DB_PASSWORD"; exec pg_restore -h 127.0.0.1 -U "$NOBIS_DB_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-acl --exit-on-error' < "$NOBIS_RESTORE"
docker compose --env-file .env.production -f compose.yaml run --rm backend python -m app.cli migrate
docker compose --env-file .env.production -f compose.yaml up -d --wait
```

## 기존 SQLite 데이터 보존·PostgreSQL 이전

기존 SQLite는 자동 전환하지 않습니다. 기존 Compose를 계속 쓰려면 **-f docker-compose.sqlite.yml**을 명시해 원래 프로젝트명/디렉터리에서 실행합니다. 기존 `nobis-data` 볼륨을 유지합니다. SQLite v5 적용 전 `.pre-phase35.bak`를 보존하며 계정·집·코인은 유지합니다.

로컬 SQLite 온라인 일관 백업:

```sh
cd backend
../.venv/bin/python -m app.cli backup --output ../backups/sqlite-before-postgres.sqlite3
cd ..
```

기존 SQLite Compose에서 백업할 때(구성 전환 전에 실행):

```sh
docker compose -f docker-compose.sqlite.yml exec -T backend python -m app.cli backup --output /app/data/sqlite-before-postgres.sqlite3
docker compose -f docker-compose.sqlite.yml cp backend:/app/data/sqlite-before-postgres.sqlite3 backups/sqlite-before-postgres.sqlite3
docker compose -f docker-compose.sqlite.yml stop backend frontend
```

새 PostgreSQL 구성 초기화 후, 사용자 데이터가 **없는 대상 DB**에만 가져옵니다. 기존 소스는 읽기 전용으로 백업한 사본을 마이그레이션하며 원본을 수정하지 않습니다.

```sh
docker compose --env-file .env.production -f compose.yaml stop backend frontend
docker compose --env-file .env.production -f compose.yaml run --rm -v "$PWD/backups/sqlite-before-postgres.sqlite3:/import/source.sqlite3:ro" backend python -m app.cli import-sqlite --source /import/source.sqlite3
docker compose --env-file .env.production -f compose.yaml up -d --wait
```

가져오기는 한 DB 트랜잭션이며 기존 사용자 존재 시 거부합니다. 계정·역할·집·재화·가구·대화·감사 기록을 이전합니다. 운영 환경에서 기존 개발 세션은 사용할 수 없으므로 위 set-password로 계정을 전환합니다. SQLite 복원은 앱 정지 후 `python -m app.cli restore --source BACKUP --replace`(backend 디렉터리, DATABASE_PATH 설정)로 수행하며 기존 DB의 pre-restore 백업을 만듭니다. PostgreSQL은 이 CLI backup/restore 대신 pg_dump/pg_restore를 사용합니다.

## 새 운영 서버 이전·ARM64 점검

1. 원 서버의 코드 버전·env·DB를 백업합니다. 마지막 이전 직전 앱 쓰기를 중지하고 최종 DB dump를 만듭니다.
2. 새 서버에 64비트 OS/Docker/Compose를 설치합니다. 프로젝트(실행 데이터·node_modules·.venv 제외)와 비밀 env를 안전하게 복사합니다. env는 600 권한을 유지하며 공개 origin/DevNest 주소를 새 도메인에 맞춥니다.
3. 새 서버에서 postgres 초기화 → backend/frontend 빌드 → migrate → 위 pg_restore → migrate → 전체 up 순서로 실행합니다. 관리자·가구·잔액·귓속말·두 브라우저 이동/채팅을 확인한 후 접속 경로를 전환합니다.
4. ARM64 대상에서는 `sh infra/verify-arm64.sh .env.production`을 실행합니다. 스크립트는 아키텍처·서비스 health·마이그레이션을 확인합니다. 컨테이너 재시작·볼륨 보존·복원은 별도 실제 운영 점검이 필요합니다.

Raspberry Pi 4 8GB는 목표 장비이며 부하·메모리·SD/SSD 내구성·전원·발열을 실기기로 측정하지 않았습니다. Phase 4에서는 별도 Colima ARM64 VM에서 실제 Compose 빌드·기동·Nginx WebSocket·PostgreSQL 보상·백업/복원·재시작·볼륨 보존까지 확인했습니다. Raspberry Pi 실기기 검증과는 구분합니다.

## 장애 복구

- 포트 점유: `docker compose ... ps` 및 `ss -ltnp`로 충돌 확인, env의 HTTP_PORT/DEV_HTTP_PORT 변경 후 up. DB 포트를 외부에 열어 해결하지 않습니다.
- DB 연결 실패: postgres 로그·health·디스크 여유·앱 역할 암호를 확인합니다. env만 바꾼 기존 볼륨은 초기화 스크립트가 재실행되지 않습니다. 기존 볼륨을 지우지 말고 역할 자격 증명을 복원합니다.
- 마이그레이션/배치 저장 실패: 응답 오류와 로그를 확인하고 같은 버전으로 재시도합니다. 구매/배치 실패는 트랜잭션 롤백됩니다. 배치 revision 충돌은 최신 배치를 불러와 다시 편집합니다.
- 복구 불가능한 데이터 손상: 현재 데이터도 보관한 뒤 위 백업 복원 절차를 사용합니다. `down -v`/볼륨 삭제는 복구 방법이 아닙니다.
- WebSocket 불가: HTTPS에서 wss·프록시 Upgrade/Connection 헤더·ALLOWED_ORIGINS·단일 worker를 확인합니다. Nginx /ws 경로는 현재 구성에 포함되어 있습니다.
- DevNest 실패: 설정에서 HTTP(S) URL 확인·팝업 허용·새 탭의 네트워크 오류를 확인합니다. 운영 기본 URL은 DEVNEST_URL, 개발 기본값은 DEVNEST_DEV_URL입니다. 운영에서는 localhost/loopback URL을 거부합니다. 다른 origin의 실제 HTTP 성공 여부는 브라우저 보안상 자동 판별하지 않고 재시도/주소 설정 안내를 제공합니다. DevNest 원본·계정 연동은 변경하지 않습니다.

## 테스트와 확장

```sh
cd backend
../.venv/bin/python -m pytest tests -q
cd ..
npm --prefix frontend test
npm --prefix frontend run build
cd frontend
CHROME_BIN='/실제/Chrome/실행파일' npm run test:e2e
```

브라우저 검증은 현재 macOS Chrome 경로가 기본입니다. PostgreSQL 통합 테스트는 **별도 테스트 서버**의 NOBIS_TEST_POSTGRES_URL(DB 생성/삭제 권한)과 NOBIS_TEST_POSTGRES_APP_URL(일반 앱 역할)을 사용합니다. 테스트가 생성한 `nobis_test_*` DB만 삭제합니다. 브라우저도 별도 DB URL을 NOBIS_E2E_DATABASE_URL로 전달할 수 있습니다. 운영 DB를 테스트 URL로 지정하지 않습니다.

좌표/A*/충돌/상호작용·카메라·입력·화면 레이블은 독립 모듈입니다. 추가 미니게임 보상도 서버 거래 원장을 통해, 소셜 그룹/피드/사진/첨부는 별도 membership·공개 범위 ACL로 확장합니다. Phase 4에는 두더지 잡기 1종만 추가했습니다. 소셜 피드·음성/영상·실제 결제·외부 일정 연동·다중 worker 클러스터·최종 아트는 추가하지 않았습니다. 배포 전 TLS·운영 백업 복원·실기기 부하·비밀번호 복구 정책을 확정해야 합니다.


## Phase 4 — 아케이드 사용 방법

1. 라운지의 **NOBIS 아케이드 게임기**를 클릭합니다. 캐릭터가 A*로 인접 바닥까지 걸어간 뒤 게임 로비를 엽니다. 사이드바 ‘미니게임 · 아케이드’도 같은 오브젝트 접근 동작입니다. 새 존·존 이동 메뉴·WASD는 추가하지 않았습니다.
2. **두더지 잡기 → 플레이 시작**. 3×3 보드에서 30초 동안 나타난 두더지를 클릭/터치합니다. 한 두더지는 한 번만 명중하고 빈 칸은 0점입니다. 점수와 남은 시간은 서버 상태를 기준으로 표시합니다.
3. 종료 후 점수·명중·획득 Coin·서버 확인 잔액을 표시합니다. 다시 플레이하거나 오피스로 복귀합니다. ‘게임 종료 · 보상 없이 끝내기’는 중도 취소이며 보상은 없습니다.
4. 로비 **내 게임 기록**에서 최근 30회, 게임별 총 플레이·최고 점수·누적 Coin을 확인합니다. 취소/만료도 상태와 함께 표시하며 업무 성과와 연결하지 않습니다.
5. 카드 짝 맞추기·코인 모으기는 준비 중으로 비활성화합니다. 두 번째 게임은 구현하지 않았습니다.

게임 오버레이는 중앙 월드를 사용하며 데스크톱 우측 채팅은 그대로 이용할 수 있습니다. 모바일은 기존 하단 월드/채팅 전환을 유지합니다. 게임 중에도 채팅·귓속말·공지를 수신하고 다른 사용자에게 ‘미니게임 플레이 중’ 상태를 전합니다. 오피스 이동·집 입장·채널 변경은 서버에서도 거부합니다. 게임 종료 시 원래 좌표와 근무 상태가 유지됩니다. 새로고침/재접속하면 같은 활성 세션을 복구합니다.

## 미니게임 모듈과 확장

```text
frontend/src/games/
  core/GameModule.ts              공통 보드 props·runtime 계약
  core/GameRegistry.ts            플레이 가능한 모듈 등록
  core/GameSession.ts             시작·진행·종료·HTTP/응답 정합성
  core/GameResult.ts              공통 목록·세션·결과 타입
  whack-a-mole/WhackAMoleGame.ts   단조 시계 기반 표시 타이머·입력 제한
  whack-a-mole/WhackAMoleBoard.tsx 독립 3×3 보드
  whack-a-mole/gameConfig.ts      화면 설정
  components/                    로비·플랫폼·결과·보상·관리자
backend/app/games/
  registry.py                    게임 규칙·등장·설정
  service.py                     영속 세션·판정·정산·기록
  api.py                         인증·오브젝트 접근·RBAC·입력 계약
  schema.py                      추가형 v6 마이그레이션
```

새 게임은 서버 RULES에 규칙 객체를 등록하고 서버 판정기를 확장합니다. 프런트 GameRegistry에 GameModule(식별자·runtime 생성·Board 컴포넌트)을 등록합니다. GamePlatform은 공통 로비/시작/결과/기록을 담당하며 새로운 입력 종류가 필요하면 Strict API와 runtime 계약을 명시적으로 확장합니다. 현재 입력 계약은 두더지의 cell/wave/challenge입니다. 기존 Office UI·HomeService 지갑/상점 로직을 복사하지 않습니다. 결과와 보상은 동일 원장·정산 서비스를 통과해야 합니다.

## 서버 세션·점수 판정

**매 클릭 서버 전송 방식**입니다. 서버가 256bit 랜덤 seed를 세션에 비공개 보관하고 HMAC(seed, wave)로 해당 구간의 위치·challenge를 재현합니다. 전체 시드/미래 등장표를 클라이언트에 보내지 않습니다. 800ms마다 1개, 650ms 노출, 명중당 10점, 총 30초가 기본 규칙이며 registry.py에서 설정합니다.

클라이언트는 서버가 현재 보여준 cell/wave/challenge와 UUID event_id만 제출합니다. 서버 수신 시각으로 활성 세션·소유권·현재 구간·challenge·유효 시간·이전 명중을 검사합니다. 최종 score/reward/클라이언트 타임스탬프를 받아 확정하지 않으며 추가 필드는 422로 거부합니다. 입력 80ms 미만은 429, UI는 100ms 간격과 단일 pointerdown으로 터치 중복을 막습니다. 같은 event_id의 같은 입력은 재사용하고 다른 입력에 재사용하면 409입니다. 한 세션·구간에는 명중 1건만 DB 유니크 인덱스로 허용합니다.

게임 시작도 UUID request_id로 멱등 처리하며 사용자당 활성 세션은 1개입니다. 시작 후 2초는 재시도를 제한합니다. 종료 전 정산은 409입니다. 종료 후 5분까지 재연결/정산할 수 있고 이후에는 만료 기록만 저장하여 보상 없이 해제합니다. 중도 취소도 기록은 남지만 보상을 지급하지 않습니다. 숨겨진 탭에서도 서버 시각은 진행하며 타이머를 멈춰 점수를 늘릴 수 없습니다.

이 방식은 임의 점수·미래/중복 명중·중복 보상 위조를 차단합니다. 실제 유효 두더지를 자동으로 누르는 봇을 사람과 구별하는 시스템은 이번 범위에 포함하지 않습니다. 요청 속도·세션 제한·일일 보상 상한을 적용합니다.

## 기존 NOBIS Coin 보상

| 서버 점수 | 테스트용 기본 보상 |
|---|---:|
| 0~49 | 0 Coin |
| 50~99 | 10 Coin |
| 100~149 | 20 Coin |
| 150 이상 | 30 Coin |

기본 일일 보상 상한은 사용자별 모든 게임 합산 **300 Coin**, 날짜 경계는 **UTC 00:00**입니다. 상한에 도달해도 자유 플레이는 가능하며 보상은 0 또는 남은 한도만큼 지급합니다. 운영 계정의 초기 코인은 기존 정책대로 0입니다.

정산은 SQLite BEGIN IMMEDIATE / PostgreSQL 트랜잭션 advisory lock 안에서 결과 확정 → 기존 user_wallets 잔액 증가 → coin_transactions(kind=minigame_reward) 기록 → game_reward_transactions의 session/원장 링크 → 감사 로그를 함께 커밋합니다. 실패하면 전체 롤백합니다. session_id PK/원장 링크 UNIQUE/세션 상태로 동시 제출도 1회 지급합니다. 같은 정산 요청을 재전송하면 저장된 결과와 현재 서버 잔액을 반환합니다. 새 별도 지갑을 만들지 않았습니다.

데이터 역할:

- game_sessions: 소유자·게임·서버 시작/만료·상태·비공개 seed·규칙/보상표 스냅샷
- game_inputs: 멱등 입력·서버 수신 시각·명중 판정
- game_results: 최종 점수·명중·종료 시각(세션당 하나)
- game_reward_transactions: 결과 세션과 기존 Coin 원장 연결·UTC 날짜·상한 적용 이유. 금액/잔액은 coin_transactions를 JOIN하여 중복 저장하지 않습니다.
- game_settings: 활성·보상표·일일 상한
- game_validation_events: 빠른 입력·잘못된 challenge·만료 입력·요청 재사용. 동일 사용자/이유는 10초 단위로 로그를 제한합니다.

## 관리자 게임 운영

기존 `/admin`에서 다음 메뉴를 사용합니다.

- **게임 설정**: 활성/비활성, 구간별 최소 점수·지급 Coin, 일일 보상 상한
- **게임 보상 내역**: 사용자·점수·지급액·잔액·상한 적용·원본 연결
- **게임 이용 현황**: 사용자·세션 상태·시작/만료 시각
- **게임 검증 기록**: 비정상 입력 사유·시각

user는 접근할 수 없습니다. moderator는 조회만, admin/super_admin은 게임 설정을 변경할 수 있습니다. 설정 변경과 보상 지급은 기존 감사 로그에 기록합니다. 보상표는 새 세션에 적용하고 진행 중 세션은 시작 당시 표를 유지합니다. 일일 상한은 정산 시 최신 설정을 사용합니다. 비활성화도 새 시작만 막으며 이미 승인된 정상 세션은 정산할 수 있습니다.

## 게임 마이그레이션·실행·이전

루트에서 로컬 SQLite 마이그레이션 후 개발 서버를 실행합니다. 기존 계정/지갑/가구를 보존하며 v6 최초 적용 전 `.pre-phase4.bak`를 만듭니다.

```sh
cd backend
../.venv/bin/python -m app.cli migrate
APP_ENV=development DEV_AUTH_ENABLED=true ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18000
# 별도 터미널, 프로젝트 루트
API_TARGET=http://127.0.0.1:18000 npm --prefix frontend run dev -- --host 127.0.0.1 --port 15173
```

PostgreSQL/운영 Compose는 기존 설정과 동일한 서비스 이름입니다. 비밀 env가 없다면 앞의 init-env.py 절차부터 수행합니다.

```sh
docker compose --env-file .env.production -f compose.yaml build backend frontend
docker compose --env-file .env.production -f compose.yaml run --rm backend python -m app.cli migrate
docker compose --env-file .env.production -f compose.yaml up -d --wait
```

게임용 별도 서버·포트·Redis·DB를 추가하지 않았습니다. 운영 서버 이전은 앞 절의 전체 pg_dump/pg_restore에 game_* 테이블이 함께 포함됩니다. SQLite → PG import-sqlite에도 game_*를 추가했습니다. 게임 seed는 사설 DB/백업에만 보관하고 공개 응답·관리자 목록·캡처에 노출하지 않습니다. 서버 재시작은 활성 세션과 결과를 DB에서 복원하며 보상을 재지급하지 않습니다.

독립 테스트 서버의 비밀번호 계정으로 실제 시간을 사용한 아케이드 smoke test(2회 30초 + 걸어서 입장, 기록/재지급/40 Coin 가구 구매 검증)를 실행할 수 있습니다. 운영 사용자에 실행하지 않습니다.

```sh
# 실행 환경에 NOBIS_VERIFY_PASSWORD를 비밀 값으로 주입한 후, 테스트 계정 ID 사용
.venv/bin/python infra/verify-arcade.py --base-url http://127.0.0.1:8080 --user-id "$NOBIS_USER_ID" --plays 2
```

스크립트는 기존 보상 기본값/상점 가격을 검증합니다. 테스트 계정의 일일 한도가 충분해야 하며 기존 세션·개인 집이 아닌 공용 오피스에서 시작합니다. 계정/집/거래가 실제 생성되므로 격리된 DB를 사용합니다.

빌드에서 발견된 기존 개발 도구 경고는 Vite 6.4.5와 Playwright 1.55.1로 최소 업데이트했습니다. [Vite 공지](https://github.com/vitejs/vite/security/advisories/GHSA-rq7h-c2jc-7f22), [Playwright 공지](https://github.com/advisories/GHSA-7mvr-c777-76hp)에 해당하는 이전 버전을 교체했으며 최종 npm audit 결과는 검증 기록에 포함합니다. 컨테이너 전체 취약점 스캔 완료를 의미하지 않습니다.

## Phase 5 — 친구·그룹·사진 기록

상단 **소셜 아이콘**에서 친구, 내 그룹, 그룹 피드, 소셜 알림, 공개 설정을 엽니다. 월드 채널·현재 존과 별개인 작은 그룹이며 그룹 전용 게임 맵은 만들지 않습니다. 다른 채널과 오프라인 사용자에게도 활동 알림을 DB에 저장하고, 접속 중에는 해당 사용자 소켓에만 갱신 신호를 보냅니다.

- 프로필: 자기소개·상태 메시지·온라인 여부·업무 상태·프로필 위치를 각각 전체/친구/비공개로 설정합니다. 월드에 실제 표시되는 캐릭터 좌표는 공동 공간 렌더링에 필요하므로 공개 설정이 캐릭터를 숨기는 기능은 아닙니다.
- 친구: 요청·수락·거절·취소·삭제, 중복 요청 방지. 차단하면 친구 관계와 대기 중 초대를 정리하고 새 귓속말·초대·친구 요청을 막으며 상대의 피드·알림을 제외합니다.
- 그룹: 기본 비공개, 기본 정원 12명. `SOCIAL_GROUP_MAX_MEMBERS=30`으로 생성 상한을 조정합니다(하드 상한 50). 사용자 ID 직접 초대 또는 공개 그룹 가입 요청을 승인합니다. 소유자는 설정·매니저 임명·삭제, 소유자/매니저는 초대·승인·일반 멤버 퇴장을 관리합니다. 그룹 역할은 월드 관리자 권한을 부여하지 않습니다.
- 기록: 텍스트·사진 최대 4장, 그룹 공개 또는 나만 보기, 작성자 수정/삭제, 한 단계 댓글·댓글 수정/삭제·이모지 반응, 커서 페이지네이션. 그룹 관리자도 다른 작성자의 ‘나만 보기’를 조회하지 못합니다.
- 알림: 친구 요청·그룹 초대·새 글·댓글·반응. 읽음/전체 읽음을 지원합니다. 화면에는 최근 300개, 피드는 페이지당 최대 30개를 조회합니다.
- 신고: 글·댓글·사용자 신고. `/admin` → **소셜 신고**에서 권한 있는 운영자만 해당 신고 대상과 연결된 이미지에 접근하고 숨김/처리 메모를 남깁니다. 검토·처리는 감사 로그를 남기며 비공개 그룹 전체 열람 권한을 부여하지 않습니다.

`backend/app/community/`는 관계·그룹·게시글·파일 권한을 관리합니다. 기존 `SocialService`의 계정·역할·감사 로그와 기존 WebSocket Hub를 재사용합니다. `frontend/src/social/`은 React UI이며 Phaser 맵 로직과 분리했습니다. 월드 UI 위의 모달에서 동작하며 좌측 존 버튼은 추가하지 않았습니다.

## 출석·무료 가챠 티켓

상단 **티켓 아이콘** → 출석 / 가구 뽑기 / 뽑기·티켓 기록. 출석은 선택 버튼 방식이며 서버 **Asia/Seoul 날짜** 기준 하루 한 번 기본 티켓 1장입니다. 달력·연속/누적 출석을 확인할 수 있습니다. 실제 근태·출퇴근·휴가·평가와 연결하지 않습니다. NOBIS Coin과 별도 잔액/원장을 사용하며 현금 구매·교환·사용자 거래는 없습니다.

현재 가챠는 **가구 대신 NOBIS Coin**을 지급합니다. 1회=티켓1장, 5회=티켓5장이며, 한 번마다 **10~1,000 Coin을 10코인 단위**로 받습니다. 기본 확률은 중심505·표준편차165의 정규분포 형태를 범위 안에서 이산화한 100개 금액입니다. 정수 확률 가중치 합계는 정확히10000(100%)이며 좌우 대칭입니다. 500/510코인은 각각2.42%, 10/1000코인은 각각0.03%, 평균 보상은505 Coin입니다. UI에 분포 그래프와 금액별 전체 확률을 공개합니다. [전체 확률 CSV](docs/coin-gacha-probabilities.csv), [변경·검증 기록](docs/coin-gacha.md).

- 서버 `secrets.randbelow`로 추첨합니다. 클라이언트는 결과를 결정하지 않고 서버 영수증만 연출하며 건너뛰기/동작 줄이기를 지원합니다.
- 출석 기록+티켓 지급, 티켓 차감+코인 지갑 증가+Coin원장+추첨 기록은 각각 단일 DB 트랜잭션입니다. 중복 요청은 같은 영수증을 반환하며 다시 지급하지 않습니다. 가구 인벤토리는 변경하지 않습니다.
- 뽑기 요청은 UUID `request_id`, 배너 ID, 횟수, 확인한 `pool_version`을 포함합니다. 확률표 변경 시 차감 전에409로 거부합니다. 네트워크 오류 시 같은 UUID로 재시도합니다.
- 확률 변경은 새 버전 추가 방식이며 과거 영수증의 당시 확률을 보존합니다. 사용자는 최근30회 뽑기·100건 티켓 거래를 볼 수 있습니다. 기존 가구 배너는 종료하고 기존 가구/영수증은 보존했습니다.
- `/admin` → **출석 · 가챠 운영**: 코인 배너 생성/활성화, 금액별 확률 편집·정규분포형 기본값 복원, 출석 보상0~10장, 무료 티켓 지급, 실제 금액별 추첨 통계·거래·거절 기록. moderator는 조회, admin 이상은 변경 가능합니다. 유료 티켓·현금 교환·사용자 거래는 없습니다.

`backend/app/collectibles/`와 `frontend/src/collectibles/`가 담당합니다. 기존 `user_wallets`와 `coin_transactions`를 재사용하며 지급 원장 종류는 `gacha_reward`입니다. 스키마v8은 `gacha_coin_pool_items`, `gacha_coin_draw_items`를 추가하고 과거 가구 테이블은 유지합니다. 미니게임·가구 상점·집 꾸미기는 기존 코인을 그대로 사용합니다.

## Phase 5 마이그레이션·테스트 데이터·운영 조회

스키마 v9는 기존 테이블을 삭제하지 않는 SQLite/PostgreSQL 공통 추가형 마이그레이션입니다. 서버 시작 또는 CLI migrate가 실행하며, 기존 SQLite v6에는 `.pre-phase5.bak`, v7에는 `.pre-coin-gacha.bak`을 먼저 만듭니다. 운영 DB·이미지를 아래 방법으로 함께 백업한 뒤 적용합니다.

```sh
# 프로젝트 루트, PostgreSQL 운영
docker compose --env-file .env.production -f compose.yaml up -d --build
docker compose --env-file .env.production -f compose.yaml run --rm backend python -m app.cli migrate
# 기존 로컬 SQLite (별도 터미널, backend 디렉터리)
cd backend
../.venv/bin/python -m app.cli migrate
```

기본 코인 배너와 기존 가구 카탈로그는 초기화 시 한 번 생성합니다. 개발 계정은 기존 개발 로그인으로 생성한 뒤 출석하거나, 운영자 계정으로 테스트용 무료 티켓을 지급합니다. 운영 환경에서 개발 로그인을 활성화하지 않습니다. 실제 사용자 ID를 대입합니다.

```sh
# 프로젝트 루트; ADMIN_ID, TARGET_USER_ID는 실제 계정 ID
NOBIS_REQUEST_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
docker compose --env-file .env.production -f compose.yaml exec -T backend python -m app.cli grant-tickets --actor-id "$ADMIN_ID" --user-id "$TARGET_USER_ID" --tickets 5 --request-id "$NOBIS_REQUEST_ID"
docker compose --env-file .env.production -f compose.yaml exec -T backend python -m app.cli ticket-history --user-id "$TARGET_USER_ID"
```

`grant-tickets`는 actor의 현재 관리자 권한을 확인하고 감사 로그를 남깁니다. 같은 요청 ID를 재사용하면 재지급하지 않습니다. `ticket-history`는 잔액·출석·뽑기 영수증·티켓 지급/차감 내역을 출력합니다. 브라우저에서는 사용자 본인 API만 허용합니다. API 인증 토큰을 환경으로 안전하게 제공한 경우:

```sh
curl --fail -H "Authorization: Bearer $NOBIS_TOKEN" http://127.0.0.1:8080/api/collectibles/attendance
curl --fail -H "Authorization: Bearer $NOBIS_TOKEN" http://127.0.0.1:8080/api/collectibles/history
```

## 사진 저장·보관 정책

Docker는 **nobis-media** 영구 볼륨을 `/app/media`에 연결합니다. 로컬 기본값은 backend에서 실행 시 `backend/data/media`, `MEDIA_ROOT`로 변경 가능합니다. JPEG/PNG/WebP 정지 이미지만 허용합니다. 파일당 5 MiB, 한 변 4096px, 사용자당 활성 파일 100 MiB, 업로드 디코딩 동시 작업 2개 제한을 둡니다. 실제 디코딩·손상/프레임 검사·재인코딩으로 형식과 메타데이터를 정리합니다. 원래 파일명·요청 MIME은 신뢰하지 않습니다.

사진은 공개 정적 URL로 서비스하지 않습니다. `/api/community/media/{id}`는 매번 현재 그룹/글 공개 범위·차단·삭제 여부를 검사하고 `private, no-store`로 응답합니다. 탈퇴·강퇴·삭제 후에는 서버 다운로드가 거부됩니다. 이미 내려받은 사본은 회수할 수 없습니다. 파일 저장 API를 `LocalMediaStore`로 분리하여 추후 객체 저장소로 교체할 수 있습니다.

글/댓글은 soft delete로 보관하며 삭제 이미지와 미사용 업로드는 아래 정리 명령으로 실제 파일을 삭제합니다. 기본 미사용 업로드 유예는 24시간입니다. 신고로 숨긴 사진은 검토 증거로 보관하고 일반 다운로드는 차단합니다. 백업 보유 기간은 운영자가 별도 정해야 하며, 정리 후에도 과거 백업에는 삭제 자료가 남을 수 있습니다.

```sh
docker compose --env-file .env.production -f compose.yaml exec -T backend python -m app.cli cleanup-media --grace-hours 24
```

## DB와 사진의 일관된 백업·복원·서버 이전

Phase 5 이후에는 DB만 복구하면 사진이 누락됩니다. 동일 시점 **DB dump + media archive**를 한 세트로 보관합니다. 아래는 쓰기를 멈춘 뒤 백업하는 실제 서비스명 기준 명령입니다. 기존 Docker/PostgreSQL 설치 절차는 위 절을 그대로 사용합니다. 백업에는 개인정보가 포함되므로 접근을 제한합니다.

```sh
mkdir -p backups
umask 077
NOBIS_SNAPSHOT="backups/phase5-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$NOBIS_SNAPSHOT"
docker compose --env-file .env.production -f compose.yaml stop frontend backend
docker compose --env-file .env.production -f compose.yaml exec -T postgres sh -c 'export PGPASSWORD="$NOBIS_DB_PASSWORD"; exec pg_dump -h 127.0.0.1 -U "$NOBIS_DB_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl' > "$NOBIS_SNAPSHOT/database.dump"
docker compose --env-file .env.production -f compose.yaml run --rm --no-deps --entrypoint tar backend -C /app/media -czf - . > "$NOBIS_SNAPSHOT/media.tar.gz"
docker compose --env-file .env.production -f compose.yaml up -d
```

복원은 현재 데이터를 덮어쓰므로 먼저 현재 DB와 media를 같은 방식으로 별도 백업합니다. 서버 이전은 기존 인프라 절의 새 서버 초기화/비밀 환경 설정/빌드 후 다음 절차를 사용합니다. 대상 media는 비어 있어야 합니다. 기존 파일이 있으면 복구 전 별도 보관하여 섞이지 않도록 합니다.

```sh
# 프로젝트 루트, 실제 백업 세트 경로 지정
NOBIS_SNAPSHOT='backups/실제-백업-디렉터리'
docker compose --env-file .env.production -f compose.yaml stop frontend backend
docker compose --env-file .env.production -f compose.yaml up -d postgres
docker compose --env-file .env.production -f compose.yaml exec -T postgres sh -c 'export PGPASSWORD="$NOBIS_DB_PASSWORD"; exec pg_restore -h 127.0.0.1 -U "$NOBIS_DB_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-acl --exit-on-error' < "$NOBIS_SNAPSHOT/database.dump"
docker compose --env-file .env.production -f compose.yaml run --rm --no-deps -T --entrypoint tar backend -C /app/media -xzf - < "$NOBIS_SNAPSHOT/media.tar.gz"
docker compose --env-file .env.production -f compose.yaml run --rm backend python -m app.cli migrate
docker compose --env-file .env.production -f compose.yaml up -d --wait
```

Compose 프로젝트 이름을 바꾸면 볼륨 이름도 달라지므로 새 서버에서도 같은 프로젝트 이름을 사용하거나 위 복원으로 채웁니다. `down -v`로 기존 볼륨을 삭제하지 않습니다. SQLite에서 PostgreSQL로 `import-sqlite` 할 때도 원본을 먼저 v8로 마이그레이션하고, `MEDIA_ROOT`의 파일을 상대 storage_key 그대로 media 볼륨에 함께 이전합니다. 이전 명령은 코인 추첨 테이블을 포함한 `community`/`collectibles` 테이블을 FK 순서로 포함합니다. 새 서버에서 본인·그룹 멤버·외부 사용자로 사진 권한, 재접속 후 출석/잔액/영수증/집 가구를 확인한 뒤 접속 경로를 전환합니다.

자동 검증은 [Phase 5 검증 기록](docs/phase5-verification.md)에 정리합니다. 최종 캐릭터/가구 디자인, 동영상, 외부 SNS 연동, 실제 결제·현금성 거래는 이번 범위에 포함하지 않습니다.

## Phase 6 — 친구 집 방문·협동 게임·가구 도감

현재 경제 흐름은 **출석 → 무료 티켓 → 코인 가챠 → 가구 상점 → 개인 집 꾸미기**입니다. 기존 코인 가챠100개 금액/확률은 변경하지 않았습니다. 가챠 화면에 누적 획득 코인과 최신 지갑 잔액을 표시합니다. 가챠에서 가구/의상/액세서리를 새로 지급하지 않으며 과거 가구 영수증·보유품은 보존합니다. 도감은 상점 구매 및 기존 보유 인벤토리 기준입니다.

상단 소셜 아이콘 → **친구와 활동**에서 집 방문, 2인 협동 게임, 가구 도감, 선택 공유를 이용합니다. 친구 프로필에도 **집 방문 요청**, **협동 게임 초대** 버튼을 추가했습니다. 좌측 존 버튼/별도 오피스 존 맵/WASD는 추가하지 않았습니다.

### 집 방문

기본 `private`(본인만), `friends`(친구 요청 후 승인), `invite_only`(차단되지 않은 사용자의 요청을 소유자가 승인)입니다. 친구 공개도 소유자 승인이 필요합니다. 승인은24시간 유효하며, 소유자가 오프라인이어도 현재 공개 범위·친구/차단 관계·유효한 승인을 확인합니다. 공개 설정과 정원은 소유자만 변경합니다.

1. 집 주인: 친구와 활동 → 집 방문 → 공개 범위·정원 저장.
2. 방문자: 집 주인 프로필 → 집 방문 요청.
3. 집 주인: 받은 방문 요청 → 승인/거절.
4. 방문자: 친구와 활동 → 집 방문 → 친구 집 입장.
5. 집 문 또는 기존 ‘오피스 월드로 돌아가기’로 복귀합니다. 집 주인은 방문자 내보내기, 방문자는 현재 집 신고를 할 수 있습니다.

같은 집에서는 원래 오피스 채널이 달라도 아바타·위치·집 채팅·배치 업데이트를 공유합니다. 방문자에게는 배치 렌더링용 맵만 전달하며 집 주인의 지갑·인벤토리·개인 설정을 전달하지 않습니다. 가구 편집은 소유자만 가능합니다. 배치 저장은 현재 입장자의 위치와 충돌을 검사하고 변경된 맵/충돌/경로 시스템을 갱신합니다. 이동하던 일반 바닥 목적지는 새 맵으로 경로를 다시 계산하며, 가구 상호작용 접근은 안전하게 취소합니다.

집 동시 인원은 소유자 포함 최대5명이며 새 집 기본값은 `HOME_MAX_OCCUPANTS=5`(1~5)입니다. 집 정원은 오피스 채널15명과 별개입니다. 복귀는 원래 채널·위치가 기본이고, 만석이면 빈 활성 채널의 시작점으로 복귀합니다. 모든 채널이 만석이면 일반 퇴장은 잠시 후 재시도합니다. 차단·권한 회수는 즉시 퇴장시키며 복귀 자리가 전혀 없으면 접속을 종료하여 무단 방문 상태를 유지하지 않습니다. 권한 유효기간/관계 변경도 주기적으로 재검증합니다. 연결 종료 시 접속 상태를 정리하고 재접속은 권한·정원·충돌을 다시 검사합니다.

### 2인 협동 카드 짝 맞추기

접속한 일반 모드 친구의 프로필 → 협동 게임 초대 → 상대의 친구와 활동 → 2인 협동 게임 → 수락. 숨겨진12장(6쌍)에서 각자 두 장씩 번갈아 선택합니다. 서버가 보드·선택·차례·revision·매칭·결과를 관리합니다. 클라이언트에는 미공개 카드 값을 전달하지 않습니다. 같은 게임/솔로 게임 중복 참가는 서버에서 거부합니다.

초대60초, 진행5분, 연결 종료 후 재접속 유예30초입니다. 상태는 `pending → active → completed`, 거절/취소/중도 포기는 `cancelled`, 시간 초과는 `expired`, 재접속 유예 초과는 `disconnected`입니다. 한 사람이 연결을 잃어도30초 내 돌아오면 같은 보드로 재개합니다. 재시작 후에는 DB 보드를 복원하고 재접속 유예를 적용합니다.

6쌍 완료 시 참가자별25 Coin, 최소 플레이10초 미만이면0 Coin입니다. 협동 게임은 UTC 하루100 Coin까지, 기존 미니게임과 합산300 Coin 상한을 적용합니다. 기존 솔로 게임의 설정 상한도 계속 적용합니다. 초대/수락/취소만으로 보상을 지급하지 않습니다. 마지막 카드 입력·완료 상태·참가자별 Coin원장·보상 참조는 단일 트랜잭션이며 DB 지급 오류 시 마지막 입력까지 롤백되어 재시도할 수 있습니다. 동일 세션/사용자의 보상은 유니크 제약으로 중복 지급하지 않습니다. 자동 플레이/허위 계정 자체를 식별하는 별도 탐지 시스템은 없으며 지급 조건·입력 검증·상한으로 제한합니다.

### 도감·직접 선택 공유·알림·운영

가구 도감은 현재 카탈로그의 카테고리·보유/설치 수량·최초 획득일·상점 구매/기존 보유 경로·종류별 진행률을 표시합니다. 미보유 가구는 어둡게 표시합니다. 가챠 전용 희귀도/의상 도감은 추가하지 않습니다.

선택 공유는 보유 가구·도감 진행률·완료한 협동 게임·내 솔로 게임 결과만 허용합니다. **대상 그룹 선택 → 서버 미리보기 → 게시 확인**을 거쳐야 글을 만들며 자동 게시하지 않습니다. 서버가 소유권과 현재 그룹 membership을 확인합니다. 집 스크린샷 공유/아바타 외형 교체는 후속 범위입니다.

방문 요청/승인/거절/입장, 게임 초대/수락/결과, 코인 가챠 지급 알림은 기존 `user_notifications`를 재사용합니다. 사용자별 소켓 갱신과 오프라인 DB 조회를 유지합니다. `/admin` → **협동 게임 · 집 방문**에서 세션 상태·거부 입력·참가자별 보상 원장·집 방문 신고를 확인합니다. 운영 권한은 기존 `games_read`/`social_moderate`를 재사용하며 개인 채팅·숨겨진 보드는 운영 목록에 노출하지 않습니다. 사용자 차단/계정 관리는 기존 메뉴를 이용합니다.

### v9 마이그레이션·Docker·이전

기존 테이블을 삭제하지 않는 추가형 스키마입니다. `home_visit_settings/requests/permissions`, `home_visitors`, `multiplayer_game_sessions/participants/actions/rewards`, `multiplayer_validation_events`, `integration_reports`를 추가합니다. 도감은 기존 보유/구매 데이터를 조회하므로 중복 `collection_entries` 저장소를 만들지 않았습니다. SQLite는 `.pre-phase6.bak`을 먼저 생성하며 PG는 기존 migration advisory lock을 사용합니다. 서버 시작 또는 실제 CLI로 적용합니다.

```sh
# 프로젝트 루트: 기존 운영 환경 파일과 DB/media 볼륨 유지
docker compose --env-file .env.production -f compose.yaml up -d --build
docker compose --env-file .env.production -f compose.yaml run --rm backend python -m app.cli migrate
docker compose --env-file .env.production -f compose.yaml logs --tail=100 backend
```

새 집 기본 정원을 바꾸려면 비밀 환경 파일의 `HOME_MAX_OCCUPANTS`를1~5로 설정하고 backend를 재생성합니다. 이미 저장된 소유자별 정원은 자동 덮어쓰지 않습니다. 기본값은5입니다. 위 Docker/PostgreSQL 설치·초기 관리자·백업/복원/새 서버 이전 절차는 그대로 유지합니다. Phase 6 데이터는 전체DB dump에 포함되며 이미지 볼륨도 같은 시점에 이전합니다. SQLite→PG 이전은 새 테이블까지 FK 순서로 포함합니다.

검증 결과·실행 화면·제한은 [Phase 6 검증](docs/phase6-verification.md), 이번 변경 파일은 [목록](docs/phase6-changes.md)을 확인하세요. 이 구조는 단일 backend 프로세스 전제입니다. 여러 worker/서버를 쓰기 전 Hub·게임 초대 전달·집 정원을 공유 상태로 분리해야 합니다.


## Phase 7 — 디자인 시스템과 에셋 교체

게임 로직과 표시 리소스를 분리했습니다. 단일 Office World·타일/존/장애물 좌표·A*·터치 이동·채팅·집·소셜·게임·관리자·기존 코인 확률표를 유지합니다. DB 스키마는 v9 그대로이며 이번 Phase의 신규 마이그레이션은 없습니다. 가챠는 **출석 → 무료 티켓 → 10~1,000 Coin → 상점 구매 → 개인 집 배치**입니다.

```text
frontend/src/design/              공통 토큰·스타일·로고·초상화·아이콘
frontend/src/game/visual/         로더·캐릭터/가구/바닥 렌더러
  manifest.json                  아틀라스·프레임·발 피벗·애니메이션 기본 규격
  overrides.json                 생성 시 보존되는 수동 에셋 등록/교체
frontend/public/visual/           해시 PNG 3개 + Phaser JSON 3개
infra/visual/build-assets.cjs     네트워크 없이 만드는 원본 픽셀 아트
```

현재 캐릭터는 48×64px, 발 피벗(24,58), 16개 외형·기존4방향·idle/walking/sitting/typing을 제공합니다. 가구는 128×160px 셀에서 하단/상단을 나누고, 기존 가구 ID/asset_key와 회전·충돌 데이터를 유지합니다. 바닥은 코드 픽셀 패턴이며 실제 이미지 타일셋은 아직 없습니다. 실제 이미지 교체는 overrides와 public/visual 파일만 수정하며 이동·배치 데이터를 수정하지 않습니다.

```sh
# 프로젝트 루트, 최초 개발 의존성 설치
npm --prefix frontend ci
# 아트를 수정했을 때만: 로컬 Chrome + 기존 Playwright 사용
npm --prefix frontend run assets:build
npm --prefix frontend run test:visual
# 일반 검사/빌드: 생성된 정적 에셋을 그대로 패키징
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

개발 실행은 앞의 ‘로컬 개발’ 절의 FastAPI18000/Vite15173 명령을 사용합니다. 운영 서버에서는 기존 PostgreSQL/Docker 설치·비밀 환경 생성·백업/복구·이전 안내를 유지하며 다음으로 재빌드합니다.

```sh
docker compose --env-file .env.production -f compose.yaml up -d --build
```

Docker 빌드는 Chrome/아트 제작기를 실행하지 않습니다. Vite가 public/visual을 dist/visual에 복사하고 Nginx는 해시 PNG/JSON을 immutable 캐시합니다. 변경 시 PNG와 JSON 각각의 **내용 해시**로 새 파일명을 사용해야 합니다. 없는 에셋 URL은404를 반환하며 게임은 누락된 캐릭터·가구를 기존 그래픽으로 대체합니다.

[비주얼 시스템 가이드](docs/visual-system.md)에 토큰 변경, 애니메이션 프레임, 캐릭터/가구/타일셋 등록, 피벗, 레이어, 라이선스 기록 방법을 작성했습니다. [에셋 출처 목록](docs/asset-licenses.json)은 원본 코드 제작과 외부 리소스 미사용을 기록합니다. 전용 한글 픽셀 폰트·일부 가구의 방향별 세부 원화·추가 행동 애니메이션·이미지 타일셋은 후속 자료입니다.

Phase 7 결과는 단위25개·브라우저24개 통과, 백엔드190개 통과/1개 조건부 생략입니다. ARM64 Colima Compose 빌드 및 실제 Nginx 화면을 확인했습니다. Raspberry Pi4 실기기·15명 동시 렌더링 부하는 검증하지 않았습니다. 개발 Chrome 단일 캐릭터 약60fps는 해당 측정 환경의 결과입니다. Vite 대형 JS 청크 경고는 남아 있습니다.


## Phase 7-A — 공용 로비와 개별 룸

원본 맵은 `design/rooms/rooms.json`, 생성기는 `infra/world/build-rooms.py`, 런타임은 `shared/rooms.json`입니다. 이전 비대칭 단일 맵은 `design/world`와 이전 검증 문서에 기록으로 남아 있습니다.

```sh
# 원본 룸 데이터를 수정한 뒤 생성·검증
python3 infra/world/build-rooms.py
npm --prefix frontend test
npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests
npm --prefix frontend run test:e2e
# 기존 SQLite 백업 후 추가형 v10 마이그레이션
cd backend
../.venv/bin/python -m app.cli migrate
cd ..
# 기존 환경 파일과 볼륨으로 컨테이너 갱신
# 운영 DB는 앞 절의 pg_dump로 먼저 백업
docker compose --env-file .env.production -f compose.yaml build
docker compose --env-file .env.production -f compose.yaml run --rm backend python -m app.cli migrate
docker compose --env-file .env.production -f compose.yaml up -d
```

서버 시작도 같은 추가형 마이그레이션을 실행합니다. 기존 SQLite는 최초 v10 적용 전에 `.pre-hybrid.bak`를 생성합니다. `room_definitions`, `room_instances`, `room_portals`, `room_presence`를 추가하며 기존 사용자·지갑·티켓·가구·소셜·채팅 데이터는 초기화하지 않습니다. 이전 단일 맵 위치에는 룸 정보가 없으므로 처음에는 로비의 안전한 시작점으로 배치합니다. 이후에는 채널별 마지막 룸/위치를 재검증해 복원합니다.

룸 추가·권한·에셋·경로 설정은 [Hybrid World 설계](docs/hybrid-world.md)를 따르세요. 설치·PostgreSQL·백업/복구·이전 절차는 앞 절을 유지합니다. 현재 PC는 최종 운영 서버가 아닙니다. 룸마다 컨테이너를 만들지 않으며 FastAPI 단일 worker가 여러 인스턴스를 관리합니다. 여러 worker/서버 분산은 지원하지 않습니다.

## Phase 7-B — 공용 로비 에셋 시스템

목재/석재 바닥, 후면 벽, 입구별 픽셀 PNG와 기존 소파·화분·조명을 적용했습니다. 신규 원화가 아닌 프로젝트 코드 제작 1차 아트이며 최종 미확보 이미지는 명시합니다. 기존 로비→룸 보행/입장, 채널·채팅·집·상점·10~1000코인 가챠·DB는 유지합니다.

규격은 [ASSET_SPEC](docs/ASSET_SPEC.md), 등록·교체·룸 입구·누락 목록은 [로비 에셋 가이드](docs/lobby-assets.md), 결과는 [Phase 7-B 검증](docs/phase7b-verification.md)을 참고하세요. `npm --prefix frontend run assets:lobby`는 코드 아트를 재생성하고 `assets:lobby:sync`는 수동 편집한 manifest를 빌드용 사본에 반영합니다. 기존 Docker/PostgreSQL 설치·이전 지침은 그대로 유지합니다. 이번 작업은 DB 마이그레이션을 추가하지 않습니다.
