# NOBIS office 에셋 추가 가이드

이 문서만 보고 새 가구·바닥·벽·문·캐릭터 동작·옷·머리를 추가할 수 있도록, 지금까지 만든 템플릿과 생성 규칙을 한곳에 모았습니다.
수치의 근거와 결정 배경은 [`visual-standard-v2.md`](visual-standard-v2.md)에 있습니다(§2 기하, §7 좌석·깊이, §13 벽·문, §14 2배 밀도, §15 옷 갈아입기).

- 대상 독자: 에셋을 추가하는 사람, 또는 이 문서를 받아 작업하는 AI 에이전트
- 마지막 갱신: 2026-11-23

---

## 1. 한눈에 보기

```
① 블록아웃(정확한 2:1 회색 입체)  →  ② AI 생성(블록아웃을 편집 대상으로 칠하기)
→  ③ 1배 빌드(정합·품질 검사, qa.json)  →  ④ 2배 밀도 빌드(norm_d2)
→  ⑤ 아틀라스 묶기(pack_v2.py → frontend/public/visual, overrides.json)
→  ⑥ 게임 연결(종류·크기별 이름표, 맵·카탈로그)  →  ⑦ 테스트
```

| 에셋 종류 | 생성 명세 | 블록아웃 | 빌드 | 게임 연결 | 절 |
|---|---|---|---|---|---|
| 가구(1×1, 2×1, 1×2) | `v2/make_spec.py` `prop()` | `v2/blockout.py` `FURNITURE` | `build.py` | `pack_v2.py` `FURNITURE` | §4 |
| 큰 가구(4칸 이상) | 〃 | 〃 + 배율 | 〃 | `FURNITURE` + `BIG` | §4.6 |
| 로비 전용 물체 | 〃 | 〃 | 〃 | `pack_v2.py` `LOBBY_OBJECTS` | §4.7 |
| 바닥 | `tex()` | 없음 | `build.py` | `pack_v2.py` `TILESETS` | §5.1 |
| 벽 | `tex()` | 없음 | 〃 | `WALLS` + `WallVisual.ts` | §5.2 |
| 문(로비 입구·방 출구) | `tex()` | 없음 | 〃 | `DOORS` + `doorTheme` | §5.3 |
| 완성형 캐릭터 동작(프리셋) | `clip()` | `blockout.py` `CLIPS`/`POSES` | 〃 | `pack_v2.py` `STATES`·`PRESETS` | §7 |
| 옷(상의·하의) | `parts/make_spec.py` `TOPS`/`BOTTOMS` | 기본 몸 시트 | `parts/process.py` | 자동(`overrides.parts`) | §6 |
| 머리 | `parts/make_spec.py` `HAIR` | 머리 시트 | 〃 | 자동 | §6.4 |

경로는 모두 `NOBIS-office/infra/visual/aigen/` 기준입니다(따로 적지 않으면).

---

## 2. 준비

### 2.1 도구
- **Codex CLI** + 내장 이미지 생성 스킬(`imagegen`, OpenAI API 키 불필요). 생성기는 `codex exec`를 부른다.
- **Python 3.12** + `Pillow`, `numpy`, `scipy`. 백엔드 가상환경(`NOBIS-office/.venv`)이나 시스템 파이썬 어느 쪽이든 된다.
- **Node 22**: 프런트 테스트(`cd frontend && npm test`, `npx playwright test`).

