# 월드·채널·채팅·관리자 구조

## 계층과 보존 범위

NOBIS World(nobis) → World Channel(ch1, ch2, …) → 같은 Office Map의 인스턴스 → Zone 구조입니다. shared/maps.json의 office 한 개와 여섯 존 좌표/통로를 보존합니다. 존 변경은 같은 Scene 내부 좌표 판정이며 채널 이동은 명시적인 인스턴스 전환입니다. 개인 집은 소유자 personal:userId scope이며 채널을 바꿔도 같은 한 집/가구/지갑을 사용합니다. 집에 있는 동안 채널 전환을 막습니다.

React는 UI, Phaser는 맵·아바타·클릭/터치 이동·A*·카메라·연출을 담당합니다. GameWorld는 user/scope/channel이 변경될 때만 Game을 교체합니다. 이전 canvas를 cleanup에서 즉시 제거해 새 Scene의 초기 입력 bounds가 어긋나지 않도록 합니다. 채팅 전용 모드는 Game loop를 sleep/wake하며 WS·존·위치·대화방·상태를 유지합니다. WASD나 좌측 존 메뉴는 없습니다.

## 서버 상태와 원자적 채널 이동

Peer.player의 world_id/channel_id/scope/zone(xy에서 서버 판정)이 기준입니다. zone_id는 기존 zone의 직렬화 별칭입니다. Hub는 로그인 사용자당 한 연결, 채널별 정원/팔레트/아바타 목록을 관리합니다. 초기 ch1만 활성화하며 채널 생성·수정은 RBAC 관리자 API로 수행합니다.

채널 이동: hub.lock 획득 → 대상 enabled/capacity 검사 → SocialService의 한 DB 트랜잭션에서 이전 channel_locations와 새 zone_presence 저장 → 메모리의 channel/xy/zone/action 교체 → 이전 채널 left, 새 채널 본인 snapshot/joined → 위치 없는 채널별 인원 집계 브로드캐스트. 정원이 차면 이전 상태를 유지합니다. 재접속은 저장된 채널/위치로 입장하며 정원이 찼으면 거부합니다. 마지막 채널이 비활성화됐으면 기본 채널을 사용합니다.

일반 /api/users, snapshot, joined/moved/status/action/presence/left, object_effect는 같은 채널만 수신합니다. 개인 방 내부 좌표·가구 액션·파생 말풍선은 다른 사용자에게 가립니다. 다른 채널의 사용자는 directory에서 ID/닉네임/온라인 여부/채널만 검색할 수 있습니다. 관리자 접속자 조회는 별도 permission 경계입니다.

## 통신과 채팅 권한

| 종류 | 범위/읽기·쓰기 |
|---|---|
| world | 인증된 전체 채널 |
| channel:CID | 같은 월드 채널 |
| zone:ZONE (ch1 호환) / zone:CID:ZONE | 같은 채널 + 서버 판정 현재 존 |
| zone:personal:USER | 현재 본인 집 |
| room:UUID | 초대 수락 active membership, 작성은 open 상태만 |
| private_messages | sender_id 또는 recipient_id 본인만 |
| announcements | 전체 또는 지정 채널 수신 / announcements_manage 권한만 발송 |

메시지 타입은 world/channel/zone/private/announcement입니다. 일반·그룹 대화는 chat_messages에 보존하고 type을 채널 ID에서 파생합니다. 귓속말과 공지는 독립 테이블입니다. 기존 announcements 채팅 기록은 새 announcements 기록으로 보존합니다. 공지는 일반 채팅 쓰기 경로에서 발송할 수 없습니다.

@닉네임은 기본 귓속말이며 공개 멘션은 보류했습니다. 자동완성은 온라인/오프라인 directory를 검색하고 user_id를 연결합니다. 원문 닉네임만 보낼 때는 NFKC/casefold 비교로 정확히 한 명이어야 하며 없거나 중복이면 오류입니다. 선택된 ID를 보내도 본문 접두사가 그 수신자의 닉네임인지 검증합니다. 발신자/시간/상태는 서버가 채웁니다. 본문은 수신자와 발신자 외에는 HTTP·snapshot·WS·관리자 메시지 목록에 전달하지 않습니다.

