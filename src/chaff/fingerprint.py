"""Custom device fingerprint per identity, stored in DB and reused across sessions."""

import random
from dataclasses import dataclass

CHROME_VERSIONS = ["126.0.0.0", "127.0.0.0", "128.0.0.0", "129.0.0.0"]


@dataclass
class Archetype:
    platform: str
    scale_factor: int
    vw_range: tuple[int, int]
    vh_range: tuple[int, int]
    screen_pad: tuple[int, int]
    ua_template: str
    weight: int


ARCHETYPES = [
    Archetype(
        platform="Win32",
        scale_factor=1,
        vw_range=(1280, 1920),
        vh_range=(720, 1080),
        screen_pad=(0, 100),
        ua_template="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
        weight=70,
    ),
    Archetype(
        platform="MacIntel",
        scale_factor=2,
        vw_range=(1280, 1680),
        vh_range=(800, 1050),
        screen_pad=(0, 40),
        ua_template="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
        weight=25,
    ),
    Archetype(
        platform="Linux x86_64",
        scale_factor=1,
        vw_range=(1280, 1920),
        vh_range=(720, 1080),
        screen_pad=(0, 0),
        ua_template="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36",
        weight=5,
    ),
]

TIMEZONES = [
    ("America/New_York", 40),
    ("America/Chicago", 25),
    ("America/Denver", 15),
    ("America/Los_Angeles", 20),
]

PROXY_GEO_TO_TZ: dict[str, str] = {
    "us-east": "America/New_York",
    "us-central": "America/Chicago",
    "us-mountain": "America/Denver",
    "us-west": "America/Los_Angeles",
}


@dataclass
class DeviceProfile:
    viewport_width: int
    viewport_height: int
    screen_width: int
    screen_height: int
    timezone_id: str
    locale: str
    user_agent: str
    color_depth: int
    device_scale_factor: int
    platform: str

    def to_context_kwargs(self) -> dict:
        return {
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "screen": {"width": self.screen_width, "height": self.screen_height},
            "timezone_id": self.timezone_id,
            "locale": self.locale,
            "user_agent": self.user_agent,
            "color_scheme": "light",
            "device_scale_factor": self.device_scale_factor,
        }


def create_profile(proxy_geo: str | None = None) -> DeviceProfile:
    arch = random.choices(ARCHETYPES, weights=[a.weight for a in ARCHETYPES], k=1)[0]

    vw = random.randint(*arch.vw_range)
    vh = random.randint(*arch.vh_range)
    pad_lo, pad_hi = arch.screen_pad
    sw = vw + random.randint(pad_lo, pad_hi)
    sh = vh + random.randint(pad_lo, pad_hi)

    if proxy_geo and proxy_geo.lower() in PROXY_GEO_TO_TZ:
        tz = PROXY_GEO_TO_TZ[proxy_geo.lower()]
    else:
        tz = random.choices(TIMEZONES, weights=[t[1] for t in TIMEZONES], k=1)[0][0]

    version = random.choice(CHROME_VERSIONS)
    ua = arch.ua_template.format(version=version)

    return DeviceProfile(
        viewport_width=vw,
        viewport_height=vh,
        screen_width=sw,
        screen_height=sh,
        timezone_id=tz,
        locale="en_US",
        user_agent=ua,
        color_depth=random.choice([24, 30]),
        device_scale_factor=arch.scale_factor,
        platform=arch.platform,
    )
