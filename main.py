#!/usr/bin/env python
# pylint: disable=W0613
# type: ignore[union-attr]

from cgi import print_arguments
import os
import logging
import logging.config
from pickle import FALSE, TRUE

# from typing import Tuple, Dict, Any
import datetime
import re

from dotenv import load_dotenv
config = load_dotenv(".env")

from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    Filters,
    CallbackQueryHandler,
    CallbackContext
)

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from pyfunction import *


# State definitions for descriptions conversation
SELECTING_FEATURE, TYPING = map(chr, range(6, 8))
# Meta states
STOPPING, SHOWING = map(chr, range(8, 10))

# Shortcut for ConversationHandler.END
END = ConversationHandler.END

(
    ZONE_RANGE,
    ACCEPTABLE_LOSS,
    FOLLOW_WOOD,
    CAPITAL,
    START_OVER,
    FEATURES,
    CURRENT_FEATURE,
    CURRENT_LEVEL,
) = map(chr, range(10, 18))

NAME = os.environ["NAME"]
TOKEN = os.environ["TOKEN"]
PORT = int(os.environ.get('PORT', 5000))
LOG_FILE_PATH = os.environ["LOG_FILE_PATH"]
DBLINK = os.environ["DBLINK"]


cred = credentials.Certificate("./cert/ihaveposition.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': DBLINK
})

# Enable logging
logging.basicConfig(
    format='[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO, filename=LOG_FILE_PATH, filemode='w', 
)
logger = logging.getLogger(__name__)

   
def handleReply(update, context):
    """Send a message when user no need to coin"""
    print("===== handleReply =====")
    query = update.callback_query.data

    userInfo = initUserInfoFromReply(update.callback_query)
    print(userInfo)

    userDBData = db.reference(str(userInfo['userid']))
    
    if query == 'cancel':
        update.callback_query.edit_message_text("Canceled!")

    elif(query == "zone_range"):
        ask = "Please enter Range"
        update.callback_query.edit_message_text(ask, reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data='cancel')]]))

    elif(query == "capital"):
        ask = "Please enter capital"
        update.callback_query.edit_message_text(ask, reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data='cancel')]]))
        ttt = update.callback_query.answer()
        print("=======")
        print(ttt)
        print("=======")

    elif(query == "accepted_loss"):
        ask = "Please enter accepted_loss"
        update.callback_query.edit_message_text(ask, reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data='cancel')]]))

    elif(query == "follow_wood"):
        existing = userDBData.get()['follow_wood']
        newOption = False if(existing) else True        
        ask = "Success. seted to {}!".format("Follow" if(newOption) else "Not follow")
        

        updateDB = db.reference(str(userInfo['userid']))
        updateDB.update({ 
            'follow_wood':newOption
        })
        update.callback_query.edit_message_text(ask)

    else:
        ask = "Error. Please press Cancel"
        update.callback_query.edit_message_text(ask, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data='cancel')]]))
    
