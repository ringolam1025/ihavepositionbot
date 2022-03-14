#!/usr/bin/env python
# pylint: disable=W0613
# type: ignore[union-attr]
# This program is dedicated to the public domain under the CC0 license.

from cgi import print_arguments
import os
import html
import json
import logging
import logging.config
from pickle import FALSE, TRUE
import traceback
import configparser
import time
import datetime

from dotenv import load_dotenv
config = load_dotenv(".env")

from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, RegexHandler, Filters, ConversationHandler, CallbackQueryHandler, CallbackContext

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from pyfunction import *

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

    if query == 'cancel':
        update.callback_query.edit_message_text("Canceled!")
    else:
        ask = "Please enter {}".format(query.capitalize())
        update.callback_query.edit_message_text(ask, reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data='cancel')]]))
    

def future(update, context):
    """Calculate Future"""
    print("==== Future ====")
    userInfo = initUserInfo(update)
    print(userInfo)
    allowedUser = False

    for key in db.reference('botWhitelist').get():
        if str(whitelist[key]) == str(userInfo['userid']):
            allowedUser = True

    if allowedUser:
        ref = db.reference(str(userInfo['userid']))
        captial = ref.get()['captial']
        accepted_loss = ref.get()['accepted_loss']
        light = {'green':'\U0001F7E2', 'red':'\U0001F534'}
        print('From Chat: {}, Message ID: {}\nFrom user: {} ({})'
            .format(userInfo['chat_id'], userInfo['message_id'], userInfo['username'], userInfo['userid']))

        orders = update.message.text
        order = orders.split("\n")

        res = {}
        counter = 0
        for line in order:
            data = line.split(" ")
            key = data[0]

            if (counter == 0):
                res["prep_name"] = data[0].upper()

            elif(key.upper() == "LONG" or key.upper() == "SHORT"):
                res["side"] = data[0].upper()
                data.pop(0)
                res["entry"] = data
                if (res["side"].upper() == "LONG"):
                    res["light"] = light['green']
                else:
                    res["light"] = light['red']

            elif(counter == (len(order)-1)):
                res["risk"] = data[0].replace("%", "")

            else:            
                if (len(data) > 1):                
                    data.pop(0)
                    res[(key.lower())] = data

            counter = counter + 1    

        # Start Calulate perfered position
        suggested_Postion = (captial*(accepted_loss/100))/(float(res['entry'][0]) - float(res['stop'][0]))
        
        userStr = "Captial:         ${}\n".format(captial)       + \
                "Acceptable Loss: {}%\n".format(accepted_loss)
                
        orderStr = "Side:            {} {}\n".format(res["side"], res['light'])                           + \
                "Stop Loss:       ${}\n".format(res['stop'][0])                                        + \
                "Entry Price:     ${}\n".format(res['entry'][0])                                       + \
                "Total Position:  <b>{}</b> {}\n".format(round(suggested_Postion, 6),res['prep_name']) + \
                "Est. Loss        ${}\n".format(round(captial*(accepted_loss/100), 6),res['prep_name'])
                # "Formula:         (${}*{}%)/(${}-${})\n".format(captial, accepted_loss, res['entry'][0], res['stop'][0]) + \

        subOrderStr = ""
        if (len(res['tp']) > 1):
            each_position = round(suggested_Postion/len(res['tp']),6)*-1
            for idx, tp in enumerate(res['tp']):
                subOrderAmount = (float(res['entry'][0])*each_position)
                subOrderProfit = round(subOrderAmount-(float(tp)*each_position), 6)
                subOrderLoss = round((float(res['stop'][0])*each_position)-subOrderAmount, 6)
                subOrderStr = subOrderStr + "<pre>{} - \n".format((idx+1))                                    + \
                    "Take Profit:     ${}\n".format(tp)                                                     + \
                    "Suggested:       <b>{}</b> {}\n".format(each_position,res['prep_name'])                + \
                    "Est. PnL:\n\U0001F4B0 ${}      \U0001F4B8 -${}\n".format(subOrderProfit, subOrderLoss) + \
                    "</pre>\n"
        
        replyStr = "<pre>Users Info:\n{} </pre>".format(userStr)              + \
                "<pre>Order Info:\n{} </pre>".format(orderStr)             + \
                "<pre>Sub-Order Breakdown:\n{} </pre>".format(subOrderStr)

        update.message.reply_text(replyStr, parse_mode=ParseMode.HTML)
    
    else:
        update.message.reply_text("Sorry! This feature not open to public!")

def set(update, context):
    """Set default value"""
    print("setting")
    userInfo = initUserInfo(update)
    print(userInfo)

    keyboard = [[InlineKeyboardButton("Captial", callback_data='captial'),
                 # InlineKeyboardButton("Follow wood?", callback_data='follow_wood'),
                 InlineKeyboardButton("Accepted Loss", callback_data='accepted_loss')]]
    update.message.reply_text('Which value you want to update?', reply_markup = InlineKeyboardMarkup(keyboard))

    ref = db.reference('/')
    ref.set({
        userInfo['userid']:{
                            'captial': 1300,
                            'accepted_loss': 2,
                            'follow_wood': 'Y',
                            'join_date': datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                        }
        })    

def help_command(update, context):
    """Send a message when the command /help is issued."""
    update.effective_message.reply_html(        
        f'Calculate Method:\n(Captial * Acceptable_loss) / (Entry_Price - Stop_Loss)'
    )
    

def error(update, context):
    """Log Errors caused by Updates."""
    resStr = "Something wrong. <a href='tg://user?id={}'>{}</a>\n#Error".format(622225198, 'Ringo (Lampgo)')
    update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)

    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    """Start the bot."""
    MODE = os.environ["MODE"]
    HEROKULINK = os.environ["HEROKULINK"]

    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher    
    dispatcher.add_handler(CommandHandler("set", set))
    dispatcher.add_handler(CommandHandler("future", future))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CallbackQueryHandler(handleReply))
    dispatcher.add_handler(MessageHandler(Filters.regex("(\r\n|\r|\n)"), future))

    # log all errors
    dispatcher.add_error_handler(error)

    # Start the Bot
    if (MODE == "DEV"):
        # Testing
        updater.start_polling()
    else:
        # Production
        updater.start_webhook(listen="0.0.0.0", port=int(PORT), url_path=TOKEN)
        updater.bot.setWebhook(HEROKULINK + TOKEN)
    updater.idle()

if __name__ == '__main__':
    main()
