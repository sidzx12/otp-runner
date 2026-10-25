# OTP Runner

Multi-service OTP / SMS / call flood runner for Termux.

Owner: **@sidzx12**  
Repo: https://github.com/sidzx12/otp-runner

## Install (Termux)

```bash
pkg update -y && pkg upgrade -y
pkg install python git -y
git clone https://github.com/sidzx12/otp-runner.git
cd otp-runner
pip install -r requirements.txt
python otp_spam.py
