# youtube_upload.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

def upload_video(video_path):
    # YouTube APIを使用して動画をアップロードするロジックを実装
    credentials = Credentials.from_authorized_user_file('credentials.json', ['https://www.googleapis.com/auth/youtube.upload'])
    youtube = build('youtube', 'v3', credentials=credentials)

    request_body = {
        'snippet': {
            'title': 'Generated Dance Video',
            'description': 'This video was automatically generated.',
            'tags': ['dance', 'mmd', 'unity', 'avatar'],
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'public'
        }
    }

    media = MediaFileUpload(video_path)

    try:
        response = youtube.videos().insert(
            part='snippet,status',
            body=request_body,
            media_body=media
        ).execute()

        video_id = response['id']
        return video_id

    except HttpError as e:
        print(f'An error occurred: {e}')
        return None
