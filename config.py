# 수집 설정
START_DATE = "2026-05-15"
END_DATE = "2026-05-18"  # 오늘 날짜로 업데이트하거나 "today" 사용

# GDELT DOC API 엔드포인트
GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# 정상회담 관련 검색 키워드 (다양하게 잡아야 소규모 국가도 포함됨)
SUMMIT_QUERIES = [
    "bilateral summit leaders",
    "state visit president prime minister",
    "heads of state meeting",
    "presidential summit",
    "summit declaration",
    "leaders summit agreement",
    "bilateral meeting president",
    "summit communique",
]

# 엑셀 저장 경로
OUTPUT_DIR = "data"

# LLM 모델명 (ollama 기준, 변경 시 여기만 수정)
LLM_MODEL = "llama3.1:70b"
