# AI 에셋 생성 파이프라인

에셋을 추가하는 절차·프롬프트 템플릿·품질 기준은 [`docs/asset-authoring.md`](../../../docs/asset-authoring.md)에, 수치와 결정의 근거는 [`docs/visual-standard-v2.md`](../../../docs/visual-standard-v2.md)에 있습니다.
이 폴더는 그 표준을 따라 Codex 내장 `image_gen`(imagegen 스킬)으로 에셋을 생성하고, 게임 프레임으로 정규화하고, 품질 검사를 돌리고, 아틀라스로 묶는 도구입니다.

## 구성

| 경로 | 내용 |
|---|---|
| `gen.py` | Codex `image_gen` 호출기. 명세의 에셋마다 1장(약 1분). 참고 이미지가 없으면 생성 전에 멈추고, 다른 경로에 저장된 결과는 세션 폴더에서 회수 |
| `normalize.py` | 축소(`pixelize`) |
| `refs/style-office.png` | 스타일 기준 그림 |
| `raw/char_a.png`, `raw/wall_plain.png` | 캐릭터 p0·기본 벽 참고 원본 |
| `preview/` | 표준 문서가 근거로 참조하는 그림 3장 |
| `v2/standard.py` | 모든 수치의 정본(타일, 프레임, 좌석 12px, 치비 비례, 깊이, 품질 기준, 옷 색 램프) |
| `v2/blockout.py` | 미터 치수 → 정확한 2:1 블록아웃(생성 가이드) + 파트·면 마스크 |
| `v2/make_spec.py` → `v2/spec.json` | 가구·텍스처·캐릭터 생성 명세(프롬프트) |
| `v2/build.py` | 정합, 측면 밝기 맞춤, 축소, upper 분리, 클립 자르기, 옷 색 교체, 품질 검사(`qa.md`·`qa.json`). `NOBIS_DENSITY=2`면 2배 밀도(`norm_d2/`) |
| `v2/pack_v2.py` | 게임 연결: `frontend/public/visual/aigen-v2-*`(2048 한도 여러 장)와 `frontend/src/game/visual/overrides.json` |
| `v2/scene.py` | 게임과 같은 좌표·깊이로 합성한 미리보기(`v2/preview/`) |
| `v2/norm_d2/` | 2배 밀도 프레임 = 아틀라스의 원본 |
| `v2/raw/` | AI 원본 중 다음 생성의 참고로 쓰는 것(`.gitignore` 예외 목록) |
| `parts/` | 옷 갈아입기 파트: `template.py`(잠긴 템플릿), `make_spec.py`(옷·머리 목록), `process.py`(정합·레이어·내보내기), `export/`(HD 파트 프레임) |

## 자주 쓰는 명령

```sh
cd NOBIS-office/infra/visual/aigen
python3 v2/blockout.py <id ...>                          # 블록아웃(저장소에는 포함하지 않음)
python3 v2/make_spec.py                                  # v2/spec.json 갱신
python3 gen.py --config v2/spec.json --jobs 4 <id ...>   # 생성(Codex CLI 로그인 필요)
cd v2 && python3 build.py <id ...>                       # 1배 정규화 + 품질 검사
NOBIS_DENSITY=2 python3 build.py <id ...>                # 2배 밀도(정합값은 qa.json 재사용)
python3 pack_v2.py                                       # 아틀라스·overrides(게임 반영)

cd ../parts && python3 make_spec.py                      # 옷·머리 명세
python3 ../gen.py --config spec.json <id ...>            # 옷 시트 생성(경로는 명세 폴더 기준)
python3 process.py layers && python3 process.py export   # 레이어 → HD 파트 프레임
```

zsh에서 id 목록을 변수 하나로 넘기지 마세요(`$W`가 단어별로 나뉘지 않아 아무것도 빌드되지 않습니다).
