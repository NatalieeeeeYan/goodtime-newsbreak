from __future__ import annotations

import logging
import sys

from headsup.config import load_settings
from linger.bot import build_app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = load_settings()
    if not settings.telegram_bot_token:
        sys.exit("TELEGRAM_BOT_TOKEN is not set in .env")
    app = build_app(settings.telegram_bot_token)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
