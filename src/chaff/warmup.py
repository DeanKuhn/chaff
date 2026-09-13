"""After account creation, keep the account "warm" so that Google doesn't think it's a bot."""

import logging

from patchright.async_api import TimeoutError as PlaywrightTimeout
from patchright.async_api import async_playwright

from chaff.fingerprint import DeviceProfile
from chaff.gmail import fetch_verification_code

log = logging.getLogger(__name__)


async def warm_account(
    email: str,
    password: str,
    settings,
    gmail_service,
    device_profile: DeviceProfile | None = None,
) -> None:
    async with async_playwright() as p:
        context_args = {
            "locale": settings.locale,
        }
        if settings.proxy_url:
            context_args["proxy"] = {"server": settings.proxy_url}
        if device_profile:
            context_args.update(device_profile.to_context_kwargs())
        browser = await p.chromium.launch(
            headless=settings.headless,
            slow_mo=settings.slow_mo,
            args=["--disable-external-intent-requests"],
        )
        context = await browser.new_context(**context_args)  # type:ignore

        page = await context.new_page()
        page.set_default_timeout(settings.timeout)

        await page.goto("https://accounts.google.com/signin")

        # email setup
        await page.locator("input[name='identifier']").wait_for(
            state="visible", timeout=10000
        )
        await page.locator("input[name='identifier']").fill(email)
        await page.get_by_role("button", name="Next").click()

        # password setup
        await page.locator("input[name='Passwd']").wait_for(
            state="visible", timeout=10000
        )
        await page.locator("input[name='Passwd']").fill(password)
        await page.get_by_role("button", name="Next").click()

        # notification page -> try another way
        await page.get_by_text("Try another way").wait_for(
            state="visible", timeout=10000
        )
        await page.get_by_text("Try another way").click()

        # wait for verification email to arrive
        await page.wait_for_timeout(10000)
        code = fetch_verification_code(gmail_service)

        # fill code
        await page.locator("input[type='tel']").wait_for(state="visible", timeout=10000)
        await page.locator("input[type='tel']").fill(code)
        await page.get_by_role("button", name="Next").click()

        # optional "update password" page
        try:
            await page.get_by_text("Continue").wait_for(state="visible", timeout=10000)
            await page.get_by_role("button", name="Continue").click()
        except PlaywrightTimeout:
            pass

        # visit inbox
        await page.goto("https://mail.google.com")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(10000)

        await page.close()
        await context.close()
        await browser.close()
