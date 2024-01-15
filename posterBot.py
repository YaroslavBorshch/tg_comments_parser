import time
import telebot
from telebot import types
from parserConfig import BOT_API, MY_GROUP
from telebot.types import InputFile

from sqlalchemy import func, and_, or_
from app import db
from app.models import Tg_file_archive, Tg_comments, Tg_users

bot = telebot.TeleBot(BOT_API)


def post_to_group():
    postTypeCounter = 1
    while True:
        message_is_choosen = False
        get_message = None
        tryCount = 0
        while not message_is_choosen or tryCount < 10:
            get_message = Tg_comments.query.filter(Tg_comments.comment_is_posted == False).order_by(
                func.random()).first()
            if postTypeCounter % 3 == 0:
                get_message = Tg_comments.query.filter(
                    and_(Tg_comments.post_id == get_message.post_id, Tg_comments.comment_is_posted == False,
                         or_(Tg_comments.comment_media_type_id == 1, Tg_comments.comment_media_type_id == 4),
                         Tg_file_archive.is_downloaded == True)).join(Tg_file_archive, isouter=True).order_by(
                    Tg_comments.comment_likes_count.desc()).first()
            else:
                get_message = Tg_comments.query.filter(
                    and_(Tg_comments.post_id == get_message.post_id, Tg_comments.comment_is_posted == False,
                         Tg_comments.comment_file_id == None, Tg_comments.comment_text != None)).order_by(
                    Tg_comments.comment_likes_count.desc()).first()
            if get_message is not None:
                message_is_choosen = True
                print(get_message)
            tryCount += 1

        postTypeCounter += 1
        if get_message is None:
            continue

        print(str(get_message.post_id) + " : " + str(get_message.comment_id))
        # get_message = Tg_comments.query.get(157)
        get_user = Tg_users.query.filter_by(user_id=get_message.comment_poster_id).first()
        poster_name = ''
        if get_user.user_username:
            poster_name += "@" + get_user.user_username
        else:

            if get_user.user_firstname:
                poster_name += get_user.user_firstname
            if get_user.user_lastname:
                poster_name += " " + get_user.user_lastname
        message_string = "\u200B\n" + "<i>" + poster_name + ":</i> \n"

        if get_message.comment_text is not None:
            message_string += get_message.comment_text
        message_string += "\n\n" + get_message.comment_likes

        markup = types.InlineKeyboardMarkup()
        switch_button_comment = types.InlineKeyboardButton(text='💬', url=get_message.comment_link, show_arrow=False)
        post_link = get_message.comment_link.split("?")[0]
        switch_button_post = types.InlineKeyboardButton(text='📮', url=post_link, show_arrow=False)
        markup.add(switch_button_post, switch_button_comment)

        try:
            if get_message.comment_file_id is not None:
                get_file = Tg_file_archive.query.get(get_message.comment_file_id)
                if get_message.comment_media_type_id == 1:
                    bot.send_photo(chat_id=MY_GROUP, photo=InputFile(get_file.road_to_file), caption=message_string,
                                   reply_markup=markup, parse_mode='HTML')

                else:
                    bot.send_document(chat_id=MY_GROUP, document=open(get_file.road_to_file, 'rb'),
                                      caption=message_string, reply_markup=markup, parse_mode='HTML')
            else:
                bot.send_message(chat_id=MY_GROUP, text=message_string, reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            print(e)
            exit()

        get_message.comment_is_posted = True
        db.session.add(get_message)
        db.session.commit()
        time.sleep(420)


post_to_group()
