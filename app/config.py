from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-.env")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
