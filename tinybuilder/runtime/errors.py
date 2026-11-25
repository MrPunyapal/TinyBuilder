"""Public errors never include native stderr, paths or credentials."""


class RuntimeFailure(RuntimeError):
    def __init__(self, kind: str, *, cpu_recovery: bool = False):
        self.kind = kind
        self.cpu_recovery = cpu_recovery
        super().__init__(kind)
