# error_handling.py
import logging
from slack_sdk import WebClient

logging.basicConfig(filename='app.log', level=logging.ERROR)

def log_error(error_message):
    logging.error(error_message)

def send_alert(error_message):
    slack_token = 'your_slack_token'
    client = WebClient(token=slack_token)

    try:
        response = client.chat_postMessage(
            channel='#alerts',
            text=f'An error occurred: {error_message}'
        )
    except SlackApiError as e:
        logging.error(f'Failed to send Slack alert: {e}')
