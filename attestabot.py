#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# -----------------------------------------------------------------------------

import datetime
import random
import os
import time

from telegram import(
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ForceReply
)

from telegram.ext import(
    Updater, 
    CommandHandler, 
    MessageHandler,
    Filters, 
    ConversationHandler,
    CallbackQueryHandler,
    PicklePersistence,
)

from generate_pdf import generate_pdf

# -----------------------------------------------------------------------------

# Telegram API Token.
TELEGRAM_API_TOKEN = "telegram-API-token"

# Time to wait between sensitive system operation (in seconds).
SYSTEM_SLEEP_DELAY = 0.05

# User input strings maximum length.
USER_STR_MAX_LENGTH = 128

# Profile conversation handlers.
PROFILE_FIRST_NAME, PROFILE_LAST_NAME, PROFILE_BIRTHDATE, PROFILE_BIRTHPLACE, PROFILE_CITY, PROFILE_ADDRESS = range(6)

# Delete conversation handlers
DELETE_PROFILE_NUMBER = range(1)
# Generation wizard handlers.
GENERATE_MOTIVES, GENERATE_TIME = range(2)

# Official motives for leaving house.
AVAILABLE_ACTIONS = [
    'travail', 
    'achats', 
    'sante', 
    'famille', 
    'handicap', 
    'balade',
    'convocation', 
    'missions', 
    'enfants'
]

# Default action for the /presto command.
PRESTO_ACTION_ID = 1

# Range of random delay for retroactive timestamp (in minutes).
PRESTO_DELAY_RANGE = (8, 20)

# Timeshift query choices for the /generate command.
QUERY_TIMEFRAME = {
    "-20 minutes": -20,
    "-10 minutes": -10,
    "-5 minutes": -5,
    "Tout de suite": 0,
}

# Nice User Interaction Messages.
WAITING_MESSAGE_POOL = [
    "( ˘ ³˘) Votre attestation arrive bientôt",
    "(~‾▿‾)~ Attention les flics sont là!!!",
    ",( °□°)/ CA ARRIVE !!",
    "Oui je sais, c'est un peu long, mais ca va arriver!",
    "Ca été aujourd'hui?"
]

# -----------------------------------------------------------------------------

# Enable logging
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------

class Profile:
    """ Holds user informations and generate PDF attestation from them """

    def __init__(self, first_name, last_name, birth_date, birth_city, current_city, address):
        self.first_name = first_name[:USER_STR_MAX_LENGTH]
        self.last_name = last_name[:USER_STR_MAX_LENGTH]
        self.birth_date = birth_date[:USER_STR_MAX_LENGTH]
        self.birth_city = birth_city[:USER_STR_MAX_LENGTH]
        self.current_city = current_city[:USER_STR_MAX_LENGTH]
        self.address = address[:USER_STR_MAX_LENGTH]

    def generate(self, actionId=1, timeshift=0):
        """ Generate a pdf document for the profile, returns its global filename """

        backtothefuture = datetime.timedelta(minutes=timeshift)
        leave_date = datetime.datetime.now() + backtothefuture
        self.leave_date = leave_date.strftime("%d/%m/%Y")
        self.leave_hour = leave_date.strftime("%Hh%M")
        self.motives = AVAILABLE_ACTIONS[actionId]
        fn = generate_pdf(self.first_name, self.last_name, self.birth_date, self.birth_city, self.current_city, self.address, self.leave_date, self.leave_hour, self.motives)

        return os.path.join(os.getcwd(), fn)

    def __str__(self):
        output = self.first_name + " " + self.last_name + "\n"
        output +=  "Né.e le " + self.birth_date + " à " + self.birth_city + "\n"
        output += "Adresse: " + self.address
        return output
# -----------------------------------------------------------------------------

