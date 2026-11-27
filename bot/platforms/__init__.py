from .facebook import FacebookPublisher
from .instagram import InstagramPublisher
from .tiktok import TikTokPublisher
from .x import XPublisher

PUBLISHERS = {
    "facebook": FacebookPublisher,
    "instagram": InstagramPublisher,
    "x": XPublisher,
    "tiktok": TikTokPublisher,
}