### 2.2 폴더
| 경로 | 내용 | 저장소 |
|---|---|---|
| `gen.py` | 생성기(명세의 각 에셋을 Codex로 1장씩) | 보관 |
| `normalize.py` | 축소(`pixelize`) | 보관 |
| `refs/style-office.png` | 스타일 기준 그림(모든 생성의 Image 2) | 보관 |
| `raw/char_a.png`, `raw/wall_plain.png` | 캐릭터 p0·기본 벽 참고 원본 | 보관 |
| `v2/standard.py` | **모든 수치의 정본**(타일, 프레임, 좌석 높이, 품질 기준) | 보관 |
| `v2/blockout.py` | 블록아웃 정의·렌더링 | 보관 |
| `v2/make_spec.py` → `v2/spec.json` | 생성 명세(프롬프트) | 보관 |
| `v2/build.py` | 정합·면 밝기 맞춤·축소·품질 검사·색 교체 | 보관 |
| `v2/pack_v2.py` | 아틀라스 묶기 + `frontend/src/game/visual/overrides.json` | 보관 |
| `v2/raw/` | AI 원본. 다음 생성의 참고로 쓰는 것만 보관(`.gitignore` 예외 목록) | 일부 |
| `v2/norm/` | 1배 프레임(품질 검사용) | 로컬 |
| `v2/norm_d2/` | 2배 밀도 프레임 = **아틀라스의 원본** | 보관 |
| `v2/blockout/` | 블록아웃 그림(`blockout.py`로 재생성) | 로컬 |
| `parts/` | 옷 갈아입기 파트(템플릿·명세·처리·내보낸 HD 프레임) | §6 |

> AI 원본은 장당 약 1MB라 대부분 저장소에 두지 않습니다. 이미 있는 에셋을 다시 처리하려면 원본이 있는 로컬 작업 폴더가 필요합니다. 새 에셋은 생성 → 빌드 → 묶기만 하면 되므로 원본이 없어도 됩니다(묶기는 `norm_d2`만 읽습니다).

### 2.3 명령을 쓸 때 주의
- **zsh에서 변수로 여러 id를 넘기지 마세요.** `W="a b"; python3 build.py $W`는 `"a b"` 한 덩어리로 넘어가서 아무것도 빌드되지 않습니다. id를 그대로 나열합니다.
- 생성은 **장당 약 1분**입니다. `--jobs 4`로 병렬 실행할 수 있습니다.
- 생성기는 참고 이미지가 없으면 생성 전에 멈춥니다(`FAILED (missing image …)`). 명세의 `refs`·`guide` 경로는 **명세 파일이 있는 폴더 기준**입니다(`v2/spec.json`이면 `raw/x.png` = `v2/raw/x.png`, `../raw/x.png` = `aigen/raw/x.png`).
- Codex가 결과를 지정 경로가 아닌 곳에 저장하는 일이 있습니다. 생성기가 그 세션 폴더에서 회수(`ok (recovered)`)하지만, `FAILED (see log)`이면 `<rawDir>/<id>.log`를 확인하세요.

---

## 3. 공통 규격(바꾸지 마세요)

`v2/standard.py`가 정본입니다. 요약:

| 항목 | 값 |
|---|---|
| 투영 | 2:1 다이메트릭(26.565°). 화면 x = (x−y)·32, y = (x+y)·16 − z·32 (1배) |
| 타일 | 64×32, 1타일 = 1m, 높이 1m = 32px |
| 가구 프레임 | 1배 128×160, 기준점 (64,104) = 원점 칸 중심 / 2배 256×320, (128,208) |
| 캐릭터 프레임 | 1배 48×64, 발 (24,58) / 2배 96×128, (48,116). 전신 54px, 머리 40% |
| 좌석 높이 | 12px(0.375m) |
| 광원 | 바로 위. 윗면 가장 밝고 두 옆면은 같은 톤(좌우 반전해도 되도록) |
| 외곽선 | 1px 짙은 자두색. 재질당 3톤, 디더링·그라데이션 없음 |
| 그림 밀도 | 게임 아틀라스는 2배(그림 2px = 월드 1px). `overrides.json`의 아틀라스 `scale: 0.5` |
| 생성 배율 | 블록아웃 8배(1배 1px = 8px). 1배는 1/8, 2배는 1/4로 축소 |
| 높이 한도 | 1×1 가구는 **2.3m 이하**. 2.5m면 블록아웃 캔버스 위 끝에 닿아 생성 그림이 잘림 |

