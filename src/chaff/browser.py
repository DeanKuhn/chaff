import logging

from patchright.async_api import async_playwright
from rich.prompt import Confirm

from chaff.config import Settings
from chaff.exceptions import UsernameConflictError, VerificationRequiredError
from chaff.identity import Identity

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


async def create_account(identity: Identity, password: str, settings: Settings) -> str:
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

        await page.goto(
            "https://accounts.google.com/lifecycle/steps/signup/name"
            "?flowName=GlifWebSignIn&flowEntry=SignUp"
        )

        if "unknownerror" in page.url:
            await page.get_by_role("button", name="Next").click()

        # step 1: name
        await page.get_by_label("First name").fill(identity.first_name)
        await page.get_by_label("Last name").fill(identity.last_name)
        await page.get_by_role("button", name="Next").click()

        # step 2: DOB + gender
        await page.wait_for_url("**/lifecycle/steps/signup/birthdaygender**")
        year, month, day = identity.dob.split("-")
        await page.get_by_label("Day").fill(day.lstrip("0"))
        month_combobox = page.get_by_role("combobox", name="Month")
        await month_combobox.click()
        await page.get_by_role("option", name=MONTHS[int(month)]).click()
        await page.get_by_label("Year").fill(year)
        gender_combobox = page.get_by_role("combobox", name="Gender")
        await gender_combobox.click()
        await page.get_by_role("option", name="Rather not say").click()
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
            await username_input.fill(username)
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
        await page.get_by_label("Password", exact=True).fill(password)
        await page.get_by_label("Confirm").fill(password)
        await page.get_by_role("button", name="Next").click()

        # step 5: QR verification (manual)
        try:
            await page.wait_for_url(
                "**/lifecycle/steps/signup/mophoneverification/**",
                timeout=10000,
            )
            log.info("QR verification page detected — scan with your phone")
            if not Confirm.ask(
                "Scan the QR code with your phone, complete verification, then confirm"
            ):
                raise VerificationRequiredError("user skipped verification")
        except Exception as exc:
            if isinstance(exc, VerificationRequiredError):
                raise
            log.info("No QR verification required, continuing")

        # step 6: recovery email — skip
        await page.wait_for_url("**/signup/addrecoveryemail**")
        await page.get_by_role("button", name="Skip").click()

        # step 7: review
        await page.get_by_role("button", name="Next").click()

        # step 8: TOS
        await page.get_by_role("button", name="I agree").click()

        # step 9: confirm settings dialog
        await page.get_by_role("button", name="Confirm").click()

        log.info("Account created: %s@gmail.com", chosen_username)

        await context.close()
        await browser.close()

    return chosen_username
