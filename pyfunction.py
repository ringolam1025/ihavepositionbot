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