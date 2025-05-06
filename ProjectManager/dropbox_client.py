import dropbox
import os
from django.conf import settings

def get_dropbox_client():
    return dropbox.Dropbox(
        oauth2_refresh_token=os.getenv('DROPBOX_REFRESH_TOKEN'),
        app_key=os.getenv('DROPBOX_APP_KEY'),
        app_secret=os.getenv('DROPBOX_APP_SECRET')
    )