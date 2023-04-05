import logging
import time
from aiogram import Bot, Dispatcher, executor, types
import openai
import yaml
import csv

with open("creds.yaml", "r") as f:
    creds = yaml.safe_load(f)
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

bot_token = creds["bot_token"]
api_key = creds["api_key"]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=bot_token)
dp = Dispatcher(bot)

openai.api_key = api_key

messages = {}

# Replace this with the path to your CSV file
CSV_FILE_PATH = 'users.csv'

# Define a function to check if a user is in the CSV database
async def is_user_in_db(message: types.Message) -> bool:
    with open(CSV_FILE_PATH, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if int(row['user_id']) == message.from_user.id or row['user_name'] == message.from_user.username:
                return True
    return False

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    try:
        username = message.from_user.username
        messages[username] = []
        user_in_db = await is_user_in_db(message=message)
        if user_in_db:
            await message.answer(f"Hello {username}, I'm bot powered on OpenAI API")
        else:
            await message.answer(f"Hello {username}, I'm bot powered by OpenAI API. " +\
                                 "Sorry, the bot is under development and you are not logged in." +\
                                 "If you want to discuss anything feel free to contact @mozikov")
    except Exception as e:
        print(e)
        logging.error(f'Error in start_cmd: {e}')

@dp.message_handler(commands=['newtopic'])
async def new_topic_cmd(message: types.Message):
    try:
        userid = message.from_user.id
        messages[str(userid)] = []
        await message.reply('Starting a new topic! * * * \n\nНачинаем новую тему! * * *', parse_mode='Markdown')
    except Exception as e:
        logging.error(f'Error in new_topic_cmd: {e}')

@dp.message_handler()
async def echo_msg(message: types.Message):
    try:
        user_message = message.text
        userid = message.from_user.username

        # Add the user's message to their message history
        if userid not in messages:
            messages[userid] = []
        messages[userid].append({"role": "user", "content": user_message})
        # messages[userid].append({"role": "system", "content": "prompt"})
        cur_time = time.strftime('%d/%m/%Y %H:%M:%S')
        messages[userid].append({"role": "user",
                                 "content": f"chat: {message.chat} Сейчас {cur_time} user: {message.from_user.first_name} message: {message.text}"})
        logging.info(f'{userid}: {user_message}')

        # Check if the message is a reply to the bot's message or a new message
        should_respond = not message.reply_to_message or message.reply_to_message.from_user.id == bot.id

        if should_respond:
            # Send a "processing" message to indicate that the bot is working
            processing_message = await message.reply(
                'Your request is being processed, please wait \n\n(If the bot does not respond, write /newtopic, openai killed my feature on auto-cleaning the topic when the token overflow) * * * \n\nВаш запрос обрабатывается, пожалуйста подождите \n\n(Если бот не отвечает, напишите /newtopic, openai убили мою функцию по автоочистке темы при переполнении токенов) * * *',
                parse_mode='Markdown')

            # Send a "typing" action to indicate that the bot is typing a response
            await bot.send_chat_action(chat_id=message.chat.id, action="typing")

            # Generate a response using OpenAI's Chat API
            completion = await openai.ChatCompletion.acreate(
                model=config["model"],
                messages=messages[userid],
                max_tokens=2500,
                temperature=0.7,
                frequency_penalty=0,
                presence_penalty=0,
                user=userid
            )
            chatgpt_response = completion.choices[0]['message']

            # Add the bot's response to the user's message history
            messages[userid].append({"role": "assistant", "content": chatgpt_response['content']})
            logging.info(f'ChatGPT response: {chatgpt_response["content"]}')

            # Send the bot's response to the user
            await message.reply(chatgpt_response['content'])

            # Delete the "processing" message
            await bot.delete_message(chat_id=processing_message.chat.id, message_id=processing_message.message_id)

    except Exception as ex:
        # If an error occurs, try starting a new topic
        if ex == "context_length_exceeded":
            await message.reply(
                'The bot ran out of memory, re-creating the dialogue * * * \n\nУ бота закончилась память, пересоздаю диалог * * *',
                parse_mode='Markdown')
            await new_topic_cmd(message)
            await echo_msg(message)




if __name__ == '__main__':
    executor.start_polling(dp)




print("done")