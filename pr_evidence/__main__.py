import argparse
import sys
from pathlib import Path

from pr_evidence.classify import classify
from pr_evidence.render import render_comment
from pr_evidence.rules import RulesError, load_rules

CONFIG_ERROR = 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pr_evidence")
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--files", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        rules = load_rules(args.rules.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Arquivo de regras não encontrado: {args.rules}", file=sys.stderr)
        return CONFIG_ERROR
    except RulesError as error:
        print(f"{args.rules}: {error}", file=sys.stderr)
        return CONFIG_ERROR

    files = [line.strip() for line in args.files.read_text(encoding="utf-8").splitlines()]
    comment = render_comment(classify(filter(None, files), rules))
    args.output.write_text(comment, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
