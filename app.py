import os
import urllib.parse

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

db = SQLAlchemy()
notify_client_id = os.getenv('LINE_NOTIFY_CLIENT_ID', None)
notify_client_secret = os.getenv('LINE_NOTIFY_CLIENT_SECRET', None)

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
    job_code = db.Column(db.Integer, nullable=False)

    def __init__(self, userid, name, job):
        self.userid = userid
        self.username = name
        self.job_code = job


class RoomState(db.Model):
    __tablename__ = 'room_states'
    userid = db.Column(db.String(33), primary_key=True)

    def __init__(self, userid):
        self.userid = userid


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


waiting_room_notification = False
room_number = -1


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text == '[設定房務頻道]':
        RoomState.query.filter_by(userid=event.source.user_id).delete()
        line_bot_api.reply_message(event.reply_token, TemplateSendMessage(
            alt_text='請設定房務通知的頻道',
            template=ButtonsTemplate(
                title='房務頻道',
                text='請設定您的職位，以便第一時間推播客房狀態~',
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
    elif '[設定頻道' in event.message.text:
        RoomState.query.filter_by(userid=event.source.user_id).delete()
        code = int(event.message.text[5])
        try:
            user = Personnel.query.filter_by(userid=event.source.user_id).first()
            if user is not None:
                user.job_code = code
            else:
                db.session.add(
                    Personnel(event.source.user_id, line_bot_api.get_profile(event.source.user_id).display_name, code))
            db.session.commit()

            data = {
                'response_type': 'code',
                'client_id': notify_client_id,
                'redirect_uri': 'https://room-service-linebot.onrender.com/callback/notify',
                'scope': 'notify',
                'state': event.source.user_id
            }
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f'設定完成，初次設定請點選此連結完成Line Notify綁定: https://notify-bot.line.me/oauth/authorize?{urllib.parse.urlencode(data)}'))
        except LineBotApiError:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='設定頻道失敗!'))
    elif event.message.text == '[傳送客房通知]':
        job = Personnel.query.filter_by(userid=event.source.user_id).first().job_code
        if job == 3:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='此職位暫無通知其他人員之權限'))
        user = RoomState.query.filter_by(userid=event.source.user_id).first()
        if user is None:
            db.session.add(RoomState(event.source.user_id))
            db.session.commit()

        if job == 1:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請填入已退房的房間號碼:'))
        elif job == 2:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請填入整理完成的房間號碼:'))
    elif event.message.text.isnumeric():
        job = Personnel.query.filter_by(userid=event.source.user_id).first().job_code
        user = RoomState.query.filter_by(userid=event.source.user_id).first()
        if user is not None:
            RoomState.query.filter_by(userid=event.source.user_id).delete()
            for personnel in Personnel.query.all():
                if personnel.job_code == job + 1:
                    line_bot_api.push_message(to=personnel.userid, messages=TextSendMessage(text='[通知] {}號房已{}'.format(event.message.text, '退房' if job == 1 else '整理完畢')))
            db.session.commit()
    else:
        RoomState.query.filter_by(userid=event.source.user_id).delete()


if __name__ == "__main__":
    app.run()