귓속말은 먼저 stored로 저장하고 활성 소켓 전달 성공 때 delivered로 갱신합니다. 연결이 없거나 실패하면 stored 상태를 보존합니다. 재접속 snapshot은 본인 최근 100건을 포함하고 미전달분을 처리하며 온라인 발신자에게 전달 상태를 갱신합니다. delivered는 읽음 확인이 아닙니다. 닉네임은 고유 키가 아니고 UUID가 권한의 기준입니다.

초대 카페/회의는 기존 owner/invited/active/left 상태와 종료 기록을 유지합니다. 운영자도 membership을 우회하지 않습니다. 채널 이동은 명시적으로 수락한 비공개 대화방 membership을 자동 해제하지 않습니다. 그룹 비공개 대화는 귓속말 표시와 구분합니다.

## 채팅 말풍선과 상태

user_chat_preferences.chat_bubbles_enabled의 초기값은 false입니다. 서버는 공개 world/channel/zone 메시지이며 scope=office, 해당 존의 chat_bubbles_allowed=true, 발신자 설정 ON일 때만 chat_bubble을 같은 채널의 권한 있는 수신자에게 전달합니다. 집중 업무존·회의실은 false입니다. 개인 집, 귓속말, room 대화, 공지, 시스템 이벤트는 제외합니다.

Phaser는 최대 80자/160px 줄바꿈으로 6초 표시하고 새 메시지로 교체합니다. 설정 OFF, 금지 존 이동, 채널/집 이동 때 기존 채팅 말풍선을 지웁니다. WS history를 불러와도 말풍선을 재생하지 않습니다. 상태 말풍선(status_text)은 명시 상태 메시지/상호작용/Mock 근무 상태에서 파생하는 별도 텍스트입니다.

근무 상태·접속 상태·normal/spectator를 분리합니다. after_work/vacation은 spectator이며 실제 업무 감시/추정은 하지 않습니다. 발신 세션·길이·빈도·채팅 제한·채널 권한을 서버에서 검사합니다.

## 공지 큐

announcements는 제목·본문·작성자·대상 채널(null은 전체)·표시 시간·시각을 저장합니다. announcements_manage 검사 후 한 번 저장하고 대상 소켓에만 방송합니다. UI는 도착 순서대로 3~30초 표시/자동 닫기/수동 닫기하며 채팅 전용에서도 같은 고정 배너를 사용합니다. 채널 전환 시 이전 채널 전용 대기는 제거합니다. 재접속/기록 조회는 과거 공지를 토스트로 다시 재생하지 않습니다. 기록은 일반 메시지와 별도 UI입니다.

## RBAC와 계정

user_roles와 role_permissions를 서버에서 조회합니다. user < moderator < admin < super_admin 계층을 사용합니다. admin은 user/moderator 사이만 변경하고, admin/super_admin 임명·해제는 super_admin 전용입니다. 마지막 super_admin 강등은 거부합니다. 신고·공개 메시지 삭제·채팅 제한·계정 이용 제한·권한·채널·공지·중요 설정 변경은 admin_audit_logs에 기록합니다. 같은 급 이상/본인 계정 이용 제한과 채팅 제한도 거부합니다.

최초 bootstrap-admin CLI는 BEGIN IMMEDIATE로 기존 활성 계정 확인 → super_admin/초기화 플래그 검사 → 역할/플래그/감사 로그를 한 번 기록합니다. HTTP bootstrap 경로는 없습니다. 동시 bootstrap도 한 건만 성공합니다. 이후 역할 변경은 인증된 관리자 API만 사용합니다. create-user/set-password/list-users/backup/restore/migrate는 서버 운영자 CLI이며 역할 임명 우회 기능은 없습니다.

비밀번호 계정은 PBKDF2-SHA256(랜덤 salt, 600000회) 해시만 저장합니다. password 로그인으로 발행한 세션과 dev 세션을 구분합니다. production에서는 dev 로그인/테스트 관리자 키/기존 dev 세션을 모두 거부합니다. set-password는 기존 세션을 회수합니다. WS도 주기적 세션 검사로 회수를 반영합니다. 공개 회원가입/복구/SSO/MFA는 미구현입니다.

