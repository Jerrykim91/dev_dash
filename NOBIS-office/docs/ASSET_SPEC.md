# NOBIS Office 에셋 규격 — Phase 7-B

## 실제 엔진 규격

- 논리 타일:정수 그리드 한 칸. 기본 아이소메트릭 렌더링64×32px.
- 변환:worldX=(tileX-tileY)×32, worldY=(tileX+tileY)×16. 클릭은 카메라 scroll/zoom을 역변환한 뒤 반올림합니다. 기존 CoordinateSystem/SurfaceCoordinates/A*를 재사용합니다.
- 로비:30×24 논리 범위,607개 바닥 타일. 다른 룸은 별도 맵이며 동시에 렌더링하지 않습니다.
- 캐릭터:원본48×64px, origin(0.5,58/64), 표시 배율1.125(54×72px), 발 기준. idle/walking/sitting/typing의 기존4방향 프레임을 유지합니다.
- 가구:128×160px의 투명 프레임, 원점(64,104), lower/upper 두 부분. footprint는 map.width/height이며 이미지 영역과 별개입니다.
- 깊이:tile(x+y)×100, 캐릭터+1, 가구 하단−0.15/상단+0.15. 바닥·건축 후면·효과·이름표는 별도 레이어입니다.
- 기존 카메라:데스크톱 기본0.6~1, 모바일1.05, 최대1.8, 최소는 현재 룸 fit. 드래그·휠·핀치는 기존 CameraSystem/GestureSystem을 사용합니다.
- 충돌:현재 룸의 walkable_tiles/closed_edges/오브젝트 footprint. 바닥 및 벽 이미지가 경로 데이터를 결정하지 않습니다.

## 로비 리소스

frontend/public/assets/world/lobby/manifest.json과 하위 tiles/architecture/furniture/effects 구조를 사용합니다. 타일은64×32px, 건축·문은128×160px/발 pivot(64,104), 최대 아틀라스2048px입니다. PNG는 투명 배경이며 보간을 끄고 픽셀 확대합니다. 이미지 배율로 충돌 크기를 바꾸지 않습니다. 원본의 절반 해상도 Canvas에 정수 픽셀로 그린 뒤 nearest 확대하는 제작기를 사용합니다.

기존 자체 제작 아바타/가구 아틀라스를 재사용합니다. 새 코드 제작 로비 타일/벽/입구는 실제 생성된 PNG로 등록하며 최종 원화와 구분합니다. 목표 참조 이미지를 자르거나 한 장 배경으로 사용하지 않습니다. 경로는 BASE_URL 상대 경로이며 아틀라스 파일명은 내용 해시를 포함합니다. 누락 이미지·프레임은 기존 Graphics/가구 플레이스홀더로 복귀해야 합니다.

확보된 원본과 라이선스는 docs/asset-licenses.json을 참조하세요. 제3자 이미지와 외부 유료 에셋을 추가하지 않습니다. 최종 이미지와 미확보 항목은 docs/lobby-assets.md에 별도로 기록합니다.

## 실제 화면 크기와 레이어

표시되는 타일은64×zoom /32×zoom CSS px이며 데스크톱 기본0.85에서54.4×27.2px입니다. 캐릭터는54×72px 표시 크기에 zoom을 적용합니다. canvas는 부모 크기와 Phaser RESIZE를 맞추고 pixelArt=true/antialias=false를 유지합니다. 별도 고DPI 배율 최적화를 주장하지 않습니다.

| 계층 | 구현 |
|---|---|
| Background | 기존 Phaser 배경색, 별도 배경 원화 없음 |
| Floor | 개별 목재/석재 타일, 없으면 기존 Graphics |
| Back Architecture | LobbyVisual의 벽 프레임 |
| Back Furniture | FurnitureVisual.lower |
| Characters | 기존 발 위치 깊이 +1 |
| Front Furniture | FurnitureVisual.upper |
| Front Architecture | 기둥의 upper/발 깊이 정렬 |
| Effects | 별도 바닥 간접 조명 Graphics, 최종PNG 없음 |
| UI Overlay | 기존 이름표·상태·입구 이름/인원 |

고정 깊이층과 동일 층의 발 기준 정렬을 함께 사용하며 이미지 bounds로 충돌을 계산하지 않습니다.