def future(update, context):
    """Calculate Future"""
    print("==== Future ====")
    userInfo = initUserInfo(update)
    print(userInfo)
    allowedUser = False
    light = {'green':'\U0001F7E2', 'red':'\U0001F534'}
    
    whitelist = db.reference('botWhitelist').get()
    for key in whitelist:
        if str(whitelist[key]) == str(userInfo['userid']):
            allowedUser = True

    if allowedUser:
        res = {}
        ref = db.reference(str(userInfo['userid']))
        capital = float(ref.get()['capital'])
        
        print('From Chat: {}, Message ID: {}\nFrom user: {} ({})'
            .format(userInfo['chat_id'], userInfo['message_id'], userInfo['username'], userInfo['userid']))        
        orders = update.message.text
        order = orders.split("\n")

        for idx,line in enumerate(order):
            if (idx==0):
               m = re.search('([A-Za-z0-9]{1,})', line)
               res["prep_name"] = m.group(1).upper()

            elif(idx==1):
                isRange = line.find("zone")
                if (isRange>0):
                    amt = 0
                    m = re.search('(?i)(long|short)\s(zone)\s(\d+\.?\d*)[^0-9]{1,}(\d+\.?\d*)', line)
                    res["From"] = float(m.group(3))
                    res["To"] = float(m.group(4))
                    res["perTran"] = int(ref.get()['zone_range'])                   

                    diff = (res["To"]-res["From"])/(res["perTran"]-1)
                    
                    for i in range(res["perTran"]):
                        amt += round((res["From"] + diff*i), 7)

                    res["entry"] = round(amt/res["perTran"], 7)
                    
                else:
                    m = re.search('(?i)(long|short)\s(.{1}.*)', line)
                    res["entry"] = float(m.group(2))
                
                res["side"] = m.group(1).upper()

                ## Set the light color
                res["light"] = light['green'] if m.group(1).upper() == "LONG" else light['red']
                
            elif(idx==2):
                m = re.search('(?i)(stop)\s(.{1}.*)', line)
                res['stop'] = float(m.group(2))

            elif(idx==3):
                m = re.search('(?i)(tp)\s(.{1}.*)', line)
                tmp = m.group(2).strip()
                data = tmp.split(" ")
                res['tp'] = data

            elif(idx==4):
                m = re.search('(\d+\.?\d*)%', line)
                if (ref.get()['follow_wood']):
                    res['risk'] = float(m.group(1))
                else:
                    res['risk'] = float(ref.get()['accepted_loss'])
                    
        print(res)

        # Start Calulate perfered position
        suggested_Postion = (capital*(res['risk']/100))/(res['entry'] - res['stop'])
        subOrderStr = ""
        TotalEstProfit = 0
        TotalEstLoss = 0

        if (len(res['tp']) > 1):
            each_position = round(suggested_Postion/len(res['tp']),6)
            for idx, tp in enumerate(res['tp']):
                subOrderAmount = (float(res['entry'])*each_position*-1)
                subOrderProfit = round(subOrderAmount-(float(tp)*each_position*-1), 3)
                subOrderLoss = round((float(res['stop'])*each_position*-1)-subOrderAmount, 3)

                TotalEstProfit += subOrderProfit
                TotalEstLoss += subOrderLoss

                subOrderStr = subOrderStr + "<pre>{} - \n".format(idx+1)                                                           + \
                                            "Position       : <b>{}</b> {}\n".format(each_position,res['prep_name'])               + \
                                            "Take Profit    : ${}\n".format(round(float(tp),6))                                    + \
                                            "Stop Loss      : ${}\n".format(res['stop'])                                           + \
                                            "Est. PnL:\n\U0001F4B0 ${}      \U0001F4B8 -${}\n".format(subOrderProfit, subOrderLoss)+ \
                                            "</pre>\n"
                

        userStr = "Capital         : ${}\n".format(capital)       + \
                  "Acceptable Loss : {}%\n".format(res['risk'])

        orderStr = "Side              : {} {}\n".format(res["side"], res['light'])                           + \
                   "Entry Price       : ${}\n".format(res['entry'])                                          + \
                   "Stop Loss         : ${}\n".format(res['stop'])                                           + \
                   "Position          : <b>{}</b> {}\n".format(round(suggested_Postion, 6),res['prep_name']) + \
                   "Total Est. Profit : ${}\n".format(round(TotalEstProfit, 6))                              + \
                   "Total Est. Loss   : ${}\n".format(round(TotalEstLoss, 6))                   
        
        replyStr = "<pre>Users Info:\n{} </pre>".format(userStr)  + \
                   "<pre>Order Info:\n{} </pre>".format(orderStr)
        
        if (ref.get()['vip'] and len(res['tp']) > 1):
            replyStr += "<pre>Breakdown:\n{} </pre>".format(subOrderStr)

        update.message.reply_text(replyStr, parse_mode=ParseMode.HTML)
    
    else:
        update.message.reply_text("Sorry! This feature not open to public!")

def setting(update, context):
    """Set default value"""
    print("setting")
    userInfo = initUserInfo(update)
    # print(userInfo)

    userDBData = db.reference(str(userInfo['userid']))    
    buttons = [
                [
                    InlineKeyboardButton("Capital: ${}".format(userDBData.get()['capital']), callback_data="CAPITAL"),
                    InlineKeyboardButton("{}Follow Ar Wood".format("" if(userDBData.get()['follow_wood']) else "Not "), callback_data="FOLLOW_WOOD")
                 ],
                 [
                    InlineKeyboardButton("Accepted Loss: {}%".format(userDBData.get()['accepted_loss']), callback_data="ACCEPTABLE_LOSS"),
                    InlineKeyboardButton("Zone range: {}".format(userDBData.get()['zone_range']), callback_data="ZONE_RANGE")
                 ],
                 [
                    InlineKeyboardButton("Done", callback_data=str(END))
                 ]
                ]
    keyboard = InlineKeyboardMarkup(buttons)
    text = 'Hi {}{}, Which value you want to update? '.format(userInfo['first_name'], "" if (userDBData.get()['vip']) else "(VIP)")
    update.message.reply_text(text=text, reply_markup=keyboard)
    context.user_data[START_OVER] = False

    return SELECTING_FEATURE

