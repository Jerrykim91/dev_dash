from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

WorkStatus = Literal['before_work', 'working', 'meeting', 'focusing', 'break', 'outside', 'after_work', 'vacation']
ParticipationMode = Literal['normal', 'spectator']
AvatarAction = Literal['idle', 'walking', 'sitting', 'typing', 'chatting', 'working', 'meeting', 'away', 'vacation', 'after_work', 'resting', 'drinking']
PresenceState = Literal['online', 'offline', 'away']

class Login(BaseModel):
    nickname: str = Field(min_length=1, max_length=20)
    admin_key: str = Field(default='', max_length=200)

class Move(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    type: Literal['move']
    zone: str
    scope: str = Field(default='office',max_length=100)
    channel_id: str = Field(default='ch1',max_length=32)
    x: float
    y: float
    direction: Literal['north', 'south', 'east', 'west']
    moving: bool = False

class StatusChange(BaseModel):
    work_status: WorkStatus
    message: str = Field(max_length=60)

class ChatInput(BaseModel):
    channel: str = Field(max_length=100)
    text: str = Field(min_length=1, max_length=500)
    mentions: list[str] = Field(default_factory=list, max_length=15)

class RoomMembership(BaseModel):
    room_id: str
    user_id: str
    role: Literal['member', 'owner'] = 'member'
    meeting_id: str | None = None

class ChannelCreate(BaseModel):
    kind: Literal['cafe','meeting']
    name: str = Field(min_length=1,max_length=60)

class PersonalSettings(BaseModel):
    name: str = Field(min_length=1,max_length=40)
    dashboard_url: str = Field(default='',max_length=2048)

# Strict economy/editor inputs: identity, balance and price always come from the server.
from uuid import UUID
from pydantic import StrictInt
class FurniturePlacement(BaseModel):
    model_config = ConfigDict(extra='forbid')
    instance_id: str = Field(max_length=60)
    grid_x: StrictInt
    grid_y: StrictInt
    rotation: StrictInt
class HomeLayout(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: StrictInt = Field(ge=0)
    placements: list[FurniturePlacement] = Field(max_length=70)
class ShopPurchase(BaseModel):
    model_config = ConfigDict(extra='forbid')
    item_id: str = Field(max_length=80)
    request_id: UUID

from pydantic import StrictBool
class StrictInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
class PasswordLogin(StrictInput):
    user_id: str = Field(min_length=1,max_length=60)
    password: str = Field(min_length=1,max_length=200)
class WorldChannelConfig(StrictInput):
    id: str = Field(pattern=r'^[a-z][a-z0-9-]{1,31}$')
    name: str = Field(min_length=1,max_length=40)
    capacity: StrictInt = Field(ge=1,le=15)
    enabled: StrictBool = True
class RoleChange(StrictInput):
    role: Literal['user','moderator','admin','super_admin']
class AnnouncementInput(StrictInput):
    title: str = Field(min_length=1,max_length=80)
    text: str = Field(min_length=1,max_length=2000)
    target_channel_id: str | None = Field(default=None,max_length=32)
    duration_seconds: StrictInt = Field(default=8,ge=3,le=30)
class ChatPreferences(StrictInput):
    chat_bubbles_enabled: StrictBool
class MuteInput(StrictInput):
    minutes: StrictInt = Field(ge=0,le=10080)
    reason: str = Field(min_length=1,max_length=300)
class UserDisabled(StrictInput):
    disabled: StrictBool
class ReportInput(StrictInput):
    target_id: str = Field(max_length=60)
    reason: str = Field(min_length=1,max_length=500)
class ReportStatus(StrictInput):
    status: Literal['open','resolved']
class PrivateInput(StrictInput):
    text: str = Field(min_length=1,max_length=550)
    recipient_id: str | None = Field(default=None,max_length=60)
class SystemSettingsInput(StrictInput):
    world_name: str = Field(min_length=1,max_length=60)
    max_channels: StrictInt = Field(ge=1,le=64)