**회전(4-way-mirror)**: 회전 0 = 앞 뷰(`*_s`), 90 = 앞 뷰 좌우 반전(가로·세로 크기 교환), 180 = 뒤 뷰(`*_n`), 270 = 뒤 뷰 반전. 그래서 가구는 **앞·뒤 두 장만** 생성합니다.

**캐릭터 방향**: 남(앞, 왼쪽 아래)·북(뒤, 오른쪽 위)만 생성하고, 동·서는 게임이 좌우 반전합니다.

---

## 4. 가구 추가

예시: 1×1 "물 정수기"를 회전 가능하게 추가.

### 4.1 블록아웃 정의 — `v2/blockout.py`
치수는 미터, 원점 칸의 (0,0,0)부터. 회전 0에서 **사용 면(앞면)이 +y(화면 왼쪽 아래)**를 봅니다. 파트마다 `('이름', 'lower'|'upper', (x0,y0,z0,x1,y1,z1))`.
`upper`는 앉은 캐릭터보다 **앞**에 그려지는 부분(의자 등받이 등)이고, 그 밖은 `lower`입니다.

```python
def water_cooler():
    return [('base', 'lower', (.25, .30, 0, .75, .80, .90)),       # 몸통 캐비닛
            ('bottle', 'lower', (.33, .38, .90, .67, .72, 1.35))]  # 물병

FURNITURE = {
    ...,
    'water_cooler_s': (water_cooler, (1, 1)),
    'water_cooler_n': (lambda: rot180(water_cooler(), 1, 1), (1, 1)),   # 뒤 뷰
}
```
`python3 v2/blockout.py water_cooler_s water_cooler_n` → `v2/blockout/<id>.png`(가이드)·`.parts.png`·`.faces.png`·`.json`.

### 4.2 생성 명세 — `v2/make_spec.py`
`prop(id, 블록아웃_id, 묘사, phase=G)`. 묘사는 **블록아웃의 각 덩어리가 무엇인지** 순서대로 적습니다("the big slab = …, the post = …"). 뒤 뷰는 앞 뷰를 같은 물체 참고로 줍니다.

```python
prop('water_cooler_s', 'water_cooler_s', "office water cooler seen from the FRONT: the lower box = a cream cabinet "
     "with two small taps (blue and red) facing lower-left; the upper block = a big translucent blue water bottle", phase=G)
prop('water_cooler_n', 'water_cooler_n', "the SAME water cooler seen from BEHIND: plain cream back panel, the blue bottle on top",
     refs=['raw/water_cooler_s.png'], phase=G)
```
뒤 뷰는 앞 뷰 생성이 끝난 뒤에 생성합니다(참고 이미지가 있어야 함). `python3 v2/make_spec.py`로 `spec.json`을 갱신합니다.

**공통 프롬프트(자동으로 붙음)** — `COMMON['gprop']`:
> furniture sprite for a 2:1 isometric pixel-art office game; it will be downscaled exactly 8x … crisp pixel art in the style of Image 2 … one-art-pixel dark plum outline, 3-tone cel shading per material, cozy pastel palette, no dithering, no gradients, no blur … Lighting: soft light from DIRECTLY ABOVE … the two visible side faces share the SAME mid tone … Background: fully transparent … Avoid: floor, ground plane, grid, shadows on the ground, text …

역할 문구(자동): "Image 1 is the EDIT TARGET: a grey 3D blockout rendered in exact 2:1 dimetric projection. Edit Image 1: repaint every block as the described object while keeping the camera angle, every edge direction, the silhouette, proportions and position EXACTLY … Image 2 is a STYLE REFERENCE ONLY."

### 4.3 생성 → 빌드
```bash
cd NOBIS-office/infra/visual/aigen
python3 gen.py --config v2/spec.json water_cooler_s            # 앞 뷰
python3 gen.py --config v2/spec.json water_cooler_n            # 뒤 뷰(앞 뷰 참고)
cd v2
python3 build.py water_cooler_s water_cooler_n                 # 1배 + 품질 검사 → qa.json/qa.md
NOBIS_DENSITY=2 python3 build.py water_cooler_s water_cooler_n # 2배 밀도 → norm_d2/ (정합값은 qa.json 재사용)
```

