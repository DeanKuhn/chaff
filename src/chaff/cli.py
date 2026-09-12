"""CLI for various chaff commands."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from chaff.browser import create_account
from chaff.config import Settings
from chaff.exceptions import ChaffError, WarmupError
from chaff.identity import generate_identity, generate_password
from chaff.storage import (
    get_identities,
    init_db,
    save_credential,
    save_identity,
    update_status,
    get_credential_by_email,
    get_credentials_by_status,
)
from chaff.warmup import warm_account

app = typer.Typer()
console = Console()


@app.command()
def create(
    locale: str = typer.Option("en_US", "--locale", "-l"),
    backup_email: str | None = typer.Option(None, "--backup-email", "-b"),
    proxy: str | None = typer.Option(None, "--proxy", "-p"),
    headless: bool = typer.Option(False, "--headless"),
    count: int = typer.Option(1, "--count", "-c"),
) -> None:
    init_db()
    settings = Settings(
        headless=headless,
        proxy_url=proxy,
        proxy_enabled=proxy is not None,
        locale=locale,
    )
    succeed = 0

    for _ in range(count):
        try:
            identity = generate_identity(locale=locale, backup_email=backup_email)
            for i, name in enumerate(identity.usernames, 1):
                console.print(f"    {i}: {name}")

            password = generate_password()
            username = asyncio.run(
                create_account(identity=identity, password=password, settings=settings)
            )
            success_id = save_identity(
                first_name=identity.first_name,
                last_name=identity.last_name,
                dob=identity.dob,
                username=username,
                locale=locale,
                backup_email=backup_email,
            )
            success_cred = save_credential(
                identity_id=success_id,
                email=f"{username}@gmail.com",
                password=password,
                recovery_phone=None,
                proxy_used=proxy,
            )

            succeed += 1
            console.print(
                f"[green]Success! Email created. Summary:\n"
                f"    email: {username}@gmail.com\n"
                f"    success credential: {success_cred}[/green]"
            )

        except ChaffError as e:
            console.print(f"[red]Failed: {e}[/red]")

    if count > 1:
        console.print(f"Total succeed vs failed: {succeed} / {count}")


@app.command("list")
def list_accounts(status: str = typer.Option(None, "--status", "-s")) -> None:
    init_db()
    rows = get_identities(status=status)

    table = Table(title="Accounts")
    table.add_column("ID")
    table.add_column("First Name")
    table.add_column("Last Name")
    table.add_column("Email")
    table.add_column("Status")
    table.add_column("Proxy")
    table.add_column("Created At")

    for row in rows:
        table.add_row(
            str(row["id"]),
            row["first_name"],
            row["last_name"],
            row["email"],
            row["status"] or "-",
            row["proxy_used"] or "-",
            row["created_at"],
        )

    console.print(table)


@app.command("update")
def update(
    status: str = typer.Option(..., "--status", "-s"),
    credential_id: int = typer.Option(..., "--cred-id", "-i"),
) -> None:
    init_db()
    update_status(status, credential_id)
    console.print(f"[green]Updated credential {credential_id} to '{status}'[/green]")


@app.command()
def warmup(
    email: str | None = typer.Option(None, "--email", "-e"),
    status: str | None = typer.Option(None, "--status", "-s"),
    locale: str = typer.Option("en_US", "--locale", "-l"),
    proxy: str | None = typer.Option(None, "--proxy", "-p"),
    headless: bool = typer.Option(False, "--headless"),
) -> None:
    init_db()
    settings = Settings(
        headless=headless,
        proxy_url=proxy,
        proxy_enabled=proxy is not None,
        locale=locale,
    )

    if email:
        row = get_credential_by_email(email)
        if row[0]["status"] != "warmed":
            try:
                asyncio.run(warm_account(row[0]["email"], row[0]["password"], settings))
                update_status("warmed", row[0]["id"])
                console.print(f"[green]Warmed {row[0]['email']}[/green]")
            except WarmupError as e:
                console.print(f"[red]Failed to warm {row[0]['email']}: {e}[/red]")
    elif status:
        rows = get_credentials_by_status(status)
        for row in rows:
            if row["status"] != "warmed":
                try:
                    asyncio.run(warm_account(row["email"], row["password"], settings))
                    update_status("warmed", row["id"])
                    console.print(f"[green]Warmed {row['email']}[/green]")
                except WarmupError as e:
                    console.print(f"[red]Failed to warm {row['email']}: {e}[/red]")
    else:
        console.print("[red]ERROR: Must input either email or status[/red]")


if __name__ == "__main__":
    app()
