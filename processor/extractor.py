import json
from datetime import datetime
from typing import Dict, List, Optional
import ollama
from newspaper import Article as NewsArticle
from newspaper.article import ArticleException
from config import LLM_MODEL


def _parse_gdelt_date(date_str: str) -> Optional[str]:
    """GDELT 날짜 형식 파싱 (YYYYMMDDHHMMSS → YYYY-MM-DD)"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str[:8], "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return date_str


def _download_body_text(url: str) -> tuple:
    """
    URL에서 기사 본문과 제목을 크롤링.
    본문 크롤링 실패 시에도 제목은 반환 (LLM fallback용).
    반환: (body_text, title)
    """
    if not url:
        return "", ""
    try:
        article = NewsArticle(url, language='en', request_timeout=7)
        article.set_header({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        })
        article.download()
        article.parse()
        return article.text.strip(), article.title.strip()
    except ArticleException:
        return "", ""
    except Exception:
        return "", ""


def _extract_entities(text: str) -> Dict:
    """
    로컬 LLM으로 참가자/장소/내용 요약 추출.
    속도 최적화: 앞 3000자만 전달 (참가자/장소는 도입부, 합의 내용은 중반부까지 커버)
    """
    if not text:
        return {"persons": [], "locations": [], "summary": ""}

    truncated = text[:3000]

    system_instruction = (
        "You are a data analyst specializing in international diplomacy. "
        "From the given news article, extract: "
        "1) persons: full names of heads of state or government (presidents, prime ministers, kings, etc.) "
        "   who actually sat at the meeting table and participated in THIS specific summit. "
        "   Do NOT include: airport reception officials, ambassadors, ministers who only greeted the leader, "
        "   or leaders of other countries mentioned in passing or in a different context. "
        "   Include leaders of small or developing countries — do not filter by country size. "
        "2) locations: ONLY the country and city where THIS specific meeting physically took place. "
        "   Do NOT include previous or future stops on a tour, or places mentioned in background context. "
        "3) summary: one sentence describing what was discussed or agreed upon in THIS meeting. "
        "IMPORTANT: Always output names and locations in English, regardless of the article's language. "
        "If you cannot determine the specific city or country, use an empty array [] for locations. "
        "Do NOT use placeholder values like 'City' or 'Country'. "
        "Output strictly as JSON: "
        "{\"persons\": [\"Name1\", \"Name2\"], \"locations\": [\"City\", \"Country\"], \"summary\": \"...\"}"
    )

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {'role': 'system', 'content': system_instruction},
                {'role': 'user', 'content': f"Text to analyze:\n{truncated}"}
            ],
            options={'temperature': 0.0, 'num_thread': 4},
            format='json'
        )

        content = response['message']['content']
        result = json.loads(content)

        raw_persons = result.get("persons", [])
        raw_locations = result.get("locations", [])
        summary = result.get("summary", "")

        # dict 형태로 반환되는 경우 방어 처리
        cleaned_persons = []
        for p in raw_persons:
            if isinstance(p, dict):
                cleaned_persons.append(p.get("name") or p.get("person") or str(list(p.values())[0]))
            elif isinstance(p, str):
                cleaned_persons.append(p)

        cleaned_locations = []
        for l in raw_locations:
            if isinstance(l, dict):
                cleaned_locations.append(l.get("name") or l.get("location") or str(list(l.values())[0]))
            elif isinstance(l, str):
                cleaned_locations.append(l)

        return {
            "persons": cleaned_persons[:5],
            "locations": cleaned_locations[:4],
            "summary": summary if isinstance(summary, str) else ""
        }
    except Exception as e:
        print(f"   [LLM Error] → {e}")
        return {"persons": [], "locations": [], "summary": ""}


def process_article(article: Dict, index: int, total: int) -> Dict:
    """기사 하나를 크롤링하고 Llama 3로 분석하여 행(row) 데이터 변환"""
    title = article.get("title", "")
    url = article.get("url", "")
    date_raw = article.get("seendate", "")
    domain = article.get("domain", "")
    source_country = article.get("sourcecountry", "")

    print(f"  [{index}/{total}] 분석 중: {url[:60]}...")

    body_text, crawled_title = _download_body_text(url)

    # 크롤링된 제목이 있으면 우선 사용, 없으면 GDELT 제공 제목 사용
    effective_title = crawled_title or title

    if body_text and len(body_text) > 100:
        analysis_text = body_text
        extraction_source = "Body"
    elif effective_title:
        analysis_text = f"Title: {effective_title}\nSource Domain: {domain}"
        extraction_source = "Title Fallback"
    else:
        analysis_text = ""
        extraction_source = "Title Fallback"

    entities = _extract_entities(analysis_text)

    return {
        "date": _parse_gdelt_date(date_raw),
        "participants": ", ".join(entities["persons"]),
        "location": ", ".join(entities["locations"]),
        "summary": entities["summary"],
        "title": title,
        "source": domain,
        "source_country": source_country,
        "url": url,
        "extraction_method": f"{LLM_MODEL} (Body)" if extraction_source.endswith("(Body)") else f"{LLM_MODEL} (Title Fallback)"
    }


def process_all(articles: List[Dict]) -> List[Dict]:
    """전체 기사 배치 처리"""
    results = []
    total = len(articles)
    for idx, article in enumerate(articles, 1):
        row = process_article(article, idx, total)
        results.append(row)
    return results


def dedup_by_event(rows: List[Dict]) -> List[Dict]:
    """
    날짜 + 참가자 조합 기준으로 동일 정상회담 중복 기사 제거.
    참가자가 비어 있는 행은 dedup 대상에서 제외하고 그대로 포함.
    """
    seen_keys = set()
    deduped = []

    for row in rows:
        participants = row.get("participants", "").strip()
        date = row.get("date", "")

        if not participants:
            deduped.append(row)
            continue

        names = frozenset(n.strip() for n in participants.split(",") if n.strip())
        key = (date, names)

        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(row)

    removed = len(rows) - len(deduped)
    print(f"→ 이벤트 단위 중복 제거: {len(rows)}개 → {len(deduped)}개 ({removed}개 제거)")
    return deduped