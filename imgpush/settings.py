import ast
import os
from dotenv import load_dotenv

load_dotenv()

PORT = 5000
DEBUG = False
IMAGES_DIR = "/images/"
CACHE_DIR = "/cache/"
OUTPUT_TYPE = "PNG"
MAX_UPLOADS_PER_DAY = 1000
MAX_UPLOADS_PER_HOUR = 100
MAX_UPLOADS_PER_MINUTE = 20
ALLOWED_ORIGINS = ["*"]
NAME_STRATEGY = "randomstr"
MAX_TMP_FILE_AGE = 5 * 60
RESIZE_TIMEOUT = 5
JWT_PUBLIC_KEY = None
JWT_ALGORITHM = None
JWT_SECRET = None
UPLOAD_REQUIRE_AUTH = False
GET_REQUIRE_AUTH = False
DISABLE_RESIZE = False
DISABLE_URL_UPLOAD = False
DISABLE_UPLOAD_FORM = False
UPLOAD_ROUTE = "/"
IMAGES_ROOT = ""
MONGO_URI = ""
USE_MONGO = False

VALID_SIZES = []

MAX_SIZE_MB = 16

for variable in [item for item in globals() if not item.startswith("__")]:
    NULL = "NULL"
    env_var = os.getenv(variable, NULL).strip()
    if env_var is not NULL:
        try:
            env_var = ast.literal_eval(env_var)
        except Exception:
            pass
    globals()[variable] = env_var if env_var is not NULL else globals()[variable]
