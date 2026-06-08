#!/usr/bin/env python3
"""
Publish the rendered carousel to @vascoyaps via the Instagram Graph API.

Env:
  IG_USER_ID       Instagram Business Account ID (e.g. 17841446352490605)
  IG_ACCESS_TOKEN  Long-lived Page access token (does not expire)
  IMAGE_BASE_URL   Public base URL where today's slides are hosted,
                   e.g. https://raw.githubusercontent.com/<owner>/<repo>/<sha>/images/2026-06-08
  GRAPH_VERSION    optional, default v21.0
  DRY_RUN          optional, "1" to skip the final publish (build containers only)
"""
import os, sys, json, glob, time, requests

HERE = os.path.dirname(os.path.abspath(__file__))
VER = os.environ.get("GRAPH_VERSION", "v21.0")
BASE = f"https://graph.facebook.com/{VER}"
IG_USER = os.environ["IG_USER_ID"]
TOKEN = os.environ["IG_ACCESS_TOKEN"]
IMG_BASE = os.environ["IMAGE_BASE_URL"].rstrip("/")
DRY = os.environ.get("DRY_RUN") == "1"

def api(method, path, **params):
    params["access_token"] = TOKEN
    url = f"{BASE}/{path}"
    r = requests.request(method, url, params=params, timeout=60)
    try:
        data = r.json()
    except Exception:
        r.raise_for_status(); raise
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"{method} {path} failed: {json.dumps(data)}")
    return data

def main():
    out_dir = os.path.join(HERE, "output")
    slides = sorted(glob.glob(os.path.join(out_dir, "slide_*.png")))
    if not slides:
        sys.exit("No slides found in output/. Run build_carousel.py first.")
    caption = json.load(open(os.path.join(HERE, "content.json"))).get("caption", "")

    # 1) one child container per image
    children = []
    for s in slides:
        name = os.path.basename(s)
        url = f"{IMG_BASE}/{name}"
        print("Creating child for", url)
        child = api("POST", f"{IG_USER}/media", image_url=url, is_carousel_item="true")
        children.append(child["id"])

    # 2) the carousel container
    container = api("POST", f"{IG_USER}/media",
                    media_type="CAROUSEL",
                    children=",".join(children),
                    caption=caption)
    cid = container["id"]

    # wait until the container is FINISHED
    for _ in range(20):
        st = api("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            raise RuntimeError("Container processing error")
        time.sleep(3)

    if DRY:
        print("DRY_RUN: built container", cid, "- not publishing.")
        return

    # 3) publish
    pub = api("POST", f"{IG_USER}/media_publish", creation_id=cid)
    print("Published! Media id:", pub.get("id"))

if __name__ == "__main__":
    main()
