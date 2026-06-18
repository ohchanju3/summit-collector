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

    # 정상회담 관련 GDELT GKG 테마 필터 (Category List 검증 완료)
    # 조건: LEADER(정치 지도자 필수) AND 외교적 맥락 테마 중 하나 이상
    # → 정치 지도자가 등장하면서 외교적 맥락이 있는 기사만 수집
    diplomatic_context = " OR ".join([
        "Themes LIKE '%POL_HOSTVISIT%'",          # 국빈 방문, 정상 방문 (가장 직접적)
        "Themes LIKE '%GOV_INTERGOVERNMENTAL%'",  # 정부 간 공식 활동
    ])
    theme_filter = f"Themes LIKE '%LEADER%' AND ({diplomatic_context})"

    query = f"""
    SELECT
        DocumentIdentifier          AS url,
        MIN(CAST(DATE AS STRING))   AS seendate,
        MIN(SourceCommonName)       AS domain,
        ANY_VALUE(V2Persons)        AS v2persons,
        ANY_VALUE(V2Locations)      AS v2locations
    FROM `gdelt-bq.gdeltv2.gkg`
    WHERE DATE >= {start_int}
      AND DATE <  {end_int}
      AND ({theme_filter})
      AND DocumentIdentifier IS NOT NULL
      AND DocumentIdentifier != ''
    GROUP BY DocumentIdentifier
    LIMIT 2000
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
            "sourcecountry": "",            # GKG 테이블에 소재국 컬럼 없음
            "title":         "",            # GKG 테이블에 제목 없음 — newspaper3k 크롤링으로 대체
            "v2persons":     row.v2persons or "",
            "v2locations":   row.v2locations or "",
        })

    print(f"  → 중복 제거 후 {len(articles)}개 기사")
    return articles