/admin은 서버 permission 확인 후 메뉴를 렌더링합니다. UI 숨김은 권한 검사의 대체가 아닙니다. 모든 API는 별도로 세션과 permission/대상 역할을 검증합니다. moderator에게 비공개 본문이나 사용자 역할 관리 API를 제공하지 않습니다.

## 개인 집·가구·코인 보존

HomeService의 소유자 scope/normal/revision/보유 인스턴스/정수 좌표/회전/경계/겹침/출입문/캐릭터/BFS 통로 검증을 유지합니다. 저장된 배치가 서버와 Phaser의 충돌/A*/오브젝트 접근을 구성하며 미리보기는 로컬 초안입니다. 10종 카탈로그의 asset_key와 footprint를 분리하고 고정 출입문은 회수할 수 없습니다.

구매는 BEGIN IMMEDIATE + UNIQUE(user_id,request_id) + balance>=0 조건부 차감으로 코인/인스턴스/구매/거래를 함께 확정합니다. 초기 코인은 개발 계정 ID당 한 번 1000, 다른 환경 0입니다. DevNest는 기존 URL 설정/새 탭/동일 위치·상태 복귀를 유지하고 원본을 수정하지 않습니다.

## 저장·운영·확장

SQL 접근 경계는 repository.py, home.py, social.py와 운영 CLI입니다. main/admin은 인증·WS/HTTP·메모리 원자성·방송을 연결합니다. migrations.py의 추가형 v4는 worlds/world_channels/channel_locations/user_roles/role_permissions/private_messages/user_chat_preferences/announcements/admin_audit_logs/system_settings/user_reports/user_chat_restrictions 및 기존 presence/session 컬럼을 추가합니다. 최초 전환 전 .pre-multichannel.bak를 만들고 기존 사용자·집·코인·비공개 대화·공지 기록을 보존합니다.

위치는 10Hz 이하 중계/약 1Hz 주요 변경 시 저장합니다. 채널 정원과 연결 기준은 단일 FastAPI 프로세스 메모리입니다. 여러 worker/서버 간 공유나 분산 잠금은 없습니다. Raspberry Pi/전체 서버 부하는 별도 검증 대상입니다. SQLite migrate/backup/restore CLI와 PostgreSQL 어댑터·마이그레이션·가져오기를 제공합니다. PostgreSQL 백업/복원은 pg_dump/pg_restore입니다.

향후 Social Group / Group Membership / Shared Log / Activity Post / Media Attachment / Privacy Setting은 world/channel과 별도 엔터티로 둡니다. 그룹 가입이 월드 입장이나 역할을 자동 부여하지 않으며 명시적 공개 범위/멤버십 ACL을 갖게 설계합니다. 현재 사진/영상/소셜 기록 기능은 구현하지 않습니다.

## Phase 3.5 구현 경계

이 절은 위의 이전 SQLite 전용 설명을 대체합니다. PostgreSQL 17과 SQLite를 모두 연결했고 기본 Compose는 PostgreSQL, 기존 SQLite 구성은 별도로 보존합니다.

