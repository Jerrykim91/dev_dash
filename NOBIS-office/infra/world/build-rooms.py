"""Publish independent authored room maps. No DB or user-state access."""
from pathlib import Path
import json
r=Path(__file__).resolve().parents[2];source=json.loads((r/'design/rooms/rooms.json').read_text())
(r/'shared/rooms.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
(r/'shared/maps.json').write_text(json.dumps({'office':source['maps']['lobby']},ensure_ascii=False,indent=2)+'\n')
zones=[]
for d in source['definitions']:
 zones.append({'id':d['zone_id'],'name':d['name'],'map_id':d['map_id'],'private':d['room_type']=='meeting','tiles':None,'anchor':d['spawn_point'],'cells':source['maps'][d['room_type']]['walkable_tiles'],'floor':'#85768f','accent':'#c6a6f1','chat_bubbles_allowed':d['room_type'] not in ['focus','meeting']})
(r/'shared/zones.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
print('Published',len(source['maps']),'independent maps; focus seats',len(source['maps']['focus']['workstations']))
