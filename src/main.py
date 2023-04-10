import logging
import time
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.callback_data import CallbackData
import openai
import yaml
from utils import verification
print('[ + ] Imports done')

# Initialize Callback Factory for inline menu buttons
menu_cb = CallbackData("menu", "button")
### Add check on diff levels except of start

with open("configs/creds.yaml", "r") as f:
    creds = yaml.safe_load(f)
with open("configs/config.yaml", "r") as f:
    config = yaml.safe_load(f)

bot_token = creds["bot_token"]
api_key = creds["api_key"]
model = config["model"]
logging.basicConfig(level=logging.INFO)

bot = Bot(token=bot_token)
dp = Dispatcher(bot)

openai.api_key = api_key

messages = {}
prompts = {}

# Replace this with the path to your CSV file
CSV_FILE_PATH = "data/users.csv"
verified_users = verification.get_verified_users(CSV_FILE_PATH)


@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    try:
        username = await verification.check_verification(
            message,
            verified_users,
        )
        if username:
            await message.answer(f"Hello {username}, I'm bot powered on OpenAI API")
    except Exception as e:
        print(e)
        logging.error(f"Error in start_cmd: {e}")


# No use w/o premium
@dp.message_handler(commands=["gpt_chair"])
async def change_model(message: types.Message):
    pass

@dp.message_handler(commands=["invoke_gm"])
async def invoke_gm(message: types.Message or types.CallbackQuery):
    try:
        username = await verification.check_verification(
                message,
                verified_users,
            )
        if not username:
            return
        
        with open("configs/prompts.yaml", "r") as f:
            prompts = yaml.safe_load(f)
        prompts[username] = prompts["grim_gm"] 

        if username not in messages:
            messages[username] = []
        messages[username].append({"role": "system", "content": prompts[username]})
        # if this function is called from menu button it has CallbackQuery
        # as input and CallbackQuery doesn't have `.reply()` option
        if isinstance(message, types.CallbackQuery):
            message = message.message

        await message.reply(
            "I'm gamemaster now!",
            parse_mode="Markdown",
        )

    except Exception as e:
        logging.error(f"Error in invoke_gm: {e}")

### Menu block



@dp.message_handler(commands=["menu"])
async def menu_com(message: types.Message):
    try:
        username = await verification.check_verification(
                message,
                verified_users,
            )
        if not username:
            return
        
        buttons = [
            types.InlineKeyboardButton(text="Subscription",
                                       callback_data=menu_cb.new(button="subscription")),
            types.InlineKeyboardButton(text="Start new chat",
                                       callback_data=menu_cb.new(button="start_chat")),
            types.InlineKeyboardButton(text="Select prompt",
                                       callback_data=menu_cb.new(button="select_prompt"))
        ]

        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(*buttons)
        await message.answer("Нажмите на кнопку", reply_markup=keyboard)
        

    except Exception as e:
        logging.error(f"Error in invoke_gm: {e}")

@dp.callback_query_handler(menu_cb.filter(button=["subscription", "start_chat", "select_prompt"]))
async def callbacks_num_change_fab(call: types.CallbackQuery, callback_data: dict):
    
    button = callback_data["button"]
    if button == "subscription":
        await call.message.reply(
            "No data yet",
            parse_mode="Markdown",
        )
    if button == "start_chat":
        await new_topic_cmd(call)
    if button == "select_prompt":
        await invoke_gm(call)

###

@dp.message_handler(commands=["newtopic"])
async def new_topic_cmd(message: types.Message):
    try:
        username = await verification.check_verification(
            message,
            verified_users,
        )
        if not username:
            return
        
        messages[username] = []

        # if this function is called from menu button it has CallbackQuery
        # as input and CallbackQuery doesn't have `.reply()` option
        if isinstance(message, types.CallbackQuery):
            message = message.message

        await message.reply(
            "Starting a new topic!",
            parse_mode="Markdown",
        )
    except Exception as e:
        logging.error(f"Error in new_topic_cmd: {e}")


@dp.message_handler()
async def echo_msg(message: types.Message):
    try:
        user_message = message.text

        username = await verification.check_verification(
            message,
            verified_users,
        )
        if not username:
            return

        # Add the user's message to their message history
        if username not in messages:
            messages[username] = []
        messages[username].append({"role": "user", "content": user_message})


        cur_time = time.strftime("%d/%m/%Y %H:%M:%S")

        logging.info(f"{username}: {user_message}")

        # Check if the message is a reply to the bot's message or a new message
        should_respond = (
            not message.reply_to_message
            or message.reply_to_message.from_user.id == bot.id
        )

        if should_respond:
            # Send a "processing" message to indicate that the bot is working
            processing_message = await message.reply(
                "Hmm ... Let me think (You can restart running /newtopic)",
                parse_mode="Markdown",
            )

            # Send a "typing" action to indicate that the bot is typing a response
            await bot.send_chat_action(chat_id=message.chat.id, action="typing")

            # Generate a response using OpenAI's Chat API
            completion = await openai.ChatCompletion.acreate(
                model=model,
                messages=messages[username],
                max_tokens=2500,
                temperature=0.7,
                frequency_penalty=0,
                presence_penalty=0,
                user=username,
            )
            chatgpt_response = completion.choices[0]["message"]

            # Add the bot's response to the user's message history
            messages[username].append(
                {"role": "assistant", "content": chatgpt_response["content"]}
            )
            logging.info(f'ChatGPT response: {chatgpt_response["content"]}')

            # Send the bot's response to the user
            await message.reply(chatgpt_response["content"])

            # Delete the "processing" message
            await bot.delete_message(
                chat_id=processing_message.chat.id,
                message_id=processing_message.message_id,
            )

    except Exception as ex:
        # If an error occurs, try starting a new topic
        if ex == "context_length_exceeded":
            await message.reply(
                "The bot ran out of memory, re-creating the dialogue * * * \n\nУ бота закончилась память, пересоздаю диалог * * *",
                parse_mode="Markdown",
            )
            await new_topic_cmd(message)
            await echo_msg(message)


if __name__ == "__main__":
    executor.start_polling(dp)


print()
print(messages)
print("done")