def stop(update, context) -> int:
    """End Conversation by command."""
    update.message.reply_text('Okay, bye.')

    return END

def end(update, context) -> int:
    """End conversation from InlineKeyboardButton."""
    update.callback_query.answer()

    text = 'See you around!'
    update.callback_query.edit_message_text(text=text)

    return END

def ask_for_input(update, context) -> str:
    """Prompt user to input data for selected feature."""
    print("ask_for_input")
    text = 'Okay, tell me.'
    
    context.user_data['input_key'] = update.callback_query.data

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    return TYPING

def save_input(update, context) -> str:
    """Save input for feature and return to feature selection."""
    print("save_input")

    userInfo = initUserInfo(update)
    # print(userInfo)

    user_data = context.user_data
    user_data[context.user_data['input_key']] = update.message.text
    action = context.user_data['input_key'].lower()
    userDBData = db.reference(str(userInfo['userid']))
    
    if action == "zone_range":
        ask = "Done"
        updateDB = db.reference(str(userInfo['userid']))
        updateDB.update({ 
            action: update.message.text
        })
        update.message.reply_text(ask)

    elif(action == "capital"):
        ask = "Done"
        updateDB = db.reference(str(userInfo['userid']))
        updateDB.update({ 
            action: update.message.text
        })
        update.message.reply_text(ask)
        
    elif(action == "accepted_loss"):
        updateDB = db.reference(str(userInfo['userid']))
        updateDB.update({ 
            action: update.message.text
        })
        update.message.reply_text(ask)

    elif(action == "follow_wood"):
        existing = userDBData.get()['follow_wood']

        print(existing)
        newOption = False if(existing) else True        
        ask = "Success. seted to {}!".format("Follow" if(newOption) else "Not follow")

        updateDB = db.reference(str(userInfo['userid']))
        updateDB.update({ 
            'follow_wood':newOption
        })
        update.message.reply_text(ask)

    else:
        ask = "Error. Please press Cancel"
        # update.callback_query.edit_message_text(ask, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data='cancel')]]))
    
    return setting(update, context)

def end_describing(update, context) -> int:
    """End gathering of features and return to parent conversation."""
    user_data = context.user_data
    level = user_data[CURRENT_LEVEL]
    if not user_data.get(level):
        user_data[level] = []
    user_data[level].append(user_data[FEATURES])

    # Print upper level menu
    # if level == SELF:
    #     user_data[START_OVER] = True
    #     start(update, context)
    # else:
    #     select_level(update, context)

    return END

def stop_nested(update, context) -> str:
    """Completely end conversation from within nested conversation."""
    update.message.reply_text('Okay, bye.')

    return STOPPING

def help_command(update, context):
    print("help_command")
    userInfo = initUserInfo(update)
    print(userInfo)

    update.message.reply_text("Hi {}, your telegram ID is: {}".format(userInfo['first_name'], userInfo['userid']))

    update.effective_message.reply_html(        
        f'Calculate Method:\n(Capital * Acceptable_loss) / (Entry_Price - Stop_Loss)'
    )
    
def error(update, context):
    """Log Errors caused by Updates."""
    resStr = "Something wrong. <a href='tg://user?id={}'>{}</a>\n#Error".format(622225198, 'Ringo (Lampgo)')
    update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)
    res = sentEmail(os.environ, context.error)
    print("[Info] " + res['msg'])
    print("[Error] " + res['error'])
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    """Start the bot."""
    MODE = os.environ["MODE"]
    HEROKULINK = os.environ["HEROKULINK"]

    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher    
    # dispatcher.add_handler(CommandHandler("start", start))
    
    # dispatcher.add_handler(CallbackQueryHandler(handleReply))
    dispatcher.add_handler(MessageHandler(Filters.regex("(\r\n|\r|\n)"), future))

    ## Others Functions
    dispatcher.add_error_handler(error)
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("setting", setting)],
        states={
            SELECTING_FEATURE: [
                CallbackQueryHandler(ask_for_input, pattern='^(?!' + str(END) + ').*$')
            ],
            TYPING: [MessageHandler(Filters.text & ~Filters.command, save_input)],
        },
        fallbacks=[CommandHandler('stop', stop)],
    )

    dispatcher.add_handler(conv_handler)


    # Start the Bot
    if (MODE == "DEV"):
        # Testing
        updater.start_polling()
    elif (MODE == "PROD"):
        # Production
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN, 
                              webhook_url="https://" + NAME + ".herokuapp.com/" + TOKEN)

    updater.idle()

if __name__ == '__main__':
    main()
