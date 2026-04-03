#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# gpon_bwmap_parser.py
# Publishes PDUs as u8vectors on 'out' and writes human-readable hex and JSONL
# lines per PDU to /tmp/gpon_payloads.hex and /tmp/gpon_payloads.jsonl
#
# This file is intended to be used during development. It writes append-only
# logs for easier inspection of PDUs produced by the parser.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import json
import os
import pprint
import time

import numpy as np
import pandas as pd
import pmt
from gnuradio import gr

from .gpon_parser import GponPacket, find_sync_word_bitwise

# Allow configuring output directory via environment variable GPON_OUT_DIR.
# If not set, default to the current working directory.
_out_dir = os.getenv("GPON_OUT_DIR", os.getcwd())
try:
    os.makedirs(_out_dir, exist_ok=True)
except Exception:
    # Non-fatal: if creation fails, we'll still attempt to write using the computed paths.
    pass
HEX_LOG_PATH = os.path.join(_out_dir, "gpon_payloads.hex")
JSONL_LOG_PATH = os.path.join(_out_dir, "gpon_payloads.jsonl")


class gpon_bwmap_parser(gr.basic_block):
    """
    GNU Radio basic_block that parses GPON BWMap packets from an input bit stream
    (each sample is expected to be 0 or 1, dtype uint8).

    Behavior:
    - When a complete GPON packet is found it will:
        * Publish a PDU on message port 'out' where the PDU is (PMT_NIL, u8vector)
          containing the packet bytes (MSB-first packing).
        * Append a hex string line to /tmp/gpon_payloads.hex (one hex payload per line).
        * Append a JSON line with timestamp, hex and parsed fields to
          /tmp/gpon_payloads.jsonl (newline-delimited JSON).
        * Save a CSV representation (keeps historic behavior).
    """

    def __init__(self):
        gr.basic_block.__init__(
            self,
            name="gpon_bwmap_parser",
            in_sig=[np.uint8],  # each input sample is a bit (0 or 1)
            out_sig=[],
        )

        self.bit_buffer = []
        # Primary binary PDU output
        self.message_port_register_out(pmt.intern("out"))
        # Secondary human-readable debug output (optional)
        self.message_port_register_out(pmt.intern("out_debug"))

        # Ensure log files exist and are writable (create if missing)
        try:
            open(HEX_LOG_PATH, "a").close()
        except Exception:
            pass
        try:
            open(JSONL_LOG_PATH, "a").close()
        except Exception:
            pass

    def _bits_to_bytes_msb_first(self, bits):
        """
        Convert a list/iterable of bits (0/1) to a bytes object.
        Packs MSB-first: the first bit in `bits` becomes the MSB of the first byte.
        """
        if not bits:
            return b""
        rem = len(bits) % 8
        if rem != 0:
            bits = bits + [0] * (8 - rem)
        out = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for b in bits[i : i + 8]:
                byte = (byte << 1) | (1 if b else 0)
            out.append(byte)
        return bytes(out)

    def _append_hex_log(self, hex_str):
        """
        Append a hex string followed by newline to HEX_LOG_PATH.
        Uses append-per-write and fsync to try to make data visible quickly.
        """
        try:
            with open(HEX_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(hex_str + "\n")
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except Exception:
                    # Not critical if fsync fails
                    pass
        except Exception:
            # Never allow logging failures to break the parser
            pass

    def _append_jsonl(self, obj):
        """
        Append a JSON object as a single newline-delimited JSON line to JSONL_LOG_PATH.
        """
        try:
            line = json.dumps(obj, ensure_ascii=False)
            with open(JSONL_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except Exception:
                    pass
        except Exception:
            pass

    def general_work(self, input_items, output_items):
        in_bits = input_items[0].tolist()
        self.bit_buffer.extend(in_bits)
        consumed = len(in_bits)

        # Search sync word in bit buffer
        sync_bit_pos = find_sync_word_bitwise(self.bit_buffer)

        if sync_bit_pos != -1 and len(self.bit_buffer) - sync_bit_pos >= 30 * 8:
            POSTSYNC_START = sync_bit_pos + 32  # skip 32-bit SYNC_WORD
            postsync_data = self.bit_buffer[POSTSYNC_START:]
            try:
                pkt = GponPacket(postsync_data)
                total_len = pkt.get_total_length()

                if len(postsync_data) >= total_len:
                    # Extract only the bits that belong to the packet
                    bits_for_pdu = postsync_data[:total_len]

                    # Prepare the structured message (human readable)
                    msg = {
                        "ident": [
                            {
                                "fec_ind": pkt.FEC_Ind,
                                "reserved": pkt.Reserved,
                                "superframe_counter": str(pkt.Superframe_counter),
                            }
                        ],
                        "ploamd": [
                            {
                                "onud_id": pkt.ONU_ID,
                                "message_id": pkt.Message_ID,
                                "ploamd_data": str(pkt.Data),
                                "ploamd_crc": pkt.ploamdCRC,
                            }
                        ],
                        "bwmap_len": pkt.bwmap_length,
                        "allocs": [
                            {
                                "alloc_id": a.alloc_id,
                                "start": a.start_time,
                                "stop": a.stop_time,
                            }
                            for a in pkt.allocations
                        ],
                    }

                    # Save CSV representation (non-blocking best-effort)
                    try:
                        self.save_msg_to_csv(msg, "gpon.csv")
                    except Exception:
                        # don't let logging stop parsing
                        pass

                    # Convert bits to bytes (MSB-first packing)
                    payload = self._bits_to_bytes_msb_first(bits_for_pdu)

                    # Publish PDU (meta=PMT_NIL, data=u8vector)
                    try:
                        u8 = pmt.init_u8vector(len(payload), bytearray(payload))
                        pdu = pmt.cons(pmt.PMT_NIL, u8)
                        # Debug print to stdout to observe emission
                        try:
                            print(
                                "[DEBUG] Publishing PDU of {} bytes to port 'out'".format(
                                    len(payload)
                                ),
                                flush=True,
                            )
                        except Exception:
                            pass
                        self.message_port_pub(pmt.intern("out"), pdu)
                    except Exception as e:
                        try:
                            pretty_msg = pprint.pformat(msg, indent=2)
                            print(
                                "[ERROR] Failed to publish PDU, falling back to pretty PMT: {}".format(
                                    e
                                ),
                                flush=True,
                            )
                            self.message_port_pub(
                                pmt.intern("out"), pmt.to_pmt(pretty_msg)
                            )
                        except Exception:
                            pass

                    # Also publish a human-readable debug PMT on 'out_debug'
                    try:
                        debug_obj = {"hex": payload.hex(), "msg": msg}
                        self.message_port_pub(
                            pmt.intern("out_debug"), pmt.to_pmt(json.dumps(debug_obj))
                        )
                    except Exception:
                        pass

                    # Append hex and JSONL logs to files for offline inspection
                    try:
                        hex_str = payload.hex()
                        json_obj = {"ts": time.time(), "hex": hex_str, "msg": msg}
                        # write hex line
                        self._append_hex_log(hex_str)
                        # write jsonl line
                        self._append_jsonl(json_obj)
                    except Exception:
                        pass

                    # Consume the bits belonging to the processed packet
                    self.bit_buffer = self.bit_buffer[sync_bit_pos + total_len :]
                else:
                    # Not enough bits yet to complete the packet, wait for more samples
                    pass

            except Exception as e:
                # If parsing fails, advance a bit to avoid infinite loops
                try:
                    print("[ERROR] Packet parsing failed: {}".format(e), flush=True)
                except Exception:
                    pass
                # Skip 8 bytes (64 bits) as a simple recovery heuristic
                self.bit_buffer = self.bit_buffer[sync_bit_pos + 8 * 8 :]

        # Inform scheduler how many input items we've consumed
        self.consume(0, consumed)
        return 0

    def save_msg_to_csv(self, msg, filename="gpon.csv"):
        """
        Save a flattened CSV representation of the parsed message. This preserves
        the project's previous CSV-writing behavior, but is guarded against I/O
        errors so it won't stop the block if disk writes fail.
        """
        data = {}
        # ident
        for k, v in msg["ident"][0].items():
            if isinstance(v, list):
                data[("ident", k)] = [str(v)]
            else:
                data[("ident", k)] = [v]
        # ploamd
        for k, v in msg["ploamd"][0].items():
            if isinstance(v, list):
                data[("ploamd", k)] = [str(v)]
            else:
                data[("ploamd", k)] = [v]
        # bwmap_len
        data[("bwmap", "len")] = [msg["bwmap_len"]]
        # allocs
        allocs = msg["allocs"]
        allocs_df = pd.DataFrame(allocs)
        df_main = pd.DataFrame(data)
        if not allocs_df.empty:
            allocs_df.columns = pd.MultiIndex.from_product(
                [["alloc"], allocs_df.columns]
            )
            df_main = pd.concat([df_main] * len(allocs_df), ignore_index=True)
            df = pd.concat([df_main, allocs_df], axis=1)
        else:
            df = df_main

        capture_idx = 1
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith("Capture "):
                            try:
                                n = int(line.strip().split(" ")[1])
                                if n >= capture_idx:
                                    capture_idx = n + 1
                            except Exception:
                                continue
            except Exception:
                pass

        try:
            with open(filename, "a") as f:
                f.write("Capture {}\n".format(capture_idx))
                df.to_csv(f, index=False)
                f.write("\n")
        except Exception:
            pass
