"""Module entry point allowing ``python -m mac_organizer``."""

from . import main


def run() -> None:
    """Invoke the organizer CLI."""
    main()


if __name__ == "__main__":  # pragma: no cover - exercised via tests
    run()
