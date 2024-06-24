from dotenv import load_dotenv
import os

load_dotenv()

MITMPROXY = os.getenv("MITMPROXY") == "True"
DEVELOPER = os.getenv("DEVELOPER") == "True"
OSU_PATH = os.getenv("OSU_PATH")