from app import app, db
from app.models import Tg_channels, Tg_posts, Tg_comments, Tg_file_archive, Tg_media_types


@app.shell_context_processor
def make_shell_context():
    return {'db': db,
            'Tg_channels': Tg_channels,
            'Tg_posts': Tg_posts,
            'Tg_comments': Tg_comments,
            'Tg_file_archive': Tg_file_archive,
            'Tg_media_types': Tg_media_types,
            }
