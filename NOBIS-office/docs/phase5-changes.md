# Phase 5 생성·수정 파일

기존 월드/가구 정의와 DevNest는 보존했습니다. 이전 Phase 캡처는 원본을 유지하고 이번 캡처는 phase5-* 이름으로 추가합니다.

## 생성 파일

- `backend/app/collectibles/__init__.py`
- `backend/app/collectibles/api.py`
- `backend/app/collectibles/schema.py`
- `backend/app/collectibles/service.py`
- `backend/app/community/__init__.py`
- `backend/app/community/api.py`
- `backend/app/community/schema.py`
- `backend/app/community/service.py`
- `backend/app/community/storage.py`
- `backend/tests/test_collectibles.py`
- `backend/tests/test_community.py`
- `docs/phase5-changes.md`
- `docs/phase5-test-results.json`
- `docs/phase5-verification.md`
- `frontend/src/collectibles/AdminCollectibles.tsx`
- `frontend/src/collectibles/CollectiblesRoot.tsx`
- `frontend/src/social/AdminCommunity.tsx`
- `frontend/src/social/AuthImage.tsx`
- `frontend/src/social/Feed.tsx`
- `frontend/src/social/Friends.tsx`
- `frontend/src/social/Groups.tsx`
- `frontend/src/social/ProfileCard.tsx`
- `frontend/src/social/SocialRoot.tsx`
- `frontend/src/social/api.ts`
- `frontend/src/social/social.css`
- `tests/phase5.spec.ts`
- `tests/fixtures/social-upload.png`

## 수정 파일

- `.env.example`
- `README.md`
- `backend/Dockerfile`
- `backend/app/cli.py`
- `backend/app/database.py`
- `backend/app/db_transfer.py`
- `backend/app/main.py`
- `backend/app/repository.py`
- `backend/app/social.py`
- `backend/app/websocket/hub.py`
- `backend/requirements.txt`
- `backend/tests/test_phase35.py`
- `backend/tests/test_server.py`
- `compose.yaml`
- `docker-compose.dev.yml`
- `docker-compose.sqlite.yml`
- `docker-compose.yml`
- `docs/architecture.md`
- `docs/implementation-plan.md`
- `docs/storyboard.md`
- `frontend/nginx.conf`
- `frontend/playwright.config.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/AdminPage.tsx`
- `frontend/src/components/ChatInput.tsx`
- `frontend/src/components/MemberList.tsx`
- `frontend/src/components/TopBar.tsx`
- `frontend/src/components/WorkStatusIndicator.tsx`
- `frontend/src/game/types.ts`
- `frontend/src/main.tsx`
- `frontend/src/services/adminPresentation.ts`
- `frontend/src/useOffice.ts`

추가 화면: `docs/phase5-*.png`. 런타임 DB·media와 검증용 비밀 계정은 소스 파일 목록에서 제외합니다.
