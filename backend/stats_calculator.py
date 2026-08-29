import numpy as np
from typing import List, Dict, Any, Optional
from collections import Counter
from backend.price_parser import parse_price, filter_outliers

def calculate_statistics(raw_comments: List[Dict[str, Any]], correct_price: Optional[float] = None) -> Dict[str, Any]:
    parsed_items = []
    
    for c in raw_comments:
        parsed = parse_price(c.get("text", ""))
        has_price = parsed is not None
        item = {
            "comment_id": c.get("comment_id", ""),
            "author": c.get("author", "匿名"),
            "author_avatar": c.get("author_avatar", ""),
            "text": c.get("text", ""),
            "like_count": c.get("like_count", 0),
            "published_time": c.get("published_time", ""),
            "has_price": has_price,
            "price": parsed["price"] if parsed else None,
            "raw_price_str": parsed["raw_price_str"] if parsed else "",
            "is_range": parsed["is_range"] if parsed else False,
            "range_low": parsed.get("range_low") if parsed else None,
            "range_high": parsed.get("range_high") if parsed else None,
            "is_tax_excluded": parsed["is_tax_excluded"] if parsed else False,
            "reason": parsed["reason"] if parsed else "",
            "included": c.get("included", has_price)
        }
        parsed_items.append(item)

    # 統計用（チェックされている有効価格リスト）
    valid_items = [item for item in parsed_items if item["has_price"] and item["included"]]
    valid_prices = [item["price"] for item in valid_items]

    # 基本統計量
    total_comments = len(raw_comments)
    valid_answers_count = len(valid_prices)

    if valid_prices:
        arr = np.array(valid_prices)
        mean_val = float(np.mean(arr))
        median_val = float(np.median(arr))
        min_val = float(np.min(arr))
        max_val = float(np.max(arr))
        std_val = float(np.std(arr))
        q25_val = float(np.percentile(arr, 25))
        q75_val = float(np.percentile(arr, 75))

        # 最頻値（100円単位で丸めて集計）
        rounded_prices = [int(round(p, -2)) for p in valid_prices]
        most_common = Counter(rounded_prices).most_common(3)
        mode_val = float(most_common[0][0]) if most_common else median_val
        mode_count = most_common[0][1] if most_common else 0

        # ヒストグラムの自動ビン分割（500円または1000円刻み）
        span = max_val - min_val
        bin_size = 500 if span <= 5000 else 1000
        if span > 15000:
            bin_size = 2000

        bin_start = int((min_val // bin_size) * bin_size)
        bin_end = int(((max_val // bin_size) + 1) * bin_size)
        
        bins = list(range(bin_start, bin_end + bin_size, bin_size))
        counts, edges = np.histogram(valid_prices, bins=bins)
        
        histogram = []
        for i in range(len(counts)):
            label = f"{edges[i]:,.0f}〜{edges[i+1]:,.0f}円"
            histogram.append({
                "label": label,
                "range_min": float(edges[i]),
                "range_max": float(edges[i+1]),
                "count": int(counts[i]),
                "percentage": round(float(counts[i]) / valid_answers_count * 100, 1)
            })

        # 価格帯カテゴリ分け
        categories = {
            "〜1,999円 (お手頃)": sum(1 for p in valid_prices if p < 2000),
            "2,000〜3,499円 (標準)": sum(1 for p in valid_prices if 2000 <= p < 3500),
            "3,500〜4,999円 (プチ贅沢)": sum(1 for p in valid_prices if 3500 <= p < 5000),
            "5,000円以上 (高級・インバウンド)": sum(1 for p in valid_prices if p >= 5000)
        }
        category_distribution = [
            {"name": k, "count": v, "percentage": round(v / valid_answers_count * 100, 1)}
            for k, v in categories.items() if v > 0
        ]

    else:
        mean_val = median_val = min_val = max_val = std_val = mode_val = q25_val = q75_val = 0.0
        mode_count = 0
        histogram = []
        category_distribution = []

    # 正解発表・ピタリ賞/ニアピン賞判定
    quiz_result = None
    if correct_price is not None and correct_price > 0 and valid_items:
        exact_matches = []
        near_matches = []
        
        # ニアピン判定（±10%以内 または ±300円以内）
        near_margin = max(300, correct_price * 0.10)

        for item in valid_items:
            p = item["price"]
            diff = p - correct_price
            abs_diff = abs(diff)
            
            if abs_diff == 0 or (item["is_range"] and item.get("range_low") <= correct_price <= item.get("range_high")):
                exact_matches.append(item)
            elif abs_diff <= near_margin:
                near_matches.append({**item, "diff": diff, "abs_diff": abs_diff})

        # ニアピンを誤差が小さい順にソート
        near_matches.sort(key=lambda x: x["abs_diff"])

        # ギャップ分析（平均値 vs 正解）
        diff_from_mean = correct_price - mean_val
        gap_percentage = round((diff_from_mean / correct_price) * 100, 1) if correct_price else 0

        # 動画用トーク台本テキスト
        if diff_from_mean < -100:
            talk_gap = f"視聴者の予想平均（{mean_val:,.0f}円）より、実際は {abs(diff_from_mean):,.0f}円 安いという結果になりました！「コスパ最強」ですね！"
        elif diff_from_mean > 100:
            talk_gap = f"視聴者の予想平均（{mean_val:,.0f}円）よりも、実際は {abs(diff_from_mean):,.0f}円 高い高級仕様でした！"
        else:
            talk_gap = f"視聴者の予想平均（{mean_val:,.0f}円）とほぼピタリ一致！視聴者の相場観が完璧でした！"

        script_text = (
            f"【動画台本メモ・結果発表】\n"
            f"正解金額: {correct_price:,.0f}円\n"
            f"総予想回答数: {valid_answers_count}件\n"
            f"視聴者の予想平均: {mean_val:,.0f}円 (中央値: {median_val:,.0f}円)\n"
            f"最頻予想帯: {mode_val:,.0f}円前後 ({mode_count}名)\n"
            f"ピタリ賞: {len(exact_matches)}名\n"
            f"コメント: {talk_gap}"
        )

        quiz_result = {
            "correct_price": correct_price,
            "exact_matches_count": len(exact_matches),
            "exact_matches": exact_matches[:20],
            "near_matches_count": len(near_matches),
            "near_matches": near_matches[:20],
            "diff_from_mean": diff_from_mean,
            "gap_percentage": gap_percentage,
            "talk_gap": talk_gap,
            "script_text": script_text
        }

    return {
        "summary": {
            "total_comments": total_comments,
            "valid_answers_count": valid_answers_count,
            "excluded_count": total_comments - valid_answers_count,
            "mean_price": round(mean_val, 0),
            "median_price": round(median_val, 0),
            "mode_price": round(mode_val, 0),
            "mode_count": mode_count,
            "min_price": round(min_val, 0),
            "max_price": round(max_val, 0),
            "std_dev": round(std_val, 0),
            "q25_price": round(q25_val, 0),
            "q75_price": round(q75_val, 0)
        },
        "histogram": histogram,
        "category_distribution": category_distribution,
        "quiz_result": quiz_result,
        "comments": parsed_items
    }
