import requests
import time
from datetime import datetime
from typing import List, Dict

from config import GDELT_DOC_API, SUMMIT_QUERIES


def _format_date(date_str: str) -> str:
    """YYYY-MM-DD → YYYYMMDDHHMMSS (GDELT 형식)"""
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d%H%M%S")


def fetch_articles(query: str, start_date: str, end_date: str) -> List[Dict]:
    """
    GDELT DOC API로 기사 목록 수집 
    """
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": 250,
        "format": "json",
        "startdatetime": _format_date(start_date),
        "enddatetime": _format_date(end_date),
        "sort": "DateDesc",
    }

    max_retries = 3  # 최대 3번 재시도
    retry_delay = 10  # 429 발생 시 10초 대기 (이후 2배씩 증가)

    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(GDELT_DOC_API, params=params, timeout=30)
            
            # 429 에러가 나면 예외 처리로 던짐
            res.raise_for_status()
            
            data = res.json()
            return data.get("articles", [])

        except requests.exceptions.HTTPError as http_err:
            # 429 Too Many Requests 에러인 경우 대기 후 재시도
            if res.status_code == 429:
                print(f"  [429 차단 발생] 서버 Too Many Requests 에러. {retry_delay}초 후 다시 시도합니다... ({attempt}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2  # 대기 시간을 점점 늘림 (5초 -> 10초)
                continue
            else:
                print(f"  [HTTP Error {res.status_code}] 쿼리: {query}")
                return []
        except requests.exceptions.Timeout:
            print(f"  [timeout] 쿼리: {query} (재시도 중...)")
            time.sleep(2)
            continue
        except Exception as e:
            print(f"  [error] 쿼리: {query} → {e}")
            return []

    print(f"  [수집 실패] {max_retries}번 재시도했으나 GDELT 서버 차단이 풀리지 않음: {query}")
    return []


def collect_all(start_date: str, end_date: str) -> List[Dict]:
    """
    여러 키워드로 수집 후 URL 기준 중복 제거
    """
    all_articles = []
    seen_urls = set()

    for i, query in enumerate(SUMMIT_QUERIES, 1):
        print(f"  [{i}/{len(SUMMIT_QUERIES)}] 수집 중: '{query}'")
        articles = fetch_articles(query, start_date, end_date)

        added = 0
        for article in articles:
            url = article.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_articles.append(article)
                added += 1

        print(f"         → {added}개 추가 (누적 {len(all_articles)}개)")
        time.sleep(20)

    return all_articles