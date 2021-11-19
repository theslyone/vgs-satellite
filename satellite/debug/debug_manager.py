import re
import signal
import time
import uuid

from pathlib import Path
from subprocess import Popen

from .larky_debugger import LarkyDebugger


class DebugManager:
    def __init__(self) -> None:
        self.debugger = LarkyDebugger()
        self.bazel_proc = None

    def start(self, org_id: str, vault: str) -> str:

        # !!! FAKE START BEGIN
        example_path = Path(__file__).parent / "../../bazel_example"
        rules_path = example_path / "rules.bzl"
        with open(rules_path) as f:
            src = f.read()
        new_src = re.sub(r"TAG = '\d+'", f"TAG = '{int(time.time())}'", src)
        with open(rules_path, "w") as f:
            f.write(new_src)

        self.bazel_proc = Popen(
            ["bazel", "build", "--experimental_skylark_debug", "//:dbg-test"],
            cwd=example_path,
        )

        time.sleep(3)
        self.debugger.start("aa", "bbb")
        # !!! FAKE START END

        session_id = str(uuid.uuid4())
        return session_id

    def status(self, session_id: str) -> str:
        return "ready"

    def stop(self):
        if not self.bazel_proc:
            return
        for _ in range(3):
            self.bazel_proc.send_signal(signal.SIGINT)
        self.bazel_proc.wait()
        self.bazel_proc = None

    def get_debugger(self, session_id: str) -> LarkyDebugger:
        return self.debugger
