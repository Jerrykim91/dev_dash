# 월드·채팅·관리자 변경 파일

기준: backups/before-multichannel-20261106.zip 대비 SHA-256 비교. 의존성/DB/캐시/빌드 결과/백업 제외. 기존 DevNest·Phase 1-1은 수정하지 않았습니다.

world channel 식별자/원자적 입장, 귓속말 보관/전달, 공개 채팅 말풍선, 공지 큐, RBAC/CLI/관리자 UI를 추가했습니다. public office 맵 파일/존 좌표를 유지하고 존 설정에는 말풍선 허용 플래그만 추가했습니다. 기존 공개 멘션은 요청에 따라 @ 귓속말로 변경했습니다.

## 생성 (12)

- `backend/app/admin.py`
- `backend/app/cli.py`
- `backend/app/social.py`
- `backend/tests/test_social.py`
- `docs/admin-audit.png`
- `docs/chat-bubble.png`
- `docs/multichannel-live.png`
- `docs/multichannel-toast.png`
- `frontend/src/components/AdminPage.tsx`
- `frontend/src/components/AnnouncementBanner.tsx`
- `frontend/src/social.css`
- `tests/social.spec.ts`

## 수정 (43)

- `.env.example`
- `README.md`
- `backend/app/main.py`
- `backend/app/migrations.py`
- `backend/app/models/contracts.py`
- `backend/app/repository.py`
- `backend/app/websocket/hub.py`
- `backend/tests/test_server.py`
- `compose.yaml`
- `docker-compose.dev.yml`
- `docker-compose.yml`
- `docs/architecture.md`
- `docs/changes.md`
- `docs/chat-only.png`
- `docs/implementation-plan.md`
- `docs/office-desktop.png`
- `docs/office-mobile.png`
- `docs/office-world.png`
- `docs/phase2-meeting.png`
- `docs/phase2-personal-room.png`
- `docs/phase3-decorating.png`
- `docs/phase3-home.png`
- `docs/storyboard.md`
- `docs/verification.md`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/playwright.config.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/ChatInput.tsx`
- `frontend/src/components/ChatMessageList.tsx`
- `frontend/src/components/ChatPanel.tsx`
- `frontend/src/components/GameWorld.tsx`
- `frontend/src/components/LoginScreen.tsx`
- `frontend/src/components/TopBar.tsx`
- `frontend/src/game/bridge.ts`
- `frontend/src/game/scenes/WorldScene.ts`
- `frontend/src/game/types.ts`
- `frontend/src/main.tsx`
- `frontend/src/stores/officeStore.ts`
- `frontend/src/useOffice.ts`
- `shared/zones.json`
- `tests/office.spec.ts`
- `tests/phase2.spec.ts`

## 삭제 (0)

없음.

