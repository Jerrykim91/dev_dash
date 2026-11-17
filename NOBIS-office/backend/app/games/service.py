import json
import secrets
import time
import uuid
from datetime import datetime,timezone
from .registry import RULES,DEFAULT_SETTINGS,COMING

class GameError(Exception):
    def __init__(self,message,status=422):self.message=message;self.status=status

class GameService:
    def __init__(self,repo,homes,social,clock=None):self.repo=repo;self.homes=homes;self.social=social;self.clock=clock or time.time
    def initialize(self):
        with self.repo.connect() as c:
            for gid in RULES:c.execute('INSERT OR IGNORE INTO game_settings VALUES (?,?)',(gid,json.dumps(DEFAULT_SETTINGS)))
    def settings(self,c,gid):
        r=c.execute('SELECT data FROM game_settings WHERE game_id=?',(gid,)).fetchone()
        if not r or gid not in RULES:raise GameError('플레이할 수 없는 게임입니다.',404)
        return json.loads(r['data'])
    def catalog(self):
        with self.repo.connect() as c:return [{'game_id':g.game_id,'name':g.name,'description':g.description,'available':self.settings(c,g.game_id)['enabled'],'config':g.config(),'reward_policy':self.settings(c,g.game_id)} for g in RULES.values()]+COMING
    def owned(self,c,uid,sid):
        r=c.execute('SELECT * FROM game_sessions WHERE id=? AND user_id=?',(sid,uid)).fetchone()
        if not r:raise GameError('내 게임 세션을 찾을 수 없습니다.',404)
        return dict(r)
    def totals(self,c,s):
        hits=c.execute('SELECT COUNT(*) FROM game_inputs WHERE session_id=? AND hit=1',(s['id'],)).fetchone()[0]
        return hits,hits*json.loads(s['config'])['score_per_hit']
    def alert(self,uid,sid,reason):
        now=self.clock()
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM game_validation_events WHERE user_id=? AND reason=? AND created_at>?',(uid,reason,now-10)).fetchone():c.execute('INSERT INTO game_validation_events VALUES (?,?,?,?,?)',(str(uuid.uuid4()),uid,sid,reason,now))
    def _expire(self,c,uid,now):
        for row in c.execute("SELECT * FROM game_sessions WHERE user_id=? AND status='active'",(uid,)).fetchall():
            s=dict(row);cfg=json.loads(s['config'])
            if now>s['expires_at']+cfg['claim_grace_ms']/1000:
                hits,score=self.totals(c,s);c.execute("UPDATE game_sessions SET status='expired' WHERE id=?",(s['id'],));c.execute('INSERT OR IGNORE INTO game_results VALUES (?,?,?,?)',(s['id'],score,hits,now))
    def active(self,uid):
        now=self.clock()
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE');self._expire(c,uid,now)
            r=c.execute("SELECT id,game_id,expires_at FROM game_sessions WHERE user_id=? AND status='active'",(uid,)).fetchone()
        return dict(r) if r else None
    def start(self,uid,gid,request_id):
        self.homes.ensure(uid);now=self.clock()
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE');self._expire(c,uid,now)
            if hasattr(self,'multiplayer'):self.multiplayer.expire(c)
            if c.execute('SELECT 1 FROM multiplayer_game_participants WHERE user_id=? AND active=1',(uid,)).fetchone():raise GameError('협동 게임 초대를 먼저 종료하세요.',409)
            old=c.execute('SELECT id,game_id FROM game_sessions WHERE user_id=? AND request_id=?',(uid,request_id)).fetchone()
            if old:
                if old['game_id']!=gid:raise GameError('요청 번호를 다른 게임에 재사용할 수 없습니다.',409)
                sid=old['id']
            else:
                setting=self.settings(c,gid)
                if not setting['enabled']:raise GameError('현재 이용이 중지된 게임입니다.',409)
                if c.execute("SELECT 1 FROM game_sessions WHERE user_id=? AND status='active'",(uid,)).fetchone():raise GameError('진행 중인 게임으로 먼저 돌아가거나 종료해 주세요.',409)
                cfg={**RULES[gid].config(),'rewards':setting['rewards']}
                last=c.execute('SELECT started_at FROM game_sessions WHERE user_id=? ORDER BY started_at DESC LIMIT 1',(uid,)).fetchone()
                if last and now-last['started_at']<cfg['cooldown_ms']/1000:raise GameError('잠시 후 다시 시작해 주세요.',429)
                sid=str(uuid.uuid4());c.execute('INSERT INTO game_sessions(id,user_id,game_id,request_id,seed,config,started_at,expires_at,status) VALUES (?,?,?,?,?,?,?,?,?)',(sid,uid,gid,request_id,secrets.token_hex(32),json.dumps(cfg),now,now+cfg['duration_ms']/1000,'active'))
        return self.state(uid,sid)
    def state(self,uid,sid):
        now=self.clock()
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE');self._expire(c,uid,now);s=self.owned(c,uid,sid);cfg=json.loads(s['config']);hits,score=self.totals(c,s)
            result=c.execute('SELECT * FROM game_results WHERE session_id=?',(sid,)).fetchone()
            if result:hits,score=result['hits'],result['score']
            reward=c.execute('SELECT ct.amount,g.reason FROM game_reward_transactions g JOIN coin_transactions ct ON ct.id=g.coin_transaction_id WHERE g.session_id=?',(sid,)).fetchone()
            balance=c.execute('SELECT balance FROM user_wallets WHERE user_id=?',(uid,)).fetchone()[0]
            wave=max(0,int((now-s['started_at'])*1000//cfg['wave_ms']));mole=None
            if s['status']=='active' and s['started_at']<=now<s['expires_at'] and (now-s['started_at'])*1000-wave*cfg['wave_ms']<cfg['visible_ms']:
                candidate=RULES[s['game_id']].mole(s['seed'],wave)
                if not c.execute('SELECT 1 FROM game_inputs WHERE session_id=? AND wave=? AND hit=1',(sid,wave)).fetchone():mole={**candidate,'expires_at':s['started_at']+(wave*cfg['wave_ms']+cfg['visible_ms'])/1000}
        return {'session_id':sid,'game_id':s['game_id'],'status':s['status'],'started_at':s['started_at'],'expires_at':s['expires_at'],'server_now':now,'remaining_ms':max(0,round((s['expires_at']-now)*1000)),'score':score,'hits':hits,'reward':reward['amount'] if reward else 0,'reward_reason':reward['reason'] if reward else ('cancelled' if s['status']=='cancelled' else 'expired' if s['status']=='expired' else None),'balance':balance,'mole':mole,'config':{k:v for k,v in cfg.items() if k not in ('claim_grace_ms',)},'reward_settled':bool(reward)}
    def hit(self,uid,sid,event_id,cell,wave,challenge):
        now=self.clock();failure=None;hit=False;replayed=False
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE');s=self.owned(c,uid,sid);cfg=json.loads(s['config'])
            old=c.execute('SELECT * FROM game_inputs WHERE session_id=? AND event_id=?',(sid,event_id)).fetchone()
            if old:
                if (old['cell'],old['wave'],old['challenge'])!=(cell,wave,challenge):failure=('다른 입력에 같은 요청 번호를 사용할 수 없습니다.',409,'event_reuse')
                else:hit=bool(old['hit']);replayed=True
            elif s['status']!='active' or not s['started_at']<=now<s['expires_at']:failure=('이미 종료되었거나 유효 시간이 지난 게임입니다.',409,'invalid_time')
            elif now-s['last_input_at']<cfg['min_input_ms']/1000:failure=('클릭 요청이 너무 빠릅니다. 잠시 후 눌러 주세요.',429,'rapid_input')
            else:
                current=int((now-s['started_at'])*1000//cfg['wave_ms']);m=RULES[s['game_id']].mole(s['seed'],current)
                # Empty cells score zero; a claimed hit needs the current server challenge.
                if wave!=-1 and (wave!=current or not secrets.compare_digest(challenge,m['challenge'])):failure=('만료되었거나 올바르지 않은 두더지입니다.',422,'invalid_challenge')
                else:
                    visible=(now-s['started_at'])*1000-current*cfg['wave_ms']<cfg['visible_ms']
                    used=c.execute('SELECT 1 FROM game_inputs WHERE session_id=? AND wave=? AND hit=1',(sid,current)).fetchone()
                    hit=wave==current and visible and cell==m['cell'] and not used
                    c.execute('INSERT INTO game_inputs VALUES (?,?,?,?,?,?,?)',(sid,event_id,cell,wave,challenge,now,int(hit)))
                    c.execute('UPDATE game_sessions SET last_input_at=? WHERE id=?',(now,sid))
        if failure:self.alert(uid,sid,failure[2]);raise GameError(failure[0],failure[1])
        return {'hit':bool(hit),'replayed':replayed,'session':self.state(uid,sid)}
    def finish(self,uid,sid,cancel=False):
        now=self.clock()
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE');self._expire(c,uid,now);s=self.owned(c,uid,sid)
            if s['status']=='active':
                if not cancel and now<s['expires_at']:raise GameError('게임 시간이 끝난 뒤 결과를 정산할 수 있습니다.',409)
                hits,score=self.totals(c,s);cfg=json.loads(s['config']);status='cancelled' if cancel else 'completed'
                c.execute('UPDATE game_sessions SET status=? WHERE id=?',(status,sid));c.execute('INSERT INTO game_results VALUES (?,?,?,?)',(sid,score,hits,now))
                amount=0;reason='cancelled'
                if not cancel:
                    setting=self.settings(c,s['game_id']);day=datetime.fromtimestamp(now,timezone.utc).date().isoformat()
                    earned=c.execute('SELECT COALESCE(SUM(ct.amount),0) FROM game_reward_transactions g JOIN coin_transactions ct ON ct.id=g.coin_transaction_id WHERE ct.user_id=? AND g.reward_date=?',(uid,day)).fetchone()[0]
                    earned+=c.execute('SELECT COALESCE(SUM(ct.amount),0) FROM multiplayer_game_rewards r JOIN coin_transactions ct ON ct.id=r.coin_transaction_id WHERE r.user_id=? AND r.reward_date=?',(uid,day)).fetchone()[0]
                    wanted=max((r['coins'] for r in cfg['rewards'] if score>=r['min_score']),default=0);amount=min(wanted,max(0,setting['daily_cap']-earned));reason='daily_cap' if amount<wanted else 'score'
                    c.execute('UPDATE user_wallets SET balance=balance+? WHERE user_id=?',(amount,uid));balance=c.execute('SELECT balance FROM user_wallets WHERE user_id=?',(uid,)).fetchone()[0];tid=str(uuid.uuid4())
                    c.execute("INSERT INTO coin_transactions(id,user_id,amount,balance_after,kind) VALUES (?,?,?,?,'minigame_reward')",(tid,uid,amount,balance));c.execute('INSERT INTO game_reward_transactions VALUES (?,?,?,?)',(sid,tid,day,reason))
                    self.social.audit(c,uid,'game_reward_paid',sid,{'game_id':s['game_id'],'score':score,'amount':amount,'reason':reason})
        return self.state(uid,sid)
    def history(self,uid):
        with self.repo.connect() as c:
            rows=[dict(r) for r in c.execute('SELECT s.id AS session_id,s.game_id,s.status,r.score,r.hits,r.finished_at,COALESCE(ct.amount,0) AS reward FROM game_sessions s JOIN game_results r ON r.session_id=s.id LEFT JOIN game_reward_transactions g ON g.session_id=s.id LEFT JOIN coin_transactions ct ON ct.id=g.coin_transaction_id WHERE s.user_id=? ORDER BY r.finished_at DESC LIMIT 30',(uid,))]
            stats=[dict(r) for r in c.execute('SELECT s.game_id,COUNT(*) AS total_plays,MAX(r.score) AS best_score,COALESCE(SUM(ct.amount),0) AS total_rewards FROM game_sessions s JOIN game_results r ON r.session_id=s.id LEFT JOIN game_reward_transactions g ON g.session_id=s.id LEFT JOIN coin_transactions ct ON ct.id=g.coin_transaction_id WHERE s.user_id=? GROUP BY s.game_id',(uid,))]
        return {'recent':rows,'statistics':stats}
    def admin_data(self,uid,section):
        self.social.require(uid,'games_read')
        if section=='games':return self.catalog()
        with self.repo.connect() as c:
            if section=='game-rewards':return [dict(r) for r in c.execute('SELECT g.*,ct.user_id,u.nickname,ct.amount,ct.balance_after,ct.created_at,r.score,s.game_id FROM game_reward_transactions g JOIN coin_transactions ct ON ct.id=g.coin_transaction_id JOIN users u ON u.id=ct.user_id JOIN game_results r ON r.session_id=g.session_id JOIN game_sessions s ON s.id=g.session_id ORDER BY r.finished_at DESC LIMIT 100')]
            if section=='game-sessions':return [dict(r) for r in c.execute('SELECT s.id,s.user_id,u.nickname,s.game_id,s.status,s.started_at,s.expires_at FROM game_sessions s JOIN users u ON u.id=s.user_id ORDER BY s.started_at DESC LIMIT 100')]
            return [dict(r) for r in c.execute('SELECT e.*,u.nickname FROM game_validation_events e JOIN users u ON u.id=e.user_id ORDER BY e.created_at DESC LIMIT 100')]
    def configure(self,uid,gid,data):
        self.social.require(uid,'games_manage')
        with self.repo.connect() as c:
            c.execute('BEGIN IMMEDIATE');before=self.settings(c,gid);c.execute('UPDATE game_settings SET data=? WHERE game_id=?',(json.dumps(data),gid));self.social.audit(c,uid,'game_settings_changed',gid,{'before':before,'after':data})
        return self.catalog()
