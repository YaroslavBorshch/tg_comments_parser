import os
from dotenv import load_dotenv
load_dotenv()

# tg-configuration
API_ID = os.environ.get('TG_API_ID')
API_HASH = os.environ.get('TG_API_HASH')
CHANNELS_LIST = os.environ.get('TG_CHANNELS_LIST')

BOT_API = os.environ.get('BOT_API')
MY_GROUP = os.environ.get('GROUP_ID')
