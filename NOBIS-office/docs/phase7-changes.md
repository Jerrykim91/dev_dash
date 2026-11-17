# Phase 7 변경 파일

Phase 7 시작 전 소스 ZIP과 SHA256 비교한 목록입니다. 기존 파일 삭제는 없습니다. 의존성/빌드/런타임·백업 파일은 제외합니다. 이 목록 문서는 자체 생성 파일입니다.

| 파일 | 변경 |
|---|---|
| `README.md` | 수정 |
| `docs/architecture.md` | 수정 |
| `docs/asset-licenses.json` | 신규 |
| `docs/implementation-plan.md` | 수정 |
| `docs/phase7-admin.png` | 신규 |
| `docs/phase7-arcade.png` | 신규 |
| `docs/phase7-character-working.png` | 신규 |
| `docs/phase7-coin-result.png` | 신규 |
| `docs/phase7-cooperative-result.png` | 신규 |
| `docs/phase7-docker-admin.png` | 신규 |
| `docs/phase7-docker-gacha.png` | 신규 |
| `docs/phase7-docker-office.png` | 신규 |
| `docs/phase7-fallback.png` | 신규 |
| `docs/phase7-home-editor.png` | 신규 |
| `docs/phase7-home.png` | 신규 |
| `docs/phase7-login.png` | 신규 |
| `docs/phase7-mobile-gacha.png` | 신규 |
| `docs/phase7-mobile-world.png` | 신규 |
| `docs/phase7-office-overview.png` | 신규 |
| `docs/phase7-performance.json` | 신규 |
| `docs/phase7-social-feed.png` | 신규 |
| `docs/phase7-test-results.json` | 신규 |
| `docs/phase7-verification.md` | 신규 |
| `docs/storyboard.md` | 수정 |
| `docs/visual-system.md` | 신규 |
| `frontend/nginx.conf` | 수정 |
| `frontend/package.json` | 수정 |
| `frontend/public/visual/avatar-a79c399193b6.png` | 신규 |
| `frontend/public/visual/avatar-atlas-304c2d739689.json` | 신규 |
| `frontend/public/visual/furniture-2c16e38b7b6b.png` | 신규 |
| `frontend/public/visual/furniture-9ba25f6a4f4d.png` | 신규 |
| `frontend/public/visual/furniture-atlas-907ae64968ed.json` | 신규 |
| `frontend/public/visual/furniture-atlas-fe77859b7a02.json` | 신규 |
| `frontend/src/components/FurniturePreview.tsx` | 수정 |
| `frontend/src/components/LegacyFurniturePreview.tsx` | 신규 |
| `frontend/src/components/LoginScreen.tsx` | 수정 |
| `frontend/src/components/MemberList.tsx` | 수정 |
| `frontend/src/components/Modal.tsx` | 수정 |
| `frontend/src/components/SideNavigation.tsx` | 수정 |
| `frontend/src/components/TopBar.tsx` | 수정 |
| `frontend/src/components/WorkStatusIndicator.tsx` | 수정 |
| `frontend/src/design/AvatarPortrait.tsx` | 신규 |
| `frontend/src/design/LoginOfficeArt.tsx` | 신규 |
| `frontend/src/design/PixelIcon.tsx` | 신규 |
| `frontend/src/design/PixelMark.tsx` | 신규 |
| `frontend/src/design/system.css` | 신규 |
| `frontend/src/design/tokens.css` | 신규 |
| `frontend/src/design/tokens.json` | 신규 |
| `frontend/src/game/scenes/WorldScene.ts` | 수정 |
| `frontend/src/game/visual/AssetLoader.ts` | 신규 |
| `frontend/src/game/visual/CharacterVisual.ts` | 신규 |
| `frontend/src/game/visual/FloorVisual.ts` | 신규 |
| `frontend/src/game/visual/FurnitureVisual.ts` | 신규 |
| `frontend/src/game/visual/catalog.ts` | 신규 |
| `frontend/src/game/visual/manifest.json` | 신규 |
| `frontend/src/game/visual/overrides.json` | 신규 |
| `frontend/src/game/visual/visual.test.ts` | 신규 |
| `frontend/src/games/arcade.css` | 수정 |
| `frontend/src/home.css` | 수정 |
| `frontend/src/main.tsx` | 수정 |
| `frontend/src/phase35.css` | 수정 |
| `frontend/src/social.css` | 수정 |
| `frontend/src/social/ProfileCard.tsx` | 수정 |
| `frontend/src/social/social.css` | 수정 |
| `frontend/src/style.css` | 수정 |
| `infra/visual/build-assets.cjs` | 신규 |
| `tests/phase7.spec.ts` | 신규 |

핵심 구현: `game/visual` 표시 계층, `design` 토큰/공통 UI, 원본 아트 생성기, 실제 `public/visual` PNG/JSON, 공통 초상화·가구 미리보기, Nginx 정적 캐시, Phase7 단위/브라우저 검사.

보존: 기존 backend/app·shared·game/systems 전체51개 및 DevNest123개 SHA256 동일. DB 스키마·가챠 확률·A*·충돌 모듈은 변경하지 않았습니다.

수행한 검증과 제한은 [phase7-verification.md](phase7-verification.md), 등록·교체 규격은 [visual-system.md](visual-system.md)를 참조하세요.
