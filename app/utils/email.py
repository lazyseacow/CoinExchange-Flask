from threading import Thread
from flask import current_app
from flask_mail import Message
from datetime import datetime
from app import mail


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(to, phone, mailcode):
    """
    使用新线程异步发送邮箱
    :param to: 收件人
    :param phone:收件人注册时所填写手机号码
    :param mailcode: 生成的邮箱验证码
    :return: 执行线程
    """
    app = current_app._get_current_object()
    msg = Message(current_app.config['FLASK_MAIL_SUBJECT_PREFIX'] + '您的帐号注册验证码',
                  sender=app.config['FLASK_MAIL_SENDER'], recipients=[to])
    msg.body = 'sent by flask-mail'
    msg.html = '''
    <h1>
        亲爱的 {phone},
    </h1>
    <h3>
        欢迎来到 <b>Flask-Test-Project</b>!
    </h3>
    <p>
        您的验证码为 &nbsp;&nbsp; <b>{mailcode}</b> &nbsp;&nbsp; 赶快去完善注册信息吧！！！
    </p>

    <p>感谢您的支持和理解</p>
    <p>来自：Flask-Test-Project</p>
    <p><small>{time}</small></p>
    '''.format(phone=phone, mailcode=mailcode, time=datetime.utcnow())
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
