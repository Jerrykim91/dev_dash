export function formatKoreanTime(value:string){
 if(typeof value!=='string'||!value)return '알 수 없는 시각';
 const normalized=/Z$|[+-]\d\d:\d\d$/.test(value)?value:value.replace(' ','T')+'Z',date=new Date(normalized);
 return Number.isNaN(date.getTime())?'알 수 없는 시각':new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',dateStyle:'medium',timeStyle:'medium'}).format(date);
}
export function auditSummary(log:{action:string;actor_name?:string|null;target_name?:string|null;channel_name?:string|null;details:string}){
 let d:Record<string,unknown>={};try{d=JSON.parse(log.details);}catch{}
 const actor=log.actor_name??'서버 운영자',target=log.target_name??'대상 사용자',channel=log.channel_name??'대상 채널';
 switch(log.action){
  case 'home_access_changed':return `${actor}님이 내 집 방문 공개 범위와 정원을 변경했습니다.`;
  case 'home_visitor_revoked':return `${actor}님이 방문 권한을 회수했습니다.`;
  case 'home_report_resolved':return `${actor}님이 집 방문 신고를 처리했습니다.`;
  case 'multiplayer_reward_paid':return `${actor}님에게 협동 게임 보상 ${d.coins} Coin을 지급했습니다.`;
  case 'attendance_ticket_issued':return `${actor}님의 서비스 출석에 무료 티켓 ${d.tickets}장을 지급했습니다.`;
  case 'attendance_reward_changed':return `${actor}님이 출석 티켓 보상을 ${d.tickets}장으로 변경했습니다.`;
  case 'tickets_granted':return `${actor}님이 ${target}님에게 무료 티켓 ${d.tickets}장을 지급했습니다.`;
  case 'gacha_banner_changed':return `${actor}님이 ${d.name} 배너·확률표를 v${d.version}로 저장했습니다.`;
  case 'gacha_draw_completed':return `${actor}님이 무료 티켓 ${d.count}장으로 보상을 뽑았습니다.`;
  case 'social_report_reviewed':return `${actor}님이 신고된 소셜 콘텐츠를 검토했습니다.`;
  case 'social_report_resolved':return `${actor}님이 소셜 신고를 처리했습니다.`;
  case 'game_reward_paid':return `${actor}님의 두더지 잡기 ${d.score}점에 ${d.amount} Coin을 지급했습니다.`;
  case 'game_settings_changed':return `${actor}님이 게임 활성화·보상·일일 상한을 변경했습니다.`;
  case 'role_changed':return `${actor}님이 ${target}님의 권한을 ${d.before} → ${d.after}(으)로 변경했습니다.`;
  case 'bootstrap_super_admin':return `서버 운영자가 ${target}님을 최초 super_admin으로 지정했습니다.`;
  case 'channel_created':return `${actor}님이 ${d.name??channel} 채널을 만들었습니다.`;
  case 'channel_updated':return `${actor}님이 ${channel}의 정원·활성 설정을 변경했습니다.`;
  case 'announcement_sent':return `${actor}님이 ${d.target_channel_id?'채널':'전체'} 공지 “${d.title??''}”를 발송했습니다.`;
  case 'chat_muted':return `${actor}님이 ${target}님의 채팅을 ${d.minutes}분 제한했습니다.`;
  case 'chat_unmuted':return `${actor}님이 ${target}님의 채팅 제한을 해제했습니다.`;
  case 'user_disabled':return `${actor}님이 ${target}님의 계정 이용을 제한했습니다.`;
  case 'user_enabled':return `${actor}님이 ${target}님의 계정 이용을 허용했습니다.`;
  case 'message_deleted':return `${actor}님이 공개 채팅 메시지를 삭제했습니다.`;
  case 'report_updated':return `${actor}님이 신고를 ${d.status==='resolved'?'처리 완료':'접수'} 상태로 변경했습니다.`;
  case 'operator_user_created':return `서버 운영자가 ${target}님의 계정을 생성했습니다.`;
  case 'operator_password_changed':return `서버 운영자가 ${target}님의 비밀번호를 변경하고 기존 세션을 회수했습니다.`;
  case 'system_settings_changed':return `${actor}님이 월드 이름·채널 수 한도를 변경했습니다.`;
  case 'sqlite_imported':return `서버 운영자가 기존 SQLite 데이터를 가져왔습니다.`;
  default:return `${actor}님의 운영 작업: ${log.action}`;
 }
}
