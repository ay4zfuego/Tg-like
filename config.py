import os
BOT_TOKEN=os.getenv("BOT_TOKEN","")
ADMIN_IDS={int(x.strip()) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()}
SUPPORT_USERNAME=os.getenv("SUPPORT_USERNAME","@DEVELOPER_AYAZ")
BKASH_NUMBER=os.getenv("BKASH_NUMBER","01752859888")
MIN_DEPOSIT=float(os.getenv("MIN_DEPOSIT","10"))
PACKAGE_PRICE=float(os.getenv("PACKAGE_PRICE","7"))
PACKAGE_LIKES=int(os.getenv("PACKAGE_LIKES","200"))
DATABASE_PATH=os.getenv("DATABASE_PATH","bot.db")
PLAYER_INFO_API_URL=os.getenv("PLAYER_INFO_API_URL","https://auraffxserverinfocheckerapi.onrender.com/api/player")
LIKE_API_URL=os.getenv("LIKE_API_URL","")
LIKE_API_KEY=os.getenv("LIKE_API_KEY","")
