# taid

**TelegramAID** is a Telegram userbot for small personal workflow automations.

- Telethon **1.44** (stable) API.
- `src/` layout, strict typing (basedpyright), Ruff, pytest.
- Typed settings split by domain (`pydantic-settings`).
- Docker-first deployment for a VPS, with a direct systemd unit as an alternative.

## Features

- **Message merge** — consecutive plain outgoing text messages within a configurable
  timeout are merged into the first one. State is isolated per chat (and per forum
  topic). Any incoming message breaks the chain, and a reply to a different message
  starts a new one. Replies are matched by target, so answering different quoted parts of
  one message stays separate, while two answers to the same part (or to the whole message)
  merge. Messages produced by taid itself never merge.
- **Break prefix** — start a message with `. ` (configurable) to send it standalone
  (the prefix is stripped and no merge happens).
- **Manual edits are respected** — if you edit the merged base message, the next merge
  uses the edited text as the new baseline.
- **Music links** — a non-forwarded outgoing message containing exactly one explicitly
  written Spotify or Yandex Music URL is routed through
  [@OdesliBot](https://t.me/odesli_bot); surrounding text is allowed, while hidden links
  and messages with multiple URLs are left unchanged. The result is posted back to the
  original chat. Bot responses are matched to requests by the bot's reply (falling back
  to oldest-first when the bot doesn't reply to a specific message).

## Local Development

Create `.env` from `.env.example`, then set your Telegram API id and hash.

```bash
uv sync --locked --all-groups
uv run taid  # first run: prompts for phone/login code to create the session
```

The session file (default `./data/taid.session`, relative to the working directory) is
reused on subsequent runs, so interactive login is only needed once. The parent
directory (`data/`) must exist before the first run (`mkdir -p data`).

Checks:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run pytest
```

## Configuration

All settings come from environment variables / `.env` (see `.env.example`):

| Variable | Default | Description |
| --- | --- | --- |
| `APP_LOG_LEVEL` | `INFO` | Log level for taid (Telethon is muted to `WARNING` unless `DEBUG`). |
| `TELEGRAM_API_ID` | — | Telegram API id (required). |
| `TELEGRAM_API_HASH` | — | Telegram API hash (required). |
| `TELEGRAM_SESSION_PATH` | `./data/taid.session` | SQLite session file path (relative to the working directory). |
| `MERGE_ENABLED` | `true` | Enable message merging. |
| `MERGE_TIMEOUT_SECONDS` | `30` | Window within which messages merge. |
| `MERGE_BREAK_PREFIX` | `. ` | Prefix that disables merging for one message. |
| `MUSIC_LINKS_ENABLED` | `true` | Enable music link normalization. |
| `MUSIC_LINKS_BOT_USERNAME` | `odesli_bot` | Odesli bot username. |
| `MUSIC_LINKS_TIMEOUT_SECONDS` | `45` | Wait for the bot before giving up. |
| `MUSIC_LINKS_ERROR_CHAT` | `me` | Where timeout errors are reported. |

## Deployment

### Docker Compose (recommended)

```bash
cp .env.example .env
# edit .env with your API id/hash
docker compose run --rm taid  # one-time interactive login (creates ./data/taid.session)
docker compose up -d --build
```

The session lives in the mounted `./data` volume (`/data` inside the container); the
path is set to `/data/taid.session` in `docker-compose.yml` regardless of `.env`. The
container runs as the host user's uid (`${UID:-1000}`) so the bind mount stays writable
— if your uid is not 1000, export `UID` and `GID` before running compose. A
systemd wrapper for Compose is provided in `deploy/taid-docker.service`.

### Direct systemd (no Docker)

Install the project (e.g. under `/opt/taid`), place `.env` and a writable `data/`
directory there, then install `deploy/taid.service` and run it once interactively to
authenticate:

```bash
sudo systemctl edit --force --full taid.service  # adjust WorkingDirectory/ExecStart if needed
sudo -u taid uv run taid  # one-time login
sudo systemctl enable --now taid
```

## Architecture

```
src/taid/
  app.py                composition root: build client, register features, run
  __main__.py           entry point (asyncio.run)
  logging_setup.py      stdlib logging with a colored console formatter
  telethon_factory.py   TelegramClient construction + lifecycle (the only Telethon boundary)
  settings/             pydantic-settings models split by domain
  models.py             typed domain objects (MessageRef, MessageSnapshot, ChatRef)
  ports.py              TelegramPort / TelegramClientPort Protocols (the seams)
  sent_registry.py      bounded registry of taid's own sends, shared by all features
  infra/
    telethon_adapter.py TelethonPort implementation over Telethon 1.44
  features/
    message_merge.py    MessageMergeService (pure logic) + MessageMergeHandler
    music_links.py      MusicLinkService + MusicLinkHandler
```

Feature logic (`*Service`) is pure and fully unit-tested; `*Handler` classes wire
Telethon events to a service through the `TelegramPort` Protocol, so the Telethon API
surface is confined to `infra/telethon_adapter.py` and `telethon_factory.py`.
