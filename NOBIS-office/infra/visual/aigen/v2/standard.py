"""NOBIS 비주얼 표준 v2 수치 (docs/visual-standard-v2.md §2, §3, §8).

모든 블록아웃·정규화·QA·합성 스크립트가 이 값만 참조한다.
좌표: 1타일 = 1m, 화면 x = (x-y)*32, y = (x+y)*16 - z*32 (1x).
"""

TILE_W, TILE_H = 64, 32
PX_PER_M = 32                      # 높이 1m = 32px
ISO_DEG = 26.565                   # 2:1 다이메트릭
GEN_SCALE = 8                      # 블록아웃·생성 배율 (1x → 8x)

FURNITURE_FRAME = (128, 160)
FURNITURE_ANCHOR = (64, 104)       # 원점 타일 중심
AVATAR_FRAME = (48, 64)
AVATAR_FOOT = (24, 58)             # 서 있는 발 / 앉은 경우 좌석 타일 중심 바닥점
AVATAR_STAND_PX = 54               # 서 있는 전신 높이 (결정 4)
AVATAR_HEAD_RATIO = 0.40           # 머리 = 전신의 40% (결정 4)
SEAT_HEIGHT_PX = 12                # 표준 좌석 높이 0.375m. 앉은 엉덩이(좌석+허벅지 0.10) = 서 있는 엉덩이(다리 0.46)가 되도록 치비 다리에 맞춤.
                                   # 실측 기준 0.46m(15px)를 쓰면 앉은 키가 선 키보다 커짐

# 결정 1: 위쪽 광원, 측면 대칭 → 좌우 반전 허용. 블록아웃 면 톤
SHADE = {'top': 214, 'side': 158}  # +x면과 +y면 같은 톤
SIDE_SHADE_TOLERANCE = 0.08        # QA: 두 측면 평균 밝기 차 허용치(상대)

# 깊이 규칙 v2 (§2.4)
DEPTH = {'lower': -0.15, 'stand': 1.0, 'seated': 0.10, 'upper': 0.20}

# QA 게이트 (§4)
QA = {'angle_tol_deg': 1.5, 'iou_min': 0.85, 'iou_min_organic': 0.60, 'foot_jitter_px': 1,
      'stand_height_tol_px': 2, 'hair_allowance_px': 4, 'max_colors': 48}  # 키: 마네킹 -1 ~ +4px(머리카락 볼륨)

# 프리셋 팔레트 램프 (결정 2: 프리셋 전신 + 색 교체). 이름: 밝음→어두움
RAMPS = {
    'hair': {'black': ['#5a5266', '#3b3447', '#272033', '#17121f'],
             'blonde': ['#f6dc9b', '#e2b96a', '#b98a45', '#86602e'],
             'chestnut': ['#a8705a', '#7d4c3c', '#5a3328', '#3a2019'],
             'rose': ['#f2b3c4', '#d98aa3', '#b0647f', '#7d425a']},
    'top': {'lavender': ['#d9c8f0', '#b49ad6', '#8a70b3', '#5e4a85'],
            'mint': ['#cdeedd', '#9fd6bc', '#6fb397', '#467f69'],
            'peach': ['#ffe0c7', '#f5b98f', '#d98d63', '#a3603f'],
            'sky': ['#d3e7fb', '#a3c8ee', '#7099c9', '#4a6c99']},
}
