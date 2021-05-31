# taid

**TelegramAID** is tool for more convenient chatting in Telegram. This's fork of [opentfd](https://github.com/SlavikMIPT/opentfd) (now have some bugs and doesn't work properly).

### Functions:

- Merges series of Telegram messages if there is a pause of less than 30 seconds (you can change this) between them.
- Bash assistant — type `!bash command` in any chat to execute command on your host.
- Getting available music-links from [@OdesliBot](https://t.me/odesli_bot), when you send links from Spotify or Yandex.Music, and replacing you message to this links.

### To-do:

- [ ] Fix the problems:
	- [x] Ignoring incoming message in the chat.
	- [ ] False deleting of messages after forwarding.
- [x] Forwading messages with music-links to [@OdesliBot](https://t.me/odesli_bot) and replacing your message to bot's message.
	- [ ] Fix the double sending to [@OdesliBot](https://t.me/odesli_bot) in OdesliBot's chat.
- [ ] Docker image with tool.

### Install

1. `pip3 install -r reqirements.txt`
2. Add [API token and hash](https://core.telegram.org/api/obtaining_api_id) to secret.template.py and rename it to secret.py
3. `python3 taid.py`

### Dependencies

* Latest version of Telethon: http://telethon.readthedocs.io/en/stable/
