import logging, os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN, ADMIN_IDS, SUPPORT_USERNAME, BKASH_NUMBER, MIN_DEPOSIT, PACKAGE_PRICE, PACKAGE_LIKES
from database import DB
from api_client import player_info, send_likes, APIConfigurationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)
db = DB()

def is_admin(uid): return uid in ADMIN_IDS
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ 200 Likes Instant — ৳7", callback_data="buy")],
        [InlineKeyboardButton("💳 Add Balance", callback_data="deposit"),
         InlineKeyboardButton("👤 My Account", callback_data="account")],
        [InlineKeyboardButton("📜 Deposit History", callback_data="dep_history"),
         InlineKeyboardButton("📦 All Orders", callback_data="orders")],
        [InlineKeyboardButton("☎ Contact Admin", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"),
         InlineKeyboardButton("🛟 Support", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=update.effective_user
    db.ensure_user(u.id, u.username or "", u.full_name)
    context.user_data.clear()
    await update.message.reply_text(
        f"╔══════════════════════════╗\n🔥 WELCOME TO FF LIKES BOT 🔥\n╚══════════════════════════╝\n\n"
        f"👋 Welcome, {u.first_name}!\n🆔 Telegram ID: {u.id}\n💰 Your Balance: ৳{db.balance(u.id):.2f}\n\n👇 নিচের মেনু থেকে একটি অপশন বেছে নিন।",
        reply_markup=main_kb())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("প্রক্রিয়াটি বাতিল করা হয়েছে।", reply_markup=main_kb())

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    uid=q.from_user.id
    data=q.data
    if data == "buy":
        context.user_data.clear(); context.user_data["step"]="uid"
        await q.message.reply_text("🔥 200 Likes Instant\n💰 Price: ৳7\n❤️ Likes: 200\n\nআপনার Free Fire Player UID পাঠান:")
    elif data == "deposit":
        context.user_data.clear(); context.user_data["step"]="deposit_amount"
        await q.message.reply_text(f"💳 bKash Deposit\n📱 Send Money: {BKASH_NUMBER}\n\nসর্বনিম্ন ডিপোজিট ৳{MIN_DEPOSIT}। কত টাকা জমা দিতে চান? Amount লিখুন:")
    elif data == "account":
        await q.message.reply_text(f"👤 MY ACCOUNT\nName: {q.from_user.full_name}\nUsername: @{q.from_user.username or 'N/A'}\nTelegram ID: {uid}\n💰 Wallet: ৳{db.balance(uid):.2f}\n📦 Total Orders: {db.order_count(uid)}\n❤️ Total Likes Delivered: {db.likes_total(uid)}")
    elif data == "dep_history":
        rows=db.deposit_history(uid)
        await q.message.reply_text("📜 DEPOSIT HISTORY\n\n" + ("\n\n".join([f"৳{r['amount']:.2f} | {r['trxid']} | {r['status']}" for r in rows]) if rows else "কোনো Deposit History নেই।"))
    elif data == "orders":
        rows=db.orders(uid)
        await q.message.reply_text("📦 ALL ORDERS\n\n" + ("\n\n".join([f"#{r['id']} | UID: {r['ff_uid']} | {r['likes']} Likes | ৳{r['price']:.2f} | {r['status']}" for r in rows]) if rows else "এখনো কোনো অর্ডার নেই।"))
    elif data.startswith("server:"):
        server=data.split(":",1)[1]
        context.user_data["server"]=server
        ffuid=context.user_data.get("ff_uid")
        await q.edit_message_text("🔎 Player information যাচাই করা হচ্ছে...")
        try:
            info=await player_info(ffuid, server)
            context.user_data["player"]=info
            name=info.get("name","Unknown")
            level=info.get("level","N/A")
            honor=info.get("honor_score","N/A")
            region=info.get("region",server)
            likes=info.get("likes","N/A")
            kb=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel",callback_data="order_cancel"),
                                      InlineKeyboardButton("✅ Confirm",callback_data="order_confirm")]])
            await q.message.reply_text(
                f"🎮 PLAYER INFORMATION\n🆔 UID: {ffuid}\n👤 Name: {name}\n⭐ Level: {level}\n🏅 Honor Score: {honor}\n🌍 Region: {region}\n❤️ Current Likes: {likes}\n\n📦 Package: {PACKAGE_LIKES} Likes\n💰 Price: ৳{PACKAGE_PRICE}\n\nConfirm করবেন?",
                reply_markup=kb)
        except Exception as e:
            log.exception("Player info error")
            await q.message.reply_text(f"❌ Player Info পাওয়া যায়নি: {e}\nUID/Server যাচাই করে আবার চেষ্টা করুন।", reply_markup=main_kb())
            context.user_data.clear()
    elif data == "order_cancel":
        context.user_data.clear()
        await q.edit_message_text("❌ Order Cancelled. কোনো টাকা কাটা হয়নি।")
    elif data == "order_confirm":
        await place_order(q, context)
    elif data.startswith("dep:"):
        if not is_admin(uid): return
        action, depid=data.split(":")[1], int(data.split(":")[2])
        dep=db.get_deposit(depid)
        if not dep or dep["status"]!="PENDING":
            await q.edit_message_text("এই Deposit Request আগেই প্রসেস করা হয়েছে বা পাওয়া যায়নি।"); return
        if action=="approve":
            db.approve_deposit(depid)
            await q.edit_message_text(f"✅ Deposit #{depid} Approved. ৳{dep['amount']:.2f} যোগ হয়েছে।")
            try: await context.bot.send_message(dep["user_id"],f"✅ আপনার Deposit Approved!\n💰 ৳{dep['amount']:.2f} Wallet-এ যোগ হয়েছে।")
            except Exception: pass
        else:
            db.reject_deposit(depid)
            await q.edit_message_text(f"❌ Deposit #{depid} Rejected.")
            try: await context.bot.send_message(dep["user_id"],"❌ আপনার Deposit Reject করা হয়েছে। ভুল Transaction ID বা ভুল তথ্য থাকলে Admin-এর সঙ্গে যোগাযোগ করুন।")
            except Exception: pass

