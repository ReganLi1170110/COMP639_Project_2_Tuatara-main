from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserBadge:
    id: int
    user_id: int
    badge_id: int
    earned_date: datetime
