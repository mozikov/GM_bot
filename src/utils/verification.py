from aiogram import types
import csv


def get_verified_users(csv_file_path: str) -> bool:
    """
    Forms set of verified users
    Args:
        csv_file_path (str): path to csv with verified users 

    Returns:
        bool: True if username or user_id in csv 
    """
    verified_users = set()

    with open(csv_file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["user_name"] != '':
                verified_users.add(row["user_name"])
            elif row['user_id'] != '':
                verified_users.add(str(row['user_id']))
    return verified_users
            

async def check_verification(message: types.Message,
                             authorized_users: set,
                             ) -> bool:
    user_id = str(message.from_user.id)
    username = message.from_user.username
    if user_id in authorized_users:
        return user_id
    elif username in authorized_users:
        return username
    else:
        await message.answer(
            f"Hello {username}, I'm bot powered by OpenAI API. "
            + "Sorry, the bot is under development and you are not logged in."
            + "If you want to discuss anything feel free to contact @mozikov"
        )
        return False
    
if __name__ == "__main__":
    us = get_verified_users(r"D:\work_D\git\GM_bot\data\users.csv")
    print(us)