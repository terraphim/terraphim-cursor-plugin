"""Harmless public validator; no model or network operation."""
import argparse
import hashlib
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--check", action="store_true", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).with_name("brief.md")
    data = source.read_bytes()
    text = data.decode("utf-8")
    if "Risk" not in text or "Decision" not in text:
        parser.error("brief requires Risk and Decision")
    result = {"source": source.name, "sha256": hashlib.sha256(data).hexdigest(),
              "bytes": len(data), "riskOccurrences": text.count("Risk"),
              "decisionOccurrences": text.count("Decision")}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")

if __name__ == "__main__":
    main()
