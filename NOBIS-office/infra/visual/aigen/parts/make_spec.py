#!/usr/bin/env python3
"""옷 갈아입기 파트 생성 명세(spec.json) 만들기 — docs/asset-authoring.md §6.

옷·머리를 추가하려면 아래 TOPS / BOTTOMS / HAIR에 한 줄을 더하고 이 스크립트를 다시 실행한다.
id는 영문 소문자(파일·프레임 이름에 그대로 쓰인다), 값은 (화면 이름, 영어 묘사).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

TOPS = {
    'cardigan': ('라벤더 가디건', "a soft lavender cardigan worn open over a white collared shirt, long sleeves to the wrists"),
    'hoodie': ('네이비 후드티', "a navy blue pullover hoodie with white drawstrings and a front pocket, long sleeves to the wrists"),
}
BOTTOMS = {
    'chino': ('베이지 치노', "beige chino trousers to the ankles (replace the grey leggings)"),
    'skirt': ('네이비 플리츠 치마', "a navy pleated knee-length skirt with black tights below it (replace the grey leggings)"),
}
# 머리 시트 1장 = 스타일 4칸(2×2). 칸 순서: 1줄 왼쪽, 1줄 오른쪽, 2줄 왼쪽, 2줄 오른쪽. id는 칸 번호
HAIR = {
    '0': ('짧은 갈색 머리', "short tousled brown hair"),
    '1': ('갈색 포니테일', "long brown hair in a low ponytail with side-swept bangs"),
    '2': ('검은 단발+안경', "black bowl-cut hair with thin round glasses (glasses only on the front view)"),
    '3': ('주황 웨이브 단발', "wavy shoulder-length orange-brown bob"),
}

COMMON = {
    "part": "Use case: stylized-concept\nAsset type: character sprite SHEET for a 2:1 isometric pixel-art office game (paper-doll part system): 10 animation frames of ONE character in a fixed 5x2 grid\nStyle/medium: crisp pixel art in the style of Image 2 (style only, do not copy its characters): clean chunky pixels, one-art-pixel dark plum outline, 3-tone cel shading per material, cozy pastel palette, no dithering, no gradients, no blur; chibi proportions exactly as the mannequins\nLighting: soft light from DIRECTLY ABOVE; the two visible side faces share the SAME mid tone. No cast shadows.\nComposition/framing: exactly one painted figure over each grey mannequin of Image 1: same size, same foot position, same pose, same facing; keep the 5x2 grid, the spacing and every figure position EXACTLY. The tiny box on a head marks where the face points; do not draw it as an object.\nBackground: fully transparent background (alpha). If transparency is impossible, use a perfectly flat solid #00ff00 background.\nAvoid: chairs, desks, props, text, numbers, frame borders, ground, shadows, extra figures",
    "parthead": "Use case: stylized-concept\nAsset type: character sprite SHEET for a 2:1 isometric pixel-art office game (paper-doll part system): 8 head sprites (4 hairstyles x 2 views) in a fixed 4x2 grid\nStyle/medium: crisp pixel art in the style of Image 2 (style only, do not copy its characters): clean chunky pixels, one-art-pixel dark plum outline, 3-tone cel shading per material, cozy pastel palette, no dithering, no gradients, no blur; chibi proportions exactly as the mannequins\nLighting: soft light from DIRECTLY ABOVE; the two visible side faces share the SAME mid tone. No cast shadows.\nBackground: fully transparent background (alpha). If transparency is impossible, use a perfectly flat solid #00ff00 background.\nAvoid: bodies, necks, props, text, numbers, frame borders, ground, shadows, extra figures"
}
DIR = {'south': "every figure faces the LOWER-LEFT (front three-quarter view)",
       'north': "every figure faces away toward the UPPER-RIGHT (back three-quarter view)"}
FRAMES = ("Frames left to right, top row then bottom row: 1-2 standing idle, 3-6 walking (both legs attached at the hips, swinging from the hip joint), "
          "7-8 seated idle in the air at chair height with hands on the thighs, 9-10 seated typing with forearms forward")
BASE = ("BASE BODY for a paper-doll system, the SAME plain mannequin-like person in all 10 frames: light peach skin; a completely BALD smooth round head with NO hair and NO face features "
        "(a separate head sprite will cover it); a plain tight light-grey long-sleeve base shirt; plain tight mid-grey leggings to the ankles; simple dark-brown shoes. Nothing else.")
GARMENT_ROLE = ("Image 1 is the EDIT TARGET: a sheet of 10 frames of the SAME base character on a transparent background. Edit Image 1: paint ONLY the described garment onto every figure, "
                "fitted naturally to each pose; keep EVERYTHING else exactly as in Image 1: the bald head, skin, hands, the other clothes, shoes, every pose and position, the grid and the transparent background. "
                "Image 2 is a STYLE REFERENCE ONLY.")
HEAD_ROLE = ("Image 1 is the EDIT TARGET: 8 grey head spheres in a 4x2 grid on a transparent background (a tiny box marks where the face points; do not draw it). "
             "Edit Image 1: paint a chibi head (face and hair) over each sphere at EXACTLY the same size and position; hair may extend at most 10% beyond the sphere outline; no neck, no body, no shoulders. "
             "Image 2 is a STYLE REFERENCE ONLY (match its skin tone, outline and face style).")


def head_subject():
    h = list(HAIR.values())
    return ("4 hairstyles, each painted twice side by side: odd columns = front three-quarter view facing the LOWER-LEFT with the face visible "
            "(simple dark eyes, tiny mouth, light peach skin); even columns = back three-quarter view facing away to the UPPER-RIGHT (back of the head, no face). "
            f"Row 1, columns 1-2: {h[0][1]}. Row 1, columns 3-4: {h[1][1]}. Row 2, columns 1-2: {h[2][1]}. Row 2, columns 3-4: {h[3][1]}.")


def main():
    assets = [{'id': f'base_{d}', 'type': 'part', 'guide': f'template/body_{d}.png', 'size': '1536x1024', 'subject': f"{BASE} {DIR[d]}. {FRAMES}."} for d in DIR]
    for d in DIR:
        for k, (_, v) in TOPS.items():
            assets.append({'id': f'top-{k}_{d}', 'type': 'part', 'guide': f'work/base_{d}.png', 'size': '1536x1024', 'roles': GARMENT_ROLE,
                           'subject': f"TOP GARMENT ONLY: {v}. Paint it over the grey base shirt only; do not change the legs, shoes or head. {DIR[d]}."})
        for k, (_, v) in BOTTOMS.items():
            assets.append({'id': f'bottom-{k}_{d}', 'type': 'part', 'guide': f'work/base_{d}.png', 'size': '1536x1024', 'roles': GARMENT_ROLE,
                           'subject': f"BOTTOM GARMENT ONLY: {v}. Do not change the shirt, arms, hands or head. {DIR[d]}."})
    assets.append({'id': 'heads', 'type': 'parthead', 'guide': 'template/heads.png', 'size': '1536x1024', 'roles': HEAD_ROLE, 'subject': head_subject()})
    labels = {'top': {k: v[0] for k, v in TOPS.items()}, 'bottom': {k: v[0] for k, v in BOTTOMS.items()}, 'hair': {k: v[0] for k, v in HAIR.items()}}
    spec = {'styleRef': 'template/style-ref.png', 'rawDir': 'raw', 'common': COMMON, 'labels': labels, 'assets': assets}
    (HERE / 'spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    print(len(assets), 'assets')


if __name__ == '__main__':
    main()
