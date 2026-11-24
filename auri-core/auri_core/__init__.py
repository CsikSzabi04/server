"""Auri Core — the local thinking brain (programming-first).

Package root (owner: AI-3 / BODY). Zones per ideas_for_brain/ai_prompts.md §1.2:
  AI-1 MIND:  contracts, fakes, digest, solve, router, lang, roles/, research/, planner/
  AI-2 HANDS: sandbox, taskset, bench, curriculum/, dashboard/
  AI-3 BODY:  config, llm, scheduler, privacy, store, server/, migrate/, cloud/

Two gates nobody bypasses: every model call goes through `scheduler.lease()`,
every knowledge-store write goes through `privacy`.
"""

__version__ = "0.1.0"
