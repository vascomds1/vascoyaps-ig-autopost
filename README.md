# Vasco Yaps daily Instagram carousel autoposter

Every day this repo, on its own:

1. Asks Claude to research the top AI news of the day and write the carousel copy in the @vascoyaps voice.
2. Renders 8 branded slides (1080x1350) with `build_carousel.py`.
3. Hosts the images and publishes them as a carousel to @vascoyaps with a caption, via the Instagram Graph API.

It runs on GitHub Actions (free), so nothing needs to be open on your computer.

---

## Files

| File | What it does |
|------|--------------|
| `generate_copy.py` | Claude + web search writes `content.json` (cover, 6 cards, CTA, caption) |
| `build_carousel.py` | Renders `content.json` into 8 PNG slides in `output/` |
| `post_to_instagram.py` | Publishes the slides to Instagram as a carousel |
| `.github/workflows/daily.yml` | The daily schedule that runs all three |
| `content.sample.json` | Example copy, useful for local test renders |

Test a render locally: `python build_carousel.py content.sample.json output`

---

## One-time setup (~20 min)

### 1. Create the repo
- Create a **public** GitHub repo named `vascoyaps-ig-autopost` (public is required so Instagram can fetch the slide images by URL; no secrets live in the code).
- Upload all these files (keep the `.github/workflows/` folder structure).

### 2. Get a non-expiring Instagram token
You already have your **IG Business Account ID: `17841446352490605`**. Now get a token that does not expire:

1. In [Graph API Explorer](https://developers.facebook.com/tools/explorer), with app `vascoyaps-autopost` and the 5 permissions, click **Generate Access Token** and approve (this is your short-lived token).
2. Find **App ID** and **App Secret** in your app's **Settings > Basic**.
3. Exchange the short token for a long-lived user token. Paste this in your browser, filling in your values:
   ```
   https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN
   ```
   Copy the `access_token` from the response (the long-lived **user** token).
4. Now get the **Page** token, which does not expire. In Graph API Explorer, paste the long-lived user token into the token field, then run:
   ```
   me/accounts
   ```
   In the result, find your Vasco Yaps Page and copy its **`access_token`** value. **That Page token is what you use below, and it does not expire** as long as you keep the permissions and don't change your password.

### 3. Add repo secrets
In the repo: **Settings > Secrets and variables > Actions > New repository secret**. Add:

| Secret name | Value |
|-------------|-------|
| `IG_USER_ID` | `17841446352490605` |
| `IG_ACCESS_TOKEN` | the **Page** access token from step 2.4 |
| `ANTHROPIC_API_KEY` | your Anthropic API key (console.anthropic.com) |
| `CLAUDE_MODEL` | optional. A current model string, e.g. `claude-sonnet-4-5`. Leave unset to use the default. |

> Keep the App Secret and tokens here in GitHub Secrets only. Do not paste them into the code or anywhere public.

### 4. Enable and test
1. Open the **Actions** tab, enable workflows if prompted.
2. Click **Daily Vasco Yaps IG carousel > Run workflow**, set **dry_run = 1**, and run it. This builds everything and the slides get committed to `images/<date>/` but it does **not** post. Check that folder to review the slides.
3. When happy, run it again with **dry_run = 0** to do a real test post.
4. After that it runs automatically on the daily schedule.

---

## Schedule and timezone
The cron is `30 13 * * *` (13:30 UTC), which is **14:30 Lisbon time during summer (WEST)**. GitHub cron is always UTC and does not auto-adjust for daylight saving, so in winter (WET) this would fire at 13:30 Lisbon. To change the time, edit the `cron` line in `.github/workflows/daily.yml`.

## Changing the design
All visuals live in `build_carousel.py` (palette near the top: `AQUA`, `BLUE`, `VIOLET`, `INK_TOP/BOT`). The copy structure and voice live in `generate_copy.py`.

## Notes
- Instagram carousels allow up to 10 images; this posts 8.
- The Page token is effectively permanent. If posting ever fails with an auth error, just redo step 2 to mint a fresh Page token and update the `IG_ACCESS_TOKEN` secret.
- Old slide folders are auto-pruned to the last 7 days to keep the repo small.
