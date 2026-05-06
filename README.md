# LinkedIn Auto-Scheduler
### Tiwa Elegbeleye — May 2026 Content Calendar

Automatically schedules and publishes your 12 LinkedIn posts with images at the right times.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up credentials
cp .env.example .env
# Edit .env and add your LinkedIn token and person URN

# 3. Place your images in ./images/
# (Copy the 12 PNGs generated alongside this script)

# 4. Test without posting (dry run)
python scheduler.py --dry-run

# 5. See the full schedule
python scheduler.py --list

# 6. Run the scheduler (keep this terminal open)
python scheduler.py
```

---

## How to Get Your LinkedIn Credentials

### Step 1 — Create a LinkedIn App
1. Go to https://www.linkedin.com/developers/apps
2. Click **Create App**
3. Fill in app name, LinkedIn Page (use your profile), and logo
4. Under **Products**, request access to **Share on LinkedIn**

### Step 2 — Get Your Access Token
1. In your app, go to **Auth** tab
2. Under **OAuth 2.0 tools**, click **Request access token**
3. Select scopes: `w_member_social`, `r_liteprofile`
4. Authorize and copy the token
5. Paste it into `.env` as `LINKEDIN_ACCESS_TOKEN`

### Step 3 — Get Your Person URN
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.linkedin.com/v2/me"
```
Copy the `id` field and format it as `urn:li:person:YOUR_ID`

---

## Commands

| Command | What it does |
|---------|-------------|
| `python scheduler.py` | Start the scheduler (runs all day) |
| `python scheduler.py --list` | Preview all 12 posts and dates |
| `python scheduler.py --dry-run` | Simulate without posting |
| `python scheduler.py --run-now 1` | Immediately publish post #1 |
| `python scheduler.py --run-now 4` | Immediately publish post #4 |

---

## Post Schedule

| # | Date | Time | Topic |
|---|------|------|-------|
| 1 | May 2  | 8am | My 8-year journey — origin story |
| 2 | May 5  | 8am | Production auth checklist (GitHub) |
| 3 | May 8  | 8am | Leading a dev team of 5 |
| 4 | May 12 | 8am | 5 React patterns (GitHub) |
| 5 | May 14 | 8am | 25% sales lift from redesign |
| 6 | May 16 | 12pm | Poll: what's slowing your team? |
| 7 | May 19 | 8am | Security at every stack layer |
| 8 | May 21 | 8am | Node.js + MongoDB API (GitHub) |
| 9 | May 23 | 8am | 50% growth through engineering |
| 10 | May 26 | 8am | WordPress is underrated |
| 11 | May 28 | 12pm | 8 years → 8 lessons |
| 12 | May 30 | 8am | Personal brand closer |

---

## Keeping It Running

To keep the scheduler alive even when you close your laptop:

**macOS / Linux (nohup):**
```bash
nohup python scheduler.py > scheduler.log 2>&1 &
```

**Or use screen:**
```bash
screen -S linkedin
python scheduler.py
# Ctrl+A then D to detach
```

**On a VPS/server (recommended):**
```bash
# Add to crontab to restart on reboot
crontab -e
@reboot /usr/bin/python3 /path/to/scheduler.py >> /path/to/scheduler.log 2>&1
```

---

## Notes

- LinkedIn access tokens expire after **60 days** — refresh in the developer portal if posts start failing
- The scheduler checks every 30 seconds — it won't miss a scheduled time
- All activity is logged to `scheduler.log`
- Posts 2, 4, 7, 8, 10, 11 automatically add a first comment with the GitHub link so LinkedIn doesn't suppress reach on the main post

---

*Built for Tiwa Elegbeleye · github.com/ifetiwa*
