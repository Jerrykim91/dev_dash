# Phase 7 검증 · 2026-11-06

## 실제 적용 범위

원본 코드 제작 픽셀 아바타16개 외형·4방향·idle/walking/sitting/typing, 캐릭터640프레임·가구148프레임을 PNG3개/JSON3개에 적용했습니다. 캐릭터 발 피벗/가구 하단·상단/바닥·벽/이름표를 분리했습니다. 공통 라벤더·퍼플·크림 토큰과 버튼/모달/탭/카드 스타일은 로그인·월드·채팅·친구/그룹·집·상점·인벤토리·미니게임·출석·코인 가챠·관리자에서 사용합니다.

수동 overrides는 생성기와 분리해 이미지 교체 시 이동 로직을 수정하지 않습니다. 누락 리소스는 기존 도형으로 대체합니다. 최종 원화를 확정한 작업은 아닙니다. [규격·등록·교체·라이선스](visual-system.md), [변경 파일](phase7-changes.md)을 참조하세요.

## 테스트 결과

| 검사 | 결과 | 실제 검증 |
|---|---|---|
| TypeScript/Vite | 성공 | 정적 에셋 포함 dist 생성 |
| 순수 모듈 | 25 통과 | 기존20개 + 아틀라스 해시/프레임·피벗/전체가구회전/대체리소스/토큰5개 |
| Chrome 브라우저 | 24 통과, 약5분 | 기존21개 + Phase7 신규3개 |
| 백엔드 | 190 통과, 1 생략 | 격리 SQLite/실제 PostgreSQL17, SQLite에서 PG 전용 검사의 조건부 생략 |
| ARM64 Docker Compose | 빌드·3서비스 healthy | 전용 Colima VM, backend aarch64 |
| 실제 Nginx 배포 화면 | 통과 | 로그인·캔버스·코인 확률 UI·관리자, pageerror 없음 |
| 배포 정적 파일 | 통과 | PNG/JSON6개200+immutable 캐시, 없는 이미지404 |

브라우저 전체 회귀에는 여섯 존 클릭 이동/A* 우회/카메라 줌·핀치/경계와 채팅/귓속말·공지·권한/집 입퇴장·가구회전·회수·저장/상점·코인/미니게임·협동/소셜·집방문/관리자가 포함됩니다. 신규 Phase7 테스트는 실제 책상·의자 클릭 후 걷기→작업·앉기와 발 깊이, 이미지 요청 차단 후 대체 그래픽으로 클릭 이동,390px 모바일·동작 줄이기·채팅 모드 게임 정지/복귀·서버 Coin 결과를 확인합니다. 모달 종료 애니메이션 중 다른 팝업을 열면 같이 닫히던 문제를 수정하고 재현 검사를 추가했습니다.

가구 upper/lower와 발 depth 수식은 런타임에서 검증했습니다. 개별 모든 가구의 모든 가림 조합을 수작업으로 검수한 것은 아닙니다. 타일셋 등록 경로는 코드로 제공하지만 실제 별도 이미지 타일셋은 없으므로 그 아트 검수는 미완료입니다.

## 보존 확인

- shared 맵/존/가구 카탈로그, game/systems, backend/app 기존51개 파일은 시작 시 SHA256과 동일합니다. A*·충돌·좌표·서버 권한/경제 코드 변경이 없습니다.
- DevNest 기존123개 파일 SHA256이 동일합니다. DevNest를 수정하지 않았습니다.
- 기존 개발 SQLite의 사용자 수·지갑·가구인스턴스·배치·코인거래·가챠확률 테이블이 시작 시 백업과 동일합니다. 테스트 DB와 운영 모드 Docker 검증 DB는 분리했습니다.
- 가챠는 기존10~1,000 Coin 확률표 그대로입니다. 가구 직접 지급은 추가하지 않았습니다.
- 백업에 있던 기존 docs PNG48개는 원본을 복구했고, 현재 화면은 phase7 접두사로 별도 저장했습니다. 이전 캡처 폴더는 유지했습니다.
- 백업: backups/before-phase7-20261106.zip 및 before-phase7-20261106.sqlite3. 비밀 환경/의존성/런타임 디렉터리는 소스 ZIP에서 제외했습니다.

## 성능과 남은 문제

기존 단일 월드 장면193개 오브젝트, 전경 단일 아바타 기준 Chrome headless/Vite 개발 서버87프레임 측정 평균16.67ms, p9516.70ms(약60.0fps)였습니다. API health5회 왕복 평균3.50ms는 렌더링과 별도로 측정했습니다. 서버 순수 처리시간/부하 처리량 측정은 아닙니다.

아틀라스PNG348,932바이트, RGBA 메모리 산술 추정20,316,160바이트, 최대텍스처2048px 제한입니다. 이 추정은 텍스트/프레임버퍼/드라이버를 제외합니다. 네트워크 리소스 목록은 개발 모듈·브라우저 캐시·초상화/Phaser 재사용 요청도 포함하므로 총 전송량으로 합산하지 않습니다. 원자료는 [performance JSON](phase7-performance.json), 결과 요약은 [test-results JSON](phase7-test-results.json)입니다.

Raspberry Pi4 실기기와15명 동시 캐릭터 부하는 검증하지 않았습니다. ARM64 컨테이너가 브라우저 GPU 렌더링 성능을 증명하지 않습니다. Vite 기본 경고 기준을 넘는 약1.96MB JS(약467KB gzip)가 남아 있으며 별도 청크 분리는 후속 최적화입니다. 백엔드 테스트의 기존 Python/FastAPI deprecation 경고도 남아 있습니다.

추가 필요 자료는 전용 한글 픽셀 폰트 사용권, 정식 방향별 가구 뒤/옆 디테일, chatting/drinking/meeting/celebrating 등 추가 포즈, 이미지 타일셋 및 최종 원화입니다. 실제 가구 설치/회수 전용 연출은 확장 지점만 제공하며 신규 애니메이션으로 완료 처리하지 않았습니다. 이미지 타일/원화를 확보하면 overrides와 라이선스 목록에 등록하고 기존 회귀 테스트를 다시 수행하세요.

## 화면 확인

- [로그인](phase7-login.png) · [단일 월드 전체](phase7-office-overview.png) · [캐릭터 작업](phase7-character-working.png)
- [개인 집](phase7-home.png) · [꾸미기/회전 미리보기](phase7-home-editor.png)
- [그룹 피드](phase7-social-feed.png) · [미니게임](phase7-arcade.png) · [협동 결과](phase7-cooperative-result.png)
- [코인 결과](phase7-coin-result.png) · [관리자](phase7-admin.png)
- [모바일 월드](phase7-mobile-world.png) · [모바일 코인](phase7-mobile-gacha.png) · [누락 리소스 대체](phase7-fallback.png)
- [Docker 실제 월드](phase7-docker-office.png) · [Docker 코인 확률](phase7-docker-gacha.png) · [Docker 관리자](phase7-docker-admin.png)

프로젝트 상위 캡처 폴더: `../캡처/NOBIS-Office_Phase7_2026-11-06/index.html`.

검증 전용 Compose 서비스와 PostgreSQL을 종료하고 데이터 볼륨은 보존했습니다. 기존 개발 프런트15173·백엔드18000/health는 종료하지 않았으며 마지막 확인에서 모두HTTP200입니다. 현재 개발 PC를 최종 운영 서버로 배포하지 않았습니다.
