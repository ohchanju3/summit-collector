import json
import time
from datetime import datetime
from pathlib import Path
from config import START_DATE, END_DATE, OUTPUT_DIR
from collector.gdelt import collect_all
from processor.extractor import process_all, dedup_by_event
from exporter.excel import save_to_excel


def _cache_path() -> Path:
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    return Path(OUTPUT_DIR) / f"articles_cache_{START_DATE}_{END_DATE}.json"


def main():
    start_time = time.time()
    print("=" * 50)
    print("  정상회담 기사 수집기")
    print(f"  기간: {START_DATE} ~ {END_DATE}")
    print(f"  시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 1단계: GDELT에서 기사 메타데이터 수집 (캐시 있으면 건너뜀)
    cache = _cache_path()
    if cache.exists():
        print(f"\n[1단계] 캐시 발견 → GDELT 수집 건너뜀 ({cache.name})")
        with open(cache, "r", encoding="utf-8") as f:
            articles = json.load(f)
        print(f"→ 캐시에서 {len(articles)}개 기사 로드 완료\n")
    else:
        print("\n[1단계] GDELT에서 기사 목록 수집 중...")
        articles = collect_all(START_DATE, END_DATE)
        print(f"→ 총 {len(articles)}개 기사 후보 수집 완료")
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False)
        print(f"→ 캐시 저장 완료 ({cache.name})\n")

    if not articles:
        print("수집된 기사가 없습니다. 검색어 또는 네트워크를 확인하세요.")
        return

    # 2단계: 각 기사 URL 접속 후 본문 긁어서 NER 추출 (시간이 다소 소요됨)
    print("[2단계] URL 접속 및 기사 전문 NER 분석 중...")
    processed = process_all(articles)
    print(f"→ {len(processed)}개 기사 처리 완료\n")

    # 3단계: 이벤트 단위 중복 제거
    print("[3단계] 동일 정상회담 중복 기사 제거 중...")
    processed = dedup_by_event(processed)

    # 4단계: 엑셀 저장
    print("[4단계] 엑셀 파일 저장 중...")
    filepath = save_to_excel(processed, OUTPUT_DIR)

    elapsed = time.time() - start_time
    h, m, s = int(elapsed // 3600), int((elapsed % 3600) // 60), int(elapsed % 60)
    print("\n" + "=" * 50)
    print(f"  완료 - 파일 생성됨")
    print(f"  경로: {filepath}")
    print(f"  종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  소요: {h}시간 {m}분 {s}초")
    print("=" * 50)


if __name__ == "__main__":
    main()