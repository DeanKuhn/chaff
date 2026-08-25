import random
import secrets
import string
from dataclasses import dataclass

from faker import Faker


@dataclass
class Identity:
    first_name: str
    last_name: str
    dob: str
    usernames: list[str]
    backup_email: str | None = None
    locale: str | None = "en_US"


def generate_username_list(first_name: str, last_name: str) -> list[str]:
    usernames: list[str] = []
    for _ in range(5):
        usernames.append(
            random.choice(
                [
                    f"{first_name}{last_name}{random.randint(1000, 9999)}".lower(),
                    f"{last_name}.{first_name}{random.randint(1000, 9999)}".lower(),
                    f"{first_name[0]}{last_name}{random.randint(1000, 9999)}".lower(),
                    f"{first_name}.{last_name}{random.randint(1000, 9999)}".lower(),
                ]
            )
        )
    return usernames


def generate_identity(
    locale: str = "en_US", backup_email: str | None = None
) -> Identity:
    fake = Faker(locale)
    first_name = fake.first_name()
    last_name = fake.last_name()
    dob = fake.date_of_birth(minimum_age=20, maximum_age=45).isoformat()
    usernames = generate_username_list(first_name, last_name)
    return Identity(
        first_name=first_name,
        last_name=last_name,
        dob=dob,
        usernames=usernames,
        backup_email=backup_email,
        locale=locale,
    )


def generate_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*"),
    ]
    rest = [secrets.choice(alphabet) for _ in range(16)]
    chars = required + rest
    random.shuffle(chars)
    return "".join(chars)
