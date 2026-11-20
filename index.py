import os
import sys
import tempfile

# Đảm bảo đường dẫn gốc của project nằm trong sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Thiết lập thư mục cache Matplotlib trên môi trường Serverless (Vercel Lambda)
if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = os.path.join(tempfile.gettempdir(), "matplotlib")
try:
    os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)
except Exception:
    pass

from app.main import app
