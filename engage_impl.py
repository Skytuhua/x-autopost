import os, json, datetime
from requests_oauthlib import OAuth1Session
s = OAuth1Session(*[os.environ[n] for n in ["X_API_KEY","X_API_SECRET","X_ACCESS_TOKEN","X_ACCESS_TOKEN_SECRET"]])
now = datetime.datetime.utcnow().isoformat()+"Z"
act, target = os.environ["ACTION"].strip(), os.environ.get("TARGET","").strip().lstrip("@")
ms = json.load(open("mentions_state.json")) if os.path.exists("mentions_state.json") else {}
uid = ms.get("user_id") or s.get("https://api.x.com/2/users/me").json()["data"]["id"]
st = json.load(open("engage_state.json")) if os.path.exists("engage_state.json") else {"users": {}}
out = {"time": now, "action": act, "target": target}
if act == "scan":
    watch = [l.strip().lstrip("@") for l in open("watchlist.txt") if l.strip() and not l.startswith("#")]
    posts = []
    for name in watch:
        u = st["users"].get(name, {})
        if not u.get("id"):
            r = s.get(f"https://api.x.com/2/users/by/username/{name}")
            if not r.ok: out.setdefault("errors", []).append([name, r.status_code, r.text[:200]]); continue
            u["id"] = r.json()["data"]["id"]
        p = {"max_results": 5, "exclude": "replies,retweets", "tweet.fields": "created_at,public_metrics"}
        if u.get("since_id"): p["since_id"] = u["since_id"]
        else: p["start_time"] = (datetime.datetime.utcnow()-datetime.timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = s.get(f"https://api.x.com/2/users/{u['id']}/tweets", params=p)
        if not r.ok: out.setdefault("errors", []).append([name, r.status_code, r.text[:200]])
        else:
            j = r.json()
            for t in j.get("data", []): posts.append({"user": name, **t})
            if j.get("meta", {}).get("newest_id"): u["since_id"] = j["meta"]["newest_id"]
        st["users"][name] = u
    out["status"] = 200; out["posts"] = posts
    json.dump(out, open("watch.json","w"), indent=1)
elif act == "repost":
    r = s.post(f"https://api.x.com/2/users/{uid}/retweets", json={"tweet_id": target})
    out.update(status=r.status_code, body=r.text[:1000])
elif act == "follow":
    r = s.get(f"https://api.x.com/2/users/by/username/{target}")
    if r.ok:
        r = s.post(f"https://api.x.com/2/users/{uid}/following", json={"target_user_id": r.json()["data"]["id"]})
    out.update(status=r.status_code, body=r.text[:1000])
else:
    out.update(status=400, body="unknown action")
json.dump(st, open("engage_state.json","w"), indent=1)
json.dump(out, open("engage_result.json","w"), indent=1)
if act in ("repost","follow"):
    open("engaged.jsonl","a").write(json.dumps({"time": now, "action": act, "target": target, "status": out["status"]})+"\n")
print(json.dumps(out)[:3000])
