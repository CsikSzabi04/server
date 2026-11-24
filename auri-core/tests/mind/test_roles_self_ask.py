"""Self-questioning (02/03): cheapest source first, never the user automatically; curiosity queue
without personal data and without duplicates (fictional data only: "Teszt Elek")."""

from auri_core.fakes import FakeLLM, FakeScheduler
from auri_core.roles import (
    CuriosityQueue,
    KnowledgeGap,
    RolesConfig,
    RoleSession,
    SubQuestion,
    Understanding,
    answer_subquestions,
    gap_to_curiosity,
    model_unsure,
)


async def test_cheapest_source_first_then_more_expensive_never_the_user():
    asked = []

    def src(name, answer=None):
        async def f(q):
            asked.append((name, q))
            return answer
        return f

    u = Understanding("g", [SubQuestion("verzió?", "w", "store"), SubQuestion("API?", "w", "web"),
                            SubQuestion("melyik nyelv?", "w", "user")], [], None)
    out = await answer_subquestions(u, {"store": src("store"), "sandbox": src("sandbox", "3.12"),
                                        "web": src("web", "doc"), "user": src("user", "!")})
    a, b, c = out.subquestions
    assert (a.answer, a.answered_by) == ("3.12", "sandbox") and (b.answer, b.answered_by) == ("doc", "web")
    assert c.answer is None and not any(n == "user" for n, _ in asked)


async def test_one_more_split_with_a_session():
    sch = FakeScheduler()
    llm = FakeLLM([{"goal": "g", "subquestions": [{"q": "kisebb?", "why": "w", "source": "store"}], "unknowns": [],
                    "ask_user": None}], scheduler=sch)
    s = RoleSession(llm, sch, cfg=RolesConfig(enabled=True))

    async def store(q):
        return "igen" if q == "kisebb?" else None

    u = Understanding("g", [SubQuestion("nagy kérdés?", "w", "store")], [], None)
    out = await answer_subquestions(u, {"store": store}, session=s)
    assert out.subquestions[0].answered_by == "self_ask" and "kisebb? → igen" in out.subquestions[0].answer


def test_curiosity_queue_privacy_dedup_bound_attempts(tmp_path):
    q = CuriosityQueue(path=tmp_path / "curiosity.json", limit=3)
    assert q.add("Mikor született Teszt Elek? 1990.01.01") is None  # personal data never enters
    assert q.add(r"Miért lassú a C:\Users\tesztelek\proj build?") is None  # paths neither
    a = q.add("Hogyan korlátozható a feltöltés mérete FastAPI-ban?", usefulness=0.9, severity=2)
    again = q.add("Hogyan korlátozható a feltöltés mérete FastAPI-ban streaming közben?", usefulness=0.9, severity=2)
    assert again is a and a.seen == 2 and a.priority == 2 * 0.9 * 2  # dedup bumps the priority
    for text in ["Mi a különbség a list és a tuple között?", "Hogyan működik a Node stream backpressure?",
                 "Mikor érdemes SQLite WAL módot használni?", "Mire jó a TypeScript satisfies operátora?"]:
        q.add(text, usefulness=0.1)
    assert len([i for i in q.items if i.status == "open"]) == 3 and a in q.items  # the lowest falls out
    for _ in range(3):
        q.attempt(a, success=False)
    assert a.status == "dropped" and a not in q.next()
    q.save()
    assert len(CuriosityQueue.load(tmp_path / "curiosity.json").items) == len(q.items)


def test_gaps_and_unsure():
    q = CuriosityQueue()
    gap_to_curiosity(q, KnowledgeGap("fastapi upload", "unknown_api", 2, "th_x"), "Mi az UploadFile?")
    gap_to_curiosity(q, KnowledgeGap("x", "no_card", 3, "th_x"), "Most kell?")  # severity 3: filled now, not queued
    assert [i.question for i in q.items] == ["Mi az UploadFile?"]
    assert model_unsure("I'm not sure, maybe") and model_unsure("Nem tudom pontosan") and not model_unsure("Kész.")
