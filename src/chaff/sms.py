"""Send out SMS with android phone."""

import asyncio
import logging
from abc import ABC, abstractmethod

from chaff.exceptions import SmsVerificationError

log = logging.getLogger(__name__)


class SmsSender(ABC):
    @abstractmethod
    async def send(self, to: str, body: str) -> None:
        pass

    @abstractmethod
    async def check_ready(self) -> bool:
        pass


class AdbSmsSender(SmsSender):
    def __init__(self, device_serial: str | None = None):
        self.device_serial = device_serial

    async def send(self, to: str, body: str) -> None:
        try:
            await self._run_adb("shell", "termux-sms-send", "-n", to, body)
            log.info("termux run success")
            return
        except SmsVerificationError:
            log.info("termux not available, falling back to isms")

        try:
            stdout = await self._run_adb(
                "shell", "service", "call", "isms", "7",
                "i32", "0",
                "s16", "com.android.mms",
                "s16", to,
                "s16", "null",
                "s16", body,
                "s16", "null",
                "s16", "null"
            )
        except SmsVerificationError:
            raise SmsVerificationError(
                "Sms failed for both termux and isms"
            )
        if "00000000" not in stdout:
            raise SmsVerificationError(f"isms returned unexpected results: {stdout}")
        log.info("isms run success")

    async def _run_adb(self, *args: str) -> str:
        cmd = ["adb"]
        if self.device_serial:
            cmd += ["-s", self.device_serial]
        cmd += list(args)
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise SmsVerificationError(
                f"adb command failed: {stderr.decode().strip()}"
            )
        return stdout.decode().strip()

    async def check_ready(self) -> bool:
        try:
            stdout = await self._run_adb("devices")
            for line in stdout.splitlines()[1:]:
                parts = line.split("\t")
                if len(parts) == 2 and parts[1] == "device":
                    return True
            return False
        except SmsVerificationError:
            return False