### 4.4 품질 검사(`qa.md`에서 확인)
| 항목 | 기준 | 실패하면 |
|---|---|---|
| `iou` | 블록아웃 실루엣과 0.85 이상(식물·원형 등 유기적 형태는 0.60) | 재생성. 묘사가 블록아웃 덩어리와 맞는지 확인 |
| `angle` | 가장자리 각도 26.565° ± 1.5° | 재생성 |
| `symmetry` | 두 옆면 밝기 차 8% 이하(빌드가 자동 보정) | 재생성 |
| `bounds` | 프레임 가장자리에 닿지 않음 | 블록아웃이 너무 큼(높이 2.3m 이하) |
| `colors` | 48색 이하 | 묘사 단순화 |
각 생성은 확률적이라 같은 명세로 다시 생성하면 대부분 통과합니다(`gen.py --force <id>`).

### 4.5 게임 연결
1. **`v2/pack_v2.py`의 `FURNITURE`**: `'<kind>/<W>x<H>': (회전0 뷰, 회전180 뷰)`. 크기는 회전 0 기준.
   ```python
   'water_cooler/1x1': ('water_cooler_s', 'water_cooler_n'),
   ```
   묶기: `python3 v2/pack_v2.py` → `frontend/public/visual/aigen-v2-*.png/.json`(2048 한도로 여러 장) + `overrides.json`.
2. **앉는 가구**면 `shared/object-kinds.json`에 좌석(`seats: [{tile, facing, sitHeight}]`)을, 책상이면 `workSurface`를 추가합니다(형식은 `chair/1x1`, `sofa/2x1`, `desk/2x1` 참고).
3. **맵에 배치**: `design/rooms/rooms.json`의 해당 방 `objects`에 `{id, kind, x, y, width, height, rotation, interaction}` 추가 → `python3 infra/world/build-rooms.py`(→ `shared/rooms.json`, `maps.json`, `zones.json`).
4. **개인 방 상점**: `shared/furniture-catalog.json`에 `{item_id, name, category, size:{width,height}, rotatable, price, asset_key:'<kind>', blocking}`.
5. 게임은 `furniture/<kind>/<W>x<H>/<회전>/lower|upper` 프레임을 찾아 그립니다. 없으면 코드 도형으로 대체되므로, 묶은 뒤 화면에서 확인하세요.

### 4.6 큰 가구(4칸 이상, 예: 회의 테이블 3×5)
- 블록아웃: `FURNITURE`에 세 번째 값으로 배율을 준다(`'meeting_table': (meeting_table, (3, 5), 4)`). 캔버스에 다 들어가도록 배율을 낮춘다.
- 빌드가 프레임 크기와 기준점을 따로 계산(`qa.json`의 `frame`)한다.
- `pack_v2.py`의 `BIG`에 이름을 넣는다. 그러면 여백을 자르지 않고, 프레임에 기준점(`origin`)이 기록된다.
- 게임은 4칸 이상 가구를 **월드 폭 32px 띠로 잘라** 띠마다 가장 앞 칸의 깊이를 준다(`FurnitureVisual.sliceByFootprint`). 둘러앉은 캐릭터와 앞뒤가 맞는다.

### 4.7 로비 전용 물체
맵 물체에 `visual_asset: '<이름>'`을 주고, `pack_v2.py`의 `LOBBY_OBJECTS`에 `'<이름>': '<생성 id>'`를 추가합니다. 게임은 `lobby-object/<이름>/lower|upper`를 먼저 찾습니다(예: `bookshelf` → `home_portal`, `column` → `column`).

---

## 5. 바닥·벽·문(텍스처)

텍스처는 블록아웃 없이 **정면(또는 위에서 본) 그림**을 생성해 빌드가 아이소로 투영합니다. `v2/make_spec.py`의 `tex(id, 묘사, 크기, refs, role, key=)`.

