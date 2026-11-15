import base64, gzip, json, re, socket, ssl, struct, time, os, random
import urllib.parse, urllib.request
from flask import Flask, request, jsonify
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ═══════════ REDIS SETUP (Hardcoded) ═══════════
try:
    from upstash_redis import Redis
    redis = Redis(url="https://honest-cod-92290.upstash.io", token="gQAAAAAAAWiCAAIgcDE3NjI3NDFmM2MyYzU0MzVlOWY3Yjc5YzRlYWVlNzRlZQ")
except ImportError:
    redis = None
    print("[-] upstash-redis not installed")

# ═══════════ CONFIG & ACCOUNTS ═══════════
BACKUP_ACCOUNTS = [
    {"uid": "8455985312", "pass": "Pass_B6F0418685FE0470", "region": "PK"},
    {"uid": "8455985610", "pass": "Pass_04094031D2C60265", "region": "PK"},
    {"uid": "8455985601", "pass": "Pass_E7A35576F4B1DFA2", "region": "PK"},
    {"uid": "8448854742", "pass": "Pass_9053C8936F47B3A9", "region": "PK"},
    {"uid": "8448910654", "pass": "Pass_49E13B98067393CA", "region": "PK"},
]

STATIC_KEY = b"Yg&tc%DEuh6%Zc^8"
STATIC_IV  = b"6oyZDr22E3ychjM%"
CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
APP_ID = "100067"
OAUTH_URL = "https://100067.connect.garena.com/oauth/guest/token/grant"
MAJOR_LOGIN_URL = "https://loginbp.ppmainecoonghj.com/MajorLogin"
CLIENT_VERSION, RELEASE_VERSION = "2.133.11", "OB55"
REGION_BYTE = {"BD": 0x19, "IND": 0x14, "PK": 0x15}
AUTH_OPCODES = (0x93, 0x95, 0x89, 0x7B, 0x69, 0x8F, 0x78, 0x83)
ONLINE_OPCODES = (0x8D, 0x86, 0x67) + AUTH_OPCODES

TEMPLATE_UID, TEMPLATE_CODE = b"18827556186", b"9809812"
JOIN_TEMPLATE_B64 = ("CAQSzwoiCAEJChIZICcpKgc5ODA5ODEyMAZAAUq5CQoZSU5ESUFfTk9USU5JVD8xODgyNzU1NjE4NhAXGvcDd19ZUBQDCEQEAg4IU1YNB1ABWwMCWQJUVwQOVgAIU1ddAA9TAlMLABsAB0R0W0VBThoIFAAfGwAESQVRfHoLXm5Ja3l/Z05Eem5ff3wHcA1gfABxdQwVCU1jBV9hVV5oZ1J/BG9vB39EcU1+A0x3XWRWdH8FG1dZVkUZZn0adUhIA0pgXHB9Yl1jTmBYZlRZVwVUUVoPUX4DCXkCA3wKEQkLTVFcVll9V2Zac2gHHVNmUUMNA2Rgc35ES3pacAgUCkRMBmYXWmVnGm0LfEtrXEtaRHxeThl2E15OS3ALFgdLaHx2AWdqYlcAZH9ram9QYktERAF0AEJTS1BBBRIPSX1eQmJfY2ZIRldNYw9HDl0CAAB6XH14XlZQXwwVCQlKckdAe05hQ3J9WlQAZ3N5anx/d09iemUaWXpPBRIFRF9/e08HHUJ/Vn5Td2J9c0RweghCWHoJeVABVA8bDE1bSEl8TFNBfmB1eFBQUmxvY0RUam12BklTWlIIFAAIRFJsQGMGTGVNXXQXYWxaYH13YWBDXXBiT0AAbwgWAk5gVnpkSnAGVwx6dloTf3hNfExgBhxnanxaVwgMFQJJZlluSX0ZAXB7UQMcClZ8WXd9f0VPQm9QAE5aCxsHSnsMeVhZXGJ8aEFEAG1HeQ4AclAMcHENeW5lAAUiBHldVl0wDjoKEnB2YG9zZ2QcHEIIMi4xMzMuMTJIAlACWv0EA2JiU1E2ekhJMkFzSUFkVjJLeW9WbGRtZ201L3lmUE1Hd09oMmlnekdJd0xKKzRxb2JJZU1ybkxOUm1xU1kxcjh3Nm5Lb3M2Y1lqcEk0RWVUVnE2YWhLcUttN1hEVEc4UlFIWjNvOWpBMzFKbXZyRFFncmZXb3Z4YU5VbU9CNXF6UTlGZ0tGbEtqRS9hd25oOXhQcTdqVUlxMVUxTHpreWIydXV1QXYzemRQYkxpbUQva1FwMVMxNEpjbmdyd2NtQUtvWmE0ZHpJOFkyanZ3ZTJ3QWVLbERxMU5VWSsxWDVhcXY3Unl1bDIzVVR0eUkzajBhbEI3NC91SkhGUC83NFhncVFHRHhzcDRJeUIxUWFDcWZ1M3I0VVdheUlMd1BXMGJjZC9sQkF4Um43RUg5aXhBUTdleEdVdWdHVzBVZ0NrMHBXenAvNWNWZVB0cTRybzlWRmNHN1VWbVlTY1oxZm1lWjdvUHIrNXpuemlSS1V5bUR1L1JhNHMyY2VUczVaKzFzZ1RwVXAwZk5mNXV5dzBDd1VzeTdsVTdzTGtVZWJ3NThjeGtSYkNVUUFTVWVudGk4NGNyazVhdks4aXVSelFsbVpNb3VSb1M4ZGhxWFo2NU1FTDlyVzFTWmFtMEVxNnRFajYxMHgxSEFjUzlVUlVLUG15OHg1QWc3Z2pqVnpIQU1DbWtUVXdaTTVlYzFaazRFZ2lPd3dBbFhOeDFncGpoZW4zWlhCeTlYSFQyOXI0SkJlc3VYWlA0cEJlSkkwRjB3NGduRUFMaFZsZll2ekRiY3NOS3pRSVhvWjk4S0ZsYW01a1pTUlhiN0RkZ1NOVFhsV2xWWER3enFrPVoNCgRJREMxED0aA0lORFoNCgRJREMyEBEaA0lORGoCZW6CAQQ3T1IZogEFCAMQ+QKiAQUIBBCHA6IBBQgFEJ8BogEFCB0QyAGiAQQIFhBcogEFCA4QkAGiAQIIFboBFWFfNTg2OTU0NjgyNDM0MTM4Mzk3N9oBBAgCEAQ=")

