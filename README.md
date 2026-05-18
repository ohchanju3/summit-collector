# 정상회담 기사 수집기

전세계 정상회담 관련 뉴스를 자동 수집하여 엑셀로 정리하는 도구.

## 개요

- **데이터 소스**: [GDELT Project](https://www.gdeltproject.org/) — 전세계 뉴스를 15분마다 업데이트하는 무료 공개 DB
- **인물/장소 추출**: spaCy NER (LLM 미사용 → 논문 재현성 확보)
- **출력**: 날짜 · 참가자 · 장소 · 기사 제목 · 링크가 정리된 엑셀 파일

## 설계 배경

| 문제 | 해결 방식 |
|------|----------|
| NYT API는 본문 제공 안 함 | GDELT DOC API 사용 (무료, API 키 불필요) |
| "정상회담 언급" ≠ "정상회담 기사" 노이즈 | 다양한 키워드 조합 + URL 중복 제거 |
| today/yesterday 같은 날짜 모호함 | GDELT가 발행일 기준으로 자동 처리 |
| GPT 의존도 문제 (논문 부적합) | spaCy NER로 인물·장소 추출 |
| Wikipedia는 실시간 업데이트 느림 | GDELT 15분 주기 자동 수집 |

## 폴더 구조

```
summit-collector/
├── config.py              # 날짜 범위, 키워드 설정
├── main.py                # 실행 진입점
├── collector/
│   └── gdelt.py           # GDELT API 기사 수집
├── processor/
│   └── extractor.py       # NER로 인물·장소 추출
├── exporter/
│   └── excel.py           # 엑셀 저장
├── data/                  # 결과 파일 저장 (git 제외)
└── requirements.txt
```

## 설치

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## 실행

```bash
python main.py
```

`data/` 폴더에 `summits_YYYYMMDD_HHMMSS.xlsx` 파일이 생성됩니다.

## 설정 변경

`config.py`에서 수집 기간과 키워드를 수정할 수 있습니다.

```python
START_DATE = "2021-01-01"
END_DATE   = "2026-05-18"

SUMMIT_QUERIES = [
    "bilateral summit leaders",
    "state visit president prime minister",
    ...
]
```

## 출력 엑셀 컬럼

| 컬럼 | 설명 |
|------|------|
| 날짜 | 기사 발행일 (YYYY-MM-DD) |
| 참가자 | NER로 추출한 인물명 |
| 장소 | NER로 추출한 국가·도시명 |
| 기사 제목 | 원문 제목 |
| 언론사 | 기사 도메인 |
| 출처 국가 | 언론사 소재 국가 |
| 링크 | 원문 URL |

## 환경

- Python 3.9+
- 코랩(Colab) 환경에서도 동일하게 실행 가능