- DATABASE_URL이 DATABASE_PATH보다 우선합니다. psycopg 연결은 UTC와 일반 앱 역할을 사용합니다. database.py는 고정 SQL만 변환하며 입력값은 바인딩합니다.
- SQLite BEGIN IMMEDIATE는 PostgreSQL의 트랜잭션 advisory lock으로 대응합니다. 현재 소규모 쓰기를 직렬화해 구매·배치·bootstrap 원자성을 유지합니다. WS Hub는 여전히 단일 worker이며 분산 서버를 지원하지 않습니다.
- v5 users.account_origin은 개발/운영자/기존 미분류를 구분합니다. SQLite 최초 v5 전 .pre-phase35.bak를 생성합니다. 앱 재시작은 만료 세션과 접속 상태를 정리하며 집·지갑·채팅은 삭제하지 않습니다.
- db_transfer.py는 SQLite backup API로 읽기 전용 원본의 일관 사본을 만들고 임시 파일만 업그레이드합니다. 빈 PostgreSQL 대상에 한 트랜잭션으로 계정·집·가구·코인·권한·기록을 복사하고 sequence를 재설정합니다. 기존 사용자 존재 시 거부합니다.
- GestureSystem은 탭과 드래그/핀치를 분리합니다. CameraSystem은 viewport/scroll/zoom 좌표 변환을 독립 수행하며 오래된 카메라 행렬을 사용하지 않습니다. Phaser Camera의 width/height는 원형 접근자이므로 명시적으로 읽어 순수 스냅샷을 만듭니다.
- BubbleLayoutSystem은 화면 픽셀 기준으로 이름·상태·임시 채팅의 경계/겹침을 보정하며 공간 부족 시 낮은 우선순위 레이블을 숨깁니다. 가구 depth와 분리한 텍스트 레이어를 사용하고 HTML을 삽입하지 않습니다.
- 하단 존 이동 메뉴와 브리지 이벤트를 제거했습니다. 개인 집 서비스 메뉴는 기존 오브젝트 접근 상호작용입니다. 호버 사이드바는 캔버스를 밀지 않고 덮어 펼쳐지며 고정 폭 상태만 localStorage에 저장합니다. 모바일은 월드/채팅 전체 높이 화면을 전환합니다.
- WS 인증 프레임과 이후 프레임은 4,096자 제한이며 인증 타임아웃은 5초입니다. 입장 실패는 채널 목록과 함께 응답하여 미접속 상태에서도 다시 선택할 수 있습니다. 비활성 저장 채널의 좌표를 기본 채널에 적용하지 않습니다. 중복 연결은 이전 소켓을 닫고 서버 권한/세션을 다시 확인합니다. DB 장애는 HTTP 503/WS 1013이며 DSN을 노출하지 않습니다.
- /api/client-config는 환경·공개 DevNest 기본 URL만 제공합니다. 운영은 localhost/loopback·내장 자격 증명을 거부합니다. 개발 기본값은 127.0.0.1:8001입니다. 새 탭은 opener를 제거하며 차단 오류와 외부 도메인의 수동 연결 확인을 구분합니다.
- 관리자 dashboard는 실제 DB 집계·채널 인원·최근 공지/작업·환경/계정 출처를 표시합니다. 감사 기록은 JOIN한 이름을 표시하고 원본 JSON을 보존합니다. 저장 UTC·표시 Asia/Seoul입니다.

Docker Engine/Linux ARM64 컨테이너 실행과 재시작은 현재 환경에서 미검증입니다. native macOS ARM64 PostgreSQL의 DB 재시작·마이그레이션·가져오기·pg_dump/pg_restore·API 테스트와 구분합니다.

## Phase 4 미니게임·보상 경계

OfficeScene에 라운지 아케이드 오브젝트 1개를 추가했습니다. 존·페이지·오피스 Scene을 나누지 않습니다. 클릭 접근은 기존 InteractionSystem/A*를 재사용합니다. React GamePlatform이 중앙 오버레이를 렌더링하고 기존 Phaser loop를 멈추지만 useOffice WebSocket과 채팅·공지 상태는 유지합니다. 서버도 활성 game_session이 있으면 이동·집 입장·채널 변경·월드 상호작용을 거부합니다. Peer.minigame은 DB 활성 세션에서 파생되며 다른 사용자의 상태 표시에 사용합니다. 근무 상태와 게임 점수는 분리합니다.

서버 RULES의 두더지 규칙은 비공개 랜덤 seed + HMAC(wave)로 현재 위치와 challenge를 재현합니다. 30초·800ms 구간·650ms 노출·명중당10점은 서버 설정입니다. API는 소유자 세션과 서버 수신 시각으로 판정하며 최종 점수/코인을 클라이언트에서 받지 않습니다. cell/wave/challenge/event_id만 허용합니다. 현재 구간 밖/위조 challenge/너무 빠른 요청/다른 사용자/종료 세션을 검사하고 명중은 구간당 하나의 부분 유니크 인덱스로 보장합니다.

정규화한 데이터는 game_sessions(수명/seed/정책), game_inputs(판정), game_results(최종 점수), game_reward_transactions(결과와 기존 coin_transactions 링크), game_settings(관리 정책), game_validation_events(입력 거절 사유)입니다. 기존 user_wallets만 사용합니다. 금액과 잔액은 기존 원장에서 읽으며 게임 링크 테이블에 다시 저장하지 않습니다. 활성 점수는 명중 입력의 집계, 종료 점수는 결과 레코드입니다.

