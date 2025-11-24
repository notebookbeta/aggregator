import os
import json
import random
from pathlib import Path

import yaml  # pyyaml，requirements.txt 里应该已经有了

CRAWLED_SUBS_PATH = Path("data") / "crawledsubs.yaml"
OUTPUT_CONFIG = Path("generated-process.json")


def extract_urls(obj):
    """尽量通用地从 crawledsubs.yaml 里提取订阅 URL 列表。"""
    urls = []

    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, str):
                urls.append(item.strip())
            elif isinstance(item, dict):
                u = item.get("url") or item.get("sub") or item.get("link")
                if isinstance(u, str):
                    urls.append(u.strip())
    elif isinstance(obj, dict):
        # 常见结构：{"subs": [...]} 或 其它 map 里藏着 list
        subs = obj.get("subs")
        if isinstance(subs, list):
            urls.extend(extract_urls(subs))
        else:
            for v in obj.values():
                urls.extend(extract_urls(v))

    # 去重 + 只要 http 开头的
    deduped = []
    seen = set()
    for u in urls:
        if not u or not u.startswith("http"):
            continue
        if u in seen:
            continue
        seen.add(u)
        deduped.append(u)

    return deduped


def main():
    if not CRAWLED_SUBS_PATH.exists():
        raise SystemExit(f"{CRAWLED_SUBS_PATH} not found, did collect.py run with crawl enabled?")

    with CRAWLED_SUBS_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []

    urls = extract_urls(data)
    if not urls:
        raise SystemExit("No subscription URLs found in crawledsubs.yaml")

    # 最多取 10 条，数量不够就全用
    if len(urls) <= 10:
        selected = urls
    else:
        selected = random.sample(urls, 10)

    print(f"Found {len(urls)} urls, using {len(selected)} of them.")

    # 从环境变量 GIST_LINK 里拿 username/gistid
    gist_link = os.environ.get("GIST_LINK", "").strip()
    if not gist_link:
        raise SystemExit("GIST_LINK env not set (expected 'username/gistid')")

    parts = gist_link.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise SystemExit("GIST_LINK must be in 'username/gistid' format")
    username, gistid = parts

    # 生成 domains（每个订阅一个域）
    domains = []
    for i, url in enumerate(selected, 1):
        domains.append({
            "name": f"auto-{i}",
            "enable": True,
            "domain": "",
            "sub": [url],
            "push_to": ["main"]
        })

    config = {
        "domains": domains,
        "crawl": {
            "enable": False
        },
        "groups": {
            "main": {
                "emoji": True,
                "list": True,
                "targets": {
                    "clash": "main-clash",
                    "singbox": "main-singbox",
                    "v2ray": "main-v2ray"
                },
                "regularize": {
                    "enable": True,
                    "locate": True,
                    "residential": True,
                    "bits": 2
                }
            }
        },
        "storage": {
            "engine": "gist",
            "items": {
                "main-clash": {
                    "username": username,
                    "gistid": gistid,
                    "filename": "clash.yaml"
                },
                "main-singbox": {
                    "username": username,
                    "gistid": gistid,
                    "filename": "singbox.json"
                },
                "main-v2ray": {
                    "username": username,
                    "gistid": gistid,
                    "filename": "v2ray.txt"
                }
            }
        }
    }

    OUTPUT_CONFIG.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Wrote {OUTPUT_CONFIG} with {len(domains)} domains.")


if __name__ == "__main__":
    main()