### 5.1 바닥
```python
tex('floor_tatami', f"{FLOOR}: pale green tatami mats with dark cloth borders")
```
`FLOOR` = "a single square patch seen straight from above, seamless when repeated, muted pastel palette matching the reference".
- 빌드는 2배 밀도에서도 **1배 텍셀(32×32)로 투영**한다(더 잘게 하면 나무결·이음선이 1px 줄무늬로 촘촘해져 지글거림).
- 연결: `pack_v2.py`의 `TILESETS`에 `'<존 id>': 'floor_…'`(존 id: `focus`, `office`, `meeting`, `cafe`, `lounge`, `garden`, `outside`, `home`). 로비는 돌 = `office`, 나무 = `home` 타일셋을 쓴다.

### 5.2 벽
- 생성: 가로로 이어지는 **정면 입면도**, 1536×1024. 기본 벽(`raw/wall_plain.png`)을 참고로 주고 `WALL_ROLE`(윗단 몰딩·징두리 높이·걸레받이 비율을 같게)을 붙인다.
  ```python
  tex('wall_library', "front elevation of a library wall, horizontally seamless: upper part sage green paint, lower third dark wood panels, "
      "thin cream top cap, dark wooden baseboard; same proportions as Image 2", '1536x1024', ['../raw/wall_plain.png'], WALL_ROLE)
  ```
- 투명한 부분이 있는 벽(난간)은 `key='#00ff00'`과 "EVERYTHING … is fully transparent background (alpha)"를 넣는다.
- 연결: `pack_v2.py` `WALLS`에 `'<테마>': 'wall_…'`, 게임 `frontend/src/game/visual/WallVisual.ts`의 `WALL_THEME`에 `'<room_type>': '<테마>'`. 벽은 걸을 수 있는 칸의 −x·−y 쪽(뒤쪽 두 면)에만 그린다.

### 5.3 문
- 문은 **벽 한 칸 + 가운데 문** 정면 그림(1024×1536)이다. 문 둘레 벽이 그 문이 붙는 벽과 같아야 하므로, 붙을 벽 원본을 참고로 준다.
  ```python
  DOOR + "<문 테마 묘사>"   # DOOR: "front elevation … ONE wall segment with ONE door in its exact horizontal center. The door is about 55% of the image width, its top at about 78% of the wall height, standing on the baseboard. The wall around the door matches Image 2. No text, no letters, no numbers. Door theme: "
  ```
- 이름 규칙(`DOORS`, `WallVisual.doorTheme`):
  - 로비 입구 `portal-<방 종류>` → `door_<방 종류>`(로비 기본 벽 참고)
  - 방 출구 `room-exit` → 그 방 벽 테마에 맞춘 문: 기본 벽 `door_exit`, 카페 `door_exitcafe`, 회의실 `door_exitmeeting`, 난간 방 `door_gate`
  - 새 벽 테마를 만들면 출구 문 `door_exit<테마>`도 같이 만들고 `DOORS`에 `exit<테마>`를 추가한다.
- 난간처럼 투명한 벽의 문은 문 높이(이미지 높이의 78%)로 그리고, 옆 난간 조각은 난간 그림과 같은 높이 비율(난간은 이미지 아래 36%)로 맞추라고 적는다(`door_gate` 명세 참고).
- 문의 벽 방향(`wall_axis`)은 서버가 맵에서 계산한다(`backend/app/seats.py` `derive_wall_axis`). 문은 걸을 수 있는 칸에 두고, 그 칸의 −x 또는 −y 쪽이 바닥 밖(벽)이어야 한다.

빌드: `python3 build.py <id>` → `NOBIS_DENSITY=2 python3 build.py <id>` → `python3 pack_v2.py`.

---

## 6. 옷 갈아입기 파트(옷·머리) — 권장

캐릭터 외형을 늘릴 때는 완성형 캐릭터(§7)보다 이 방식을 씁니다. 몸을 다시 그리지 않고 **옷 시트 2장(앞·뒤)** 또는 **머리 시트 1장(4종)**만 생성하면 됩니다. 게임은 기본 몸 위에 하의 → 상의 → 머리를 실행 중에 겹쳐 그립니다.

