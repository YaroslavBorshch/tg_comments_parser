from app import db
from datetime import datetime


class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return '<User: {}>'.format(self.username)


class Tg_channels(db.Model):
    __tablename__ = "tg_channels"
    """
    Telegram-channels model
    """
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.String(32), index=True, unique=True)
    linked_chat_id = db.Column(db.String(32), index=True)
    linked_chat_link = db.Column(db.String(32), index=True)
    channel_title = db.Column(db.String(64), index=True, unique=True)
    channel_description = db.Column(db.String(512))
    channel_username = db.Column(db.String(64), index=True, unique=True)
    channel_subs_count = db.Column(db.Integer)
    channel_generated_link = db.Column(db.String(120))
    channel_posts_per_day = db.Column(db.Integer)
    channel_comments_per_post = db.Column(db.Integer)
    channel_views_per_post = db.Column(db.Integer)
    channel_posts_count = db.Column(db.Integer)
    channel_time_delta = db.Column(db.Integer)
    #
    channel_posts = db.relationship('Tg_posts', backref='channel', lazy='dynamic')
    channel_comments = db.relationship('Tg_comments', backref='channel', lazy='dynamic')
    #
    last_update = db.Column(db.DateTime, index=True, default=datetime.now)
    time_create = db.Column(db.DateTime, index=True, default=datetime.now)


class Tg_media_types(db.Model):
    __tablename__ = "tg_media_types"
    """
    Telegram-media types models
    """
    id = db.Column(db.Integer, primary_key=True)
    mediaType_title = db.Column(db.String(32), index=True, unique=True)
    mediaType_settings = db.Column(db.String(128), index=True)
    linked_posts = db.relationship('Tg_posts', backref='post_media_type', lazy='dynamic')
    linked_comments = db.relationship('Tg_comments', backref='comment_media_type', lazy='dynamic')
    #
    time_create = db.Column(db.DateTime, index=True, default=datetime.now)


class Tg_file_archive(db.Model):
    __tablename__ = "tg_file_archive"
    """
    Telegram-files storage
    """
    id = db.Column(db.Integer, primary_key=True)
    file_hash = db.Column(db.String(128), index=True, unique=True)
    road_to_file = db.Column(db.String(128), index=True, unique=True)
    is_downloaded = db.Column(db.Boolean)
    #
    linked_posts = db.relationship('Tg_posts', backref='post_file', lazy='dynamic')
    comments_posts = db.relationship('Tg_comments', backref='comment_file', lazy='dynamic')
    #
    time_create = db.Column(db.DateTime, index=True, default=datetime.now)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'file_hash': self.file_hash,
            'road_to_file': self.road_to_file,
            'is_downloaded': self.is_downloaded,
            'linked_posts': self.linked_posts.first().post_id if self.linked_posts.first() else None,
            'comments_posts': self.comments_posts.first().comment_id if self.comments_posts.first() else None,
            'time_create': self.time_create
        }


class Tg_posts(db.Model):
    __tablename__ = "tg_posts"
    """
    Telegram-posts model
    """
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.String(32), index=True)
    channel_id = db.Column(db.String(32), db.ForeignKey('tg_channels.channel_id'))
    post_date = db.Column(db.DateTime, index=True, default=None)
    post_media_type_id = db.Column(db.Integer, db.ForeignKey('tg_media_types.id'))
    post_file_id = db.Column(db.Integer, db.ForeignKey('tg_file_archive.id'))
    post_likes = db.Column(db.String(256))
    post_text = db.Column(db.Text)
    post_comments = db.relationship('Tg_comments', backref='posts', lazy='dynamic')
    post_likes_count = db.Column(db.Integer)
    post_views = db.Column(db.Integer)
    post_replies = db.Column(db.Integer)
    post_is_parsed = db.Column(db.Boolean)
    post_hours_diff = db.Column(db.Float)
    #
    time_create = db.Column(db.DateTime, index=True, default=datetime.now)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'channel_id': self.channel_id,
            'post_date': self.post_date,
            'post_media_type_id': self.post_media_type_id,
            'post_file_id': self.post_file_id,
            'post_likes': self.post_likes,
            'post_text': self.post_text,
            'post_comments': self.post_comments,
            'post_likes_count': self.post_likes_count,
            'post_views': self.post_views,
            'post_replies': self.post_replies,
            'post_is_parsed': self.post_is_parsed
        }

    @property
    def alt_serialize(self):
        trans_serialize = self.serialize
        trans_serialize['post_comments'] = 'unserialized'
        return trans_serialize


class Tg_comments(db.Model):
    __tablename__ = "tg_comments"
    """
    Telegram-comments model
    """
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.String(32), index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('tg_posts.id'))
    channel_id = db.Column(db.String(32), db.ForeignKey('tg_channels.channel_id'))
    comment_linked_channel_id = db.Column(db.String(32))
    comment_date = db.Column(db.DateTime, index=True, default=None)
    comment_media_type_id = db.Column(db.Integer, db.ForeignKey('tg_media_types.id'))
    comment_file_id = db.Column(db.Integer, db.ForeignKey('tg_file_archive.id'))
    comment_likes = db.Column(db.String(256), index=True)
    comment_text = db.Column(db.Text)
    comment_link = db.Column(db.String(128))
    comment_likes_count = db.Column(db.Integer)
    comment_is_posted = db.Column(db.Boolean)
    comment_poster_display = db.Column(db.String(128))
    comment_poster_id = db.Column(db.String(32), db.ForeignKey('tg_users.user_id'))
    #
    time_create = db.Column(db.DateTime, index=True, default=datetime.now)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'comment_id': self.comment_id,
            'post_id': self.post_id,
            'channel_id': self.channel_id,
            'comment_linked_channel_id': self.comment_linked_channel_id,
            'comment_date': self.comment_date,
            'comment_media_type_id': self.comment_media_type_id,
            'comment_file_id': self.comment_file_id,
            'comment_likes': self.comment_likes,
            'comment_text': self.comment_text,
            'comment_link': self.comment_link,
            'comment_likes_count': self.comment_likes_count,
            'comment_is_posted': self.comment_is_posted,
            'comment_poster_display': self.comment_poster_display,
            'comment_poster_id': self.comment_poster_id,
            'time_create': self.time_create,
        }

    @property
    def alt_serialize(self):
        return self.serialize


class Tg_users(db.Model):
    __tablename__ = "tg_users"
    """
    Telegram-users model
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(32), index=True, unique=True)
    user_firstname = db.Column(db.String(128))
    user_lastname = db.Column(db.String(128))
    user_username = db.Column(db.String(128))
    #
    user_comments = db.relationship('Tg_comments', backref='comment', lazy='dynamic')
    #
    time_create = db.Column(db.DateTime, index=True, default=datetime.now)
