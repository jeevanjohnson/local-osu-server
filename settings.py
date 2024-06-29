from dotenv import load_dotenv
import os

load_dotenv()

MITMPROXY = os.environ["MITMPROXY"]
MITMPROXY_PORT= int(os.environ.get("MITMPROXY_PORT", 8080))
DEVELOPER = os.environ["DEVELOPER"]
OSU_PATH = os.environ["OSU_PATH"]

DEVELOPER = os.environ["DEVELOPER"]

SQLLITE_FILE_NAME = os.environ["SQLLITE_FILE_NAME"]
