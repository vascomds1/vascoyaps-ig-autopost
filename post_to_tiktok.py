#!/usr/bin/env python3
"""
Cross-post the rendered carousel to TikTok (@vascoyaps) via the Metricool API.
Runs in the GitHub Action right after post_to_instagram.py, so the TikTok
cross-post no longer depends on a local scheduled task / the desktop app being open.

Env:
  METRICOOL_USER_TOKEN  Metricool API access token (Settings -> Metricool API).  [secret]
  METRICOOL_USER_ID     Metricool user id (default 4913287 = vascoyaps owner).
  METRICOOL_BLOG_ID     Metricool brand/blog id (default 6377217 = vascoyaps).
  IMAGE_BASE_URL        Public base URL of today's slides (same value as the Instagram step).
  METRICOOL_TZ          IANA timezone for the publish time (default Europe/Lisbon).
  DRY_RUN               "1" to skip the actual API call (build only).
"""
import os, sys, json, glob, datetime, requests
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://app.metricool.com/api"
TOKEN = os.environ.get("METRICOOL_USER_TOKEN")
USER_ID = os.environ.get("METRICOOL_USER_ID", "4913287")
BLOG_ID = os.environ.get("METRICOOL_BLOG_ID", "6377217")
TZ = os.environ.get("METRICOOL_TZ", "Europe/Lisbon")
DRY = os.environ.get("DRY_RUN") == "1"

def main():
    if not TOKEN:
        print("METRICOOL_USER_TOKEN not set; skipping TikTok cross-post (Instagram still posted).")
        return
    IMG_BASE = os.environ["IMAGE_BASE_URL"].rstrip("/")
    slides = sorted(glob.glob(os.path.join(HERE, "output", "slide_*.jpg")))
    if not slides:
        sys.exit("No slides found in output/. Run build_carousel.py first.")
    media = [f"{IMG_BASE}/{os.path.basename(s)}" for s in slides]
    caption = json.load(open(os.path.join(HERE, "content.json"))).get("caption", "")

    # publish ~10 min out: a small buffer, near-simultaneous with the Instagram post
    when = datetime.datetime.now(ZoneInfo(TZ)) + datetime.timedelta(minutes=10)
    body = {
        "text": caption,
        "providers": [{"network": "tiktok"}],
        "media": media,
        "publicationDate": {"dateTime": when.strftime("%Y-%m-%dT%H:%M:%S"), "timezone": TZ},
        "draft": False,
        "autoPublish": True,
        "tiktokData": {
            "privacyOption": "PUBLIC_TO_EVERYONE",
            "autoAddMusic": True,            # TikTok auto-adds a recommended song
            "photoCoverIndex": 0,
            "disableComment": False,
            "disableDuet": False,
            "disableStitch": False,
        },
    }

    if DRY:
        print(f"DRY_RUN: TikTok cross-post not sent ({len(media)} slides).")
        return

    url = f"{BASE}/v2/scheduler/posts"
    params = {"userToken": TOKEN, "userId": USER_ID, "blogId": BLOG_ID}
    headers = {"Content-Type": "application/json", "X-Mc-Auth": TOKEN}
    r = requests.post(url, params=params, headers=headers, json=body, timeout=60)
    if r.status_code >= 400:
        sys.exit(f"Metricool API error {r.status_code}: {r.text}")
    try:
        pid = r.json().get("data", {}).get("id")
    except Exception:
        pid = r.text[:200]
    print(f"TikTok cross-post scheduled for {when:%Y-%m-%d %H:%M} {TZ} (post id {pid}), {len(media)} slides.")

if __name__ == "__main__":
    main()
