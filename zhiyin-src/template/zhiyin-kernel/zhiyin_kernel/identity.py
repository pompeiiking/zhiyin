"""身份与会话契约。

第一期只做本地演示用户；游客临时会话仅存于 session，登录后合并。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.enums import UserRole


class ProfileSummary(BaseModel):
    """用户摘要，用于顶栏与导师列表展示。"""

    model_config = ConfigDict(extra="forbid")

    grade: Optional[str] = None
    major: Optional[str] = None
    school: Optional[str] = None


class UserAccount(BaseModel):
    """用户账号。

    约束：第一期禁止写入真实手机号 / 简历 / 身份证，演示数据必须显式标记 DEMO。
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    phone: Optional[str] = Field(default=None, description="第一期仅允许演示值")
    email: Optional[str] = None
    nickname: str = ""
    avatar_url: Optional[str] = None
    role: UserRole = UserRole.STUDENT
    profile_summary: ProfileSummary = Field(default_factory=ProfileSummary)
    created_at: datetime
    last_login_at: Optional[datetime] = None


class AuthSession(BaseModel):
    """登录会话与 token。"""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    device_info: Optional[str] = None


class GuestSession(BaseModel):
    """游客临时会话。不落长期业务库，登录合并后清除。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    temp_profile: dict[str, Any] = Field(
        default_factory=dict, description="游客已采集的画像字段片段"
    )
    answered_collect_steps: int = Field(
        default=0, description="已答采集问数，超过 2 问触发登录拦截"
    )
