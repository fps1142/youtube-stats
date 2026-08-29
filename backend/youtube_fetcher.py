import re
import json
import requests
from typing import Dict, Any, List, Optional

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

class YouTubeCommentFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        })

    def normalize_url(self, url: str) -> Dict[str, str]:
        url = url.strip()
        # コミュニティ投稿
        post_match = re.search(r'(?:youtube\.com/post/|community\?lb=)([\w\-]+)', url)
        if post_match:
            return {"type": "post", "id": post_match.group(1), "url": f"https://www.youtube.com/post/{post_match.group(1)}"}
        
        # Shorts
        shorts_match = re.search(r'youtube\.com/shorts/([\w\-]+)', url)
        if shorts_match:
            return {"type": "video", "id": shorts_match.group(1), "url": f"https://www.youtube.com/watch?v={shorts_match.group(1)}"}

        # 通常動画
        watch_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w\-]+)', url)
        if watch_match:
            return {"type": "video", "id": watch_match.group(1), "url": f"https://www.youtube.com/watch?v={watch_match.group(1)}"}

        return {"type": "unknown", "id": "", "url": url}

    def fetch_post_or_video_data(self, target_url: str, max_comments: int = 500) -> Dict[str, Any]:
        info = self.normalize_url(target_url)
        url = info["url"]

        resp = self.session.get(url)
        if resp.status_code != 200:
            raise ValueError(f"ページを取得できませんでした (HTTP Status: {resp.status_code})")

        html = resp.text

        # ytInitialData 抽出
        match = re.search(r'var ytInitialData\s*=\s*({.+?});</script>', html)
        if not match:
            match = re.search(r'window\["ytInitialData"\]\s*=\s*({.+?});', html)
        
        if not match:
            raise ValueError("YouTubeのデータ初期化オブジェクト(ytInitialData)の抽出に失敗しました。")

        try:
            initial_data = json.loads(match.group(1))
        except Exception as e:
            raise ValueError(f"JSONデータのパースに失敗しました: {e}")

        post_meta = self._extract_metadata(initial_data, info)
        comments = self._fetch_all_comments(initial_data, info, max_comments)

        return {
            "metadata": post_meta,
            "comments": comments,
            "target_type": info["type"],
            "target_id": info["id"]
        }

    def _fix_url_scheme(self, url: str) -> str:
        if not url: return ""
        if url.startswith("//"):
            return "https:" + url
        return url

    def _extract_metadata(self, data: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
        meta = {
            "title": "YouTube 投稿",
            "author": "YouTube チャンネル",
            "author_avatar": "",
            "post_text": "",
            "image_url": "",
            "images": [],
            "published_time": "",
            "total_comments_approx": 0
        }

        try:
            # チャンネル名 / アバター
            meta["author"] = data.get("metadata", {}).get("channelMetadataRenderer", {}).get("title", "YouTube チャンネル")
            avatar_thumbs = data.get("metadata", {}).get("channelMetadataRenderer", {}).get("avatar", {}).get("thumbnails", [])
            if avatar_thumbs:
                meta["author_avatar"] = self._fix_url_scheme(avatar_thumbs[-1].get("url", ""))

            # コミュニティ投稿の場合
            if info["type"] == "post":
                post_renderer = self._find_key(data, "backstagePostRenderer")
                if post_renderer:
                    runs = post_renderer.get("contentText", {}).get("runs", [])
                    meta["post_text"] = "".join([r.get("text", "") for r in runs])
                    meta["title"] = (meta["post_text"][:60] + "...") if len(meta["post_text"]) > 60 else meta["post_text"]
                    
                    # 単一画像または複数画像 (postMultiImageRenderer)
                    attachment = post_renderer.get("backstageAttachment", {})
                    if "postMultiImageRenderer" in attachment:
                        imgs = attachment["postMultiImageRenderer"].get("images", [])
                        for img_item in imgs:
                            t_list = img_item.get("backstageImageRenderer", {}).get("image", {}).get("thumbnails", [])
                            if t_list:
                                meta["images"].append(self._fix_url_scheme(t_list[-1].get("url", "")))
                    elif "backstageImageRenderer" in attachment:
                        t_list = attachment["backstageImageRenderer"].get("image", {}).get("thumbnails", [])
                        if t_list:
                            meta["images"].append(self._fix_url_scheme(t_list[-1].get("url", "")))

                    meta["published_time"] = post_renderer.get("publishedTimeText", {}).get("runs", [{}])[0].get("text", "")

                # マイクロフォーマットからのフォールバック画像取得
                if not meta["images"]:
                    mf_thumbs = data.get("microformat", {}).get("microformatDataRenderer", {}).get("thumbnail", {}).get("thumbnails", [])
                    if mf_thumbs:
                        meta["images"].append(self._fix_url_scheme(mf_thumbs[-1].get("url", "")))

            # 通常動画の場合
            else:
                video_details = data.get("videoDetails", {})
                if video_details:
                    meta["title"] = video_details.get("title", "動画")
                    meta["author"] = video_details.get("author", meta["author"])
                    thumbs = video_details.get("thumbnail", {}).get("thumbnails", [])
                    if thumbs:
                        meta["images"].append(self._fix_url_scheme(thumbs[-1].get("url", "")))
                else:
                    mf = data.get("microformat", {}).get("playerMicroformatRenderer", {})
                    meta["title"] = mf.get("title", {}).get("simpleText", "動画")
                    meta["author"] = mf.get("ownerChannelName", meta["author"])
                    thumbs = mf.get("thumbnail", {}).get("thumbnails", [])
                    if thumbs:
                        meta["images"].append(self._fix_url_scheme(thumbs[-1].get("url", "")))

            if meta["images"]:
                meta["image_url"] = meta["images"][0]

        except Exception as e:
            print("Metadata extract warning:", e)

        return meta

    def _fetch_all_comments(self, initial_data: Dict[str, Any], info: Dict[str, Any], max_comments: int) -> List[Dict[str, Any]]:
        comments = []
        seen_ids = set()
        api_endpoint = "/youtubei/v1/browse" if info["type"] == "post" else "/youtubei/v1/next"
        innertube_url = f"https://www.youtube.com{api_endpoint}?prettyPrint=false"
        client_version = "2.20260828.01.00"

        # 最初のページ読み込み用トークンを取得
        initial_token = self._find_first_continuation_token(initial_data)
        
        # 初期HTML内のコメントも念のため抽出
        initial_comments, _, _ = self._extract_comments_and_tokens(initial_data)
        for c in initial_comments:
            key = c.get("comment_id") or (c.get("author", "") + c.get("text", "")[:20])
            if key not in seen_ids:
                seen_ids.add(key)
                comments.append(c)

        current_token = initial_token
        page = 0
        max_pages = (max_comments // 20) + 15

        while current_token and len(comments) < max_comments and page < max_pages:
            page += 1
            payload = {
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": client_version,
                        "hl": "ja",
                        "gl": "JP"
                    }
                },
                "continuation": current_token
            }
            try:
                r = self.session.post(innertube_url, json=payload, timeout=12)
                if r.status_code != 200:
                    break
                resp_json = r.json()
                new_comments, next_token, reply_tokens = self._extract_comments_and_tokens(resp_json)
                
                for nc in new_comments:
                    key = nc.get("comment_id") or (nc.get("author", "") + nc.get("text", "")[:20])
                    if key not in seen_ids:
                        seen_ids.add(key)
                        comments.append(nc)

                # 返信（リプライ）コメントも取得
                for rtok in reply_tokens:
                    if len(comments) >= max_comments:
                        break
                    r_payload = {
                        "context": {
                            "client": {
                                "clientName": "WEB",
                                "clientVersion": client_version,
                                "hl": "ja",
                                "gl": "JP"
                            }
                        },
                        "continuation": rtok
                    }
                    try:
                        rr = self.session.post(innertube_url, json=r_payload, timeout=10)
                        if rr.status_code == 200:
                            rr_comments, _, _ = self._extract_comments_and_tokens(rr.json())
                            for rc in rr_comments:
                                rkey = rc.get("comment_id") or (rc.get("author", "") + rc.get("text", "")[:20])
                                if rkey not in seen_ids:
                                    seen_ids.add(rkey)
                                    comments.append(rc)
                    except Exception as re_err:
                        print("Reply fetch warning:", re_err)

                current_token = next_token
                if not new_comments and not next_token:
                    break

            except Exception as e:
                print("Comment fetch iteration error:", e)
                break

        return comments

    def _find_key(self, obj: Any, target_key: str) -> Optional[Any]:
        if isinstance(obj, dict):
            if target_key in obj:
                return obj[target_key]
            for k, v in obj.items():
                res = self._find_key(v, target_key)
                if res is not None:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = self._find_key(item, target_key)
                if res is not None:
                    return res
        return None

    def _find_first_continuation_token(self, data: Dict[str, Any]) -> Optional[str]:
        def search_token(obj):
            if isinstance(obj, dict):
                if "continuationItemRenderer" in obj:
                    cir = obj["continuationItemRenderer"]
                    if "continuationEndpoint" in cir and "continuationCommand" in cir["continuationEndpoint"]:
                        return cir["continuationEndpoint"]["continuationCommand"].get("token")
                    if "continuationCommand" in cir:
                        return cir["continuationCommand"].get("token")
                for k, v in obj.items():
                    tok = search_token(v)
                    if tok: return tok
            elif isinstance(obj, list):
                for item in obj:
                    tok = search_token(item)
                    if tok: return tok
            return None
        return search_token(data)

    def _extract_comments_and_tokens(self, data: Dict[str, Any]):
        comments = []
        next_page_token = None
        reply_tokens = []

        # 1. frameworkUpdates / entityBatchUpdate
        mutations = data.get("frameworkUpdates", {}).get("entityBatchUpdate", {}).get("mutations", [])
        for m in mutations:
            payload = m.get("payload", {})
            if "commentEntityPayload" in payload:
                cep = payload["commentEntityPayload"]
                text = cep.get("properties", {}).get("content", {}).get("content", "")
                author = cep.get("author", {}).get("displayName", "匿名")
                author_avatar = cep.get("author", {}).get("avatar", {}).get("image", {}).get("sources", [{}])[-1].get("url", "")
                like_count_str = cep.get("toolbar", {}).get("likeCountNotliked", "0")
                published_time = cep.get("properties", {}).get("publishedTime", "")
                comment_id = cep.get("properties", {}).get("commentId", "")

                try:
                    like_count = int(like_count_str) if str(like_count_str).isdigit() else 0
                except:
                    like_count = 0

                if text:
                    comments.append({
                        "comment_id": comment_id,
                        "author": author,
                        "author_avatar": self._fix_url_scheme(author_avatar),
                        "text": text,
                        "like_count": like_count,
                        "published_time": published_time
                    })

        # 2. commentRenderer 形式および continuationItemRenderer の再帰探索
        def find_comments_and_cirs(obj, in_reply=False):
            nonlocal next_page_token
            if isinstance(obj, dict):
                if "commentRenderer" in obj:
                    cr = obj["commentRenderer"]
                    author = cr.get("authorText", {}).get("simpleText", "")
                    if not author:
                        author = "".join([r.get("text", "") for r in cr.get("authorText", {}).get("runs", [])])
                    text = "".join([r.get("text", "") for r in cr.get("contentText", {}).get("runs", [])])
                    author_avatar = cr.get("authorThumbnail", {}).get("thumbnails", [{}])[-1].get("url", "")
                    like_count = cr.get("likeCount", 0)
                    published_time = cr.get("publishedTimeText", {}).get("runs", [{}])[0].get("text", "")
                    comment_id = cr.get("commentId", "")

                    if text:
                        comments.append({
                            "comment_id": comment_id,
                            "author": author or "匿名",
                            "author_avatar": self._fix_url_scheme(author_avatar),
                            "text": text,
                            "like_count": like_count if isinstance(like_count, int) else 0,
                            "published_time": published_time
                        })

                # continuationItemRenderer のトークン特定（ソートメニュー等の無関係なトークンは除外）
                if "continuationItemRenderer" in obj:
                    cir = obj["continuationItemRenderer"]
                    token = None
                    if "continuationEndpoint" in cir and "continuationCommand" in cir["continuationEndpoint"]:
                        token = cir["continuationEndpoint"]["continuationCommand"].get("token")
                    elif "continuationCommand" in cir:
                        token = cir["continuationCommand"].get("token")
                    
                    if token:
                        if in_reply:
                            reply_tokens.append(token)
                        else:
                            next_page_token = token

                for k, v in obj.items():
                    # sortFilterSubMenuRenderer（ソート順変更）の中のトークンはスクロール用ではないのでスキップ
                    if k in ["sortFilterSubMenuRenderer", "sortMenu"]:
                        continue
                    is_rep = in_reply or ("commentRepliesRenderer" in k) or ("replies" in k)
                    find_comments_and_cirs(v, is_rep)

            elif isinstance(obj, list):
                for item in obj:
                    find_comments_and_cirs(item, in_reply)

        find_comments_and_cirs(data)

        # 重複削除
        seen = set()
        unique_comments = []
        for c in comments:
            key = c.get("comment_id") or (c.get("author", "") + c.get("text", "")[:20])
            if key not in seen:
                seen.add(key)
                unique_comments.append(c)

        return unique_comments, next_page_token, reply_tokens
