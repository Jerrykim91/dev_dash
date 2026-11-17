# 가구 → NOBIS Coin 뽑기 변경 · 2026-11-06

상단 티켓 아이콘 → **코인 뽑기**. 무료 출석 티켓1장으로1회, 5장으로5회를 진행합니다. 서버가 결정한 코인을 기존 지갑에 지급하며 가구 인벤토리는 늘어나지 않습니다. 기존 가구 상점·집 꾸미기·미니게임·소셜은 보존합니다.

## 기본 확률

- 보상: 10,20,…,1000 Coin(100종)
- 중심 μ=505, 기본 σ=165인 정규분포 모양의 이산 가중치: `exp(-0.5*((amount-505)/165)^2)`
- 10~1000 구간에서 정규화 후 좌우 대칭 최대 나머지 반올림. 최소 양의 정수 BPS를 유지하고 합계10000=100%를 정확히 보장합니다.
- 10/1000은 각각0.03%, 500/510은 각각2.42%, 기대 보상505 Coin/회입니다. 범위 제한과 BPS 반올림 후 실제 표준편차는 약163.02입니다.
- UI에 현재 DB 확률표의 평균, 분포 그래프, 금액별 전체 확률을 표시합니다. 관리자 수동 조정 시 현재 확률대로 그래프·평균을 계산하며 확률 합계/중복/금액 범위를 검사합니다. 기본 정규분포형 복원 버튼을 제공합니다.
- 전체 기본표: [CSV](coin-gacha-probabilities.csv). 실제 추첨은 현재 활성 배너의 DB 확률표를 사용합니다.

## 데이터와 보존

추가형 스키마v8: `gacha_coin_pool_items`(버전별 금액/확률), `gacha_coin_draw_items`(영수증/순번/금액/원장ID). 기존 가구 확률/추첨 테이블·가구 인스턴스·기록은 유지하고 기존 가구 배너만 종료합니다. 기본 새 배너는 `daily-coins`입니다. 이전 가구 영수증을 재조회·재전송해도 재지급하지 않습니다.

코인 차감이 아닌 **티켓 차감 + 코인 지갑 증가 + Coin원장(gacha_reward) + 추첨 영수증 + 티켓원장**을 한 DB 트랜잭션으로 확정합니다. 횟수1/5, 서버난수, 사용자별 UUID 요청키, 확인한 확률표 버전, 원장ID 유니크 제약을 유지합니다. 재시도는 같은 영수증을 반환하고 다시 코인을 지급하지 않습니다. 오류 주입으로 전체 롤백을 확인했습니다.

SQLite는 마이그레이션 전에 `.pre-coin-gacha.bak`을 생성합니다. PostgreSQL은 기존 advisory migration lock/트랜잭션을 재사용합니다. DB 이전 모듈은 새 두 테이블을 FK 순서로 포함합니다. 기존 Phase 5 검증 문서는 당시 가구 지급 버전의 기록이며 현재 동작은 이 문서와 README의 코인 설명이 우선합니다.

## 변경 파일

- `backend/app/collectibles/{schema,service,api}.py`: v8·기본 확률·코인 지급·과거 기록 호환·관리자 통계
- `backend/app/{repository,database,db_transfer,cli}.py`: 양 DB 마이그레이션·이전·버전 출력
- `frontend/src/collectibles/{CoinOdds,CollectiblesRoot,AdminCollectibles}.tsx`: 확률 그래프/표·코인 결과·잔액·관리자 편집
- `frontend/src/components/HomeTools.tsx`, `services/adminPresentation.ts`, `social/social.css`: 코인 원장 표시·공통 감사 문구·스타일
- `backend/tests/test_collectibles.py`, `test_phase35.py`, `tests/phase5.spec.ts`: 코인 지급·이전·브라우저 검증
- `README.md`, 이 문서, 확률 CSV, architecture/storyboard/implementation-plan: 변경 설명

## 검증

- 전체 서버 **174 passed, 1 skipped**: SQLite + PostgreSQL17의 일반 앱 역할. skip은 SQLite에서 PG 전용 이전 사례 제외.
- Chrome UI **3 passed**: 소셜 회귀, 코인 확률 그래프·1/5회 지급·지갑/기록/관리자, 모바일390px 터치·출석·코인 뽑기.
- 같은 UI를 실제 PostgreSQL 격리 DB에서도 **3 passed**.
- TypeScript 검사 + Vite production build 성공. 기존 Phaser 번들 크기 경고는 유지됩니다.
- 정확한 확률합/대칭/단조 형태, 최저·최고 RNG 선택, 티켓 부족, 중복/동시 요청, 5회 합산·원장 지급, 지급 실패 시 잔액/티켓 전체 롤백, 관리자 외 변경 거부, 기존 가구 기록 보존, SQLite→PG 코인 데이터 이전을 검증했습니다.
- 기존 개발 DB의 사용자·가구·배치·지갑·Coin원장·귓속말 수와 잔액 합계를 재시작 전후 비교하여 동일함을 확인했습니다. 테스트 코인은 격리 DB에만 지급했습니다.

## 실행

현재 개발 화면: `http://127.0.0.1:15173/`. 재실행/마이그레이션 명령은 README와 같습니다. 프로젝트 루트에서 테스트:

```sh
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run build
npm --prefix frontend run test:e2e -- ../tests/phase5.spec.ts
```

기본 pytest는 PG 환경 변수가 없으면 PG 사례를 제외합니다. 이번 PG 검증은 별도 `NOBIS_TEST_POSTGRES_URL`, `NOBIS_TEST_POSTGRES_APP_URL`, `NOBIS_E2E_DATABASE_URL`을 사용했습니다. 사용자 DB를 테스트 DB로 지정하지 않습니다. 이번 변경은 native SQLite/PG/Chrome에서 검증했으며 Docker 컨테이너 재빌드·복구 테스트는 이번 변경 후 다시 수행하지 않았습니다. 이전 Phase 5의 Docker 저장 검증과 구분합니다.
