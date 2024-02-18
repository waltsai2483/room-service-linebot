import os

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError, LineBotApiError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, ButtonsTemplate, MessageTemplateAction
)

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import insert

db = SQLAlchemy()

app = Flask(__name__)
app.config['DEBUG'] = True
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'postgresql://{}:{}@dpg-cn8v86i1hbls73ddaj9g-a.singapore-postgres.render.com:5432/room_service_line_db'.format(
    os.getenv('DB_USERNAME', None), os.getenv('DB_PASSWORD', None))
db.init_app(app)


class Personnel(db.Model):
    __tablename__ = 'personnels'
    userid = db.Column(db.String(33), primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    job_code = db.Column(db.Integer, nullable=True)

    def __init__(self, id, name, job):
        self.userid = id
        self.username = name
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
    if event.message.text == '[設定房務頻道]':
        line_bot_api.reply_message(event.reply_token, TemplateSendMessage(
            alt_text='請設定房務通知的頻道',
            template=ButtonsTemplate(
                title='房務頻道',
                text='請設定您的職位，以便第一時間推播有關客房狀態~',
                actions=[
                    MessageTemplateAction(
                        label='櫃台人員',
                        text='[設定頻道1]'
                    ),
                    MessageTemplateAction(
                        label='房務人員',
                        text='[設定頻道2]'
                    ),
                    MessageTemplateAction(
                        label='查房人員',
                        text='[設定頻道3]'
                    )
                ]
            )
        ))
    elif '設定頻道' in event.message.text:
        code = int(event.message.text[5])
        try:
            user = Personnel.query.filter_by(userid=event.source.user_id).first()
            if user is not None:
                user.job_code = code
            else:
                db.session.add(Personnel(event.source.user_id, line_bot_api.get_profile(event.source.user_id).display_name, code))
            db.session.commit()
        except LineBotApiError:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='無法'))

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))


if __name__ == "__main__":
    app.run()