정산은 기존 쓰기 트랜잭션 경계에서 상태 전이·결과·잔액·원장·세션 유일 링크·감사 기록을 함께 저장합니다. SQLite 쓰기 lock/PostgreSQL advisory transaction lock과 UNIQUE가 동시 정산을 직렬화합니다. 중복 finish는 기존 결과와 현재 서버 잔액을 반환합니다. 설정 변경 중에도 시작 당시 보상표를 유지하고 일일 상한은 최신 정책으로 UTC 일자 합계를 적용합니다. 현재 첫 게임만 구현했으며 다른 게임의 개별 입력·일일 정책을 확장할 때 공통 계약을 명시적으로 늘립니다.

GameRegistry의 GameModule은 Board/runtime을 등록하고 공통 GameSession이 HTTP·오래된 응답·완료 상태를 관리합니다. polling 응답이 늦게 도착해 완료된 게임을 활성 상태로 되돌리지 않습니다. 브라우저 단조 시계는 표시용이며 서버 시간과 입력을 바꾸지 못합니다. 터치는 pointerdown 한 경로만 사용합니다. 중도 종료는 보상 없이 결과를 남깁니다. 완료 후 5분까지 재접속 정산, 이후 만료/보상0으로 해제합니다. 사용자별 활성 1개·시작2초 간격·입력80ms·일일300 Coin 기본 정책을 적용합니다.

RBAC games_read는 moderator 이상, games_manage는 admin 이상입니다. user는 게임 관리자 API를 사용할 수 없습니다. 관리자 메뉴는 활성/보상/일일 상한·지급 내역·이용 현황·검증 기록을 제공합니다. seed와 비밀번호는 어느 관리자 목록에도 노출하지 않습니다. 자동 클릭 봇의 유효한 플레이를 사람과 구분하는 기능은 미구현이며 보상량/중복/입력 수신 검증 범위를 문서화합니다.

v6 추가형 마이그레이션은 기존 테이블/지갑을 재작성하지 않습니다. SQLite 적용 전 .pre-phase4.bak, PG는 기존 전체 dump 절차를 사용합니다. import-sqlite의 테이블 순서에도 game_*를 포함합니다. Phase 4에서 실제 Linux ARM64 Compose·PostgreSQL·Nginx WebSocket·재시작/재생성 볼륨·dump/restore를 별도 Colima VM으로 검증했습니다. Raspberry Pi 실기기 성능은 여전히 별도입니다.

## Phase 5: 월드와 독립된 관계·기록 계층

community 모듈은 계정 ID만 참조하며 world/channel/zone을 그룹 키로 사용하지 않습니다. group_memberships의 owner/manager/member 권한과 전역 RBAC는 독립적입니다. 공유 기록/댓글/반응/이미지/알림은 모든 요청에서 현재 membership·공개 범위·차단·삭제/숨김을 검사합니다. 자기 전용 기록은 그룹 운영자도 읽지 못합니다. 그룹 탈퇴/강퇴 후 새 이미지 다운로드도 거부합니다. 신고 검토는 특정 신고 대상에만 별도 운영 권한을 적용하고 감사합니다.

파일은 MEDIA_ROOT에 UUID 이름으로 재인코딩 저장하고 log_media에 상대 storage_key만 저장합니다. 이미지 검증은 Pillow 실제 형식·크기·정지 프레임·디코딩 검사 후 EXIF 정리 및 재인코딩합니다. 파일 API는 인증된 no-store 응답이며 nginx 공개 media mount는 없습니다. 파일 원자 쓰기와 DB 참조는 서로 다른 저장장치이므로 업로드 후 DB 저장 실패 시 파일을 정리하고, 미사용 업로드/soft delete는 cleanup-media로 회수합니다. 운영 백업은 쓰기를 멈춰 DB와 media를 함께 스냅샷합니다. LocalMediaStore 경계에서 추후 객체 저장소/서명 다운로드를 적용할 수 있습니다.

알림은 user_notifications에 영속 저장합니다. 트랜잭션 후 수신자별 opaque social_refresh를 해당 Peer에 전송하고 React가 인증 API로 다시 조회합니다. 공용 브로드캐스트에 개인 알림 본문은 넣지 않습니다. 오프라인은 재로그인 시 API로 복원합니다. 프로필 공개 범위는 API/directory/Hub.public_player에 적용하며 공유 월드의 아바타 렌더링 좌표는 유지합니다.

