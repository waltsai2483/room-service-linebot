import os

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

app = Flask(__name__)
app.config['DEBUG'] = True
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'postgresql://{}:{}@dpg-cn8v86i1hbls73ddaj9g-a.singapore-postgres.render.com:5432/room_service_line_db'.format(
    os.getenv('DB_USERNAME', None), os.getenv('DB_PASSWORD', None))
db.init_app(app)


class Personnel(db.Model):
    __tablename__ = 'personnels'
    line_id = db.Column(db.String(32), primary_key=True)
    account_name = db.Column(db.String(20), nullable=False)
    job_code = db.Column(db.Integer, nullable=False)

    def __init__(self, id, name, job):
        self.line_id = id
        self.account_name = name
        self.job_code = job


line_bot_api = LineBotApi(os.getenv('LINE_ACCESS_TOKEN', None))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET', None))


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    db.session.add(Personnel('dwa3erf', '蔡俊驊', 1))
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))


if __name__ == "__main__":
    app.run()
