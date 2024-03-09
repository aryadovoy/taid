import asyncio
from time import time
from contextlib import suppress

from telethon import TelegramClient, events, custom
import secret

default_proxy = None

client = TelegramClient('taid_session', secret.api_id, secret.api_hash).start()
chat_id = 1
state = None
state_time = 0
msg_flag = True
time_flag = False
MERGE_TIMEOUT = 30


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
async def breaker(event: custom.Message):
    global msg_flag
    global chat_id
    if chat_id == event.chat_id:
        msg_flag = False


@client.on(events.NewMessage(outgoing=True))
async def merger(event: custom.Message):
    global chat_id
    global state
    global state_time
    global time_flag
    global msg_flag
    global MERGE_TIMEOUT
    event_time = int(time())
    chat_id = event.chat_id
    if state != None:
        if abs(event_time - state_time) < MERGE_TIMEOUT:
            time_flag = True
            state_time = int(time())
        else:
            time_flag = False
    else:
        state = event
        state_time = int(time())
    if state.chat_id != event.chat_id or \
       (event.media or event.fwd_from or event.via_bot_id or \
       event.reply_to_msg_id or event.reply_markup):
        msg_flag = False
    elif event.text.startswith('.'):
        state = await event.edit(event.text[2:])
        msg_flag = False
    if time_flag and msg_flag:
        state.message.text = '{0}\n{1}'.format(state.message.text, event.message.text)
        await state.edit(state.message.text)
        await event.delete()
    else:
        state = event
        msg_flag = True
        state_time = int(time())


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