## Phase 5: 출석·티켓·서버 가챠

collectibles는 HomeService의 가구 인스턴스와 SocialService의 RBAC/감사를 재사용합니다. NOBIS Coin과 독립 ticket_balances/ticket_transactions를 둡니다. KST 서버 날짜에 unique(user_id,attendance_date), 이전 출석일로 streak 계산, 동일 트랜잭션에서 지급합니다. 신뢰 경계는 서버 시간·인증 사용자 ID이며 클라이언트 날짜를 받지 않습니다.

확률은 10000 기준 정수 BPS이며 아이템 합계와 4등급별 합계를 검증합니다. 배너 설정 변경은 immutable pool_version을 추가합니다. 뽑기 요청은 확인한 버전과 UUID 요청 키를 보내고, 버전 불일치 시 차감 전에 409로 거부합니다. secrets.randbelow로 추첨하며 티켓 조건부 차감·가구 인스턴스·아이템 영수증·티켓 원장·감사는 한 트랜잭션입니다. 재시도는 같은 영수증을 반환하며 페이로드가 달라지면 거부합니다. SQLite BEGIN IMMEDIATE 및 PostgreSQL 어댑터의 트랜잭션 advisory lock을 재사용합니다.

가챠 연출은 서버 확정 영수증에만 적용합니다. 브라우저는 네트워크 실패 시 요청 UUID/버전/횟수를 보관해 동일 요청을 재시도합니다. 성공 후 기존 집 인벤토리를 새로 조회합니다. Coin 구매·미니게임 보상 경로는 변경하지 않습니다.

추가형 스키마 v7은 community/schema.py와 collectibles/schema.py에 분리했습니다. db_transfer.TABLES는 FK 순서로 새 테이블을 포함합니다. PostgreSQL advisory migration lock, SQLite pre-phase5 백업을 유지합니다. Docker는 기존 DB 볼륨에 별도 nobis-media 볼륨만 추가합니다. 공유 Hub/레이트리밋은 여전히 단일 앱 프로세스 전제이며 다중 worker 확장 시 분산 상태/알림 전달 계층이 필요합니다. 최종 아트·영상·외부 SNS·유료 재화는 구현하지 않습니다.

## v8 코인 뽑기 변경

현재 가챠 보상은 가구 대신 기존 user_wallets/coin_transactions의 Coin입니다. gacha_coin_pool_items는 버전별10~1000/10단위 금액과BPS를, gacha_coin_draw_items는 각 지급 원장ID를 유니크 참조합니다. 티켓 차감·5회까지 개별 지갑/원장 증가·영수증/티켓 원장을 동일 트랜잭션에 묶습니다. 과거 가구 풀/영수증/인벤토리는 유지하며 예전 배너만 비활성화합니다. 기본 정규분포형100금액은 μ505/σ165에서 대칭 정수 반올림하여10000BPS로 만들고, UI는 현재 확률표의 분포/평균을 표시합니다. 상세는 coin-gacha.md입니다.

## Phase 6 통합 계층(v9)

integration 모듈은 HomeService(가구 소유권/배치), SocialService(RBAC/감사), CommunityService(친구/차단/개인 알림/글), GameService(기존 솔로 게임/지갑)를 재사용합니다. 홈 방문 설정/24시간 승인과 Hub의 scope 기반 입장자가 권한 경계입니다. 집은 `personal:OWNER` scope이며 서로 다른 Office Channel의 사용자도 같은 집 좌표/채팅을 공유합니다. 방문자 맵은 별도 scope_map/home_layout 이벤트이며 자신의 HomeState(wallet/inventory)와 분리합니다. 배치 저장은 입장자 전원의 위치 충돌을 검사합니다. 입장/퇴장 때 snapshot을 다시 계산하고 원래 office_return을 보존합니다. 채널 정원과 집 정원은 각각 검사합니다.

