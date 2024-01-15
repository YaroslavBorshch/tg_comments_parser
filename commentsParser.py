from app.models import Tg_channels, Tg_posts, Tg_media_types, Tg_file_archive, Tg_comments, Tg_users
from sqlalchemy import or_, and_, update, func, extract
from parserConfig import API_ID, API_HASH
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon import functions
from app import db
import asyncio
import time


class commentsParser:
    """
    парсинг комментов основываясь на истории, без привязки к событиям каналов
    """
    def __init__(self):
        self.savedMediaTypes = {}
        self.channels = []

    async def initial(self):
        mediaTypes = Tg_media_types.query.all()
        self.channels = Tg_channels.query.all()

        self.savedMediaTypes = {}
        for mediaType in mediaTypes:
            self.savedMediaTypes[str(mediaType.mediaType_title)] = mediaType


    async def add_channel(self, channel_to_parse):
        """
        функция добавления канала и анализа его скоропостинга
        """
        # Вначале обработаем полученную строку - это id канала или это ссылка на канал
        channel_dialog_name = channel_to_parse if channel_to_parse.find('/') == -1 else channel_to_parse.split(
            '/').pop()
        if channel_dialog_name.isnumeric():
            channel_dialog_name = int(channel_dialog_name)
        # Проверим есть ли у нас уже такой канал
        is_channel_saved = Tg_channels.query.filter((Tg_channels.channel_username == channel_dialog_name) | (
                Tg_channels.channel_id == channel_dialog_name)).first()

        if is_channel_saved is not None:
            return {'result': False, 'message': 'channel already exist'}

        # Если этот канал еще не добавлен, то добавляем его
        async with TelegramClient("my_account", API_ID, API_HASH) as tgApp:
            # получаем полную информацию о канале
            channel_info = await tgApp(functions.channels.GetFullChannelRequest(channel_dialog_name))
            # Считаем среднее количество постов за ? дней
            channel_time_delta = 20
            # Получаем дату до которой выкачиваем данные
            date_until_parse = datetime.now() - timedelta(days=channel_time_delta)

            replies_count = 0
            views_count = 0
            # Сперва получим id крайнего сообщения
            offset_post_min_id = await tgApp.get_messages(channel_info.full_chat.id, offset_date=date_until_parse)
            # Начиная с этого id получаем все сообщения
            channel_posts = await tgApp.get_messages(channel_info.full_chat.id, min_id=offset_post_min_id[0].id,
                                                     max_id=0)
            # Узнаем количество постов за переданный день
            post_count = len(channel_posts) if len(channel_posts) != 0 else 1
            # Подсчитываем комментарии постов
            for current_post in channel_posts:
                if current_post.replies:
                    replies_count += current_post.replies.replies
                if current_post.views:
                    views_count += current_post.views
            # Добавляем данные по каналу
            # with db.session.begin():
            add_channel = Tg_channels(
                channel_id=channel_info.full_chat.id,
                channel_time_delta=channel_time_delta,
                channel_subs_count=channel_info.full_chat.participants_count,
                linked_chat_id=channel_info.full_chat.linked_chat_id,
            )
            for current_channel in channel_info.chats:
                if channel_info.full_chat.linked_chat_id and current_channel.id == channel_info.full_chat.linked_chat_id:
                    add_channel.linked_chat_link = "https://t.me/c/" + str(current_channel.id)
                    continue
                if current_channel.id != channel_info.full_chat.id:
                    continue
                if current_channel.username is None:
                    if not current_channel.usernames:
                        continue
                    current_channel.username = list(current_channel.usernames)[0].username
                add_channel.channel_username = current_channel.username,
                add_channel.channel_generated_link = 'https://t.me/' + current_channel.username,
                add_channel.channel_title = current_channel.title,
            if channel_info.full_chat.about:
                add_channel.channel_description = channel_info.full_chat.about

            add_channel.channel_posts_per_day = post_count // add_channel.channel_time_delta
            if add_channel.channel_posts_per_day == 0:
                add_channel.channel_posts_per_day = 1
            add_channel.channel_comments_per_post = replies_count // post_count
            add_channel.channel_views_per_post = views_count // post_count
            if add_channel.channel_views_per_post == 0:
                add_channel.channel_views_per_post = 1
            add_channel.channel_posts_count = post_count

            db.session.add(add_channel)
            db.session.commit()
        return {'result': True, 'message': 'Channel is parsed'}

    async def add_posts(self):
        total_parse_count = 1
        async with TelegramClient("my_account", API_ID, API_HASH) as app:
            for channel_info in self.channels:
                if total_parse_count % 10 == 0:
                    print('flood await')
                    time.sleep(10)
                channel_posts = await app.get_messages(int(channel_info.channel_id),
                                                       limit=channel_info.channel_posts_per_day)
                total_parse_count += 1
                alreadyParsedPosts = {}

                getPosts = Tg_posts.query.filter_by(channel_id=channel_info.channel_id).all()
                if getPosts:
                    for post in getPosts:
                        alreadyParsedPosts[int(post.post_id)] = post

                for post_info in channel_posts:
                    if post_info.id in alreadyParsedPosts.keys():
                        print(str(post_info.id) + " is skiped")
                        continue

                    post_media_name = type(post_info.media).__name__
                    if post_media_name in self.savedMediaTypes.keys():
                        newMediaType = self.savedMediaTypes[post_media_name]
                    elif post_info.media:
                        newMediaType = Tg_media_types(
                            mediaType_title=post_media_name,
                            mediaType_settings=''
                        )
                        db.session.add(newMediaType)
                        db.session.commit()
                        self.savedMediaTypes[post_media_name] = newMediaType
                    else:
                        newMediaType = self.savedMediaTypes[str(None)]

                    post_file = None
                    if newMediaType.id == 1:
                        file_hash = post_info.media.photo.id
                        post_file = self.save_file(db=db, file_hash=str(file_hash), media_type=newMediaType.id)
                    elif newMediaType.id == 4:
                        file_hash = post_info.media.document.id
                        file_razsh = post_info.media.document.mime_type.split("/").pop()
                        post_file = self.save_file(db=db, file_hash=str(file_hash), media_type=newMediaType.id,
                                                   file_razsh=file_razsh)

                    new_post = Tg_posts(
                        post_id=post_info.id,
                        channel_id=channel_info.channel_id,
                        post_date=post_info.date,
                        post_media_type_id=newMediaType.id,
                        post_file_id=post_file,
                        post_views=post_info.views if post_info.views is not None else 0,
                        post_is_parsed=False,
                        post_hours_diff=48 / channel_info.channel_posts_per_day
                    )
                    if post_info.message:
                        new_post.post_text = post_info.message
                    elif post_info.media and hasattr(post_info.media, 'caption'):
                        new_post.post_text = post_info.media.caption
                    else:
                        new_post.post_text = ''

                    if post_info.replies:
                        new_post.post_replies = post_info.replies.replies
                    else:
                        new_post.post_replies = 0
                    likes_count = 0
                    if post_info.reactions:
                        for reaction in post_info.reactions.results:
                            likes_count += reaction.count
                    new_post.post_likes_count = likes_count
                    db.session.add(new_post)
                    db.session.commit()
        print("posts are parsed")

    async def parse_comments_loop(self):
        data_to_parse = db.session.query(Tg_channels.channel_id,
                                         Tg_channels.channel_username,
                                         Tg_posts.post_id,
                                         Tg_posts.id,
                                         Tg_channels.linked_chat_id
                                         ).join(Tg_posts).filter(
            and_(
                Tg_posts.post_is_parsed == False,
                or_(
                    (100 * Tg_posts.post_views / Tg_channels.channel_views_per_post >= 69),
                    (Tg_posts.post_views >= Tg_channels.channel_views_per_post),
                    func.trunc((
                       extract('epoch', datetime.now()) -
                       extract('epoch', Tg_posts.post_date)
                    ) / 3600) >= 48 / Tg_channels.channel_posts_per_day,
                ),
                Tg_posts.post_replies >= 2
            )
        ).all()
        async with TelegramClient("my_account", API_ID, API_HASH) as app:
            sleeper_count = 1
            for parse_info in data_to_parse:
                if sleeper_count % 10 == 0:
                    print('speem')
                    time.sleep(10)
                upd_post = Tg_posts.query.filter_by(post_id=str(parse_info[2])).first()
                upd_post.post_is_parsed = True
                db.session.add(upd_post)
                db.session.commit()
                parsed_post = await self.parse_comments(
                    channel_id=int(parse_info[0]),
                    post_id=int(parse_info[2]),
                    post_to_link=int(parse_info[3]),
                    linked_chat_id=int(parse_info[4]),
                    app=app,
                    db=db,
                    channel_username=parse_info[1])
                sleeper_count += 1

    async def parse_comments(self, channel_id: int, post_id: int, post_to_link, linked_chat_id, app, db,
                             channel_username):
        print("{channel_id}, {post_id}".format(channel_id=channel_id, post_id=post_id))
        try:
            post_comments = await app.get_messages(channel_id, reply_to=post_id, limit=None)
        except Exception as e:
            if e == 'The message ID used in the peer was invalid (caused by GetRepliesRequest)':
                print('without comments(')
                return post_id
        print('parse_is_started')
        best_five_comments = {}
        post_comments_dict = {}
        for comment in post_comments:
            if comment.reactions:
                smilyCount = 0
                smilyString = ""
                for smily in comment.reactions.results:
                    smilyCount += smily.count
                    try:
                        smilyString += f"{smily.reaction.emoticon}:{smily.count} "
                    except:
                        custom_smily_info = await app(
                            functions.messages.GetCustomEmojiDocumentsRequest(document_id=[smily.reaction.document_id]))
                        is_alt = 'custom:'
                        for custom_smily in custom_smily_info:
                            for atributes in custom_smily.attributes:
                                if hasattr(atributes, 'alt'):
                                    is_alt = atributes.alt
                        smilyString += f"{is_alt}:{smily.count} "
                if smilyCount != 0:
                    comment.reactions = smilyString
                    best_five_comments[comment.id] = smilyCount
                    post_comments_dict[comment.id] = comment

        best_five_comments = sorted(best_five_comments.items(), key=lambda item: item[1], reverse=True)[0:5]
        for comment_id in best_five_comments:
            comment = post_comments_dict[comment_id[0]]
            try:
                user_info = await app.get_entity(comment.from_id)
            except:
                user_info = await app.get_entity(comment.chat_id)
            is_user_saved = Tg_users.query.filter_by(user_id=str(user_info.id)).first()
            if is_user_saved is None:
                new_user = Tg_users(
                    user_id=user_info.id
                )
                if hasattr(user_info, 'title'):
                    new_user.user_username = user_info.title
                else:
                    if user_info.username:
                        new_user.user_username = user_info.username
                    if user_info.first_name:
                        new_user.user_firstname = user_info.first_name
                    if user_info.last_name:
                        new_user.user_lastname = user_info.last_name
                db.session.add(new_user)
                db.session.commit()
            else:
                new_user = is_user_saved

            new_comment = Tg_comments(
                comment_id=comment.id,
                post_id=post_to_link,
                channel_id=channel_id,
                comment_date=comment.date,
                comment_likes_count=comment_id[1],
                comment_likes=comment.reactions,
                comment_text=comment.text,
                comment_link="https://t.me/" + str(channel_username) + "/" + str(post_id) + "?comment=" + str(
                    comment_id[0]),
                comment_poster_display='',
                comment_poster_id=new_user.user_id,
                comment_is_posted=False,
                comment_linked_channel_id=linked_chat_id
            )

            if comment.text:
                new_comment.comment_text = comment.message
            elif comment.media and hasattr(comment.media, 'caption'):
                new_comment.comment_text = comment.media.caption
            else:
                new_comment.comment_text = ''
            comment_media_name = type(comment.media).__name__
            if comment_media_name in self.savedMediaTypes.keys():
                newMediaType = self.savedMediaTypes[comment_media_name]
            elif comment.media:
                newMediaType = Tg_media_types(
                    mediaType_title=comment_media_name,
                    mediaType_settings=''
                )
                db.session.add(newMediaType)
                db.session.commit()
                self.savedMediaTypes[comment_media_name] = newMediaType
            else:
                newMediaType = self.savedMediaTypes[str(None)]
            new_comment.comment_media_type_id = newMediaType.id

            comment_file = None
            if new_comment.comment_media_type_id == 1:
                file_hash = comment.media.photo.id
                comment_file = self.save_file(db=db, file_hash=str(file_hash),
                                              media_type=new_comment.comment_media_type_id)
            elif new_comment.comment_media_type_id == 4:
                file_hash = comment.media.document.id
                file_razsh = comment.media.document.mime_type.split("/").pop()
                comment_file = self.save_file(db=db, file_hash=str(file_hash),
                                              media_type=new_comment.comment_media_type_id, file_razsh=file_razsh)
            new_comment.comment_file_id = comment_file
            db.session.add(new_comment)
        db.session.commit()
        print('comments are parsed')
        return post_id

    def save_file(self, db, file_hash, media_type, file_razsh=None):
        new_file = None
        if media_type == 1:
            file_name = "storage/i_" + str(file_hash) + ".png"
        elif media_type == 4:
            razsh = file_razsh
            file_name = "storage/v_" + str(file_hash) + "." + str(razsh)

        isFileSaved = Tg_file_archive.query.filter_by(file_hash=str(file_hash)).first()
        if isFileSaved is None:
            new_file = Tg_file_archive(
                file_hash=str(file_hash),
                road_to_file=file_name,
                is_downloaded=0
            )
            db.session.add(new_file)
            db.session.commit()
            new_file = new_file.id
        else:
            new_file = isFileSaved.id
        return new_file

    async def save_parsed_files(self):
        undownloaded_files = Tg_file_archive.query.filter_by(is_downloaded=False).all()
        undownloaded_files = [x.serialize for x in undownloaded_files]
        recordsToUpdate = []
        count_sleeper = 1
        async with TelegramClient("my_account", API_ID, API_HASH) as app:
            print(len(undownloaded_files))
            for iFile in undownloaded_files:
                count_sleeper += 1
                print(count_sleeper)
                if count_sleeper % 10 == 0 or count_sleeper - 1 == len(undownloaded_files):
                    print('speem' + str(count_sleeper))
                    # with db.session as engine:
                    test = db.session.execute(
                        update(Tg_file_archive), recordsToUpdate
                    )
                    db.session.commit()
                    time.sleep(7)
                    recordsToUpdate = []

                # with db.session as engine:
                from_post = Tg_posts.query.filter_by(post_id=iFile['linked_posts']).first()
                from_comment = Tg_comments.query.filter_by(comment_id=iFile['comments_posts']).first()

                data_to_link = from_post if from_post is not None else from_comment
                data_to_link = data_to_link.alt_serialize
                del from_post
                del from_comment
                print(iFile['road_to_file'])
                if 'comment_link' in data_to_link:
                    # getComment = await app.get_messages(int(data_to_link.channel_id), reply_to=int(data_to_link.post_id), ids=int(data_to_link.comment_id), limit=1)
                    getComment = await app.get_messages(int(data_to_link['comment_linked_channel_id']),
                                                        ids=int(data_to_link['comment_id']), limit=1)
                else:
                    getComment = await app.get_messages(int(data_to_link['channel_id']),
                                                        ids=int(data_to_link['post_id']), limit=1)

                if getComment is not None:
                    if getComment.media and hasattr(getComment.media, 'document'):
                        getComment.media.document.attributes[0].supports_streaming = False
                    lets_download_file = await app.download_media(getComment, file=iFile['road_to_file'])
                else:
                    lets_download_file = True
                if lets_download_file:
                    recordsToUpdate.append({
                        "id": iFile['id'],
                        "is_downloaded": True,
                    })

