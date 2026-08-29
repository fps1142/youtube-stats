import re
import numpy as np
from typing import Dict, Any, Optional, List

def normalize_text(text: str) -> str:
    text = text.translate(str.maketrans(
        '０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ，．￥',
        '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz,.¥'
    ))
    return text

def _parse_single_segment(clean_text: str, is_tax_excluded: bool) -> Optional[Dict[str, Any]]:
    # 1. 範囲指定 (例: 3500〜4000円, 3000~4000, 3000-4000円, 3000円から4000円)
    range_match = re.search(r'(\d+)\s*(?:円)?\s*(?:[〜~～\-]|から)\s*(\d+)\s*(?:円|えん)?', clean_text)
    if range_match:
        low = int(range_match.group(1))
        high = int(range_match.group(2))
        if 100 <= low < high <= 10000000:
            avg_price = (low + high) / 2
            reason = clean_text.replace(range_match.group(0), '').strip(' :：,、。!?！？\n\t')
            return {
                'price': avg_price,
                'raw_price_str': range_match.group(0),
                'is_range': True,
                'range_low': low,
                'range_high': high,
                'is_tax_excluded': is_tax_excluded,
                'confidence': 0.95,
                'reason': reason if len(reason) > 2 else ''
            }

    # 2. 〇万〇千〇円 (例: 1万2000円, 1.5万, 1万5千円)
    man_match = re.search(r'(\d+(?:\.\d+)?)\s*万\s*(?:(\d+)\s*千)?(?:\s*(\d+))?\s*(?:円|えん)?', clean_text)
    if man_match:
        val = float(man_match.group(1)) * 10000
        if man_match.group(2):
            val += float(man_match.group(2)) * 1000
        if man_match.group(3):
            val += float(man_match.group(3))
        if 100 <= val <= 10000000:
            reason = clean_text.replace(man_match.group(0), '').strip(' :：,、。!?！？\n\t')
            return {
                'price': int(val),
                'raw_price_str': man_match.group(0),
                'is_range': False,
                'is_tax_excluded': is_tax_excluded,
                'confidence': 0.95,
                'reason': reason if len(reason) > 2 else ''
            }

    # 3. 〇千〇百 (例: 3千500円, 3千5百円, 3千円)
    sen_match = re.search(r'(\d+)\s*千\s*(?:(\d+)\s*百|\s*(\d+))?\s*(?:円|えん)?', clean_text)
    if sen_match:
        val = int(sen_match.group(1)) * 1000
        if sen_match.group(2):
            val += int(sen_match.group(2)) * 100
        elif sen_match.group(3):
            val += int(sen_match.group(3))
        if 100 <= val <= 10000000:
            reason = clean_text.replace(sen_match.group(0), '').strip(' :：,、。!?！？\n\t')
            return {
                'price': int(val),
                'raw_price_str': sen_match.group(0),
                'is_range': False,
                'is_tax_excluded': is_tax_excluded,
                'confidence': 0.95,
                'reason': reason if len(reason) > 2 else ''
            }

    # 4. k表記 (例: 3.5k, 4k, 3.8K)
    k_match = re.search(r'(\d+(?:\.\d+)?)\s*[kK]\b', clean_text)
    if k_match:
        val = float(k_match.group(1)) * 1000
        if 100 <= val <= 10000000:
            reason = clean_text.replace(k_match.group(0), '').strip(' :：,、。!?！？\n\t')
            return {
                'price': int(val),
                'raw_price_str': k_match.group(0),
                'is_range': False,
                'is_tax_excluded': is_tax_excluded,
                'confidence': 0.90,
                'reason': reason if len(reason) > 2 else ''
            }

    # 5. 通常の「数字 + 円/えん/yen/¥」 (例: 3500円, ¥4,000, 3980えん)
    yen_match = re.search(r'(?:[¥￥]\s*(\d+)|(\d+)\s*(?:円|えん|yen))', clean_text, re.IGNORECASE)
    if yen_match:
        val = int(yen_match.group(1) or yen_match.group(2))
        if 50 <= val <= 50000000:
            reason = clean_text.replace(yen_match.group(0), '').strip(' :：,、。!?！？\n\t')
            return {
                'price': val,
                'raw_price_str': yen_match.group(0),
                'is_range': False,
                'is_tax_excluded': is_tax_excluded,
                'confidence': 0.98,
                'reason': reason if len(reason) > 2 else ''
            }

    # 6. 単独の3〜6桁の数値 (例: 「3800くらい」「4000かな」「2500」)
    num_match = re.search(r'(?<!\d)(\d{3,6})(?!\d)', clean_text)
    if num_match:
        val = int(num_match.group(1))
        if val not in [2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]:
            reason = clean_text.replace(num_match.group(0), '').strip(' :：,、。!?！？\n\t')
            return {
                'price': val,
                'raw_price_str': num_match.group(0),
                'is_range': False,
                'is_tax_excluded': is_tax_excluded,
                'confidence': 0.80,
                'reason': reason if len(reason) > 2 else ''
            }

    return None

def parse_price(raw_text: str) -> Optional[Dict[str, Any]]:
    if not raw_text:
        return None
    
    text = normalize_text(raw_text)
    clean_text = text.replace(',', '')

    is_tax_excluded = bool(re.search(r'(?:税別|税抜|税抜き|\+\s*税)', clean_text))

    # 範囲指定（例: 2500〜3500円）が含まれている場合は範囲を最優先
    range_match = re.search(r'(\d+)\s*(?:円)?\s*(?:[〜~～\-]|から)\s*(\d+)\s*(?:円|えん)?', clean_text)
    if range_match:
        return _parse_single_segment(clean_text, is_tax_excluded)

    # 願望・希望 vs 予想の逆接構文の判定
    # 例: 「2500円位で食べたいけど3500とかいっちゃうのかなぁ」「希望は2000円だけど3800円しそう」
    wish_pattern = r'(?:食べたい|買いたい|行きたい|希望|願望|ならいい|なら嬉しい|であってほしい|理想|であれ)'
    adversative_pattern = r'(?:けど|けれど|だが|だけど|が|でも|ただし|しかし)'
    
    wish_adv_split = re.split(rf'{wish_pattern}[^、。！？\n]*?{adversative_pattern}', clean_text, maxsplit=1)
    if len(wish_adv_split) > 1:
        # 逆接の後ろ（結論・本命の予想）側から金額を抽出
        after_text = wish_adv_split[1]
        res_after = _parse_single_segment(after_text, is_tax_excluded)
        if res_after:
            return res_after

    # 「予想は〇〇円」という明示キーワードがあれば優先
    guess_keyword_match = re.search(r'(?:予想|本命|実際|相場)[は:：\s]*([^、。！？\n]+)', clean_text)
    if guess_keyword_match:
        res_guess = _parse_single_segment(guess_keyword_match.group(1), is_tax_excluded)
        if res_guess:
            return res_guess

    # 通常パース
    return _parse_single_segment(clean_text, is_tax_excluded)

def filter_outliers(prices: List[float], min_price: float = 100, max_price: float = 100000) -> List[bool]:
    if len(prices) < 4:
        return [min_price <= p <= max_price for p in prices]

    arr = np.array(prices)
    q25 = np.percentile(arr, 25)
    q75 = np.percentile(arr, 75)
    iqr = q75 - q25

    lower_bound = max(min_price, q25 - 2.5 * iqr)
    upper_bound = min(max_price, q75 + 2.5 * iqr)

    return [(lower_bound <= p <= upper_bound) for p in prices]