### 6.1 구조(`parts/`)
| 파일 | 역할 |
|---|---|
| `template.py` → `template/` | 잠긴 지오메트리 템플릿. 몸 시트(방향별 1536×1024, 5×2칸: 대기 2·걷기 4·앉기 2·타이핑 2, 마네킹 6배), 머리 시트(4×2칸, 12배), 칸·머리 중심·파트 마스크 JSON |
| `make_spec.py` → `spec.json` | 생성 명세. **`TOPS`·`BOTTOMS`·`HAIR`에 한 줄 추가** |
| `process.py base` | 기본 몸 시트 정합 → `work/base_<dir>.png`(옷 생성의 편집 대상) |
| `process.py layers` | 옷 레이어 추출, 머리 잘라 내기 |
| `process.py export` | HD 파트 프레임 → `export/`(+ `parts.json`: 상태별 프레임 번호, 머리 위치 표, 목록·이름) |
| `../v2/pack_v2.py` | `export/`를 아틀라스에 넣고 `overrides.parts`와 서버 검증 목록 `shared/avatar-parts.json` 생성 |

### 6.2 상의·하의 추가
1. `parts/make_spec.py`:
   ```python
   TOPS = { ..., 'blazer': ('차콜 블레이저', "a charcoal single-breasted blazer over a light blue shirt, long sleeves to the wrists") }
   BOTTOMS = { ..., 'jeans': ('청바지', "straight blue denim jeans to the ankles (replace the grey leggings)") }
   ```
   - id는 영문 소문자(프레임 이름에 그대로 들어감), 첫 값은 화면에 보일 이름, 둘째 값은 영어 묘사.
   - 상의는 소매가 손목까지 오도록, 하의는 "(replace the grey leggings)"를 붙인다(기본 몸은 회색 셔츠·레깅스).
2. 생성(옷마다 앞·뒤 2장) → 레이어·내보내기 → 묶기:
   ```bash
   cd NOBIS-office/infra/visual/aigen/parts
   python3 make_spec.py
   cd .. && python3 gen.py --config parts/spec.json --jobs 4 top-blazer_south top-blazer_north bottom-jeans_south bottom-jeans_north
   cd parts && python3 process.py layers && python3 process.py export
   cd ../v2 && python3 pack_v2.py
   ```
   `process.py layers`·`export`는 `work/base_<dir>.png`(기본 몸 정합 결과)가 있어야 합니다. 새 작업 폴더라면 먼저 기본 몸을 생성·정합합니다: `gen.py --config parts/spec.json base_south base_north` → `process.py base`. 기본 몸을 다시 생성하면 **모든 옷을 다시 생성**해야 합니다(옷은 기본 몸 위에 그려지므로).
3. 확인: `parts/export/runtime_preview_south.png`(게임과 같은 방식으로 겹친 결과)와 `process.py combos` → `out/combos_<dir>.png`.

**옷 생성 프롬프트(자동)**: 역할 = "Image 1 is the EDIT TARGET: a sheet of 10 frames of the SAME base character on a transparent background. Edit Image 1: paint ONLY the described garment onto every figure, fitted naturally to each pose; keep EVERYTHING else exactly as in Image 1 …", 주제 = "TOP GARMENT ONLY: <묘사>. Paint it over the grey base shirt only; do not change the legs, shoes or head. <방향>".

### 6.3 옷 레이어 추출 규칙(`process.py layers`)
- 시트 전체 정합(배율·이동) → 칸마다 이동 재정합.
- 각 픽셀을 가장 가까운 마네킹 파트(몸통·팔 = 상의 영역, 다리 = 하의 영역)로 나눈다.
- **옷 색 모델**: 확실히 바뀐 픽셀(색 차 > 80)로 옷 팔레트(16색)를 만들고, 내 영역의 픽셀이 그 자리 기본 몸 색보다 옷 팔레트에 가까우면 옷으로 본다(라벤더-회색처럼 차이가 작은 색도 잡힘).
- 남의 영역·몸 밖은 크게 바뀌고(색 차 > 110) 내 영역의 옷과 이어진 덩어리만(긴 밑단·치마). 머리 중심보다 위로는 뻗지 않는다.
- 구멍 메우기, 옷에 붙은 어두운 외곽선 포함, 민머리 턱 외곽선 제외. 내보낼 때 작은 구멍을 한 번 더 메우고 불투명 판정을 70/255로 낮춰 레이어 경계 틈을 막는다.

