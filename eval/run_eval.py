"""Leave-one-session-out metrics.

Sessions used to train or to set thresholds are never the sessions that are scored.
"""


def main() -> None:
    raise SystemExit(
        "Evaluation runs after labeled sessions exist. "
        "There is nothing to score in the scaffold."
    )


if __name__ == "__main__":
    main()
