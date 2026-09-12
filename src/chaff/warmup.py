"""After account creation, keep the account "warm" so that Google doesn't think it's a bot."""

import logging

from patchright.async_api import TimeoutError as PlaywrightTimeout
from patchright.async_api import async_playwright

from chaff.config import Settings
from chaff.exceptions import (
    WarmupError,
)

log = logging.getLogger(__name__)


async def warm_account(email: str, password: str, settings) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=settings.headless,
            slow_mo=settings.slow_mo,
        )
        context = await browser.new_context(
            locale=settings.locale,
            proxy={"server": settings.proxy_url} if settings.proxy_url else None,
        )
        page = await context.new_page()
        page.set_default_timeout(settings.timeout)

        await page.goto("https://accounts.google.com/signin")

        # fills email -> next
        # fills password -> next
        # find out what happens after this