협동 보드는 DB에만 원본을 저장하고 참가자의 조회에서 공개된 선택/매칭 카드만 투영합니다. pending/active 참가자에 대한 부분 유니크 인덱스, 입력 revision+event_id, DB 쓰기 직렬화로 중복 참가/선택을 검사합니다. 마지막 입력/세션 완료/두 지갑 증가/기존 Coin원장/각 지급 참조가 같은 트랜잭션입니다. 실패는 마지막 입력까지 롤백하여 재시도합니다. 게임 보상은 협동 일일100 및 솔로와 합산300(UTC), 기존 솔로 설정 상한도 유지합니다. 초대/진행/재접속 유예는60/300/30초이며 주기 작업이 만료와 권한 회수를 정리합니다. 게임 상태 본문은 참가자 API만, 운영자는 보드/채팅을 제외한 현황과 지급 참조를 봅니다.

도감은 기존 furniture_instances/placements/shop_purchases를 조회하므로 별도 원장 복제를 만들지 않습니다. 공유 미리보기/게시 API는 서버 소유 데이터에서 문구를 생성하고 CommunityService의 현재 그룹 ACL로 글을 작성합니다. 직접 누른 공유만 게시합니다. 기존 Coin 가챠 확률/지급은 보존하고 지갑 잔액/누적 가챠 보상과 기존 알림 통합만 추가했습니다. 통합 알림은 user_notifications에 저장하고 사용자별 social_refresh로 전달합니다.

집/게임 상태는 DB에 영속 저장하지만 연결/정원/방송은 여전히 단일 Hub 프로세스입니다. 다중 worker/호스트 확장은 분산 상태/잠금 및 전달 계층이 필요합니다. 실제 기기/장시간15명 부하는 후속 검증입니다.


## Phase 7 표시 계층

React는 design/tokens.json → tokens.css 및 공통 system.css로 UI를 표시하고, Phaser는 game/visual/catalog → AssetLoader → CharacterVisual/FurnitureVisual/FloorVisual을 사용합니다. 로직은 기존 game/systems와 shared/맵·존·카탈로그 그대로입니다. manifest/overrides가 리소스와 프레임·피벗을 연결하므로 이동/충돌/서버 계약은 이미지 파일에 의존하지 않습니다.

캐릭터 발 기준 depth는 유지하며 가구 하단/상단은 같은 월드 anchor의 독립 depth입니다. 머리 레이블은 실제 스프라이트 표시 높이와 발 피벗에서 계산하고 기존 화면 경계/겹침 보정 시스템을 유지합니다. 아틀라스는 텍스처 매니저에서 공유하며 애니메이션은 사용 시 생성합니다. UI의 초상화/가구 미리보기도 같은 아틀라스를 참조합니다.

OfficeScene은 여섯 존을 포함하는 단일 맵입니다. 개인 집만 별도 소유 공간이고 기존 공통 WorldScene 렌더러와 이동 시스템을 재사용합니다. 서비스 메뉴 접기/모바일 채팅 전용 렌더 중지와 서버 WebSocket 동작은 보존했습니다. 코인/권한/DB 구조 변경은 없습니다.

[비주얼 규격](visual-system.md), [검증 및 제한](phase7-verification.md)을 참조하세요.


## Phase 7-A · 비대칭 월드(v2 맵,DB v9 유지)

WorldMap의 실제 바닥은 walkable_tiles 마스크,벽/난간은 closed_edges,계단은 surface.stairs,높이는 surface.regions의 셀 마스크입니다. Zone도 cells로 다각형/분리된 하위 공간을 표현합니다. 원본 design/world/office-world-v2.json을 infra/world/build-world.py로 shared3개 파일에 생성합니다. API/DB 스키마를 변경하지 않으며 기존 맵 좌표 배치만 바꿉니다.

기존 A*와 MovementSystem은 그대로입니다. CollisionSystem의 neighbors가 바닥/가구/닫힌 edge/계단을 반영하고 서버 world.valid_move도 같은 공유 데이터를 검사합니다. 서버는 stale 위치가 유효하지 않으면 기존 spawn 복귀 검증을 사용합니다. SurfaceCoordinates는 카메라 역변환 후 높이별 가시 표면과 계단을 선택하며 렌더링은 foot 기준입니다.

[실제 데이터/연결/제작 규격](phase7a-world-design.md),[검증](phase7a-verification.md). 이전 Phase7의 좌표 보존 기록은 당시 버전의 기록이며 이번 Phase7-A에서는 사용자 지시대로 공용 맵/존/배치를 변경했습니다. 개인 집/카탈로그/사용자 DB는 보존합니다.