def start_cmd(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text("""
Bienvenue sur jeVeuxSorir !

Un bot pour générer facilement des attestations de sortie pendant le 
confinement 2020.

Pour bien débuter, créer votre profile via /profile, vous pouvez ajouter 
plusieurs profiles en relancant la commande /profile.
Vous pouvez effacer un profil avec la commande /remove

Ensuite, utilisez /generate pour une attestation personalisée ou /presto
pour une attestation rétroactive pour des courses de premières nécessitées.

Vous pouvez afficher la liste des commandes via /help.

Et si le bot ne semble plus répondre, pensez à /cancel :)

(Mise à jour : Novembre 2020)
""")

def help_cmd(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text("""
/help Affiche la liste des commandes.
/profile Assistant pour créer une liste de profils.
/remove Efface un profil
/generate Génère une attestation en quelques clics.
/presto Génère une attestation instantanée et retroactive pour faire les courses.. en cas d'oublie seulement.
/cancel Annulation de la tâche en cours.
""")
    ForceReply()


def profile_cmd(update, context):
    """Launch the profile wizard / conversation."""
    update.message.reply_text("Nous allons créer votre profile pour générer facilement vos attestations !")
    update.message.reply_text("(1/6) Quel est votre prénom ?")
    return PROFILE_FIRST_NAME

def profile_first_name(update, context):
    context.user_data['first_name'] = update.message.text
    update.message.reply_text("(2/6) Votre nom de famille ?")
    return PROFILE_LAST_NAME

def profile_last_name(update, context):
    context.user_data['last_name'] = update.message.text
    update.message.reply_text("(3/6) Votre date de naissance [JJ/MM/AAAA] ?")
    return PROFILE_BIRTHDATE

def profile_birthdate(update, context):
    context.user_data['birthdate'] = update.message.text
    update.message.reply_text("(4/6) Votre lieu de naissance ?")
    return PROFILE_BIRTHPLACE

def profile_birthplace(update, context):
    context.user_data['birthplace'] = update.message.text
    update.message.reply_text("(5/6) Votre ville de résidence ?")
    return PROFILE_CITY

def profile_city(update, context):
    context.user_data['city'] = update.message.text
    update.message.reply_text("(6/6) Votre addresse complete ?")
    return PROFILE_ADDRESS

def profile_address(update, context):
    context.user_data['address'] = update.message.text
    compile_profile(context)
    update.message.reply_text("Merci !\nVous pouvez désormais utiliser les commandes /generate et /presto")
    return ConversationHandler.END


def cancel_cmd(update, context):
    """Cancel current conversation command."""
    query = update.callback_query
    if query:
        query.answer()
    return ConversationHandler.END


def generate_cmd(update, context):
    """Launch the generate conversation."""

    actionMap = dict(zip(AVAILABLE_ACTIONS, range(len(AVAILABLE_ACTIONS))))
    button_list = [InlineKeyboardButton(k, callback_data=str(v)) for (k, v) in actionMap.items()]
    update.message.reply_text(
        "(1/2) De quel motif avez-vous besoin ?",
        reply_markup=InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
    )
    return GENERATE_MOTIVES

def generate_motives(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['action_id'] = "{}".format(query.data)

    button_list = [InlineKeyboardButton(k, callback_data=str(v)) for (k, v) in QUERY_TIMEFRAME.items()]
    query.edit_message_text(
        text="(2/2) A partir de quand ?",
        reply_markup=InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    )

    return GENERATE_TIME

def generate_time(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['timeshift'] = "{}".format(query.data)

    actionId = int(context.user_data['action_id'])
    timeshift = int(context.user_data['timeshift'])

    # Add stochastic noise FTW.
    timeshift += random.randrange(-3, 2)
    
    _generate(query.message, context, actionId, timeshift)

    return ConversationHandler.END


def presto_cmd(update, context):
    """ Generate a quick retroactive document """
    actionId = PRESTO_ACTION_ID
    timeshift = -random.randrange(*PRESTO_DELAY_RANGE)
    _generate(update.message, context, actionId, timeshift)

def show_cmd(update, context):
    """ Show all profiles """
    profiles = context.user_data.get('profile', None)
    if not profiles:
        update.message.reply_text("Vous n'avez aucun profil, créer un profil via /profile.")
        return
    count = 0
    for profile in profiles:
        count += 1
        update.message.reply_text("Profil " + str(count) + "\n" + profile.__str__())

def removeProfile_cmd(update, context):
    show_cmd(update, context)
    update.message.reply_text("Quel profil voulez vous effacer?")
    return DELETE_PROFILE_NUMBER

def deleteProfileNumber(update, context):
    ans = update.message.text
    update.message.reply_text("Ok retirons le profil " + ans)
    profiles = context.user_data.get('profile', None)
    del profiles[int(ans)-1]
    show_cmd(update, context)
    return ConversationHandler.END


# -----------------------------------------------------------------------------

def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    # @so45558984
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu

def compile_profile(context):
    """Create a user profile in the bot user data, then delete temporary datas"""
    profile = context.user_data.get('profile', None)
    if not profile:
        profile = []
    profile.append(Profile(
        context.user_data['first_name'],
        context.user_data['last_name'],
        context.user_data['birthdate'],
        context.user_data['birthplace'],
        context.user_data['city'],
        context.user_data['address']
    ))
    context.user_data['profile'] = profile
    del context.user_data['last_name']
    del context.user_data['birthdate']
    del context.user_data['birthplace']
    del context.user_data['city']
    del context.user_data['address']

def _generate(message, context, actionId, timeshift=0):
    """ Generate a PDF file from the user profile with given action & time shift """
    
    profiles = context.user_data.get('profile', None)
    if not profiles:
        message.reply_text("Pour générer une attestation, créer un profil via /profile.")
        return
    for profile in profiles:
        # Generate the PDF file and return its locale filename.
        filename = profile.generate(actionId, timeshift)
        
        # Message the user.
        waiting_msg = WAITING_MESSAGE_POOL[random.randrange(len(WAITING_MESSAGE_POOL))]
        message.reply_text(waiting_msg)
        time.sleep(SYSTEM_SLEEP_DELAY)

        # Send the PDF document to the user.
        with open(filename, "rb") as fd: 
            message.reply_document(fd)
        
        # Remove the local file after a sleep.
        time.sleep(SYSTEM_SLEEP_DELAY)
        os.remove(filename)

# -----------------------------------------------------------------------------

def main():
    pp = PicklePersistence(filename="attestabot")
    updater = Updater(TELEGRAM_API_TOKEN, persistence=pp, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Command List
    dp.add_handler(CommandHandler("start", start_cmd))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("presto", presto_cmd))
    dp.add_handler(CommandHandler("show", show_cmd))
    # dp.add_handler(CommandHandler("remove", removeProfile_cmd))

    # Generate command via conversation.
    remove_handler = ConversationHandler(
        entry_points = [CommandHandler('remove', removeProfile_cmd)],
        states = {
            DELETE_PROFILE_NUMBER: [MessageHandler(Filters.regex(r'^\d+$'), deleteProfileNumber)]
        },
        fallbacks = [CommandHandler('cancel', cancel_cmd)]
    )
    dp.add_handler(remove_handler)

    # Profile build command via conversation.
    profile_handler = ConversationHandler(
        entry_points = [CommandHandler('profile', profile_cmd)],
        states = {
            PROFILE_FIRST_NAME: [MessageHandler(Filters.text, profile_first_name)], 
            PROFILE_LAST_NAME: [MessageHandler(Filters.text, profile_last_name)], 
            PROFILE_BIRTHDATE: [MessageHandler(Filters.regex(r'^(0[1-9]|1\d|2\d|3[01])\/(0[1-9]|1[0-2])\/(19|20)\d{2}$'), profile_birthdate)], 
            PROFILE_BIRTHPLACE: [MessageHandler(Filters.text, profile_birthplace)], 
            PROFILE_CITY: [MessageHandler(Filters.text, profile_city)], 
            PROFILE_ADDRESS: [MessageHandler(Filters.text, profile_address)]
        },
        fallbacks = [CommandHandler('cancel', cancel_cmd)],
        name = "profile_info",
        persistent=True
    )
    dp.add_handler(profile_handler)

    # Generate command via conversation.
    generate_handler = ConversationHandler(
        entry_points = [CommandHandler('generate', generate_cmd)],
        states = {
            GENERATE_MOTIVES: [CallbackQueryHandler(generate_motives)], 
            GENERATE_TIME: [CallbackQueryHandler(generate_time)], 
        },
        fallbacks = [CommandHandler('cancel', cancel_cmd)]
    )
    dp.add_handler(generate_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
