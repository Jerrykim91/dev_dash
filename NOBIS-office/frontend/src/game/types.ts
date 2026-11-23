export type Point = {x:number;y:number};
export type Direction = 'north'|'south'|'east'|'west';
export type WorkStatus = 'before_work'|'working'|'meeting'|'focusing'|'break'|'outside'|'after_work'|'vacation';
export type PresenceState = 'online'|'offline'|'away'|'private';
export type ParticipationMode = 'normal'|'spectator';
export type AvatarAction = 'idle'|'walking'|'sitting'|'typing'|'chatting'|'working'|'meeting'|'away'|'vacation'|'after_work'|'resting'|'drinking';
/** 옷 갈아입기(파트 외형). 없으면 팔레트로 고른 완성 캐릭터(외형 16칸) */
export type AvatarParts = {hair:string;top:string;bottom:string};
export type Avatar = {id:string;palette:string;parts?:AvatarParts};
export type User = {id:string;nickname:string;role:'user'|'moderator'|'admin'|'super_admin';work_status:WorkStatus|null;message:string};
export type Player = User & Point & {room_type?:string;room_id?:string;room_instance_id?:string;profile_location_visible?:boolean;minigame?:{session_id:string;game_id:string}|null;direction:Direction;zone:string;scope:string;world_id?:string;channel_id?:string;active_object?:string|null;seat_id?:string|null;status_text?:string;presence:PresenceState;participation_mode:ParticipationMode;action:AvatarAction;avatar:Avatar};
export type Interaction = {kind:'action'|'menu'|'dashboard'|'channel'|'home_exit'|'arcade'|'public_enter'|'public_exit'|'meeting_lobby';room_type?:string;channel_kind?:'cafe'|'meeting';personal_entry?:boolean;personal_exit?:boolean;toggle?:boolean;action?:AvatarAction;message?:string;targets?:string[];label?:string};
export interface InteractableObject extends Point {id:string;kind:string;wall_axis?:'x'|'y'|null;label:string;visual_asset?:string;axis?:'x'|'y';instance_id?:string;width?:number;height?:number;blocking?:boolean;rotation?:number;placeholder?:boolean;interaction?:Interaction}
export type MapObject = InteractableObject;
export type SurfaceSpec = {regions:{id:string;tiles:{x:number;y:number;width:number;height:number};elevation:number;cells?:Point[]}[];stairs:{id:string;from:Point;to:Point}[]};
export type Workstation={id:string;desk_id:string;chair_id:string;plot:Point[];approach:Point};
export type Seat = {id:string;object_id:string;tile:Point;facing:Direction;sit_height:number;approach:Point;work_surface_id?:string|null};
export type MapData = {seats?:Seat[];workstations?:Workstation[];meeting_seats?:{chair_id:string;approach:Point}[];visualAreas?:{id:string;name:string;anchor:Point}[];id?:string;version?:number;walkable_tiles?:Point[];closed_edges?:[Point,Point][];surface?:SurfaceSpec;width:number;height:number;spawn:Point;exit?:Point;objects:MapObject[]};
export type Zone = {cells?:Point[];id:string;name:string;map_id:string;private:boolean;tiles:{x:number;y:number;width:number;height:number}|null;anchor:Point;floor:string;accent:string;chat_bubbles_allowed?:boolean};
export type ChatChannel = {id:string;kind:'world'|'zone'|'private_cafe'|'meeting'|'announcement';name:string;meeting_id?:string};
export type Chat = {id:string;user_id:string;nickname:string;text:string;time:string;channel:string;mentions:string[];message_type?:'world'|'channel'|'zone'|'private'|'announcement';recipient_id?:string;recipient_nickname?:string;delivery?:'stored'|'delivered'};
export type RoomMembership = {room_id:string;user_id:string;role:'member'|'owner';meeting_id?:string};
export type Notification = {id:string;kind:'mention'|'announcement'|'invite'|'private';message:string;channel:string|null};
export type Session = {token:string;user:User;home_id:string};
export type UserAvatarContext = {user:Pick<User,'id'|'nickname'>;avatar:Avatar};
export const workStatusLabels:Record<WorkStatus,string> = {before_work:'출근 전',working:'근무 중',meeting:'회의 중',focusing:'집중 중',break:'휴식',outside:'외근',after_work:'퇴근',vacation:'휴가 중'};

export type ChannelMember={user_id:string;nickname:string;state:'active'|'invited'|'left';role:'owner'|'member'};
export type PrivateChannel={id:string;kind:'cafe'|'meeting';name:string;owner_id:string;meeting_id:string|null;status:'open'|'closed';membership:'active'|'invited';member_role:'owner'|'member';members:ChannelMember[]};
export type PersonalRoomSettings={id:string;name:string;dashboard_url:string};

export type FurnitureItem={item_id:string;name:string;category:string;size:{width:number;height:number};rotatable:boolean;price:number;asset_key:string;blocking:boolean};
export type FurnitureInstance={id:string;owner_id:string;item_id:string;acquired_at:string};
export type FurniturePlacement={instance_id:string;grid_x:number;grid_y:number;rotation:number};
export type HomeState={home:{id:string;owner_id:string;revision:number};catalog:FurnitureItem[];inventory:FurnitureInstance[];placements:FurniturePlacement[];balance:number;transactions:{id:string;amount:number;balance_after:number;kind:string;created_at:string}[];map:MapData};

export type WorldChannel={id:string;world_id:string;name:string;capacity:number;enabled:boolean|number;online:number};
export type Announcement={id:string;title:string;text:string;target_channel_id:string|null;duration_seconds:number;time:string};
export type ChatPreferences={chat_bubbles_enabled:boolean};
export type DirectoryUser={id:string;nickname:string;online?:boolean;channel_id?:string|null};

export type DashboardConfig={environment:string;default_url:string;allow_local:boolean};

export const workStatusText=(status:WorkStatus|null|undefined)=>status?workStatusLabels[status]:'비공개';
