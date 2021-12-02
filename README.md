# taid

**TelegramAID** is tool for more convenient chatting in Telegram. This's fork of [opentfd](https://github.com/SlavikMIPT/opentfd) (now have some bugs and doesn't work properly).

### Functions

- Merges series of Telegram messages if there is a pause of less than 30 seconds (you can change this) between them.
- Bash assistant — type `!bash command` in any chat to execute command on your host (Docker version is limited by container).
- Getting available music-links from [@OdesliBot](https://t.me/odesli_bot), when you send links from Spotify or Yandex.Music, and replacing you message to this links.

### Install and usage

1. Add [API token and hash](https://core.telegram.org/api/obtaining_api_id) to `secret.template.py` and rename it to `secret.py`.
2. `pip3 install -r reqirements.txt`
3. `python3 taid.py`
4. Log in.

### Docker install and usage

1. Same as first point above.
2. `docker build -t taid .`
3. `docker run --name=taid -it taid`
4. Log in.
5. Detach container by `Ctrl`+`P`.
6. You can stop container by `docker stop taid` and start by `docker start taid` (don't use `run` because it will make new container).

### Dependencies

- Latest version of Telethon: http://telethon.readthedocs.io/en/stable/
