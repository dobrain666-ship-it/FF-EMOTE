import base64, gzip, json, queue, re, socket, ssl, struct, threading, time
import urllib.parse, urllib.request, os, random
from flask import Flask, request, jsonify
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# ═══════════ REDIS SETUP ═══════════
try:
    from upstash_redis import Redis
    redis = Redis(url="https://honest-cod-92290.upstash.io", token="gQAAAAAAAWiCAAIgcDE3NjI3NDFmM2MyYzU0MzVlOWY3Yjc5YzRlYWVlNzRlZQ")
except ImportError:
    redis = None
    print("[-] upstash-redis not installed")

# ═══════════ CONFIG & ACCOUNT ═══════════
BACKUP_ACCOUNTS = [
    {"uid": "8457006743", "pass": "Pass_DC41A5900E6B6794", "region": "PK"}
]

STATIC_KEY = b"Yg&tc%DEuh6%Zc^8"
STATIC_IV  = b"6oyZDr22E3ychjM%"
CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
APP_ID = "100067"
OAUTH_URL = "https://100067.connect.garena.com/oauth/guest/token/grant"
MAJOR_LOGIN_URL = "https://loginbp.ppmainecoonghj.com/MajorLogin"
DEFAULT_CLIENT_HOST = "https://loginbp.ppmainecoonghj.com/"
CLIENT_VERSION, RELEASE_VERSION = "2.133.11", "OB55"

AUTH_OPCODES = (0x93, 0x95, 0x89, 0x7B, 0x69, 0x8F, 0x78, 0x83)
ONLINE_OPCODES = (0x8D, 0x86, 0x67) + AUTH_OPCODES
REGION_BYTE = {"BD": 0x19, "IND": 0x14, "PK": 0x15}
DEFAULT_EMOTE_ID = 909000001

TEMPLATE_UID, TEMPLATE_CODE = b"18827556186", b"9809812"
JOIN_TEMPLATE_B64 = (
    "CAQSzwoiCAEJChIZICcpKgc5ODA5ODEyMAZAAUq5CQoZSU5ESUFfTk9USU5JVD8xODgyNzU1NjE4NhAXGvcDd19ZUBQDCEQEAg4I"
    "U1YNB1ABWwMCWQJUVwQOVgAIU1ddAA9TAlMLABsAB0R0W0VBThoIFAAfGwAESQVRfHoLXm5Ja3l/Z05Eem5ff3wHcA1gfABxdQwV"
    "CU1jBV9hVV5oZ1J/BG9vB39EcU1+A0x3XWRWdH8FG1dZVkUZZn0adUhIA0pgXHB9Yl1jTmBYZlRZVwVUUVoPUX4DCXkCA3wKEQkL"
    "TVFcVll9V2Zac2gHHVNmUUMNA2Rgc35ES3pacAgUCkRMBmYXWmVnGm0LfEtrXEtaRHxeThl2E15OS3ALFgdLaHx2AWdqYlcAZH9r"
    "am9QYktERAF0AEJTS1BBBRIPSX1eQmJfY2ZIRldNYw9HDl0CAAB6XH14XlZQXwwVCQlKckdAe05hQ3J9WlQAZ3N5anx/d09iemUa"
    "WXpPBRIFRF9/e08HHUJ/Vn5Td2J9c0RweghCWHoJeVABVA8bDE1bSEl8TFNBfmB1eFBQUmxvY0RUam12BklTWlIIFAAIRFJsQGMG"
    "TGVNXXQXYWxaYH13YWBDXXBiT0AAbwgWAk5gVnpkSnAGVwx6dloTf3hNfExgBhxnanxaVwgMFQJJZlluSX0ZAXB7UQMcClZ8WXd9"
    "f0VPQm9QAE5aCxsHSnsMeVhZXGJ8aEFEAG1HeQ4AclAMcHENeW5lAAUiBHldVl0wDjoKEnB2YG9zZ2QcHEIIMi4xMzMuMTJIAlAC"
    "Wv0EA2JiU1E2ekhJMkFzSUFkVjJLeW9WbGRtZ201L3lmUE1Hd09oMmlnekdJd0xKKzRxb2JJZU1ybkxOUm1xU1kxcjh3Nm5Lb3M2"
    "Y1lqcEk0RWVUVnE2YWhLcUttN1hEVEc4UlFIWjNvOWpBMzFKbXZyRFFncmZXb3Z4YU5VbU9CNXF6UTlGZ0tGbEtqRS9hd25oOXhQ"
    "cTdqVUlxMVUxTHpreWIydXV1QXYzemRQYkxpbUQva1FwMVMxNEpjbmdyd2NtQUtvWmE0ZHpJOFkyanZ3ZTJ3QWVLbERxMU5VWSsx"
    "WDVhcXY3Unl1bDIzVVR0eUkzajBhbEI3NC91SkhGUC83NFhncVFHRHhzcDRJeUIxUWFDcWZ1M3I0VVdheUlMd1BXMGJjZC9sQkF4"
    "Um43RUg5aXhBUTdleEdVdWdHVzBVZ0NrMHBXenAvNWNWZVB0cTRybzlWRmNHN1VWbVlTY1oxZm1lWjdvUHIrNXpuemlSS1V5bUR1"
    "L1JhNHMyY2VUczVaKzFzZ1RwVXAwZk5mNXV5dzBDd1VzeTdsVTdzTGtVZWJ3NThjeGtSYkNVUUFTVWVudGk4NGNyazVhdks4aXVS"
    "elFsbVpNb3VSb1M4ZGhxWFo2NU1FTDlyVzFTWmFtMEVxNnRFajYxMHgxSEFjUzlVUlVLUG15OHg1QWc3Z2pqVnpIQU1DbWtUVXda"
    "TTVlYzFaazRFZ2lPd3dBbFhOeDFncGpoZW4zWlhCeTlYSFQyOXI0SkJlc3VYWlA0cEJlSkkwRjB3NGduRUFMaFZsZll2ekRiY3NO"
    "S3pRSVhvWjk4S0ZsYW01a1pTUlhiN0RkZ1NOVFhsV2xWWER3enFrPVoNCgRJREMxED0aA0lORFoNCgRJREMyEBEaA0lORGoCZW6C"
    "AQQ3T1IZogEFCAMQ+QKiAQUIBBCHA6IBBQgFEJ8BogEFCB0QyAGiAQQIFhBcogEFCA4QkAGiAQIIFboBFWFfNTg2OTU0NjgyNDM0"
    "MTM4Mzk3N9oBBAgCEAQ="
)

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

