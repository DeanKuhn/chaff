"""Browser instructions to create an account."""

import io
import json
import logging

from patchright.async_api import TimeoutError as PlaywrightTimeout
from patchright.async_api import async_playwright
from PIL import Image
from pyzbar.pyzbar import decode

from chaff.config import Settings
from chaff.exceptions import (
    SmsVerificationError,
    UsernameConflictError,
)
from chaff.fingerprint import (
    DeviceProfile,
)
from chaff.identity import Identity
from chaff.sms import AdbSmsSender
from chaff.utils import human_type, random_delay

log = logging.getLogger(__name__)


MONTHS = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


async def create_account(
    identity: Identity,
    password: str,
    settings: Settings,
    backup_email: str | None = None,
    device_profile: DeviceProfile | None = None,
) -> str:
    log.info(f"Password for {identity.last_name}, {identity.first_name}: {password}")
    async with async_playwright() as p:
        context_args = {
            "locale": settings.locale,
        }
        if settings.proxy_url:
            context_args["proxy"] = {"server": settings.proxy_url}
        if device_profile:
            context_args.update(device_profile.to_context_kwargs())
        browser = await p.chromium.launch(
            channel="chrome",
            headless=settings.headless,
            slow_mo=settings.slow_mo,
            args=["--disable-external-intent-requests"],
        )
        context = await browser.new_context(**context_args)  # type:ignore
        page = await context.new_page()
        page.set_default_timeout(settings.timeout)

        await page.goto(
            "https://accounts.google.com/lifecycle/steps/signup/name"
            "?flowName=GlifWebSignIn&flowEntry=SignUp"
        )

        if "unknownerror" in page.url:
            await page.get_by_role("button", name="Next").click()

        # step 1: name
        await human_type(page.get_by_label("First name"), identity.first_name)
        await random_delay(0.3, 1.0)
        await human_type(page.get_by_label("Last name"), identity.last_name)
        await random_delay(0.5, 1.5)
        await page.get_by_role("button", name="Next").click()

        # step 2: DOB + gender
        await page.wait_for_url("**/lifecycle/steps/signup/birthdaygender**")
        year, month, day = identity.dob.split("-")
        await human_type(page.get_by_label("Day"), day.lstrip("0"))
        await random_delay(0.3, 0.8)
        month_combobox = page.get_by_role("combobox", name="Month")
        await month_combobox.click()
        await random_delay(0.2, 0.5)
        await page.get_by_role("option", name=MONTHS[int(month)]).click()
        await random_delay(0.3, 0.8)
        await human_type(page.get_by_label("Year"), year)
        await random_delay(0.3, 0.8)
        gender_combobox = page.get_by_role("combobox", name="Gender")
        await gender_combobox.click()
        await random_delay(0.2, 0.5)
        await page.get_by_role("option", name="Rather not say").click()
        await random_delay(0.5, 1.5)
        await page.get_by_role("button", name="Next").click()

        # step 3: username
        await page.wait_for_url("**/lifecycle/steps/signup/username**")
        await page.locator(
            "[role='radiogroup'], input[name='Username']"
        ).first.wait_for(state="visible", timeout=10000)

        # Google sometimes offers radio choices instead of a text input
        custom_option = page.locator("input[value='custom']")
        if await custom_option.is_visible():
            await custom_option.click()
            await page.wait_for_timeout(1000)

        username_input = page.locator("input[name='Username']")
        await username_input.wait_for(state="visible")

        chosen_username = ""
        for username in identity.usernames:
            await username_input.fill("")
            await human_type(username_input, username)
            await random_delay(0.5, 1.5)
            await page.get_by_role("button", name="Next").click()

            try:
                await page.wait_for_url("**/signup/password**", timeout=5000)
                chosen_username = username
                break
            except Exception:
                error = page.get_by_text("That username is taken")
                if await error.is_visible():
                    log.info("Username %s taken, trying next", username)
                    continue
                raise
        else:
            raise UsernameConflictError("all usernames taken")

        # step 4: password
        await human_type(page.get_by_label("Password", exact=True), password)
        await random_delay(0.3, 1.0)
        await human_type(page.get_by_label("Confirm"), password)
        await random_delay(0.5, 1.5)
        await page.get_by_role("button", name="Next").click()

        # step 5: QR verification
        try:
            await _handle_qr_verification(context, page, settings)
        except SmsVerificationError:
            raise
        except PlaywrightTimeout:
            log.info("no QR verification required, continuing")

        # step 6: recovery email — skip
        await page.wait_for_url("**/signup/addrecoveryemail**")
        recoveryemail_input = page.locator("input[name='recovery']")
        await recoveryemail_input.wait_for(state="visible")
        if backup_email:
            await human_type(recoveryemail_input, backup_email)
            await random_delay(0.5, 1.5)
            await page.get_by_role("button", name="Next").click()
        else:
            await page.get_by_role("button", name="Skip").click()

        # step 6b: optional second recovery email prompt
        try:
            skip_btn = page.get_by_role("button", name="Skip")
            await skip_btn.wait_for(state="visible", timeout=5000)
            await skip_btn.click()
        except PlaywrightTimeout:
            pass

        # step 7: review
        await random_delay(5, 10)
        await page.get_by_role("button", name="Next").click()

        # step 8: TOS
        await random_delay(5, 10)
        await page.get_by_role("button", name="I agree").click()

        # step 9: confirm settings dialog
        await random_delay(5, 10)
        await page.get_by_role("button", name="Confirm").click()

        log.info("Account created: %s@gmail.com", chosen_username)

        # warmup: visit Google properties while already logged in
        await random_delay(2, 3)
        await page.goto("https://mail.google.com")
        await page.wait_for_load_state("networkidle")
        sign_in_btn = page.get_by_text("Sign in")
        try:
            await sign_in_btn.wait_for(state="visible", timeout=5000)
            await sign_in_btn.click()
            await page.wait_for_load_state("networkidle")
        except PlaywrightTimeout:
            pass
        await random_delay(10, 20)

        await page.goto("https://www.youtube.com")
        await page.wait_for_load_state("networkidle")
        await random_delay(10, 30)

        await page.goto("https://www.google.com")
        await page.wait_for_load_state("networkidle")
        await random_delay(5, 15)

        await page.goto("https://drive.google.com")
        await page.wait_for_load_state("networkidle")
        await random_delay(5, 15)

        log.info("Warmup browsing complete for %s@gmail.com", chosen_username)

        await context.close()
        await browser.close()

    return chosen_username


