"""Utils for Patchright runs."""

import asyncio
import random


async def human_type(locator, text: str) -> None:
    for c in text:
        if c.isdigit():
            delay = random.uniform(0.1, 0.25)
        elif random.random() > 0.95:
            delay = random.uniform(0.3, 0.6)
        else:
            delay = random.uniform(0.05, 0.12)
        await locator.press(c)
        await asyncio.sleep(delay)
    await asyncio.sleep(random.uniform(0.2, 0.5))


async def random_delay(low: float = 0.5, high: float = 2.5) -> None:
    await asyncio.sleep(random.uniform(low, high))
