from dotenv import load_dotenv
import os

load_dotenv()

MITMPROXY = os.getenv("MITMPROXY") == "True"
MITMPROXY_PORT= int(os.environ["MITMPROXY_PORT"]) or 8080
DEVELOPER = os.getenv("DEVELOPER") == "True"
OSU_PATH = os.getenv("OSU_PATH")