async def place_order(q, context):
    uid=q.from_user.id
    info=context.user_data.get("player")
    ffuid=context.user_data.get("ff_uid")
    server=context.user_data.get("server")
    if not info or not ffuid or not server:
        await q.message.reply_text("অর্ডারের তথ্য পাওয়া যায়নি। আবার শুরু করুন।",reply_markup=main_kb()); return
    # Reserve funds atomically before external call; restore on definite failure.
    order_id=db.create_order(uid,ffuid,server,PACKAGE_LIKES,PACKAGE_PRICE)
    if not order_id:
        await q.message.reply_text(f"❌ Insufficient Balance!\n💰 Price: ৳{PACKAGE_PRICE}\n👛 Balance: ৳{db.balance(uid):.2f}\nAdd Balance করুন।",reply_markup=main_kb()); return
    status_msg=await q.message.reply_text("⏳ অর্ডার প্রসেস হচ্ছে...")
    try:
        import asyncio
        for frame in ["⏳ অর্ডার প্রসেস হচ্ছে.", "⏳ অর্ডার প্রসেস হচ্ছে..", "⏳ অর্ডার প্রসেস হচ্ছে..."]:
            await status_msg.edit_text(frame)
            await asyncio.sleep(0.65)
        result=await send_likes(ffuid,server)
        if result.get("ok") is True:
            db.finish_order(order_id,"SUCCESS",result.get("order_no",""),result.get("likes",PACKAGE_LIKES))
            before=info.get("likes","N/A")
            after=(int(before)+int(result.get("likes",PACKAGE_LIKES))) if str(before).isdigit() else "API-তে প্রদত্ত"
            await status_msg.edit_text(f"✅ ORDER COMPLETED!\n🆔 UID: {ffuid}\n📦 Likes Delivered: {result.get('likes',PACKAGE_LIKES)}\n❤️ Before Likes: {before}\n❤️ After Likes: {after}\n💰 Paid: ৳{PACKAGE_PRICE}\n🧾 Order ID: {result.get('order_no',order_id)}\n📌 Status: SUCCESS")
        else:
            db.refund_order(order_id, "FAILED")
            await status_msg.edit_text("❌ ORDER FAILED!\nঅর্ডার সম্পন্ন হয়নি। কাটা টাকা Wallet-এ ফেরত দেওয়া হয়েছে।")
    except APIConfigurationError as e:
        db.refund_order(order_id,"FAILED")
        await status_msg.edit_text(f"⚠️ Like API এখনো Configure করা হয়নি। অর্ডার বাতিল এবং টাকা ফেরত দেওয়া হয়েছে.\n{e}")
    except Exception:
        log.exception("Like order error")
        # Unknown network outcome: do not auto-refund; reconcile with provider before retry/refund.
        db.finish_order(order_id,"PENDING","",0)
        await status_msg.edit_text("⏳ API থেকে নিশ্চিত ফলাফল পাওয়া যায়নি। অর্ডার PENDING রাখা হয়েছে; পুনরায় অর্ডার করবেন না। Admin যাচাই করবেন।")
    context.user_data.clear()

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=update.effective_user
    db.ensure_user(u.id,u.username or "",u.full_name)
    step=context.user_data.get("step")
    value=(update.message.text or "").strip()
    if not step:
        await update.message.reply_text("মেনু থেকে একটি অপশন বেছে নিন।",reply_markup=main_kb()); return
    if step=="uid":
        if not value.isdigit() or len(value)<5 or len(value)>15:
            await update.message.reply_text("❌ UID সঠিক মনে হচ্ছে না। আবার Player UID পাঠান:"); return
        context.user_data["ff_uid"]=value; context.user_data["step"]="server"
        await update.message.reply_text("আপনার Free Fire Server নির্বাচন করুন:",reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇧🇩 Bangladesh",callback_data="server:Bangladesh"),
             InlineKeyboardButton("🇮🇳 India",callback_data="server:India")]]))
    elif step=="deposit_amount":
        try: amount=float(value)
        except ValueError:
            await update.message.reply_text("সঠিক Amount লিখুন:"); return
        if amount<MIN_DEPOSIT:
            await update.message.reply_text(f"❌ সর্বনিম্ন ডিপোজিট ৳{MIN_DEPOSIT}। আবার Amount লিখুন:"); return
        context.user_data["deposit_amount"]=round(amount,2); context.user_data["step"]="deposit_trx"
        await update.message.reply_text(f"bKash নম্বর: {BKASH_NUMBER}\nAmount: ৳{amount:.2f}\nSend Money করার পর Transaction ID পাঠান:")
    elif step=="deposit_trx":
        amount=context.user_data["deposit_amount"]
        if len(value)<5 or len(value)>80:
            await update.message.reply_text("Transaction ID সঠিকভাবে পাঠান:"); return
        depid=db.create_deposit(u.id,u.username or "",amount,value)
        context.user_data.clear()
        await update.message.reply_text(f"⏳ DEPOSIT REQUEST SUBMITTED\n💰 Amount: ৳{amount:.2f}\n🧾 TrxID: {value}\n📌 Status: PENDING\nAdmin Approval-এর অপেক্ষায় থাকুন।",reply_markup=main_kb())
        for admin in ADMIN_IDS:
            try:
                await context.bot.send_message(admin,f"💳 NEW DEPOSIT REQUEST\n👤 Username: @{u.username or 'N/A'}\n🆔 Telegram ID: {u.id}\n💰 Amount: ৳{amount:.2f}\n🧾 TrxID: {value}\nRequest: #{depid}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve",callback_data=f"dep:approve:{depid}"),InlineKeyboardButton("❌ Reject",callback_data=f"dep:reject:{depid}")]]))
            except Exception: log.warning("Could not notify admin %s",admin)

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Access Denied."); return
    await update.message.reply_text("🛠 ADMIN PANEL",reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 All Users",callback_data="adm_users"),InlineKeyboardButton("💰 Edit User Balance",callback_data="adm_balance")],
        [InlineKeyboardButton("💳 Deposit Requests",callback_data="adm_deposits"),InlineKeyboardButton("📜 Deposit History",callback_data="adm_dephistory")],
        [InlineKeyboardButton("📦 All Orders",callback_data="adm_orders"),InlineKeyboardButton("📊 Bot Statistics",callback_data="adm_stats")]
    ]))

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    if not q.data.startswith("adm_"): return
    await q.answer()
    if not is_admin(q.from_user.id): return
    key=q.data[4:]
    if key=="users":
        rows=db.all_users()
        await q.message.reply_text("👥 ALL USERS\n"+("\n".join([f"{x['name']} | @{x['username']} | ID {x['user_id']} | ৳{x['balance']:.2f}" for x in rows]) if rows else "No users"))
    elif key=="balance":
        context.user_data["admin_step"]="balance_uid"
        await q.message.reply_text("যে User-এর Balance পরিবর্তন করবেন তার Telegram ID পাঠান:")
    elif key=="deposits":
        rows=db.pending_deposits()
        for x in rows:
            await q.message.reply_text(f"Deposit #{x['id']} | User {x['user_id']} | ৳{x['amount']:.2f} | TrxID {x['trxid']}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Approve",callback_data=f"dep:approve:{x['id']}"),InlineKeyboardButton("Reject",callback_data=f"dep:reject:{x['id']}")]]))
        if not rows: await q.message.reply_text("Pending Deposit নেই।")
    elif key=="dephistory":
        rows=db.all_deposits()
        await q.message.reply_text("📜 DEPOSIT HISTORY\n"+("\n".join([f"#{x['id']} User {x['user_id']} ৳{x['amount']:.2f} {x['status']} {x['trxid']}" for x in rows]) if rows else "No deposits"))
    elif key=="orders":
        rows=db.all_orders()
        await q.message.reply_text("📦 ALL ORDERS\n"+("\n".join([f"#{x['id']} User {x['user_id']} UID {x['ff_uid']} ৳{x['price']:.2f} {x['status']}" for x in rows]) if rows else "No orders"))
    elif key=="stats":
        s=db.stats()
        await q.message.reply_text(f"📊 BOT STATISTICS\nUsers: {s['users']}\nOrders: {s['orders']}\nSuccessful: {s['success']}\nLikes Delivered: {s['likes']}\nDeposits: ৳{s['deposits']:.2f}")

