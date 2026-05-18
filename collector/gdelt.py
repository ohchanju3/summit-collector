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
    - API 키 불필요, 완전 무료
    - 15분마다 업데이트되므로 실시간성 보장
    - maxrecords: 1회 최대 250건
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

    try:
        res = requests.get(GDELT_DOC_API, params=params, timeout=30)
        res.raise_for_status()
        data = res.json()
        return data.get("articles", [])
    except requests.exceptions.Timeout:
        print(f"  [timeout] 쿼리: {query}")
        return []
    except Exception as e:
        print(f"  [error] 쿼리: {query} → {e}")
        return []


def collect_all(start_date: str, end_date: str) -> List[Dict]:
    """
    여러 키워드로 수집 후 URL 기준 중복 제거
    - 소규모 국가 정상회담도 포함하기 위해 다양한 쿼리 사용
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
        time.sleep(1)  # API 과부하 방지

    return all_articles
