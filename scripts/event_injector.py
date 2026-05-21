"""
Event Injector - Simulates real-time event streaming from event.json.

Reads events from a JSON file and writes them to a JSONL file incrementally,
simulating the upstream team's real-time event capture.

Usage:
    # Realtime mode, 120x speed (40min -> 20s)
    python event_injector.py --input data/event_clean.json --speed 120

    # Fixed interval, one event per 0.5s
    python event_injector.py --input data/event_clean.json --mode fixed --interval 0.5

    # With noise file
    python event_injector.py --input data/event_with_noise.json --speed 200
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Event Injector - simulate real-time event streaming")
    parser.add_argument("--input", required=True, help="Input event JSON file path")
    parser.add_argument("--output", default=None, help="Output JSONL file path (default: workspace/event_stream.jsonl)")
    parser.add_argument("--speed", type=float, default=120, help="Time compression factor for realtime mode (default: 120)")
    parser.add_argument("--mode", choices=["realtime", "fixed"], default="realtime", help="Injection mode (default: realtime)")
    parser.add_argument("--interval", type=float, default=0.5, help="Fixed interval in seconds for fixed mode (default: 0.5)")
    parser.add_argument("--reset", action="store_true", help="Clear output file before starting")
    return parser.parse_args()


def load_events(input_path: str) -> list[dict]:
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    events = data.get("event_logs", [])
    print(f"[*] Loaded {len(events)} events from {input_path}")
    print(f"    dataset_id: {data.get('dataset_id', 'N/A')}")
    print(f"    case_id:    {data.get('case_id', 'N/A')}")
    return events


def calc_time_deltas(events: list[dict]) -> list[float]:
    """Calculate time deltas (in seconds) between consecutive events."""
    fmt = "%Y-%m-%d %H:%M:%S"
    deltas = []
    for i in range(len(events)):
        if i == 0:
            deltas.append(0.0)
        else:
            t_prev = datetime.strptime(events[i - 1]["event_time"], fmt)
            t_curr = datetime.strptime(events[i]["event_time"], fmt)
            deltas.append((t_curr - t_prev).total_seconds())
    return deltas


def inject(events: list[dict], output_path: str, mode: str, speed: float, interval: float, reset: bool):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    if reset:
        output.write_text("", encoding="utf-8")
        print(f"[*] Reset output file: {output}")
    else:
        print(f"[*] Append mode: {output}")

    if mode == "realtime":
        deltas = calc_time_deltas(events)
        print(f"[*] Realtime mode, speed={speed}x")
        total_time = sum(deltas)
        print(f"[*] Original span: {total_time/60:.1f} min, compressed: {total_time/speed:.1f} s")
    else:
        print(f"[*] Fixed mode, interval={interval}s")
        deltas = [0] + [interval] * (len(events) - 1)

    print(f"\n{'='*60}")
    print(f"{'Seq':>5} | {'Delay':>7} | {'LogID':<12} | {'Time':<20} | Event")
    print(f"{'-'*60}")

    for i, event in enumerate(events):
        delay = deltas[i] / speed if mode == "realtime" else deltas[i]
        if i > 0 and delay > 0:
            time.sleep(delay)

        # Append to JSONL
        with open(output, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        log_id = event.get("log_id", "?")
        event_time = event.get("event_time", "?")
        event_name = event.get("event_name", "?")
        is_noise = log_id.startswith("NOISE")
        marker = "[NOISE]" if is_noise else "[SOP]  "

        print(f"{i+1:>5} | {delay:>6.2f}s | {log_id:<12} | {event_time:<20} | {marker} {event_name}")

    print(f"{'='*60}")
    print(f"[*] Done. {len(events)} events injected to {output}")


def main():
    args = parse_args()

    if args.output is None:
        args.output = str(Path(__file__).parent / "event_stream.jsonl")

    events = load_events(args.input)
    if not events:
        print("[!] No events found.")
        sys.exit(1)

    inject(events, args.output, args.mode, args.speed, args.interval, args.reset)


if __name__ == "__main__":
    main()
