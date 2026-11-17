import os
import time
from fastapi import Depends
from .social import PERMISSIONS,SocialError
from .models.contracts import WorldChannelConfig,RoleChange,AnnouncementInput,MuteInput,UserDisabled,ReportInput,ReportStatus,SystemSettingsInput

def install_admin(app,repo,social,hub,current_user,channel_payload,channel_counts):
    @app.get('/api/admin/session')
    def admin_session(user=Depends(current_user)):
        social.require(user['id'],'reports_read');role=social.role(user['id'])
        return {'role':role,'permissions':sorted(PERMISSIONS[role]),'user_id':user['id']}
    @app.get('/api/admin/system-settings')
    def get_system(user=Depends(current_user)):return social.system_settings(user['id'])
    @app.put('/api/admin/system-settings')
    def set_system(data:SystemSettingsInput,user=Depends(current_user)):return social.system_settings(user['id'],data.model_dump())
    @app.get('/api/admin/{section}')
    def admin_get(section:str,user=Depends(current_user)):
        result=social.admin_data(user['id'],section)
        if section=='channels':return channel_payload()
        if section=='online':return [hub.public_player(p.player,user['id']) for p in hub.peers.values()]
        if section=='dashboard':
            result.update(online=len(hub.peers),channel_population=channel_payload(),server={'environment':os.getenv('APP_ENV','development'),'database':repo.kind,'database_status':'ready','uptime_seconds':round(time.monotonic()-app.state.started_at),'mode':'single-process'})
        return result
    @app.post('/api/admin/channels')
    async def create_channel(data:WorldChannelConfig,user=Depends(current_user)):
        if not data.name.strip():raise SocialError('채널 이름을 입력하세요.')
        async with hub.lock:social.manage_channel(user['id'],data.id,data.name.strip(),data.capacity,data.enabled,create=True)
        await channel_counts();return channel_payload()
    @app.put('/api/admin/channels/{cid}')
    async def update_channel(cid:str,data:WorldChannelConfig,user=Depends(current_user)):
        social.require(user['id'],'channels_manage')
        if cid!=data.id:raise SocialError('채널 ID가 일치하지 않습니다.')
        async with hub.lock:
            count=sum(p.player['channel_id']==cid for p in hub.peers.values())
            if count>data.capacity or (count and not data.enabled):raise SocialError('접속자가 있는 채널의 정원을 줄이거나 닫을 수 없습니다.',409)
            social.manage_channel(user['id'],cid,data.name.strip(),data.capacity,data.enabled)
        await channel_counts();return channel_payload()
    @app.post('/api/admin/announcements')
    async def announce(data:AnnouncementInput,user=Depends(current_user)):
        if not data.title.strip() or not data.text.strip():raise SocialError('제목과 본문을 입력하세요.')
        item=social.announce(user['id'],data.title.strip(),data.text.strip(),data.target_channel_id,data.duration_seconds)
        await hub.broadcast({'type':'announcement','announcement':item},lambda p:not item['target_channel_id'] or p.player['channel_id']==item['target_channel_id'])
        return item
    @app.put('/api/admin/users/{uid}/role')
    async def role(uid:str,data:RoleChange,user=Depends(current_user)):
        social.change_role(user['id'],uid,data.role)
        if uid in hub.peers:
            p=hub.peers[uid];p.player['role']=data.role;await hub.presence('status',p)
        return {'user_id':uid,'role':data.role}
    @app.put('/api/admin/users/{uid}/disabled')
    async def disabled(uid:str,data:UserDisabled,user=Depends(current_user)):
        social.disable(user['id'],uid,data.disabled)
        if data.disabled and uid in hub.peers:await hub.peers[uid].ws.close(code=1008,reason='계정 이용 제한')
        return {'user_id':uid,'disabled':data.disabled}
    @app.put('/api/admin/users/{uid}/mute')
    def mute(uid:str,data:MuteInput,user=Depends(current_user)):
        if not data.reason.strip():raise SocialError('이유를 입력하세요.')
        social.mute(user['id'],uid,data.minutes,data.reason.strip());return {'ok':True}
    @app.delete('/api/admin/messages/{mid}')
    async def delete_message(mid:str,user=Depends(current_user)):
        old=social.delete_message(user['id'],mid)
        await hub.broadcast({'type':'message_deleted','id':mid},lambda p:hub.can_read(p,old['channel']))
        return {'ok':True}
    @app.post('/api/reports')
    def report(data:ReportInput,user=Depends(current_user)):
        if not data.reason.strip():raise SocialError('신고 이유를 입력하세요.')
        social.report(user['id'],data.target_id,data.reason.strip());return {'ok':True}
    @app.put('/api/admin/reports/{rid}')
    def report_status(rid:str,data:ReportStatus,user=Depends(current_user)):
        social.report_status(user['id'],rid,data.status);return {'ok':True}
