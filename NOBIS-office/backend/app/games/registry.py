"""Only the server owns game timing/scoring; future games register another rules object."""
import hashlib
import hmac
from dataclasses import dataclass

@dataclass(frozen=True)
class WhackAMole:
    game_id:str='whack_a_mole'
    name:str='두더지 잡기'
    description:str='30초 동안 등장하는 두더지를 클릭하거나 터치하세요.'
    def config(self):return {'duration_ms':30000,'cells':9,'wave_ms':800,'visible_ms':650,'score_per_hit':10,'min_input_ms':80,'cooldown_ms':2000,'claim_grace_ms':300000}
    def mole(self,seed,wave):
        digest=hmac.new(bytes.fromhex(seed),str(wave).encode(),hashlib.sha256).hexdigest()
        return {'wave':wave,'cell':int(digest[:8],16)%9,'challenge':digest[8:]}

RULES={'whack_a_mole':WhackAMole()}
DEFAULT_SETTINGS={'enabled':True,'daily_cap':300,'rewards':[{'min_score':0,'coins':0},{'min_score':50,'coins':10},{'min_score':100,'coins':20},{'min_score':150,'coins':30}]}
COMING=[{'game_id':'memory_cards','name':'카드 짝 맞추기','description':'준비 중','available':False},{'game_id':'coin_collect','name':'코인 모으기','description':'준비 중','available':False}]
