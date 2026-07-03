import argparse
import json

from rag_service import evaluate_retrieval


def main():
    parser = argparse.ArgumentParser(description="Evaluate semantic RAG recall.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of retrieved docs per case.")
    parser.add_argument("--eval-file", default="", help="Optional JSON eval case file.")
    args = parser.parse_args()

    result = evaluate_retrieval(
        top_k=args.top_k,
        eval_file=args.eval_file or None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
