def initUserInfo(update):
    """ Init information"""
    userInfo = {
        "chat_id":update.message.chat.id,
        "message_id":update.message.message_id,
        "userid":update.message.from_user.id,
        "username":update.message.from_user.username,
        "first_name":update.message.from_user.first_name,
    }
    return userInfo

def initUserInfoFromReply(update):
    """ Init information FromReply """
    userInfo = {
        "chat_id":update.chat_instance,
        "message_id":update.message.message_id,
        "userid":update.from_user.id,
        "username":update.from_user.username,
        "first_name":update.from_user.first_name,        
    }
    return userInfo

def sentEmail(env, error):
    import smtplib, ssl
    from smtplib import SMTPException
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    res = {}
    SMTP = env["SMTP"]
    sender = env["FROMADDRESS"]
    receiver = env["TOADDRESS"]
    GMAILAPPPW = env["GMAILAPPPW"]

    text_type = 'plain' # or 'html'
    msg = MIMEText(str(error), text_type, 'utf-8')
    msg['Subject'] = 'IHavePositionBot - Error Log'
    msg['From'] = sender
    msg['To'] = receiver

    try:
        server = smtplib.SMTP_SSL(SMTP, 465)
        server.login(sender, GMAILAPPPW)
        server.send_message(msg)
        server.quit()
        res = {"msg":"Email Sent!", "error":str(error)}
    except Exception as ex:
        print("Something went wrong….",ex)
        res = {"msg":"Something went wrong", "error":"NA"}
        
    return res
    