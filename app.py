import json, os, requests, time, re, sys, asyncio, random, base64, gzip, socket, ssl, struct
import urllib.parse, urllib.request
from flask import Flask, request, jsonify
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ═══════════ PATH FIX FOR VERCEL ═══════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "Pb2"))
sys.path.insert(0, "/var/task")

try:
    import login_engine
    print("[+] login_engine imported successfully!", flush=True)
except Exception as e:
    print(f"[-] FATAL ERROR importing login_engine: {e}", flush=True)
    raise e

# ═══════════ REDIS SETUP ═══════════
try:
    from upstash_redis import Redis
    redis = Redis(url="https://honest-cod-92290.upstash.io", token="gQAAAAAAAWiCAAIgcDE3NjI3NDFmM2MyYzU0MzVlOWY3Yjc5YzRlYWVlNzRlZQ")
except ImportError:
    redis = None

# ═══════════ CONFIG & BACKUP ACCOUNTS ═══════════
BACKUP_ACCOUNTS = [
    {"uid": "8455985312", "pass": "Pass_B6F0418685FE0470", "region": "PK"},
    {"uid": "8455985610", "pass": "Pass_04094031D2C60265", "region": "PK"},
    {"uid": "8455985601", "pass": "Pass_E7A35576F4B1DFA2", "region": "PK"},
    {"uid": "8448854742", "pass": "Pass_9053C8936F47B3A9", "region": "PK"},
    {"uid": "8448910654", "pass": "Pass_49E13B98067393CA", "region": "PK"},
]

STATIC_KEY = b"Yg&tc%DEuh6%Zc^8"
STATIC_IV  = b"6oyZDr22E3ychjM%"
REGION_BYTE = {"BD": 0x19, "IND": 0x14, "PK": 0x15}
AUTH_OPCODES = (0x93, 0x95, 0x89, 0x7B, 0x69, 0x8F, 0x78, 0x83)
ONLINE_OPCODES = (0x8D, 0x86, 0x67) + AUTH_OPCODES

# ═══════════ CRYPTO & PROTOBUF HELPERS ═══════════
def aes_enc(data, key=STATIC_KEY, iv=STATIC_IV): 
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(data, 16))

def _wv(n):
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        if n: out.append(b | 0x80)
        else: out.append(b); return bytes(out)

def pb_build(fields):
    out = bytearray()
    for f, w, v in fields:
        out += _wv(f << 3 | w)
        out += _wv(v) if w == 0 else (_wv(len(v)) + v if w == 2 else v)
    return bytes(out)

# ═══════════ LOGIN VIA login_engine ═══════════
def do_login(account):
    uid, password, region = account["uid"], account["pass"], account["region"]
    print(f"\n[DEBUG] Logging in {uid} via login_engine...", flush=True)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        r = loop.run_until_complete(login_engine.do_login(uid, password, region))
        if not r:
            print(f"[-] {uid} login_engine returned None", flush=True)
            return None
        
        session = {
            "uid": int(r.get("bot_uid")),
            "jwt": r.get("token"),
            "key": r.get("key").hex() if isinstance(r.get("key"), (bytes, bytearray)) else r.get("key"),
            "iv": r.get("iv").hex() if isinstance(r.get("iv"), (bytes, bytearray)) else r.get("iv"),
            "kts": int(r.get("timestamp", time.time())),
            "online_ip": r.get("online_ip"),
            "online_port": int(r.get("online_port")),
            "region": r.get("region", region)
        }
        print(f"[+] {uid} Login OK. Bot UID: {session['uid']}", flush=True)
        return session
    except Exception as e:
        print(f"[-] {uid} login_engine Exception: {type(e).__name__}: {e}", flush=True)
        return None
    finally:
        loop.close()

def get_session(account):
    if redis:
        try:
            cached = redis.get(f"ff_session_{account['uid']}")
            if cached:
                print(f"[CACHE HIT] {account['uid']}", flush=True)
                return json.loads(cached)
        except Exception as e: print("Redis Read Err:", e)
    
    print(f"[CACHE MISS] Doing fresh login for {account['uid']}", flush=True)
    session = do_login(account)
    
    if session and redis:
        try: 
            redis.setex(f"ff_session_{account['uid']}", 14400, json.dumps(session))
            print(f"[+] Saved cache for {account['uid']}", flush=True)
        except Exception as e: print("Redis Save Err:", e)
    return session

# ═══════════ TCP CONNECT & EMOTE ═══════════
class Conn:
    def __init__(self, host, port, auth_pkts):
        self.host, self.port, self.auth_pkts = host, int(port), auth_pkts
    def connect(self):
        for op, pkt in self.auth_pkts:
            s = socket.create_connection((self.host, self.port), timeout=15)
            s.sendall(pkt)
            s.settimeout(4.0)
            if len(s.recv(5)) == 5: 
                self.sock = s; 
                return
            s.close()
        raise RuntimeError("TCP Auth failed")

app = Flask(__name__)

@app.after_request
def cors(res): 
    res.headers["Access-Control-Allow-Origin"] = "*"
    return res

@app.get("/api/refresh")
def refresh_all():
    results = {}
    for acc in BACKUP_ACCOUNTS:
        s = get_session(acc)
        results[acc['uid']] = "Cached" if s else "Failed"
    return jsonify(ok=True, msg="Cron refresh done", results=results)

@app.get("/rishu")
def rishu():
    tc = request.args.get("Tc")
    eid = request.args.get("Emote_id")
    tuid = request.args.get("Target_Uid")
    
    if not tc or not eid or not tuid:
        return jsonify(ok=False, error="Tc, Emote_id, and Target_Uid are required"), 400

    acc = random.choice(BACKUP_ACCOUNTS)
    try:
        lg = get_session(acc)
        if not lg: 
            return jsonify(ok=False, error="Login failed"), 500
        
        key, iv = bytes.fromhex(lg["key"]), bytes.fromhex(lg["iv"])
        
        # Build Auth Packets
        auth_pkts = []
        for op in ONLINE_OPCODES:
            enc_jwt = aes_enc(lg["jwt"].encode(), key, iv)
            pkt = bytes([op, REGION_BYTE.get(lg["region"].upper(), 0x15)]) + int(lg["uid"]).to_bytes(8, "big") + int(lg["kts"]).to_bytes(4, "big") + b"\x00\x00\x00\x00" + struct.pack(">I", len(enc_jwt)) + enc_jwt
            auth_pkts.append((op, pkt))
            
        conn = Conn(lg["online_ip"], lg["online_port"], auth_pkts)
        conn.connect()
        
        # Build Emote Packet
        inner = pb_build([(1, 0, int(lg["uid"])), (2, 0, int(eid)), (5, 2, pb_build([(1, 0, int(tuid)), (3, 0, int(eid))]))])
        payload = pb_build([(1, 0, 21), (2, 2, inner)])
        enc_emote = aes_enc(payload, key, iv)
        emote_pkt = bytes.fromhex("0514") + struct.pack(">I", len(enc_emote)) + enc_emote
        
        conn.sock.sendall(emote_pkt)
        time.sleep(1.0)
        conn.sock.close()
        
        return jsonify(ok=True, msg=f"Sent via {lg['uid']}")
    except Exception as e:
        print(f"[-] Emote Error: {e}", flush=True)
        return jsonify(ok=False, error=str(e)), 500

@app.get("/")
def health():
    return jsonify(ok=True, status="Online", msg="Devils Will Rise API")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
