#!/usr/bin/env python3
"""스타일 보드 v2 생성 설정(spec.json)을 만든다. 표준 v2 결정(위쪽 광원·대칭 측면, 치비 40%, 좌석 12px)을 프롬프트에 고정.

phase A: 기준 뷰(가구 앞/한쪽, 텍스처, 새 프리셋 턴어라운드, 기존 프리셋 클립)
phase B: A 결과를 '같은 디자인' 레퍼런스로 받는 반대 뷰·새 프리셋 클립
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIGHT = ("Lighting: soft light from DIRECTLY ABOVE. Top faces are the brightest; the two visible side faces share the SAME mid tone "
         "(symmetric shading, because the sprite will also be used horizontally mirrored). No cast shadows.")
PIXEL = ("Style/medium: crisp pixel art in the style of Image 2 (style only, do not copy its content): clean chunky pixels, "
         "one-art-pixel dark plum outline, 3-tone cel shading per material, cozy pastel palette, no dithering, no gradients, no blur")
COMMON = {
    'gprop': "\n".join([
        "Use case: stylized-concept",
        "Asset type: furniture sprite for a 2:1 isometric pixel-art office game; it will be downscaled exactly 8x to final pixel art",
        PIXEL, LIGHT,
        "Background: fully transparent background (alpha). If transparency is impossible, use a perfectly flat solid {key} background.",
        "Avoid: floor, ground plane, grid, shadows on the ground, text, letters, numbers, logos, people, extra objects, any change of camera angle"]),
    'gclip': "\n".join([
        "Use case: stylized-concept",
        "Asset type: character animation strip for a 2:1 isometric pixel-art office game; every figure will be downscaled exactly 8x into a 48x64 px frame",
        PIXEL + "; chibi proportions exactly as the mannequin (cube-like big head = 40% of height, short legs)", LIGHT,
        "Composition/framing: one painted figure exactly over each grey mannequin of Image 1 (same size, same foot position, same pose, same facing). "
        "The tiny box on a mannequin's head marks where the FACE points; do not draw it as an object. Frames read left to right. "
        "The head (including hair) must exactly fill the mannequin's sphere head: do not enlarge the head or add big hair volume; keep the same head size in every frame.",
        "Background: fully transparent background (alpha). If transparency is impossible, use a perfectly flat solid {key} background.",
        "Avoid: extra figures, chairs, desks, props, text, numbers, frame borders, ground, shadows, changing outfit or hairstyle between frames"]),
    'texture': "\n".join([
        "Use case: stylized-concept",
        "Asset type: tileable game texture that will be projected onto isometric floor geometry",
        "Style/medium: crisp pixel art matching the palette and material rendering of Image 1 (reference only): clean flat colors, subtle 2-3 tone variation, no noise, no dithering",
        "Composition/framing: perfectly flat orthographic top view, NO perspective, edge to edge, no border",
        "Avoid: perspective, shadows, text, logos, watermark, furniture, people"]),
}
SAME_OBJ = "Image 3 is the OBJECT IDENTITY reference: paint the SAME object design, materials and colors, now seen from the other side as the blockout shows."
SAME_CHR = "Image 3 is the CHARACTER IDENTITY reference: keep exactly the same hair, face, clothes and colors."

A, B = [], []


def prop(id_, guide, subject, key='#00ff00', refs=None, phase=A):
    e = {'id': id_, 'kind': 'furniture', 'type': 'gprop', 'guide': f'blockout/{guide}.png', 'key': key, 'subject': subject}
    if refs:
        e.update(refs=refs, refRole=SAME_OBJ)
    phase.append(e)


def clip(id_, guide, subject, refs=None, phase=A, key='#00ff00'):
    e = {'id': id_, 'kind': 'avatar', 'type': 'gclip', 'guide': f'blockout/{guide}.png', 'size': '1536x1024', 'key': key, 'subject': subject}
    if refs:
        e.update(refs=refs, refRole=SAME_CHR)
    phase.append(e)


prop('desk_r0', 'desk_r0', "office work desk: the big slab = warm peach wooden desktop; left block = wooden side-panel leg; right box = cream 3-drawer cabinet "
     "(drawers face lower-left); thin back panel = peach modesty panel; thin upright panel = dark monitor whose SCREEN faces lower-left showing bright green code "
     "lines, on a small grey stand; flat strip = light grey keyboard; small box on the right = a row of 5 colorful books")
prop('desk_r180', 'desk_r180', "the SAME desk seen from the opposite side: the big slab = the same peach desktop; left box = the cream drawer cabinet seen from its plain back; "
     "right block = the wooden side-panel leg; the panel facing us = the peach modesty panel; the upright panel = the BACK of the dark monitor (plain grey back, no screen visible); "
     "flat strip = keyboard on the far side; small box = the same colorful books", refs=['raw/desk_r0.png'], phase=B)
prop('chair_n', 'chair_n', "lavender office swivel chair seen from BEHIND: the upright panel nearest to us = the padded backrest seen from its back, with a small grey support bar; "
     "slab = seat cushion; post = chrome gas lift; cross = five-star base with small dark wheels")
prop('chair_s', 'chair_s', "the SAME lavender office chair seen from the FRONT: the upright panel at the back = the backrest showing its cushioned front; slab = seat cushion facing us; "
     "post = chrome gas lift; cross = five-star base with small dark wheels", refs=['raw/chair_n.png'], phase=B)
prop('sofa_s', 'sofa_s', "cozy mustard-yellow two-seat sofa seen from the FRONT: long back slab = backrest with two soft back cushions; front slab = two seat cushions; "
     "end blocks = rounded armrests; tiny dark wooden legs", key='#ff00ff')
prop('sofa_n', 'sofa_n', "the SAME mustard sofa seen from BEHIND: the tall slab nearest to us = the plain fabric BACK of the backrest; seat cushions barely visible behind it; "
     "armrests at both ends; tiny dark wooden legs", key='#ff00ff', refs=['raw/sofa_s.png'], phase=B)
prop('plant', 'plant', "lush potted areca palm: bottom box = round cream ceramic pot; the upper volume = bushy bright green fronds (organic leafy silhouette that may "
     "spill a little outside the box)", key='#ff00ff')
A.append({'id': 'floor_wood', 'kind': 'floor', 'type': 'texture', 'size': '1024x1024',
          'subject': "a single square patch of light oak floor seen straight from above: 4 planks running vertically, DESATURATED warm beige-brown (not orange), "
                     "subtle grain, thin darker seams; seamless when repeated"})

P0 = "the character from Image 3 (brown short hair, white shirt, lavender cardigan, dark grey trousers, brown shoes)"
P1 = ("young woman office worker: long dark brown hair tied in a low ponytail, mint green blouse, navy knee-length skirt, dark tights, black flat shoes")
CLIPTXT = {
    'idle_s': "2-frame IDLE breathing loop of {who}, standing, facing the LOWER-LEFT (front three-quarter view); frame 2 = body 1 pixel higher",
    'idle_n': "2-frame IDLE breathing loop of {who}, standing, seen from BEHIND facing the UPPER-RIGHT (back three-quarter view, back of the head visible); frame 2 = body 1 pixel higher",
    'walk_s': "4-frame WALK cycle of {who} walking toward the LOWER-LEFT (front three-quarter view): 1 left leg forward, 2 passing, 3 right leg forward, 4 passing; arms swing opposite to legs; both legs stay attached at the hips and swing from the hip joint as straight diagonal limbs exactly like the mannequin (trousers/skirt continuous from the waist, no gap between body and legs, small natural stride)",
    'walk_n': "4-frame WALK cycle of {who} walking away toward the UPPER-RIGHT (back three-quarter view, back of the head visible): 1 left leg forward, 2 passing, 3 right leg forward, 4 passing; both legs stay attached at the hips and swing from the hip joint as straight diagonal limbs exactly like the mannequin (trousers/skirt continuous from the waist, no gap between body and legs, small natural stride)",
    'sittype_s': "2-frame SIT-AND-TYPE loop of {who} sitting on an invisible chair facing the LOWER-LEFT: thighs horizontal toward the viewer, forearms forward typing on an invisible keyboard; frame 2 = hands slightly moved. Paint ONLY the character",
    'sittype_n': "2-frame SIT-AND-TYPE loop of {who} sitting on an invisible chair seen from BEHIND facing the UPPER-RIGHT: back and back of the head visible, forearms forward typing; frame 2 = hands slightly moved. Paint ONLY the character",
}
GUIDE = {'idle_s': 'm_idle_south', 'idle_n': 'm_idle_north', 'walk_s': 'm_walk_south', 'walk_n': 'm_walk_north',
         'sittype_s': 'm_sit.type_south', 'sittype_n': 'm_sit.type_north'}
for k, txt in CLIPTXT.items():
    clip(f'p0_{k}', GUIDE[k], txt.format(who=P0), refs=['../raw/char_a.png'])
clip('p1_turn', 'm_turnaround', f"identity turnaround of a NEW chibi character: {P1}. LEFT figure = front three-quarter view facing the lower-left; "
     "RIGHT figure = back three-quarter view facing the upper-right (back of head and ponytail visible); both standing idle")
for k, txt in CLIPTXT.items():
    clip(f'p1_{k}', GUIDE[k], txt.format(who="the character from Image 3 (" + P1 + ")"), refs=['raw/p1_turn.png'], phase=B)

# ---- 데모 검증 배치(C: 기준 뷰, D: 레퍼런스 필요) ----
C, D = [], []
prop('desk_work_r0', 'desk_s1_r0', "office work desk: the big slab = warm peach wooden desktop; RIGHT block = wooden side-panel leg; LEFT box = cream 3-drawer cabinet "
     "(drawers face lower-left); thin back panel = peach modesty panel; thin upright panel = dark monitor whose SCREEN faces lower-left showing bright green code "
     "lines, on a small grey stand; flat strip = light grey keyboard; small box on the left = a row of 5 colorful books", phase=C)
prop('desk_work_r180', 'desk_s1_r180', "the SAME desk seen from the opposite side: the big slab = the same peach desktop; RIGHT box = the cream drawer cabinet seen from its plain back; "
     "LEFT block = the wooden side-panel leg; the panel facing us = the peach modesty panel; the upright panel = the BACK of the dark monitor (plain grey back, no screen visible); "
     "flat strip = keyboard on the far side; small box = the same colorful books", refs=['raw/desk_work_r0.png'], phase=D)
prop('armchair_s', 'armchair_s', "cozy mustard-yellow single armchair seen from the FRONT: back slab = padded backrest; front slab = one seat cushion; side blocks = rounded armrests; "
     "tiny dark wooden legs; same fabric and colors as a matching mustard two-seat sofa", key='#ff00ff', refs=['raw/sofa_s.png'], phase=C)
D.append(None)
prop('armchair_n', 'armchair_n', "the SAME mustard armchair seen from BEHIND: the tall slab nearest to us = the plain fabric BACK of the backrest; armrests on both sides; tiny dark legs",
     key='#ff00ff', refs=['raw/armchair_s.png'], phase=D)
D.remove(None)
SITIDLE = {'sitidle_s': ("2-frame SIT-AND-REST loop of {who} sitting relaxed on an invisible chair facing the LOWER-LEFT: thighs horizontal toward the viewer, "
                         "hands resting on the lap; frame 2 = body 1 pixel higher (breathing). Paint ONLY the character", 'm_sit.idle_south'),
           'sitidle_n': ("2-frame SIT-AND-REST loop of {who} sitting relaxed on an invisible chair seen from BEHIND facing the UPPER-RIGHT: back and back of the head visible, "
                         "hands on the lap; frame 2 = body 1 pixel higher. Paint ONLY the character", 'm_sit.idle_north')}
for k, (txt, g) in SITIDLE.items():
    clip(f'p0_{k}', g, txt.format(who=P0), refs=['../raw/char_a.png'], phase=C)
    clip(f'p1_{k}', g, txt.format(who="the character from Image 3 (" + P1 + ")"), refs=['raw/p1_turn.png'], phase=C)


# ---- 묶음 1: 건축 + 가구 (G: 기준 뷰·텍스처, H: 반대 뷰) ----
G, H = [], []
def tex(id_, subject, size='1024x1024', refs=None, role=None, phase=G, key=None):
    e = {'id': id_, 'kind': 'texture', 'type': 'texture', 'size': size, 'subject': subject}
    if refs: e.update(refs=refs, refRole=role)
    if key: e['key'] = key
    phase.append(e)

FLOOR = "a single square patch seen straight from above, seamless when repeated, muted pastel palette matching the reference"
tex('floor_meeting', f"{FLOOR}: soft blue-grey low-pile office carpet with a very subtle woven texture")
tex('floor_lounge', f"{FLOOR}: soft lavender plush carpet with a faint diamond weave")
tex('floor_grass', f"{FLOOR}: neat short rooftop-garden grass with a few tiny clover and darker blades, gentle green (not neon)")
tex('floor_deck', f"{FLOOR}: grey-brown outdoor wooden deck boards running vertically with small screw dots and thin gaps")
tex('floor_cafe', f"{FLOOR}: warm caramel herringbone wooden parquet")
WALL_ROLE = "Image 2 is the WALL DESIGN reference: keep exactly the same wall proportions, top cap, wainscot height and baseboard so segments line up."
tex('wall_cafe', "front elevation of an interior cafe wall, horizontally seamless: upper part warm cream plaster, lower third exposed red-brown brick, a thin cream top cap at the very top and a dark wooden baseboard; same proportions as Image 2", '1536x1024', ['../raw/wall_plain.png'], WALL_ROLE)
tex('wall_meeting', "front elevation of a meeting-room wall, horizontally seamless: upper part muted blue-grey painted wall, lower third light grey acoustic panels, thin cream top cap, grey baseboard; same proportions as Image 2", '1536x1024', ['../raw/wall_plain.png'], WALL_ROLE)
tex('railing', "front elevation of a low rooftop railing, horizontally seamless: light wooden top rail and slim dark metal balusters on a short concrete curb; EVERYTHING between the balusters and above the rail is fully transparent background (alpha)", '1536x1024', key='#00ff00')
DOOR_ROLE = "Image 2 is the WALL DESIGN reference: the wall around the door must match it exactly (lavender upper wall, cream wainscot, peach baseboard, cream top cap) so the segment replaces one wall segment seamlessly."
DOOR = ("front elevation (perfectly flat, no perspective) of ONE wall segment with ONE door in its exact horizontal center. The door is about 55% of the image width, "
        "its top at about 78% of the wall height, standing on the baseboard. The wall around the door matches Image 2. No text, no letters, no numbers. Door theme: ")
for k, theme in {'door_cafe': "warm wooden cafe door with a small striped awning above and a tiny coffee-cup icon plate",
                 'door_focus': "calm dark-navy door with a soft lamp above and a small monitor icon plate",
                 'door_meeting': "frosted glass door with a slim light-wood frame and a small two-people icon plate",
                 'door_lounge': "plum purple door with rounded top panel and a small sofa icon plate",
                 'door_garden': "sage green door with climbing vines and tiny flowers around the frame and a small leaf icon plate",
                 'door_terrace': "dusk-blue door with a small crescent moon and star icon plate and a little wall lantern",
                 'door_exit': "simple light-wood door with a small arrow-free exit icon plate (a door pictogram)"}.items():
    tex(k, DOOR + theme, '1024x1536', ['../raw/wall_plain.png'], DOOR_ROLE)

# 방 출구 문: 방 벽 테마별(문 둘레 벽이 그 방 벽과 같아야 한다). 난간 방(정원·테라스)은 벽 없는 정원 문
for k, (wall, role) in {'door_exitcafe': ('wall_cafe', "warm cream plaster upper wall, red-brown brick lower third, cream top cap, dark wooden baseboard"),
                        'door_exitmeeting': ('wall_meeting', "muted blue-grey upper wall, light grey acoustic panels on the lower third, cream top cap, grey baseboard")}.items():
    tex(k, DOOR.replace('The wall around the door matches Image 2.', f'The wall around the door matches Image 2 exactly ({role}).') + "simple light-wood door with a small exit icon plate (a door pictogram)",
        '1024x1536', [f'raw/{wall}.png'], "Image 2 is the WALL DESIGN reference: the wall around the door must match it exactly so the segment replaces one wall segment seamlessly.")
tex('door_gate', "front elevation (perfectly flat, no perspective) of ONE wall-segment-sized image for a rooftop garden: a door-height wooden garden ARCH GATE in the exact horizontal center: "
    "two square light-wood posts joined by a small arched wooden top, a light-wood slatted gate door between them with a small exit door pictogram plate; the gate is about 55% of the image width and its arched top is at about 78% of the image height (same size as a normal door), standing on the bottom edge. "
    "At both sides of the gate, short pieces of the railing from Image 2 at EXACTLY the same height as in Image 2: the railing occupies only the bottom 36% of the image height (its wooden top rail at 36% from the bottom). "
    "EVERYTHING else (sky above the railing, around and above the gate) is fully transparent background (alpha). No text, no letters, no numbers.",
    '1024x1536', ['raw/railing.png'], "Image 2 is the RAILING DESIGN reference: keep the same rail, balusters and curb so the side pieces line up with the railing.", key='#00ff00')

FURN = {
    'desk_small': ("small wooden side desk: peach wooden top, two slim side panels, a back modesty panel, an open light-grey laptop whose screen faces lower-left", "the SAME small desk seen from behind: the plain back modesty panel faces us, the laptop's grey back lid visible"),
    'bookshelf': ("tall wooden bookshelf with four shelves full of colorful book spines and one small plant, the open shelf side faces lower-left", "the SAME bookshelf seen from behind: plain wooden back panel"),
    'whiteboard': ("mobile whiteboard on two grey metal posts with feet: white board with a few yellow sticky notes and simple chart doodles (no readable text), marker tray in front", "the SAME whiteboard seen from behind: plain light-grey back of the board"),
    'computer': ("small computer stand table with a dark monitor showing a pastel dashboard (no readable text) facing lower-left and a slim keyboard", "the SAME computer stand seen from behind: dark plastic back of the monitor with a cable"),
    'coffee': ("cafe coffee counter: peach wooden cabinet with an espresso machine, a grinder and a few white cups on top, front panel faces lower-left", "the SAME coffee counter seen from the back: plain back panel, machines visible on top from behind"),
    'arcade': ("retro arcade cabinet: purple body with pastel side art, glowing pixel game screen and joystick panel facing lower-left", "the SAME arcade cabinet seen from behind: plain purple back with vent slots"),
    'bed_long': ("cozy single bed: light wooden frame, headboard at the far end, white pillow, lavender blanket folded toward the foot end which faces the viewer", "the SAME bed seen from the head end: the wooden headboard is nearest to us"),
    'daybed': ("compact daybed: light wooden base with a low padded back rest at the far side, cream mattress and a small lavender pillow", "the SAME daybed seen from the back: the padded back rest is nearest to us"),
}
for k, (front, back) in FURN.items():
    prop(f'{k}_s', f'{k}_s', front, phase=G)
    prop(f'{k}_n', f'{k}_n', back, refs=[f'raw/{k}_s.png'], phase=H)
prop('lamp', 'lamp', "floor lamp: round brass base, slim brass pole, cream drum lampshade glowing softly", phase=G)
prop('table_round', 'table_round', "small ROUND cafe table (the square top is a round tabletop seen in isometric): light wood top, single slim pedestal and round foot", phase=G)
prop('meeting_table', 'meeting_table', "long rectangular meeting table: light oak tabletop with rounded corners, two sturdy dark pedestal bases; tabletop empty except a small cable tray in the middle", phase=G)
prop('rug', 'rug', "ROUND woven rug lying flat on the floor (an ellipse inside the diamond): warm beige with a soft pink border ring", key='#00ff00', phase=G)
prop('cat_bed', 'cat_bed', "round lavender pet cushion with an orange-and-white cat sleeping curled up on it", phase=G)
prop('home_portal', 'home_portal', "freestanding entrance door to a personal home in a cozy office lobby: cream wooden door frame, soft lavender-purple door with a small brass knob, a little warm-yellow name plate near the top of the door, a plum doormat in front", phase=G)
prop('column', 'column', "slim interior column: cream plaster shaft with a simple lavender capital and plinth", phase=G)

# ---- 묶음 2: 캐릭터 (J: 새 프리셋 턴어라운드, K: 동작 클립 전량) ----
J, K = [], []
PRESET = {
    'p0': ("the character from Image 3 (brown short hair, white shirt, lavender cardigan, dark grey trousers, brown shoes)", '../raw/char_a.png'),
    'p1': ("the character from Image 3 (" + P1 + ")", 'raw/p1_turn.png'),
    'p2': ("the character from Image 3 (young man, short black hair, round glasses, navy hoodie, light grey trousers, white sneakers)", 'raw/p2_turn.png'),
    'p3': ("the character from Image 3 (young woman, wavy auburn shoulder-length hair, cream knit sweater, olive skirt, brown boots)", 'raw/p3_turn.png'),
}
clip('p2_turn', 'm_turnaround', "identity turnaround of a NEW chibi character: young man, short black hair, round glasses, navy hoodie, light grey trousers, white sneakers. "
     "LEFT figure = front three-quarter view facing the lower-left; RIGHT figure = back three-quarter view facing the upper-right; both standing idle", phase=J)
clip('p3_turn', 'm_turnaround', "identity turnaround of a NEW chibi character: young woman, wavy auburn shoulder-length hair, cream knit sweater, olive skirt, brown boots. "
     "LEFT figure = front three-quarter view facing the lower-left; RIGHT figure = back three-quarter view facing the upper-right; both standing idle", phase=J)
FACE = {'s': "facing the LOWER-LEFT (front three-quarter view)", 'n': "seen from BEHIND facing the UPPER-RIGHT (back of the head visible)"}
ACTIONS = {
    'sit.talk': "2-frame SIT-AND-TALK loop: {who} sitting on an invisible chair {face}, one hand gesturing while talking, the other hand on the lap",
    'sit.relax': "1 frame: {who} leaning back RELAXED on an invisible sofa {face}, arms resting on invisible armrests, legs stretched forward",
    'sit.drink': "3-frame SIT-AND-DRINK: {who} sitting on an invisible chair {face}, lifting a small white coffee cup from the lap (1) to chest (2) to the mouth (3)",
    'stand.drink': "3-frame STAND-AND-DRINK: {who} standing {face}, lifting a small white coffee cup from waist (1) to chest (2) to the mouth (3)",
    'stand.read': "2-frame READING loop: {who} standing {face}, holding an open book with both hands at chest height; frame 2 head tilted slightly down",
    'stand.present': "2-frame PRESENTING loop: {who} standing {face}, one arm raised pointing up and forward as if presenting a whiteboard",
    'stand.play': "2-frame ARCADE PLAYING loop: {who} standing {face}, both hands forward at waist height on invisible arcade controls, small hand movement",
    'gesture.wave.stand': "3-frame WAVE gesture: {who} standing {face}, one hand raised high above the head waving side to side",
    'gesture.nod.stand': "2-frame NOD gesture: {who} standing {face}; frame 2 head nods down",
    'gesture.clap.stand': "3-frame CLAP gesture: {who} standing {face}, hands apart (1), clapped together in front of the chest (2), apart (3)",
    'gesture.cheer.stand': "3-frame CHEER gesture: {who} {face}, arms down (1), both arms raised high with a small jump (2), arms still up landing (3)",
    'gesture.thumbsup.stand': "2-frame THUMBS-UP gesture: {who} standing {face}, one fist forward with the thumb up",
    'gesture.wave.sit': "3-frame WAVE gesture: {who} sitting on an invisible chair {face}, one hand raised high waving side to side",
    'gesture.nod.sit': "2-frame NOD gesture: {who} sitting on an invisible chair {face}; frame 2 head nods down",
    'gesture.clap.sit': "3-frame CLAP gesture: {who} sitting on an invisible chair {face}, hands apart, clapped together, apart",
    'gesture.cheer.sit': "3-frame CHEER gesture: {who} sitting on an invisible chair {face}, arms down then both arms raised high",
    'gesture.thumbsup.sit': "2-frame THUMBS-UP gesture: {who} sitting on an invisible chair {face}, one fist forward with the thumb up",
}
BASE = {'idle_s': CLIPTXT['idle_s'], 'idle_n': CLIPTXT['idle_n'], 'walk_s': CLIPTXT['walk_s'], 'walk_n': CLIPTXT['walk_n'],
        'sittype_s': CLIPTXT['sittype_s'], 'sittype_n': CLIPTXT['sittype_n']}
for pid, (who, ref) in PRESET.items():
    if pid in ('p2', 'p3'):
        for k, txt in BASE.items():
            clip(f'{pid}_{k}', GUIDE[k], txt.format(who=who), refs=[ref], phase=K)
        for k, (txt, g) in SITIDLE.items():
            clip(f'{pid}_{k}', g, txt.format(who=who), refs=[ref], phase=K)
    for act, txt in ACTIONS.items():
        for d in 'sn':
            clip(f"{pid}_{act.replace('.', '-')}_{d}", f"m_{act}_{'south' if d == 's' else 'north'}", txt.format(who=who, face=FACE[d]) + ". Paint ONLY the character", refs=[ref], phase=K)
    for d in 'sn':
        e = {'id': f'{pid}_lay_{d}', 'kind': 'avatar', 'type': 'gprop', 'guide': f'blockout/m_lay_{d}.png', 'key': '#00ff00',
             'subject': f"{who} LYING on their back asleep on an invisible bed, eyes closed, relaxed; head on the side where the grey sphere is. Paint ONLY the character, no bed, no pillow",
             'refs': [ref], 'refRole': SAME_CHR}
        K.append(e)

spec = {'styleRef': '../refs/style-office.png', 'rawDir': 'raw', 'common': COMMON, 'orientation': {},
        'phases': {'A': [e['id'] for e in A], 'B': [e['id'] for e in B], 'C': [e['id'] for e in C], 'D': [e['id'] for e in D],
                   'G': [e['id'] for e in G], 'H': [e['id'] for e in H], 'J': [e['id'] for e in J], 'K': [e['id'] for e in K]},
        'assets': A + B + C + D + G + H + J + K}
(HERE / 'spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=1))
print('spec.json', len(A), 'phase A,', len(B), 'phase B')
