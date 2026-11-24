"""Ollama's 'token repeat limit reached' abort is a MODEL failure, never 'infrastruktúra' (heldout 2026-11-22)."""

from auri_core.contracts import REPEAT_ABORT, SolveOptions, chat_or_abort
from auri_core.fakes import FakeLLM, FakeSandbox, FakeScheduler, make_task
from auri_core.solve import solve

TESTS = {"tests/test_visible.py": "from solution import double\n\ndef test_ok():\n    assert double(2) == 4\n"}
GOOD = {"files": [{"path": "solution.py", "content": "def double(n: int) -> int:\n    return n * 2\n"}]}


class OllamaHttpError(RuntimeError):  # the shape of auri_jarvis LLMError (kind, user_message, detail)
    def __init__(self, detail: str) -> None:
        super().__init__(f"http: {detail}")
        self.kind, self.user_message, self.detail = "http", "Hiba történt a nyelvi modellnél.", detail


def repeat() -> OllamaHttpError:
    return OllamaHttpError("HTTP 500: prediction aborted, token repeat limit reached")


async def run(replies, script, rounds):
    sch, events = FakeScheduler(), []
    out = await solve(make_task(), llm=FakeLLM(replies, scheduler=sch), sandbox=FakeSandbox(script), store=None,
                      scheduler=sch, opts=SolveOptions(repair_rounds=rounds, model="m"), visible=TESTS,
                      on_event=lambda e, d: events.append(e))
    return out, events


async def test_repeat_abort_is_a_model_failure_in_model_only_mode():
    out, events = await run([repeat()], [], 0)
    assert out.kind == "give_up" and out.llm_calls == 1
    assert not (out.reason_hu or "").startswith("infrastruktúra") and "model_error" in events


async def test_repeat_abort_is_repaired_like_garbage():
    out, _ = await run([repeat(), GOOD], ["pass"], 1)
    assert out.kind == "pass" and out.rounds == 1 and out.llm_calls == 2


async def test_other_errors_stay_infrastructure():
    out, _ = await run([OllamaHttpError("HTTP 500: out of memory")], [], 0)
    assert out.reason_hu.startswith("infrastruktúra")


async def test_chat_or_abort_returns_an_empty_aborted_reply():
    sch = FakeScheduler()
    llm = FakeLLM([repeat()], scheduler=sch)
    async with sch.lease(0, "m") as lease:
        r = await chat_or_abort(llm, lease, [{"role": "user", "content": "x"}])
    assert r.text == "" and r.stats.done_reason == REPEAT_ABORT
