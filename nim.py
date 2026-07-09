"""Minimal client for the Nemotron Omni model on NVIDIA NIM.

Uses the standard `openai` client library pointed at NVIDIA's OpenAI-compatible
endpoint (as shown on the model card). `describe_video` builds the request, sends
it, prints the reply, and returns timing metrics.

Quirk of this model: the answer streams token-by-token in the `reasoning_content`
field. In /no_think mode the `content` field just duplicates it; in /think mode
`content` holds the distinct final answer. We render each piece exactly once so
the output is never doubled and never blank.

Two things are non-standard, handled below:
  - `reasoning_budget` is passed via `extra_body`
  - `reasoning_content` is read from the delta/message with `getattr`
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from openai import OpenAI, OpenAIError

BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"


class NimError(RuntimeError):
    """Raised for any failure talking to the endpoint."""


@dataclass
class Metrics:
    ttft: float | None            # time to first token (streaming only)
    gen_time: float | None        # first token -> last token
    total: float                  # full request round-trip
    completion_tokens: int | None
    tokens_exact: bool            # True if reported by the server, False if estimated


def describe_video(
    video_url: str,
    prompt: str,
    api_key: str,
    *,
    model: str = MODEL,
    think: bool = False,
    max_tokens: int = 65536,
    temperature: float = 0.2,
    top_p: float | None = None,
    reasoning_budget: int = 16384,
    stream: bool = True,
) -> Metrics:
    """Send `prompt` + `video_url` to the model; print the reply and return Metrics."""
    client = OpenAI(base_url=BASE_URL, api_key=api_key)

    messages = [
        # The docs recommend /no_think for video; /think enables reasoning.
        {"role": "system", "content": "/think" if think else "/no_think"},
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "video_url", "video_url": {"url": video_url}},
        ]},
    ]

    params: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }
    if top_p is not None:
        params["top_p"] = top_p
    if think:
        # `reasoning_budget` is NVIDIA-specific, so it travels in extra_body.
        params["extra_body"] = {"reasoning_budget": reasoning_budget}
    if stream:
        # Ask the server for a final usage chunk so we get exact token counts.
        params["stream_options"] = {"include_usage": True}

    print("Calling the model ...\n")
    started = time.perf_counter()
    try:
        completion = client.chat.completions.create(**params)
        if stream:
            return _render_stream(completion, started, think)
        return _render_response(completion, started, think)
    except OpenAIError as exc:
        raise NimError(str(exc)) from exc


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _render_response(completion, started: float, think: bool) -> Metrics:
    total = time.perf_counter() - started
    message = completion.choices[0].message
    reasoning = (getattr(message, "reasoning_content", None) or "").strip()
    answer = (message.content or "").strip()
    _print_answer(reasoning, answer, think)
    tokens = completion.usage.completion_tokens if completion.usage else None
    metrics = Metrics(None, total, total, tokens, tokens is not None)
    _print_metrics(metrics)
    return metrics


def _render_stream(completion, started: float, think: bool) -> Metrics:
    reasoning_parts: list[str] = []
    answer_parts: list[str] = []
    reasoning_header = False
    answer_streamed = False
    first_t: float | None = None
    last_t: float | None = None
    tokens: int | None = None
    counted = 0

    for chunk in completion:
        # The final chunk (from stream_options) carries usage and has no choices.
        if chunk.usage is not None:
            tokens = chunk.usage.completion_tokens
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None)
        content = delta.content

        if reasoning or content:
            now = time.perf_counter()
            if first_t is None:
                first_t = now
            last_t = now
            counted += 1

        if reasoning:
            reasoning_parts.append(reasoning)
            if think and not reasoning_header:
                print("--- thinking ---")
                reasoning_header = True
            print(reasoning, end="", flush=True)

        if content:
            answer_parts.append(content)
            # Only stream `content` live for plain models with no reasoning channel;
            # otherwise it just repeats text we already printed.
            if not reasoning_parts:
                print(content, end="", flush=True)
                answer_streamed = True
    print()

    reasoning_text = "".join(reasoning_parts).strip()
    answer_text = "".join(answer_parts).strip()
    if think:
        # The thinking streamed above; now show the distinct final answer.
        if answer_text and answer_text != reasoning_text:
            print("\n--- answer ---")
            print(answer_text)
        elif not reasoning_text and not answer_text:
            print("[no text returned]")
    elif not reasoning_text and not answer_streamed:
        # Nothing streamed live: fall back to whatever content we captured.
        print(answer_text or "[no text returned]")

    ttft = (first_t - started) if first_t is not None else None
    gen = (last_t - first_t) if first_t is not None and last_t is not None else None
    exact = tokens is not None
    if tokens is None and counted:
        tokens = counted           # fall back to counting streamed chunks
    metrics = Metrics(ttft, gen, time.perf_counter() - started, tokens, exact)
    _print_metrics(metrics)
    return metrics


def _print_answer(reasoning: str, answer: str, think: bool) -> None:
    """Print a non-streamed reply, showing each channel once."""
    if think:
        if reasoning:
            print("--- thinking ---")
            print(reasoning)
        if answer and answer != reasoning:
            print("\n--- answer ---" if reasoning else "--- answer ---")
            print(answer)
        elif not reasoning and not answer:
            print("[no text returned]")
    else:
        print(answer or reasoning or "[no text returned]")


def _print_metrics(m: Metrics) -> None:
    print("\n" + "-" * 60)
    if m.ttft is not None:
        print(f"  time to first token : {m.ttft:.2f} s")
    if m.gen_time is not None:
        print(f"  generation time     : {m.gen_time:.2f} s")
    print(f"  total time          : {m.total:.2f} s")
    if m.completion_tokens is not None:
        prefix = "" if m.tokens_exact else "~"
        suffix = "" if m.tokens_exact else " (approx)"
        rate = f"  ({m.completion_tokens / m.gen_time:.1f} tok/s)" if m.gen_time else ""
        print(f"  tokens generated    : {prefix}{m.completion_tokens}{rate}{suffix}")
    else:
        print("  tokens generated    : (not reported)")
    print("-" * 60)
