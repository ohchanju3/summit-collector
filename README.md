# 정상회담 기사 수집

전세계 정상회담 관련 뉴스를 자동 수집하고, 기사 본문을 크롤링하여 인물과 장소를 정밀 추출한 뒤 엑셀로 정리하는 논문 연구용 데이터 수집 도구입니다.

## 개요

- **데이터 소스**: [GDELT Project](https://www.gdeltproject.org/) — 전세계 뉴스를 15분마다 업데이트하는 무료 공개 메타데이터 DB
- **본문 크롤링**: GDELT가 제공하는 URL 원문에 직접 접속하여 기사 전문(Body Text) 자동 수집 (`newspaper3k` 활용)
- **인물/장소 추출**: Llama 3 (Meta, 2024) — [Ollama](https://ollama.com/)를 통해 **로컬에서 실행되는 오픈소스 모델** → 외부 API 의존 없이 맥락 기반 정밀 추출 및 **논문 재현성 확보**
- **출력**: 날짜 · 참가자 · 장소 · 내용 요약 · 기사 제목 · 언론사 · 원문 링크 · 추출 방식이 정리된 엑셀 파일

## 설계 배경

| 문제 상황                              | 해결 방식                                                                                | 효과                                                        |
| :------------------------------------- | :--------------------------------------------------------------------------------------- | :---------------------------------------------------------- |
| NYT API 등은 기사 본문을 제공 안 함    | GDELT BigQuery(GKG 테이블)에서 URL 수집 후 **원문 직접 크롤링**                          | 데이터의 완전성(Completeness) 확보                          |
| 기사 제목만 분석 시 정보 누락 발생     | 기사 전문(Full-text)을 기반으로 NER 모델 가동                                            | 인물/장소 추출 정확도 획기적 상승                           |
| "정상회담 언급" ≠ "실제 정상회담 기사" | GDELT GKG 테마 필터(`LEADER` + `POL_HOSTVISIT`/`GOV_INTERGOVERNMENTAL`) + LLM 2차 필터링 | 데이터셋 내 노이즈 최소화                                   |
| 오늘/어제 등 날짜 표기의 모호함        | GDELT가 기사 발행일 기준으로 타임스탬프 자동 처리                                        | 시계열 데이터의 신뢰도 확보                                 |
| GPT 등 상업용 LLM 의존 (논문 부적합)   | **오픈소스 Llama 3**를 로컬 실행 (Ollama)                                                | 외부 API 없이 맥락 기반 추출 + 재현성(Reproducibility) 증명 |

## 폴더 구조

```
summit-collector/
├── config.py              # 수집 기간(START_DATE/END_DATE), BigQuery 설정, LLM 모델명
├── main.py                # 실행 진입점 (파이프라인 제어, filter.py 자동 호출)
├── filter.py              # LLM 기반 정상회담 여부 2차 필터링 (main.py에서 자동 실행)
├── evaluate.py            # 랜덤 샘플 수동 정확도 평가 도구
├── collector/
│   └── gdelt.py           # GDELT BigQuery(GKG 테이블) 기사 메타데이터 수집
├── processor/
│   └── extractor.py       # 원문 크롤링 및 로컬 Llama 3 기반 정보 추출 (핵심 로직)
├── exporter/
│   └── excel.py           # pandas 활용 엑셀 저장
├── data/                  # 결과 엑셀 파일 저장 폴더 (.gitignore 등록)
└── requirements.txt       # 의존성 패키지 목록
```

## 설치

### 1. 가상환경 생성 및 활성화

```bash
python3 -m venv venv
source venv/bin/activate
# 프롬프트가 (venv) 로 바뀌면 성공
```

> 다음번에 프로젝트 열 때도 `source venv/bin/activate` 먼저 실행해야 합니다.

### 2. Ollama 설치 및 모델 준비

[Ollama 공식 사이트](https://ollama.com/)에서 설치 후 Llama 3 모델을 받아둡니다.

```bash
ollama pull llama3.1:70b
```

> 이후 실행 시 ollama가 백그라운드에서 자동으로 켜져 있으면 됩니다. (`ollama serve` 또는 앱 실행)

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

💡 Python 3.10 이상 환경(예: 3.13)에서 실행 시 주의사항
newspaper3k 라이브러리 내부 호환성 문제로 lxml.html.clean ImportError가 발생할 수 있습니다. 에러 발생 시 가상환경이 켜진 상태에서 아래 명령어를 추가로 실행해 주세요.

```bash
pip install lxml_html_clean "lxml[html-clean]"
```

## 실행

### 방법 ①: 일반 실행 (소량의 테스트 데이터 수집 시)

가상환경이 활성화된 상태에서 메인 스크립트를 실행합니다.

```bash
# 가상환경이 활성화된 상태에서
python main.py
```

### 방법 ②: 백그라운드 대량 실행 (몇 개월~5년 치 배치 수집 시)

기사 본문을 일일이 크롤링하므로 대용량 수집 시 시간이 오래 걸립니다. 터미널을 종료하거나 컴퓨터를 닫아도 안정적으로 돌아가도록 nohup을 사용합니다.

```bash
source venv/bin/activate
nohup python -u main.py > output.log 2>&1 &
tail -f output.log  # 실시간 로그 확인
```

`data/` 폴더에 `summits_YYYYMMDD_HHMMSS.xlsx` 파일이 생성됩니다.

### 방법 ③: 노이즈 필터링 (자동 실행)

main.py 실행 완료 시 filter.py가 자동으로 실행되어 `data/summits_filtered_YYYYMMDD_HHMMSS.xlsx`를 생성합니다.

수동으로 재실행이 필요한 경우에만 아래 명령어를 사용하세요.

```bash
python filter.py data/summits_YYYYMMDD_HHMMSS.xlsx
```

## 설정 변경 (`config.py`)

수집 기간과 BigQuery 프로젝트 정보를 설정합니다.

```python
START_DATE = "2026-05-01"   # 수집 시작일 (YYYY-MM-DD)
END_DATE   = "2026-05-18"   # 수집 종료일 (YYYY-MM-DD)

BQ_PROJECT  = "summit-collector"               # Google Cloud 프로젝트 ID
BQ_KEY_PATH = "summit-collector-xxxx.json"     # 서비스 계정 키 파일 경로

LLM_MODEL = "llama3.1:70b"  # Ollama 모델명
```

> 기사 필터링은 GDELT GKG 테마(`LEADER` AND (`POL_HOSTVISIT` OR `GOV_INTERGOVERNMENTAL`))로 수행되며, `collector/gdelt.py`에서 수정할 수 있습니다.

## 출력 엑셀 컬럼

| 컬럼명    | 데이터 타입         | 설명                                                                                  |
| --------- | ------------------- | ------------------------------------------------------------------------------------- |
| 날짜      | `Date (YYYY-MM-DD)` | 기사 실제 발행일 (상대 날짜 노이즈 제거됨)                                            |
| 참가자    | `Text`              | Llama 3가 본문에서 추출한 회담 참가 인물 (최대 5명, `,` 분리)                         |
| 장소      | `Text`              | Llama 3가 본문에서 추출한 회담 국가 및 도시명 (최대 4곳, `,` 분리)                    |
| 내용 요약 | `Text`              | 회담에서 논의/합의된 내용 한 문장 요약                                                |
| 기사 제목 | `Text`              | 언론사 원문 기사 제목                                                                 |
| 언론사    | `Text`              | 기사 도메인 (예: `reuters.com`, `nytimes.com`)                                        |
| 출처 국가 | `Text`              | GDELT가 분류한 해당 언론사 소재국 코드                                                |
| 링크      | `Text (URL)`        | 원문 검증 및 추적을 위한 기사 고유 URL                                                |
| 추출 방식 | `Text`              | `Llama3 (Body)`: 본문 전체 분석 / `Llama3 (Title Fallback)`: 크롤링 실패 시 제목 분석 |

## 환경

- Python 3.9+
- Ollama (로컬 Llama 3 실행 필수)
- 코랩(Colab) 환경에서는 Ollama 미지원 — 로컬 맥/리눅스 환경 권장
