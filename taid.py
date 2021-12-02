import asyncio
from time import time, sleep
from contextlib import suppress

from telethon import TelegramClient, events, sync, errors, custom
from proxy import mediatube_proxy
import secret
import getopt
import re
import sys

default_proxy = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'p', ['proxy'])
    for opt, arg in opts:
        if opt in ('-p', '--proxy'):
            default_proxy = mediatube_proxy
except getopt.GetoptError:
    sys.exit(2)

client = TelegramClient('taid_session', secret.api_id, secret.api_hash, proxy=default_proxy).start()
chat_id = 1
last_msg = None
last_msg_time = 0
MERGE_TIMEOUT = 30
merge_semaphore = asyncio.Semaphore(value=1)


@client.on(events.NewMessage(outgoing=True, pattern=r'^.*(open\.spotify\.com|music\.yandex\.ru).*'))
async def get_link(event: custom.Message):
    await client.send_message('odesli_bot', event.message)
    await event.delete()


@client.on(events.NewMessage(chats='odesli_bot'))
async def replace_message(event: custom.Message):
    global chat_id
    await client.send_message(chat_id, event.message)
    chat_id = 1


@client.on(events.NewMessage(incoming=True))
async def break_updater(event: events.NewMessage.Event):
    global last_msg, last_msg_time
    with suppress(Exception):
        if event.chat:
            if event.chat.bot:
                return
    with suppress(Exception):
        if last_msg:
            if event.chat_id == last_msg.chat_id:
                last_msg = None
                last_msg_time = 0


@client.on(events.NewMessage(outgoing=True))
async def merger(event: custom.Message):
    global chat_id
    global last_msg
    global last_msg_time
    global MERGE_TIMEOUT
    event_time = int(time())
    if (event.media or event.fwd_from or event.via_bot_id or
        event.reply_to_msg_id or event.reply_markup):
        last_msg = None
    elif last_msg is None:
        last_msg = event
    elif last_msg is None or event.text.startswith('.'):
        if event.text.startswith('.'):
            last_msg = await event.edit(event.text[2:])
        else:
            last_msg = event
        last_msg_time = event_time
    elif last_msg.to_id == event.to_id:
        if event_time - last_msg_time < MERGE_TIMEOUT:
            try:
                await merge_semaphore.acquire()
                last_msg = await last_msg.edit('{0}\n{1}'.format(last_msg.text, event.text))
                last_msg_time = event_time
                await event.delete()
            finally:
                merge_semaphore.release()
        else:
            last_msg = event
            last_msg_time = event_time
    else:
        last_msg = event
        last_msg_time = event_time


async def run_command_shell(cmd, e):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    msg_text = ''
    msg_text_old = ''
    blank_lines_count = 0
    lines_max = 20
    start_time = time()
    msg_lines = []
    await asyncio.sleep(1)
    while time() - start_time <= 60:
        for i in range(lines_max):
            data = await process.stdout.readline()
            line = data.decode().strip()
            if blank_lines_count <= 5:
                if line == '':
                    blank_lines_count += 1
                if line != '':
                    blank_lines_count = 0
                    msg_lines.append(line)
            else:
                break
        msg_lines = msg_lines[-lines_max:]
        msg_text = ''
        for ln in msg_lines:
            msg_text += f'`${ln}`\n'
        with suppress(Exception):
            if msg_text_old != msg_text:
                await e.edit(msg_text, parse_mode='Markdown')
                msg_text_old = msg_text
        await asyncio.sleep(5)
        if blank_lines_count >= 5:
            break

    msg_text += '$-----TERMINATED-----'
    await e.edit(msg_text)
    return await process.kill()


@client.on(events.NewMessage(pattern=r'^!bash (.+)', outgoing=True))
async def bash(e: events.NewMessage.Event):
    cmd = e.pattern_match.group(1)
    print(cmd)
    try:
        await asyncio.wait_for(run_command_shell(cmd, e), timeout=60.0)
    except asyncio.TimeoutError:
        print('timeout!')


client.run_until_disconnected()
