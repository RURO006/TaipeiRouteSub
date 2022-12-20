
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib


def getSetting() -> dict:
    '''取得設定檔'''
    return json.loads(readFile("setting.json"))


def writeToFile(fileName, obj):
    if (type(obj).__name__ == "str"):
        text = obj
    else:
        text = json.dumps(obj, ensure_ascii=False)
    os.makedirs(os.path.dirname(fileName), exist_ok=True)
    with open(fileName, "w", encoding="utf8") as f:
        f.write(text)
        f.flush()
        f.close()


def readFile(fileName):
    OUT = None
    with open(fileName, "r+b") as f:
        OUT = f.read().decode("utf8")
        f.close()
    return OUT


def sendEmail(recipient, msg):
    '''寄信，純文字的信'''
    setting = getSetting()
    content = MIMEMultipart()  # 建立MIMEMultipart物件
    content["subject"] = msg  # 郵件標題
    content["from"] = setting["email"]  # 寄件者
    content["to"] = recipient  # 收件者
    content.attach(MIMEText(msg))  # 郵件內容
    # 設定SMTP伺服器
    with smtplib.SMTP(host=setting["emailSmtp"], port=setting["emailSmtpPort"]) as smtp:
        try:
            smtp.ehlo()  # 驗證SMTP伺服器
            smtp.starttls()  # 建立加密傳輸
            # 登入寄件者gmail
            smtp.login(setting["email"], setting["emailPassword"])
            smtp.send_message(content)  # 寄送郵件
        except Exception as e:
            print("Error message: ", e)