def aes_enc(data, key=STATIC_KEY, iv=STATIC_IV): return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(data, 16))
def aes_dec(data, key=STATIC_KEY, iv=STATIC_IV): return unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(data), 16)
def aes_dec_raw(data, key=STATIC_KEY, iv=STATIC_IV):
    if not data or len(data) % 16 != 0: return None
    try: return AES.new(key, AES.MODE_CBC, iv).decrypt(data)
    except: return None

def _wv(n):
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        if n: out.append(b | 0x80)
        else: out.append(b); return bytes(out)

def _rv(b, i):
    n = s = 0
    while True:
        c = b[i]; i += 1
        n |= (c & 0x7F) << s; s += 7
        if not c & 0x80: return n, i

def pb_parse(b):
    i, out = 0, []
    while i < len(b):
        k, i = _rv(b, i)
        f, w = k >> 3, k & 7
        if f == 0: raise ValueError("field 0")
        if w == 0: v, i = _rv(b, i)
        elif w == 2:
            l, i = _rv(b, i)
            if i + l > len(b): raise ValueError("overrun")
            v, i = b[i:i + l], i + l
        elif w == 1: v, i = b[i:i + 8], i + 8
        elif w == 5: v, i = b[i:i + 4], i + 4
        else: raise ValueError("wire type")
        out.append((f, w, v))
    return out

def pb_build(fields):
    out = bytearray()
    for f, w, v in fields:
        out += _wv(f << 3 | w)
        out += _wv(v) if w == 0 else (_wv(len(v)) + v if w == 2 else v)
    return bytes(out)

def pb_get(fields, n):
    for f, w, v in fields:
        if f == n: return v

def pb_encode(d):
    out = []
    for k, v in d.items():
        if isinstance(v, int): out.append((k, 0, v))
        else: out.append((k, 2, v.encode() if isinstance(v, str) else bytes(v)))
    return pb_build(out)

def retarget(b, repl, depth=0):
    if b and all(32 <= c < 127 for c in b):
        for old, new in repl.items(): b = b.replace(old, new)
        return b
    try:
        fields = pb_parse(b)
        if depth < 8 and fields and pb_build(fields) == b:
            return pb_build([(f, w, retarget(v, repl, depth + 1) if w == 2 else v) for f, w, v in fields])
    except: pass
    for old, new in repl.items(): b = b.replace(old, new)
    return b

