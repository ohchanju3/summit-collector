import spacy
from datetime import datetime
from typing import Dict, List, Optional

# spaCy NER 모델 로드 (LLM 미사용 - 논문 재현성 확보)
# 첫 실행 시: python -m spacy download en_core_web_sm
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise OSError(
        "spaCy 모델이 없습니다.\n"
        "다음 명령어로 설치하세요: python -m spacy download en_core_web_sm"
    )


def _parse_gdelt_date(date_str: str) -> Optional[str]:
    """
    GDELT 날짜 형식 파싱
    입력 예시: '20240115T120000Z'
    출력 예시: '2024-01-15'
    - today/yesterday 같은 상대 표현 문제를 GDELT가 발행일 기준으로 자동 처리
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str[:8], "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return date_str


def _extract_entities(text: str) -> Dict:
    """
    spaCy NER로 인물/장소/국가 추출
    - PERSON: 정상 이름
    - GPE (Geo-Political Entity): 국가, 도시
    - LOC: 지역명
    """
    doc = nlp(text)

    persons = list(dict.fromkeys(  # 순서 유지하면서 중복 제거
        ent.text for ent in doc.ents if ent.label_ == "PERSON"
    ))
    locations = list(dict.fromkeys(
        ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC")
    ))

    return {
        "persons": persons[:4],    # 최대 4명
        "locations": locations[:3],  # 최대 3곳
    }


def process_article(article: Dict) -> Dict:
    """기사 하나를 구조화된 행(row)으로 변환"""
    title = article.get("title", "")
    url = article.get("url", "")
    date_raw = article.get("seendate", "")
    domain = article.get("domain", "")
    source_country = article.get("sourcecountry", "")

    entities = _extract_entities(title)

    return {
        "date": _parse_gdelt_date(date_raw),
        "participants": ", ".join(entities["persons"]),
        "location": ", ".join(entities["locations"]),
        "title": title,
        "source": domain,
        "source_country": source_country,
        "url": url,
    }


def process_all(articles: List[Dict]) -> List[Dict]:
    """전체 기사 처리"""
    results = []
    for article in articles:
        row = process_article(article)
        results.append(row)
    return results
