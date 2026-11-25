"""Public errors never include native stderr, paths or credentials."""


class RuntimeFailure(RuntimeError):
    def __init__(self, kind: str, *, cpu_recovery: bool = False, stage: str | None = None,
                 os_code: int | None = None, exit_code: int | None = None):
        self.kind = kind
        self.cpu_recovery = cpu_recovery
        self.stage = stage
        self.os_code = os_code
        self.exit_code = exit_code
        super().__init__(kind)
