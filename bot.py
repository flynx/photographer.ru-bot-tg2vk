#!/usr/bin/python3

# systemd service...
# see:
#   https://tecadmin.net/run-shell-script-as-systemd-service/
#   https://tecadmin.net/setup-autorun-python-script-using-systemd/

import telebot
import vk_api
import requests
import io
import datetime
import re


# Токен бота в Телеграме
telegram_token = open('telegrm.token', 'r').read().strip()

# Токен группы ВКонтакте
vk_token = open('vk.token', 'r').read().strip()

# ID группы ВКонтакте
vk_group_id = open('vk_group.id', 'r').read().strip()


def getDate():
    return datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')

TEXT_SNIP = 50

# CONTENT_TYPES = [
#     "text", 
#     "audio", 
#     "document", 
#     "photo", 
#     "sticker", 
#     "video", 
#     "video_note", 
#     "voice", 
#     "location", 
#     "contact",
#     "new_chat_members",
#     "left_chat_member",
#     "new_chat_title",
#     "new_chat_photo",
#     "delete_chat_photo",
#     "group_chat_created",
#     "supergroup_chat_created",
#     "channel_chat_created",
#     "migrate_to_chat_id",
#     "migrate_from_chat_id",
#     "pinned_message",
# ]
TRACK_TYPES = [
    "text", 
    "photo", 
]

# Создаем объекты бота в Телеграме и API ВКонтакте
bot = telebot.TeleBot(telegram_token)
vk_session = vk_api.VkApi(token=vk_token)
vk = vk_session.get_api()

print(f'{getDate()}: Bot started...')


# XXX TODO:
#   - for some reason this does not see attached images at all...
#        message.photo == None...
#   - get telegram formatting (markdown???)
#       (see notes for: repost_photo_to_vk(..) below)
@bot.channel_post_handler(content_types=['text'])
def repost_text_to_vk(message):
    print(f"{getDate()}: Received message: {(message.text or '')[:TEXT_SNIP]}")

    attachments = []

    # Если в сообщении есть изображения, загружаем их в ВКонтакте
    # XXX for some reason we are not getting any photos here...
    print(f"  --- PHOTOS: {message.photo}")
    if message.photo:
        for photo in message.photo:
            # Скачиваем фото
            file_info = bot.get_file(photo.file_id)
            photo_url = "https://api.telegram.org/file/bot{}/{}".format(
                telegram_token, file_info.file_path)

            # Загружаем фото в ВКонтакте
            photo_id = upload_photo_to_vk(vk, photo_url)
            attachments.append(photo_id)

            print(f"  --- PHOTO {len(attachments)}: {attachments[-1]}")

    # Публикуем сообщение в группе ВКонтакте
    vk.wall.post(
        owner_id="-" + vk_group_id,
        message=message.text,
        attachments=",".join(attachments),
    )
    print(f"{getDate()}: Posted message: {(message.text or '')[:TEXT_SNIP]}")


# XXX HACK -- mini/cute html2 -> markdown parser...
def html2md(text):
    text = re.sub(r'<b>(.*)</b>', r'*\1*', text, flags=re.I|re.M)
    text = re.sub(r'<i>(.*)</i>', r'_\1_', text, flags=re.I|re.M)
    text = re.sub(r'<a\s+[ˆ>]*href="(.*)"[ˆ>]*>(.*)</a>', r'[\2](\1)', text, flags=re.I|re.M)
    return text


# see:
#   https://github.com/python273/vk_api/blob/master/examples/upload_photo.py
#   https://vk-api.readthedocs.io/en/latest/upload.html (see: photo_wall(..))
#
# XXX TODO
#   - multiple images per post are treated  as separate posts for some reason -- need 
#       to find a way to group...
#   - get telegram formatting:
#       - links
#       - header
#       - ...
#   - Q: is the largest image alwways the last??
#       ...check telegram API
@bot.channel_post_handler(content_types=['photo'])
def repost_photo_to_vk(message):
    print(f"{getDate()}: Received photo: {(message.caption or '')[:TEXT_SNIP]}")

    # download images (memory)...
    upload = vk_api.VkUpload(vk_session)
    ids = []
    photo = message.photo[-1]
    file_info = bot.get_file(photo.file_id)
    photo_url = "https://api.telegram.org/file/bot{}/{}".format(
        telegram_token, 
        file_info.file_path)
    response = requests.get(photo_url)

    # upload images...
    photo_info = upload.photo_wall(
        io.BytesIO(response.content),
        group_id=vk_group_id)[0]

    ids += [
        "photo{}_{}".format(
            photo_info["owner_id"], 
            photo_info["id"]) ]

    print(f"  --- PHOTO {len(ids)}: {ids[-1]}")

    vk.wall.post(
        owner_id="-" + vk_group_id,
        message=message.caption,
        #message=message.html_caption,
        attachments=",".join(ids))

    print(f"{getDate()}: Posted photo: {(message.caption or '')[:TEXT_SNIP]}")


# Запускаем бота в Телеграме с измененными параметрами опроса
bot.polling(none_stop=False, interval=0, timeout=60)