### 6.4 머리 추가
머리 시트 1장 = 스타일 4종(2×2칸, 칸마다 앞·뒤). 현재 `HAIR`의 id `0`~`3`이 시트 한 장을 다 쓴다.
- **스타일 교체**: `HAIR`의 묘사를 바꾸고 `gen.py --config parts/spec.json --force heads` → `process.py layers` → `export` → `pack_v2.py`.
- **5종 이상으로 늘리기**: 지금 `process.py`·`template.py`는 머리 시트 1장만 다룬다. 시트를 여러 장 받으려면 `template.heads()`의 칸 번호(`style`)에 시트 번호를 더하고, `stage_layers`가 `heads`, `heads2`…를 차례로 처리하도록 확장한다(코드 수정 필요).
- 머리는 v2 캐릭터와 크기를 맞추려 1.08배(`HEAD_SCALE`)로 붙이고, 턱(뒷모습은 목덜미)을 마네킹 구 아랫면에 맞춘다. 바깥 1px 테두리는 외곽선 색 하나로 통일한다(반투명 가장자리의 보라 후광 제거).

### 6.5 게임·서버
- 저장: `avatar_profiles.parts`(서버가 `shared/avatar-parts.json` 목록으로 검증). 메시지 `{type:'avatar_parts', parts:{hair,top,bottom}|null}`.
- UI: 내 상태 패널의 접이식 "옷 갈아입기". 목록·이름은 묶기 결과(`overrides.parts`)에서 자동으로 나온다.
- 파트 프레임은 게임이 쓰는 4가지 동작(대기·걷기·앉기·타이핑)만 있다. 다른 동작을 추가하려면 `template.FRAMES`에 칸을 늘리고(시트 칸 수가 바뀌므로 기본 몸·옷을 모두 다시 생성) `process.STATES`에 상태를 추가한다.

---

## 7. 완성형 캐릭터 동작(프리셋)

외형 16칸 = 프리셋 4종(p0~p3) × 색 4종. 동작마다 남·북 스트립을 생성합니다. 새 외형은 §6을 쓰고, 이 절은 프리셋의 **동작을 추가**할 때 씁니다.

1. 마네킹 자세: `v2/blockout.py`의 `CLIPS`(기본 4종) 또는 `POSES`(몸짓 등). 팔다리는 엉덩이·어깨에서 **기울어진 상자**(`mannequin_walk`의 `rod`)로 만든다 — 상자째 옮기면 AI가 다리가 몸에서 떨어진 그림을 그린다.
2. 명세: `v2/make_spec.py`의 `CLIPTXT`/`ACTIONS`(프레임 순서·동작을 영어로 적는다). 프리셋마다 `clip()`으로 생성되고 `refs`로 프리셋 아이덴티티 그림을 준다.
3. 빌드: `python3 build.py <id>…` → 품질 검사(`iou` ≥ 0.60, 발 흔들림 ≤ 2px, 키 = 마네킹 −1~+4px, 방향 = 머리 피부색 비율 급변 없음). 이어서 `NOBIS_DENSITY=2 python3 build.py <id>…` — 끝에 색 교체(`recolor`)가 프리셋 전체에 다시 적용된다.
4. 게임 상태로 쓰려면 `pack_v2.py`의 `STATES`(`'<게임 상태>': ('<클립 이름>', 프레임 수)`)와 `frontend/src/game/visual/manifest.json`의 `avatar.animations`(fps·프레임 수).

