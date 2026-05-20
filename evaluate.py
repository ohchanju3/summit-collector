"""
수집 데이터 정확도 평가 스크립트
랜덤 샘플링으로 각 항목(정상회담 여부, 참가자, 장소, 요약)을 직접 검증하고 정확도를 계산합니다.

Usage: python evaluate.py data/summits_filtered_YYYYMMDD_HHMMSS.xlsx
       python evaluate.py data/summits_filtered_YYYYMMDD_HHMMSS.xlsx --sample 50
"""
import sys
import argparse
import webbrowser
import pandas as pd
from datetime import datetime
from pathlib import Path
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import LLM_MODEL


ITEMS = [
    ("is_summit",    "이 기사가 실제 정상회담/공식 외교 회담 기사인가?"),
    ("participants", "참가자 추출이 정확한가? (주요 정상이 맞게 들어있는가)"),
    ("location",     "장소 추출이 정확한가? (회담 국가/도시가 맞는가)"),
    ("summary",      "내용 요약이 적절한가? (회담 핵심 내용을 담고 있는가)"),
]


def translate_to_korean(text: str) -> str:
    """Llama 3로 텍스트를 한국어로 번역"""
    if not text or str(text) == "nan":
        return ""
    try:
        import ollama
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {'role': 'system', 'content': "Translate the following text to Korean. Output only the translation, nothing else."},
                {'role': 'user', 'content': str(text)}
            ],
            options={'temperature': 0.0, 'num_thread': 4}
        )
        return response['message']['content'].strip()
    except Exception:
        return str(text)


def get_input(prompt: str) -> str:
    while True:
        val = input(prompt).strip().lower()
        if val in ("y", "n", "s"):
            return val
        print("  y(정확) / n(오류) / s(건너뜀) 중 하나를 입력하세요.")


def evaluate(df: pd.DataFrame, sample_n: int):
    sample = df.sample(n=min(sample_n, len(df)), random_state=42).reset_index(drop=True)
    total = len(sample)

    scores = {key: {"correct": 0, "wrong": 0, "skip": 0} for key, _ in ITEMS}
    results = []

    print(f"\n총 {total}개 랜덤 샘플 평가 시작")
    print("y = 정확  |  n = 오류  |  s = 건너뜀 (판단 어려울 때)\n")
    print("=" * 60)

    for i, row in sample.iterrows():
        print(f"\n[{i+1}/{total}] 번역 중...")
        title_ko = translate_to_korean(row['기사 제목'])
        summary_ko = translate_to_korean(row['내용 요약'])

        print(f"\n[{i+1}/{total}]")
        print(f"  날짜     : {row['날짜']}")
        print(f"  참가자   : {row['참가자']}")
        print(f"  장소     : {row['장소']}")
        print(f"  내용 요약: {summary_ko}")
        print(f"  기사 제목: {title_ko}")
        print(f"  언론사   : {row['언론사']}  |  추출 방식: {row['추출 방식']}")
        print(f"  링크     : {row['링크']}")

        open_link = input("\n  링크 열기? (Enter=열기 / 건너뜀=아무 키): ").strip()
        if open_link == "":
            webbrowser.open(str(row['링크']))

        row_result = {"index": i}
        for key, question in ITEMS:
            ans = get_input(f"\n  {question} (y/n/s): ")
            scores[key][{"y": "correct", "n": "wrong", "s": "skip"}[ans]] += 1
            row_result[key] = ans

        results.append(row_result)
        print("-" * 60)

        remaining = total - (i + 1)
        if remaining > 0:
            cont = input(f"\n  계속? ({remaining}개 남음) Enter=계속 / q=종료: ").strip()
            if cont.lower() == "q":
                print("\n평가 중단됨.")
                break

    # 결과 출력
    evaluated = i + 1
    print(f"\n{'=' * 60}")
    print(f"  평가 완료: {evaluated}개 샘플")
    print(f"{'=' * 60}\n")

    summary_rows = []
    for key, question in ITEMS:
        s = scores[key]
        valid = s["correct"] + s["wrong"]
        acc = (s["correct"] / valid * 100) if valid > 0 else 0
        print(f"  [{key}] {question}")
        print(f"    정확: {s['correct']}  오류: {s['wrong']}  건너뜀: {s['skip']}  → 정확도: {acc:.1f}%\n")
        summary_rows.append({
            "항목": question,
            "정확": s["correct"],
            "오류": s["wrong"],
            "건너뜀": s["skip"],
            "정확도(%)": round(acc, 1)
        })

    # 결과 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = Path("data") / f"eval_result_{timestamp}.csv"
    pd.DataFrame(summary_rows).to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  결과 저장: {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("excel_file", help="평가할 엑셀 파일 경로")
    parser.add_argument("--sample", type=int, default=100, help="샘플 수 (기본값: 100)")
    args = parser.parse_args()

    df = pd.read_excel(args.excel_file)
    print(f"파일 로드 완료: {len(df)}행")
    evaluate(df, args.sample)


if __name__ == "__main__":
    main()
