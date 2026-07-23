#!/usr/bin/env python3
"""Lectura y presentación de tramas GPON parseadas en JSON/NDJSON.

Uso típico:
    python3 sandbox/read_json.py
    python3 sandbox/read_json.py --mode frame --index 3
    python3 sandbox/read_json.py --mode summary --top-allocs 12
"""

from __future__ import annotations

import argparse
import ast
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


def _bits_to_int(bits: list[int] | tuple[int, ...] | None) -> int | None:
    if bits is None:
        return None
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    return value


def _parse_bits_from_string(maybe_bits: Any) -> list[int] | None:
    """Convierte "[0, 1, ...]" a lista de int si aplica."""
    if isinstance(maybe_bits, list):
        return [int(x) for x in maybe_bits]
    if isinstance(maybe_bits, str):
        try:
            parsed = ast.literal_eval(maybe_bits)
            if isinstance(parsed, list):
                return [int(x) for x in parsed]
        except (SyntaxError, ValueError):
            return None
    return None


def _load_records(path: Path) -> list[dict[str, Any]]:
    """Soporta NDJSON (1 objeto por línea) y JSON estándar (array u objeto)."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    # Intento 1: JSON estándar
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [r for r in parsed if isinstance(r, dict)]
        if isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError:
        pass

    # Intento 2: NDJSON
    records: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"Línea NDJSON inválida {i}: {e}") from e
        if isinstance(obj, dict):
            records.append(obj)
    return records


def _grant_size(alloc: dict[str, Any]) -> int:
    start = int(alloc.get("start", 0))
    stop = int(alloc.get("stop", -1))
    return max(0, stop - start + 1)


def _render_summary(records: list[dict[str, Any]], top_allocs: int = 10) -> str:
    n = len(records)
    if n == 0:
        return "No hay registros para resumir."

    ts = [float(r["ts"]) for r in records if "ts" in r]
    bwmap_lengths = [int((r.get("msg") or {}).get("bwmap_len", 0)) for r in records]

    alloc_id_counter: Counter[int] = Counter()
    grants_per_frame: list[int] = []
    grant_sizes: list[int] = []
    for r in records:
        allocs = (r.get("msg") or {}).get("allocs") or []
        grants_per_frame.append(len(allocs))
        for a in allocs:
            alloc_id_counter[int(a.get("alloc_id", -1))] += 1
            grant_sizes.append(_grant_size(a))

    fec_counter: Counter[int] = Counter()
    for r in records:
        ident_list = (r.get("msg") or {}).get("ident") or []
        if ident_list and isinstance(ident_list[0], dict):
            fec = int(ident_list[0].get("fec_ind", 0))
            fec_counter[fec] += 1

    lines = []
    lines.append("=== Resumen de captura GPON ===")
    lines.append(f"Frames: {n}")

    if ts:
        ts_span = max(ts) - min(ts)
        lines.append(
            f"Rango temporal: {min(ts):.6f} .. {max(ts):.6f} s (Δ={ts_span:.6f} s)"
        )
        if len(ts) > 1:
            sorted_ts = sorted(ts)
            deltas = [b - a for a, b in zip(sorted_ts, sorted_ts[1:])]
            lines.append(
                "Δt entre frames: "
                f"media={statistics.mean(deltas):.6f} s, "
                f"mediana={statistics.median(deltas):.6f} s"
            )

    if bwmap_lengths:
        lines.append(
            "BWmap_len: "
            f"min={min(bwmap_lengths)}, max={max(bwmap_lengths)}, "
            f"media={statistics.mean(bwmap_lengths):.2f}"
        )

    if grants_per_frame:
        lines.append(
            "Allocs/frame: "
            f"min={min(grants_per_frame)}, max={max(grants_per_frame)}, "
            f"media={statistics.mean(grants_per_frame):.2f}"
        )

    if grant_sizes:
        lines.append(
            "Tamaño grant (stop-start+1): "
            f"min={min(grant_sizes)}, max={max(grant_sizes)}, "
            f"media={statistics.mean(grant_sizes):.2f}"
        )

    if fec_counter:
        fec_str = ", ".join(f"fec_ind={k}: {v}" for k, v in sorted(fec_counter.items()))
        lines.append(f"FEC indicator: {fec_str}")

    if alloc_id_counter:
        lines.append(f"Top {top_allocs} alloc_id más frecuentes:")
        for alloc_id, count in alloc_id_counter.most_common(top_allocs):
            lines.append(f"  - alloc_id={alloc_id}: {count} apariciones")

    return "\n".join(lines)


def _render_frame(record: dict[str, Any], idx: int, hex_preview_bytes: int = 20) -> str:
    msg = record.get("msg") or {}
    ident = (msg.get("ident") or [{}])[0]
    ploamd = (msg.get("ploamd") or [{}])[0]
    allocs = msg.get("allocs") or []

    superframe_bits = _parse_bits_from_string(ident.get("superframe_counter"))
    superframe_counter = (
        _bits_to_int(superframe_bits) if superframe_bits is not None else None
    )

    onud_id_bits = ploamd.get("onud_id") if isinstance(ploamd, dict) else None
    message_id_bits = ploamd.get("message_id") if isinstance(ploamd, dict) else None
    crc_bits = ploamd.get("ploamd_crc") if isinstance(ploamd, dict) else None

    onud_id = _bits_to_int(onud_id_bits) if isinstance(onud_id_bits, list) else None
    message_id = (
        _bits_to_int(message_id_bits) if isinstance(message_id_bits, list) else None
    )
    crc = _bits_to_int(crc_bits) if isinstance(crc_bits, list) else None

    hex_raw = str(record.get("hex", ""))
    hex_preview_len = max(0, int(hex_preview_bytes)) * 2
    hex_preview = hex_raw[:hex_preview_len]
    if len(hex_raw) > len(hex_preview):
        hex_preview += "..."

    lines = []
    lines.append(f"=== Frame #{idx} ===")
    lines.append(f"timestamp: {record.get('ts', 'N/A')}")
    lines.append(f"hex_len: {len(hex_raw)} chars")
    lines.append(f"hex_preview: {hex_preview}")
    lines.append("")

    lines.append("[IDENT]")
    lines.append(f"fec_ind: {ident.get('fec_ind', 'N/A')}")
    lines.append(f"reserved: {ident.get('reserved', 'N/A')}")
    lines.append(
        "superframe_counter: "
        f"{superframe_counter if superframe_counter is not None else ident.get('superframe_counter', 'N/A')}"
    )
    lines.append("")

    lines.append("[PLOAMd]")
    lines.append(f"onud_id: {onud_id if onud_id is not None else onud_id_bits}")
    lines.append(
        f"message_id: {message_id if message_id is not None else message_id_bits}"
    )
    lines.append(f"ploamd_crc: {crc if crc is not None else crc_bits}")
    lines.append("")

    lines.append("[BWMAP]")
    lines.append(f"bwmap_len: {msg.get('bwmap_len', 'N/A')}")
    lines.append(f"alloc_count: {len(allocs)}")
    for i, a in enumerate(allocs):
        size = _grant_size(a)
        lines.append(
            f"  alloc[{i}]: id={a.get('alloc_id')} start={a.get('start')} stop={a.get('stop')} size={size}"
        )

    return "\n".join(lines)


def _build_arg_parser(default_path: Path) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Visualizador de payloads GPON parseados (JSON/NDJSON)."
    )
    p.add_argument(
        "--input",
        type=Path,
        default=default_path,
        help=f"Ruta al archivo JSON/NDJSON (default: {default_path})",
    )
    p.add_argument(
        "--mode",
        choices=["summary", "frame", "both"],
        default="both",
        help="Qué imprimir",
    )
    p.add_argument(
        "--index",
        type=int,
        default=0,
        help="Índice de frame para --mode frame/both",
    )
    p.add_argument(
        "--hex-bytes",
        type=int,
        default=20,
        help="Cuántos bytes mostrar en hex_preview",
    )
    p.add_argument(
        "--top-allocs",
        type=int,
        default=10,
        help="Cuántos alloc_id frecuentes mostrar en resumen",
    )
    return p


def main() -> None:
    default_path = (
        Path(__file__).resolve().parents[1] / "outputs" / "cli" / "gpon_payloads.json"
    )
    parser = _build_arg_parser(default_path)
    args = parser.parse_args()

    records = _load_records(args.input)
    if not records:
        print(f"No se encontraron registros en: {args.input}")
        return

    if args.mode in {"summary", "both"}:
        print(_render_summary(records, top_allocs=args.top_allocs))

    if args.mode in {"frame", "both"}:
        idx = args.index
        if idx < 0 or idx >= len(records):
            raise IndexError(
                f"index fuera de rango: {idx}, total frames={len(records)}"
            )
        print()
        print(_render_frame(records[idx], idx=idx, hex_preview_bytes=args.hex_bytes))


if __name__ == "__main__":
    main()