async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or context.user_data.get("admin_step")!="balance_uid": return False
    try: target=int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("সঠিক Telegram ID দিন:"); return True
    context.user_data["balance_target"]=target; context.user_data["admin_step"]="balance_action"
    await update.message.reply_text("কোন কাজ করবেন?",reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Add",callback_data="bal:add"),InlineKeyboardButton("Subtract",callback_data="bal:sub"),InlineKeyboardButton("Set",callback_data="bal:set")]]))
    return True

async def balance_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    if not q.data.startswith("bal:"): return
    await q.answer()
    if not is_admin(q.from_user.id): return
    context.user_data["balance_action"]=q.data.split(":")[1]
    context.user_data["admin_step"]="balance_amount"
    await q.message.reply_text("Amount লিখুন:")
async def balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or context.user_data.get("admin_step")!="balance_amount": return False
    try: amount=float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("সঠিক Amount লিখুন:"); return True
    action=context.user_data["balance_action"]; target=context.user_data["balance_target"]
    db.admin_balance(target,action,amount)
    context.user_data.clear()
    await update.message.reply_text(f"✅ Balance update হয়েছে। User ID: {target}\nবর্তমান Balance: ৳{db.balance(target):.2f}")
    return True

async def text_router(update, context):
    if await admin_text(update,context): return
    if await balance_amount(update,context): return
    await on_text(update,context)

def main():
    if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN সেট করা হয়নি। .env ফাইল তৈরি করুন।")
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("cancel",cancel))
    app.add_handler(CommandHandler("admin",admin_cmd))
    app.add_handler(CallbackQueryHandler(admin_buttons,pattern=r"^adm_"))
    app.add_handler(CallbackQueryHandler(balance_buttons,pattern=r"^bal:"))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_router))
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__": main()