def http_post(url, data, headers, verify=True, timeout=30):
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    ctx = None if verify else ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r: return r.status, r.read()

def parse_response(raw, validator):
    if raw[:2] == b"\x1f\x8b": raw = gzip.decompress(raw)
    for buf in [aes_dec_raw(raw), aes_dec_raw(raw[64:]) if len(raw)>64 else None, raw]:
        if not buf: continue
        try:
            fields = pb_parse(buf)
            if fields and validator(fields): return fields
        except: pass
    raise ValueError("cannot parse server response")

def _s(fields, n, default=""):
    v = pb_get(fields, n)
    return v.decode(errors="ignore") if isinstance(v, bytes) else default

def oauth(uid, password, verify):
    body = urllib.parse.urlencode({"uid": uid, "password": password, "response_type": "token", "client_type": "2", "client_secret": CLIENT_SECRET, "client_id": APP_ID}).encode()
    st, raw = http_post(OAUTH_URL, body, {"User-Agent": "GarenaMSDK/4.0.19P9(SM-M526B ;Android 13;en;PK;)", "Content-Type": "application/x-www-form-urlencoded", "Connection": "close"}, verify, 20)
    j = json.loads(raw)
    if not j.get("open_id") or not j.get("access_token"): raise RuntimeError("OAuth failed: %s" % j)
    return j["open_id"], j["access_token"]

def _client_info(open_id, access_token, platform="4", extra=None):
    d = {3: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 4: "free fire", 5: 1, 7: CLIENT_VERSION,
         8: "Android OS 10 / API-29 (QP1A.190711.020/1617006012)", 9: "Handheld", 10: "Vi India", 11: "WIFI",
         12: 1600, 13: 720, 14: "320", 15: "ARM64 FP ASIMD AES | 2301 | 8", 16: 2799,
         17: "PowerVR Rogue GE8320", 18: "OpenGL ES 3.2 build 1.11@5425693",
         19: "Google|9f7d6b8b-b10c-454a-852d-06332cd498eb", 20: "151.158.158.220", 21: "en",
         22: open_id, 23: platform, 24: "Handheld", 25: "realme RMX2189", 26: "PK",
         29: access_token, 30: 1, 41: "Vi India", 42: "WIFI", 57: "1ac4b80ecf0478a44203bf8fac6120f5",
         60: 19799, 61: 2536, 62: 5056, 64: 2768, 65: 19999, 66: 2536, 67: 19799, 73: 1,
         74: "/data/app/com.dts.freefiremax-ShI7E0dK8p1IiZ785pvuVQ==/lib/arm64", 76: 2,
         77: "38f4751a330688ab124c2c804cec90a5|/data/app/com.dts.freefiremax-ShI7E0dK8p1IiZ785pvuVQ==/base.apk",
         78: 2, 79: 2, 81: "64", 83: "2019118527", 86: "OpenGLES3", 87: 3071, 88: 4, 92: 67920,
         93: "android_max",
         94: "KqsHT+UrR1HKqb6+1db+Ofei+NtZr2+hbiBo3yKDL8w+8E3S5qF2IgEEe1fFQFyHRzl4iyHjHp+QsfeLbjJ6+DidTiKxm0ak2uYYa6QR4nAUdlZR",
         95: 111107, 96: '{"cur_rate":null,"support_etc2":true}', 97: 1, 98: 1, 99: platform, 100: platform,
         102: "", 104: 83812, 105: 1,
         106: "https://dl-bs.ggpolarbear.com/live/ABHotUpdates/|https://core-bs.ggpolarbear.com/live/ABHotUpdates/|a4332cb1c1a84e51dd77441e4856ed5a",
         107: "1.9393e7b8e53e8aeb"}
    d.update(extra or {})
    return pb_encode(d)

def _ga_headers(bearer=""):
    return {"User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)", "Accept": "*/*", "Accept-Encoding": "deflate, gzip", "X-GA-SV": str(int(time.time())), "Authorization": "Bearer " + bearer, "X-GA": "v1 1", "ReleaseVersion": RELEASE_VERSION, "Content-Type": "application/x-www-form-urlencoded", "X-Unity-Version": "2018.4.12f1"}

