# 정상회담 기사 수집 프로젝트 진행 보고

## 1. 개요

전세계 정상회담 관련 뉴스를 자동 수집하여 날짜 · 참가자 · 장소 · 내용 요약을 엑셀로 정리하는 파이프라인 구축.

---

## 2. 실행 환경

### 개발 환경 (로컬)

- MacBook M2
- Python 3.13 / venv
- Ollama (Llama 3, 4.7GB) 로컬 실행

### 수집 환경 (서버)

- OS: Linux
- CPU: 64코어
- GPU: NVIDIA RTX A5000 × 2 (VRAM 24GB each)
- CUDA 12.4
- Python 3 / venv

> GPU 서버에서 실행 시 Llama 3 추론이 MacBook 대비 대폭 빨라짐 (VRAM에 모델 전체 로드)

---

## 3. 데이터 소스

### GDELT Project (https://www.gdeltproject.org/)

- 전세계 뉴스를 15분마다 업데이트하는 무료 공개 이벤트 데이터베이스
- 100개 이상 언어, 65개 이상 국가 언론사 커버
- **GDELT DOC API**를 통해 기사 URL · 제목 · 발행일 · 언론사 메타데이터 수집

### 수집 키워드 (10개) - 추가 가능

| #   | 키워드                               |
| --- | ------------------------------------ |
| 1   | bilateral summit leaders             |
| 2   | state visit president prime minister |
| 3   | heads of state meeting               |
| 4   | presidential summit                  |
| 5   | diplomatic summit                    |
| 6   | leaders summit agreement             |
| 7   | official visit signed agreement      |
| 8   | joint statement leaders              |
| 9   | foreign minister bilateral talks     |
| 10  | summit communique                    |

> 키워드를 다양하게 설정하여 소규모 국가 간 정상회담도 최대한 포함되도록 설계

---

## 4. 파이프라인 구조

```
[1단계] GDELT DOC API
        키워드별 기사 메타데이터(URL, 제목, 날짜, 언론사) 수집
        URL 기준 중복 제거
            ↓
[2단계] newspaper3k 크롤링
        각 기사 URL 접속 → 본문 전문(Full-text) 수집
        크롤링 실패 시 기사 제목으로 자동 대체(Fallback)
            ↓
[3단계] Llama 3 (로컬 오픈소스 LLM)
        본문 앞 3000자 분석
        참가자 · 장소 · 내용 요약 추출
            ↓
[4단계] Excel 저장
        날짜 내림차순 정렬
        한글 헤더 적용
```

---

## 5. 출력 데이터 컬럼

| 컬럼      | 설명                                        |
| --------- | ------------------------------------------- |
| 날짜      | 기사 실제 발행일 (YYYY-MM-DD)               |
| 참가자    | 회담 참가 인물 (최대 5명)                   |
| 장소      | 회담 국가 및 도시 (최대 4곳)                |
| 내용 요약 | 회담에서 논의/합의된 내용 한 문장 요약      |
| 기사 제목 | 언론사 원문 기사 제목                       |
| 언론사    | 기사 도메인 (예: reuters.com)               |
| 출처 국가 | GDELT가 분류한 언론사 소재국                |
| 링크      | 원문 기사 URL                               |
| 추출 방식 | `Llama3 (Body)` / `Llama3 (Title Fallback)` |

---

## 6. 정확도 및 신뢰성

### 장점

- **재현성 확보**: GPT 등 상업용 API 미사용, 오픈소스 Llama 3 고정 모델 사용
- **맥락 기반 추출**: rule-based NER(spaCy) 대비 실제 참가자 판별 정확도 높음
- **날짜 신뢰도**: "today/yesterday" 등 상대 날짜 표기 문제 없음 — GDELT가 기사 발행 타임스탬프로 자동 처리
- **추출 추적 가능**: `추출 방식` 컬럼으로 본문 분석/제목 분석 여부 확인 가능

### 한계 및 유의사항

- **미디어 보도 편향**: GDELT는 실제 정상회담 전수가 아닌 **언론에 보도된** 정상회담을 수집함
  - 소규모 국가 간 정상회담은 국제 언론 보도가 적어 누락될 수 있음
  - 논문 기술 시 "media-reported summits" 프레임으로 명시 권장
- **크롤링 차단**: 일부 언론사는 봇 차단 정책으로 본문 수집 실패 → 제목 기반 Fallback 처리
- **Llama 3 오류**: 드물게 JSON 파싱 실패 시 해당 기사 참가자/장소 공란 처리됨

---

## 7. 향후 논의 필요 사항

- [ ] 수집 기간 범위 확정 (몇 년치 데이터가 필요한지)
- [ ] GDELT 기반 데이터로 연구 목적 충족 가능한지 확인
  - 충족 불가 시: 특정 지역/국가 외교부 공식 사이트 추가 수집 검토
- [ ] 소규모 국가 커버리지 보완 방안 협의
