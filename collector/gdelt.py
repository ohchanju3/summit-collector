import os
from datetime import datetime, timedelta
from typing import List, Dict

from google.cloud import bigquery
from config import BQ_PROJECT, BQ_KEY_PATH

# 서비스 계정 키 경로 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = BQ_KEY_PATH


def _to_bq_int(date_str: str) -> int:
    """YYYY-MM-DD → YYYYMMDD000000 정수 (GKG DATE 필드 형식)"""
    return int(datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d000000"))


def collect_all(start_date: str, end_date: str) -> List[Dict]:
    """
    GDELT BigQuery (gdelt-bq.gdeltv2.gkg) 에서 정상회담 관련 기사 수집.
    API 호출 없이 SQL 한 번으로 완료 → 429 없음.
    """
    client = bigquery.Client(project=BQ_PROJECT)

    start_int = _to_bq_int(start_date)
    end_int = int(
        (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d000000")
    )

    # 정상회담 관련 GDELT GKG 테마 필터
    # Themes 컬럼은 세미콜론(;) 구분 문자열
    theme_filter = " OR ".join([
        "Themes LIKE '%GOV_LEADER%'",
        "Themes LIKE '%LEADER%'",
        "Themes LIKE '%BILATERAL%'",
        "Themes LIKE '%WB_587%'",       # International Meetings (World Bank taxonomy)
        "Themes LIKE '%WB_131%'",       # Peace Negotiations
        "Themes LIKE '%ECON_TRADE_DEAL%'",
        "Themes LIKE '%SUMMIT%'",
    ])

    query = f"""
    SELECT DISTINCT
        DocumentIdentifier  AS url,
        CAST(DATE AS STRING) AS seendate,
        SourceCommonName    AS domain
    FROM `gdelt-bq.gdeltv2.gkg`
    WHERE DATE >= {start_int}
      AND DATE <  {end_int}
      AND ({theme_filter})
      AND DocumentIdentifier IS NOT NULL
      AND DocumentIdentifier != ''
    LIMIT 5000
    """

    print(f"  BigQuery 쿼리 실행 중 ({start_date} ~ {end_date})...")
    rows = list(client.query(query).result())
    print(f"  → 원본 {len(rows)}행 수신")

    # URL 기준 중복 제거 + 필드 정규화
    seen_urls: set = set()
    articles: List[Dict] = []
    for row in rows:
        url = row.url or ""
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        articles.append({
            "url":           url,
            "seendate":      row.seendate or "",
            "domain":        row.domain or "",
            "sourcecountry": "",   # GKG 테이블에 소재국 컬럼 없음
            "title":         "",   # GKG 테이블에 제목 없음 — newspaper3k 크롤링으로 대체
        })

    print(f"  → 중복 제거 후 {len(articles)}개 기사")
    return articles