def aes_enc(data, key=STATIC_KEY, iv=STATIC_IV): return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(data, 16))
def aes_dec_raw(data, key=STATIC_KEY, iv=STATIC_IV):
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
        if w == 0: v, i = _rv(b, i)
        elif w == 2:
            l, i = _rv(b, i)
            v, i = b[i:i + l], i + l
        elif w == 1: v, i = b[i:i + 8], i + 8
        elif w == 5: v, i = b[i:i + 4], i + 4
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

def do_login(account):
    uid, password = account["uid"], account["pass"]
    body = urllib.parse.urlencode({"uid": uid, "password": password, "response_type": "token", "client_type": "2", "client_secret": CLIENT_SECRET, "client_id": APP_ID}).encode()
    st, raw = http_post(OAUTH_URL, body, {"User-Agent": "GarenaMSDK/4.0.19P9(SM-M526B ;Android 13;en;IN;)", "Content-Type": "application/x-www-form-urlencoded"}, True, 20)
    j = json.loads(raw)
    d = {3: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 4: "free fire", 5: 1, 7: CLIENT_VERSION, 22: j["open_id"], 26: account["region"], 29: j["access_token"], 57: "1ac4b80ecf0478a44203bf8fac6120f5"}
    st, raw = http_post(MAJOR_LOGIN_URL, aes_enc(pb_encode(d)), {"User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)", "X-GA": "v1 1", "ReleaseVersion": "OB55", "X-Unity-Version": "2022.3.47f1"}, True)
    r = parse_response(raw, lambda f: True)
    bot_uid, jwt = pb_get(r, 1), _s(r, 8)
    key, iv = pb_get(r, 22), pb_get(r, 23)
    st, raw = http_post(_s(r, 10).rstrip("/") + "/GetLoginData", aes_enc(pb_encode(d)), {"User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)", "X-GA": "v1 1", "ReleaseVersion": "OB55", "X-Unity-Version": "2022.3.47f1", "Authorization": "Bearer " + jwt}, True)
    r2 = parse_response(raw, lambda f: True)
    return {"uid": bot_uid, "jwt": jwt, "key": key.hex(), "iv": iv.hex(), "kts": pb_get(r, 21), "online_ip": _s(r2, 14).split(":")[0], "online_port": int(_s(r2, 14).split(":")[1]), "region": _s(r2, 3, account["region"])}

def get_session(account):
    if redis:
        try:
            cached = redis.get(f"ff_session_{account['uid']}")
            if cached: return json.loads(cached)
        except: pass
    session = do_login(account)
    if redis:
        try: redis.setex(f"ff_session_{account['uid']}", 14400, json.dumps(session))
        except: pass
    return session

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
        raise RuntimeError("Auth failed")

app = Flask(__name__)
@app.after_request
def cors(res): res.headers["Access-Control-Allow-Origin"] = "*"; return res

@app.get("/api/refresh")
def refresh_all():
    results = {}
    for acc in BACKUP_ACCOUNTS:
        try:
            s = do_login(acc)
            if redis: redis.setex(f"ff_session_{acc['uid']}", 14400, json.dumps(s))
            results[acc['uid']] = "Refreshed"
        except Exception as e:
            results[acc['uid']] = f"Failed: {e}"
    return jsonify(ok=True, msg="Cron refresh done", results=results)

@app.get("/rishu")
def rishu():
    tc, eid, tuid = request.args.get("Tc"), request.args.get("Emote_id"), request.args.get("Target_Uid")
    acc = random.choice(BACKUP_ACCOUNTS)
    try:
        lg = get_session(acc)
        key, iv = bytes.fromhex(lg["key"]), bytes.fromhex(lg["iv"])
        auth_pkts = [(op, bytes([op, REGION_BYTE.get(lg["region"].upper(), 0x15)]) + int(lg["uid"]).to_bytes(8, "big") + int(lg["kts"]).to_bytes(4, "big") + b"\x00\x00\x00\x00" + struct.pack(">I", len(aes_enc(lg["jwt"].encode(), key, iv))) + aes_enc(lg["jwt"].encode(), key, iv)) for op in ONLINE_OPCODES]
        conn = Conn(lg["online_ip"], lg["online_port"], auth_pkts)
        conn.connect()
        inner = pb_build([(1, 0, int(lg["uid"])), (2, 0, int(eid)), (5, 2, pb_build([(1, 0, int(tuid)), (3, 0, int(eid))]))])
        payload = pb_build([(1, 0, 21), (2, 2, inner)])
        conn.sock.sendall(bytes.fromhex("0514") + struct.pack(">I", len(aes_enc(payload, key, iv))) + aes_enc(payload, key, iv))
        time.sleep(1.0)
        conn.sock.close()
        return jsonify(ok=True, msg=f"Sent via {lg['uid']}")
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