**색 교체**: `build.py`의 `TOP_HUE`(프리셋별 교체 대상 색상 범위·채도·명도)와 `standard.py`의 `RAMPS`. 바지 등 다른 옷이 같은 색상 범위에 걸리면 명도 하한을 올린다(p0: 0.40).

---

## 8. 테스트와 확인

```bash
cd NOBIS-office/frontend
npm test                                  # 아틀라스 무결성·메모리 예산(48MB)·프레임 완전성(가구 카탈로그 전 회전, 캐릭터 16칸, 옷 파트)
npx playwright test lobby-assets seats wardrobe display   # 화면 확인(스크린샷은 docs/에 저장되므로 커밋 전에 되돌린다)
cd ../backend && ../.venv/bin/python -m pytest -q tests/test_seats.py tests/test_avatar_parts.py
```
- 새 가구가 카탈로그에 있으면 `visual.test.ts`가 전 회전 프레임을 검사한다.
- 화면에서 볼 때는 배율 4(그림 1px = 장치 2px)로 확인한다.

---

## 9. 지금까지 배운 것(되풀이하지 않기)

| 증상 | 원인 | 규칙 |
|---|---|---|
| 각도가 틀어지거나 비대칭 | 자유 생성 | 반드시 블록아웃을 편집 대상으로 생성하고, 묘사는 덩어리 순서대로 |
| 흐릿함 | 1/8 평균 축소 + 큰 화면 배율 | 2배 밀도(1/4 축소). 격자 고정 재생성·후처리 선명화는 디테일 손실로 기각 |
| 다리가 몸에서 떨어진 걷기 | 다리 상자를 평행 이동한 마네킹 | 엉덩이에서 회전하는 기울어진 상자 |
| 생성 그림 윗부분 잘림 | 블록아웃이 캔버스 위 끝에 닿음 | 1×1 가구 높이 2.3m 이하 |
| 촘촘한 줄무늬 바닥 | 2배 텍셀로 투영 | 바닥은 1배 텍셀 |
| 문 둘레만 다른 벽 | 모든 출구 문이 기본 벽 문 하나 | 문은 붙을 벽을 참고로 벽 테마별 생성 |
| 참고 없이 생성됨 | 잘못된 참고 경로 | 경로는 명세 폴더 기준. 생성기가 없으면 멈춤 |
| 저장 실패를 성공으로 처리 | 예전 파일이 남아 있음 | 다시 생성 전 파일 삭제(생성기가 처리) |
| 옷 레이어 구멍·회색 띠 | 색 차만으로 옷 판정 | 옷 색 모델 + 내 영역 규칙(§6.3) |
| 머리 둘레 보라 후광 | 반투명 가장자리 | 바깥 1px 외곽선 색 통일 |
| 키가 튐(대기보다 큰 걷기) | 생성 편차 | 키 검사 경계값이면 한 번 더 생성해 대기 동작과 키를 맞춘다 |

---

## 10. AI 에이전트에게 맡길 때

아래처럼 요청하면 이 문서만으로 작업할 수 있습니다.

> `NOBIS-office/docs/asset-authoring.md`를 따라 **[에셋 종류]**를 추가해 줘.
> - 이름(id): `[영문 소문자]`, 화면 이름: `[한국어]`
> - 모양·재질·색: `[묘사]`
> - (가구) 크기 `[W×H]`, 회전 `[가능/불가]`, 높이 약 `[m]`, 앉을 수 있음 `[예/아니오]`, 배치할 곳 `[방·좌표 또는 상점]`
> - (옷) 상의/하의, (머리) 교체할 칸 번호
> 생성 → 1배 품질 검사 → 2배 밀도 → 묶기 → 연결 → `npm test`까지 하고, 품질 검사 결과와 게임 화면 캡처를 보여 줘.

작업이 끝나면 확인할 것: `qa.md`에서 새 id가 모두 통과, `npm test` 통과, 게임 화면 캡처(배율 4), 테스트가 바꾼 `docs/*.png`는 되돌리기.