async def _handle_qr_verification(context, page, settings) -> None:
    await page.wait_for_url(
        "**/lifecycle/steps/signup/mophoneverification/**",
        timeout=10000,
    )

    # decode QR code
    qr_img = page.locator("img.pSHvwe").first
    screenshot_bytes = await qr_img.screenshot()
    img = Image.open(io.BytesIO(screenshot_bytes))
    results = decode(img)
    if results:
        qr_url = results[0].data.decode()
        log.info(f"QR code URL: {qr_url}")
    else:
        raise SmsVerificationError("Could not decode QR code")

    # Open up new page from QR code url
    verify_page = await context.new_page()
    await verify_page.goto(qr_url)
    await verify_page.wait_for_load_state("networkidle")

    # Look for part of response with info we want about Sms sending
    sms_data = []

    async def capture_response(response):
        if "devicephoneverification" in response.url:
            body = await response.text()
            sms_data.append(body)
            log.info(f"Captured response from: {response.url}")

    verify_page.on("response", capture_response)
    await verify_page.get_by_text("Send SMS").click()
    await verify_page.wait_for_timeout(5000)

    try:
        raw = next(d for d in sms_data if "MTflnb" in d)
        line = next(l for l in raw.splitlines() if l.startswith("[["))
        outer = json.loads(line)
        inner = json.loads(outer[0][2])
        short_code, message_body = inner[0], inner[1]
    except (StopIteration, json.JSONDecodeError, IndexError, KeyError):
        raise SmsVerificationError("Could not parse sms details from response")

    print("\n>>> Send this SMS from the other phone <<<")
    print(f"    To: {short_code}")
    print(f"    Body: {message_body}\n")
    input("Press Enter after SMS is sent...")

    await page.wait_for_url("**/signup/addrecoveryemail**", timeout=120000)
    await verify_page.close()
