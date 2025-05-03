from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = "7090927578:AAGwlO8PonwM6a_yUNAM2PSn-d3_WKws6u0"
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", 3306)
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
