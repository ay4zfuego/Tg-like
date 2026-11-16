# FF Likes Telegram Bot (Starter Project)

## এই প্রজেক্টে যা আছে
- `/start` welcome ও user main menu
- 200 Likes Instant প্যাকেজ; retail price ৳7
- UID → Bangladesh/India server → Player Info lookup → Confirm/Cancel
- অর্ডার চলাকালে Telegram message edit করে loading-style animation
- bKash deposit request; নম্বর 01752859888; minimum deposit ৳10
- Admin Approve/Reject; একই TrxID duplicate আটকাতে SQLite UNIQUE constraint
- My Account, Deposit History, All Orders
- `/admin`: All Users, Edit User Balance, Deposit Requests, Deposit History, All Orders, Statistics
- SQLite wallet ledger ও order/deposit records

## জরুরি API সীমাবদ্ধতা
Player Info URL-এর query parameter `uid` এবং `region` ধরে রাখা হয়েছে। আপনার API-তে server parameter-এর নাম বা accepted values আলাদা হলে `api_client.py` বদলাতে হবে।
Like API সংযুক্ত করা হয়েছে: `POST` request, JSON body `{"key":"...","uid":"..."}` এবং `Content-Type: application/json`। Render Environment Variables-এ `LIKE_API_URL`-এ provider-এর সম্পূর্ণ webhook URL এবং `LIKE_API_KEY`-এ API key দিন। গোপন URL/key GitHub বা README-তে রাখবেন না। Provider-এর দেওয়া response অনুযায়ী top-level `ok: true` হলে success এবং `ok: false` হলে ব্যর্থতা ধরা হয়। HTTP/network timeout হলে ফলাফল অনিশ্চিত বলে অর্ডার PENDING থাকবে; একই UID দিয়ে সঙ্গে সঙ্গে আবার অর্ডার দেবেন না।

Player Info URL-এর query parameter `uid` ও `region` আগের মতো রাখা হয়েছে; provider-এর Player Info API-তে `region` parameter/মান গ্রহণ করে কি না আলাদাভাবে যাচাই করা দরকার।
`charged: 4.5` provider cost এবং user retail price ৳7 আলাদা। এই starter project user wallet থেকে ৳7 reserve করে; API response reconciliation-এর পরে final settlement policy production-এর আগে যাচাই করতে হবে।
Player Info API-র actual response-এ fields `name`, `level`, `honor_score`, `region`, `likes`, `uid` থাকা প্রত্যাশা করা হয়েছে।

## Local setup (Windows)
1. Python 3.11 বা নতুন ভার্সন ইনস্টল করুন।
2. ZIP Extract করুন।
3. Folder-এর ভিতরে Command Prompt খুলুন।
4. চালান:
   ```bash
   py -m venv venv
   venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
5. `.env.example` কপি করে `.env` নাম দিন।
6. `.env`-এ BotFather থেকে পাওয়া `BOT_TOKEN` এবং আপনার numeric Telegram ID `ADMIN_IDS`-এ বসান।
7. চালান:
   ```bash
   python app.py
   ```

## Telegram Admin ID বের করা
নিজের Telegram numeric ID নির্ভরযোগ্য ID-bot দিয়ে দেখে `.env`-এর `ADMIN_IDS`-এ দিন। একাধিক Admin হলে comma দিয়ে লিখুন: `111111,222222`। Bot token বা API secret কাউকে দেবেন না।

## Render-এ ফ্রি হোস্টিং (সম্ভাব্য)
1. GitHub-এ নতুন private repository তৈরি করুন।
2. Extract করা project files repository-তে upload/push করুন।
3. Render account খুলে New → Blueprint অথবা Background Worker তৈরি করুন।
4. Repository connect করুন; `render.yaml` থাকলে Blueprint deploy করা যায়।
5. Environment variables-এ `BOT_TOKEN`, `ADMIN_IDS`, `LIKE_API_URL` ও `LIKE_API_KEY` দিন।
6. Deploy logs-এ `Application started`/polling startup errors নেই কি না দেখুন।

**Free hosting সতর্কতা:** Render-এর free availability/worker eligibility ও sleep policy পরিবর্তিত হতে পারে। Free web service-কে 24/7 background worker ধরে নেবেন না। Telegram bot polling-এর জন্য always-on worker/VPS প্রয়োজন হতে পারে; free tier-এ sleep, restart বা usage limits থাকলে bot বন্ধ থাকতে পারে। Render dashboard-এ বর্তমান plan ও worker support যাচাই করুন। SQLite local disk ephemeral হলে redeploy/restart-এ database হারাতে পারে; production-এ persistent disk বা managed PostgreSQL ব্যবহার করুন।

## Production-এর আগে অবশ্যই
- Like API contract implement ও test
- Player Info API server parameter confirm
- Database persistence/backup configure
- bKash payment manual verification policy
- Admin balance adjustment audit review
- Pending order reconciliation, webhook/retry strategy
- Bot token ও secrets শুধু environment variables-এ রাখা
