"""Shared signal for pipeline stages that are laid out but not built yet."""


class StageNotReady(NotImplementedError):
    """Raised when a stage is called before its implementation exists."""

    def __init__(self, stage: str) -> None:
        self.stage = stage
        super().__init__(f"{stage} is not implemented")


def not_ready(stage: str) -> None:
    raise StageNotReady(stage)
