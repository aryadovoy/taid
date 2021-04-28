# taid

**TelegramAID** is tool for more convenient chatting in Telegram. This's fork of [opentfd](https://github.com/SlavikMIPT/opentfd).

### Functions:

- Merges series of Telegram messages if there is a pause of less than 30 seconds between them.
- Integrated Google Translator (just put /en in the end of message to translate into English or /ru to translate into russian). Full list of supported languages you can see in supported_langs at opentfd.py.
- Bash assistant — type `!bash command` in any chat to execute command on your host.

### To-do:

- [ ] Fix the problems:
	- [ ] Ignoring incoming message in the chat.	
	- [ ] False deleting of messages instead of merging.
- [x] Forwading messages with music-links to [@OdesliBot](https://t.me/odesli_bot) and replacing your message to bot's message.
	- [ ] Fix the double sending to [@OdesliBot](https://t.me/odesli_bot) in OdesliBot's chat.
- [ ] Docker image with tool.

### Install

1. `pip3 install -r reqirements.txt`
2. Add [API token and hash](https://core.telegram.org/api/obtaining_api_id) to secret.template.py and rename it to secret.py
3. `python3 taid.py`

### Dependencies

* Latest version of Telethon: http://telethon.readthedocs.io/en/stable/
* Translator: https://github.com/mouuff/mtranslate.git	