def do_login(account):
    open_id, access_token = oauth(account["uid"], account["pass"], True)
    st, raw = http_post(MAJOR_LOGIN_URL, aes_enc(_client_info(open_id, access_token)), _ga_headers(), True)
    r = parse_response(raw, lambda f: True)
    bot_uid, jwt, key, iv = pb_get(r, 1), _s(r, 8), pb_get(r, 22), pb_get(r, 23)
    
    st, raw = http_post(_s(r, 10).rstrip("/") + "/GetLoginData", aes_enc(_client_info(open_id, access_token, "4", {20: "27.59.76.15", 90: "New Delhi", 91: "DL", 99: "0"})), _ga_headers(jwt), True, 20)
    r2 = parse_response(raw, lambda f: True)
    online = _s(r2, 14)
    
    return {"uid": bot_uid, "jwt": jwt, "key": key.hex(), "iv": iv.hex(), "kts": pb_get(r, 21), "online_ip": online.split(":")[0], "online_port": int(online.split(":")[1]), "region": _s(r2, 3, "PK")}

def get_session(account):
    if redis:
        try:
            cached = redis.get(f"ff_session_{account['uid']}")
            if cached:
                print(f"[CACHE HIT] {account['uid']}", flush=True)
                return json.loads(cached)
        except: pass
    
    print(f"[CACHE MISS] Fresh login for {account['uid']}", flush=True)
    try:
        session = do_login(account)
        if redis:
            try: redis.setex(f"ff_session_{account['uid']}", 14400, json.dumps(session))
            except: pass
        return session
    except Exception as e:
        print(f"[-] Login failed for {account['uid']}: {e}", flush=True)
        return None

# ═══════════ 4-HOUR AUTO REFRESH ═══════════
def auto_refresh_job():
    print("[*] 4-Hour Cron: Refreshing tokens...", flush=True)
    for acc in BACKUP_ACCOUNTS:
        get_session(acc) # Forces login if expired

scheduler = BackgroundScheduler()
scheduler.add_job(auto_refresh_job, 'interval', hours=4)
scheduler.start()

class Conn:
    def __init__(self, host, port, auth_pkts):
        self.host, self.port, self.auth_pkts = host, int(port), auth_pkts
    def connect(self):
        for op, pkt in self.auth_pkts:
            s = socket.create_connection((self.host, self.port), timeout=15)
            s.sendall(pkt)
            s.settimeout(4.0)
            if len(s.recv(5)) == 5: self.sock = s; return
            s.close()
        raise RuntimeError("TCP Auth failed")

app = Flask(__name__)
@app.after_request
def cors(res): res.headers["Access-Control-Allow-Origin"] = "*"; return res

@app.get("/api/refresh")
def refresh_all():
    results = {}
    for acc in BACKUP_ACCOUNTS:
        s = get_session(acc)
        results[acc['uid']] = "Cached" if s else "Failed"
    return jsonify(ok=True, msg="Manual Refresh Done", results=results)

@app.get("/rishu")
def rishu():
    tc, eid, tuid = request.args.get("Tc"), request.args.get("Emote_id"), request.args.get("Target_Uid")
    if not tc or not eid or not tuid: return jsonify(ok=False, error="Tc, Emote_id, Target_Uid required"), 400
    
    acc = random.choice(BACKUP_ACCOUNTS)
    lg = get_session(acc)
    if not lg: return jsonify(ok=False, error="Login failed"), 500
        
    key, iv = bytes.fromhex(lg["key"]), bytes.fromhex(lg["iv"])
    auth_pkts = [(op, bytes([op, REGION_BYTE.get(lg["region"].upper(), 0x15)]) + int(lg["uid"]).to_bytes(8, "big") + int(lg["kts"]).to_bytes(4, "big") + b"\x00\x00\x00\x00" + struct.pack(">I", len(aes_enc(lg["jwt"].encode(), key, iv))) + aes_enc(lg["jwt"].encode(), key, iv)) for op in ONLINE_OPCODES]
    
    try:
        conn = Conn(lg["online_ip"], lg["online_port"], auth_pkts)
        conn.connect()
        # Join + Emote Packet Building
        inner = pb_build([(1, 0, int(lg["uid"])), (2, 0, int(eid)), (5, 2, pb_build([(1, 0, int(tuid)), (3, 0, int(eid))]))])
        payload = pb_build([(1, 0, 21), (2, 2, inner)])
        conn.sock.sendall(bytes.fromhex("0514") + struct.pack(">I", len(aes_enc(payload, key, iv))) + aes_enc(payload, key, iv))
        time.sleep(1.0)
        conn.sock.close()
        return jsonify(ok=True, msg=f"Sent via {lg['uid']}")
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.get("/")
def health(): return jsonify(ok=True, status="Running")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), threaded=True)
