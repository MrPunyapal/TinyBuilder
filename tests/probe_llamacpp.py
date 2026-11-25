"""Opt-in manual probe; no downloads, raw responses or credential output."""
import getpass
from pathlib import Path
import secrets
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tinybuilder.agent import Agent
from tinybuilder.model import ChatModel, ManagedConnection, ModelError
from tinybuilder.protocol import ProtocolError, parse_strict_action, strict_response_format
from tinybuilder.tools import LocalTools


def main():
    model = ChatModel.from_managed(ManagedConnection(
        input("Loopback base URL: "), input("Model alias: "), getpass.getpass("Session key: ")))
    try:
        response = model.complete([{"role": "user", "content":
            'Return exactly {"type":"final","content":"ready"}'}], [], strict_response_format())
        print("constrained HTTP/message accepted")
        if response.get("tool_calls"):
            raise ProtocolError("mixed_native_action")
        action = parse_strict_action(response.get("content"))
        print("valid strict action: True")
        print("expected final:", action["type"] == "final" and action["content"] == "ready")
    except (ModelError, ProtocolError) as exc:
        print("constrained probe failure:", exc.kind if isinstance(exc, ModelError) else exc.code)
    for protocol in ("native", "strict-json"):
        events = []
        fact = secrets.token_hex(12)
        exact_reads = []
        class ProbeTools(LocalTools):
            def call(self, name, args):
                observation = super().call(name, args)
                if name == "read_file" and args.get("path") == "fact.txt" and observation == fact:
                    exact_reads.append(True)
                return observation
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "fact.txt").write_text(fact, encoding="utf-8")
            agent = Agent(model, ProbeTools(Path(root)), tool_protocol=protocol,
                          strict_json_profile="constrained" if protocol == "strict-json" else "prompt",
                          on_event=events.append)
            answer = None
            try:
                answer = agent.run("Read fact.txt using read_file. Return only its exact contents.")
            except (ModelError, ProtocolError) as exc:
                print(protocol, "failure:", exc.kind if isinstance(exc, ModelError) else exc.code)
            reads = sum(e.get("event") == "tool_end" and e.get("tool") == "read_file"
                        and e.get("status") == "ok" for e in events)
            print(protocol, "successful reads:", reads, "exact fact:", answer == fact,
                  "required file reads:", len(exact_reads),
                  "task success:", reads > 0 and bool(exact_reads) and answer == fact)


if __name__ == "__main__":
    try:
        main()
    except (ModelError, ProtocolError) as exc:
        print("probe failed:", exc.kind if isinstance(exc, ModelError) else exc.code)
        sys.exit(1)
