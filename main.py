from config import START_DATE, END_DATE, OUTPUT_DIR
from collector.gdelt import collect_all
from processor.extractor import process_all
from exporter.excel import save_to_excel


def main():
    print("=" * 50)
    print("  정상회담 기사 수집기")
    print(f"  기간: {START_DATE} ~ {END_DATE}")
    print("=" * 50)

    # 1단계: GDELT에서 기사 수집 (실시간, 무료)
    print("\n[1단계] GDELT에서 기사 수집 중...")
    articles = collect_all(START_DATE, END_DATE)
    print(f"→ 총 {len(articles)}개 기사 수집 완료\n")

    if not articles:
        print("수집된 기사가 없습니다. 네트워크 연결을 확인하세요.")
        return

    # 2단계: NER로 인물/장소 추출
    print("[2단계] NER로 인물·장소 추출 중...")
    processed = process_all(articles)
    print(f"→ {len(processed)}개 처리 완료\n")

    # 3단계: 엑셀 저장
    print("[3단계] 엑셀 파일 저장 중...")
    filepath = save_to_excel(processed, OUTPUT_DIR)

    print("\n" + "=" * 50)
    print(f"  완료! → {filepath}")
    print("=" * 50)


if __name__ == "__main__":
    main()
