#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2025 Lucas Inglés Loggia.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#


import numpy as np
from gnuradio import gr
import pmt
from .gpon_parser import find_sync_word, GponPacket 


class gpon_bwmap_parser(gr.basic_block):
    """
    docstring for block gpon_bwmap_parser
    """
    def __init__(self):
        gr.basic_block.__init__(self,
            name="gpon_bwmap_parser",
            in_sig=[np.uint8],
            out_sig=[])
        self.set_output_multiple(1)
        self.message_port_register_out(pmt.intern("out"))
        self.buffer = bytearray()

    #def forecast(self, noutput_items, ninputs):
        # ninputs is the number of input connections
        # setup size of input_items[i] for work call
        # the required number of input items is returned
        #   in a list where each element represents the
        #   number of required items for each input
        #ninput_items_required = [noutput_items] * ninputs
        #return ninput_items_required

    def general_work(self, input_items, output_items):
        in0 = input_items[0].tobytes()
        self.buffer += in0
        consumed = len(in0)

        # CAMBIO: Quitar el while True - procesar solo UN paquete por llamada
        sync_pos = find_sync_word(self.buffer)
        if sync_pos != -1 and len(self.buffer) - sync_pos >= 64:
            try:
                if not GponPacket.is_downlink_packet(self.buffer[sync_pos:]):
                    self.buffer = self.buffer[sync_pos + 8:]
                else:
                    pkt = GponPacket(self.buffer[sync_pos:])
                    total_len = pkt.get_total_length()
                    if sync_pos + total_len <= len(self.buffer):
                        # Publicar como mensaje
                        self.message_port_pub(
                            pmt.intern("out"),
                            pmt.to_pmt({
                                "bwmap_len": pkt.bwmap_length,
                                "allocs": [
                                    {
                                        "alloc_id": a.alloc_id,
                                        "start": a.start_time,
                                        "stop": a.stop_time
                                    } for a in pkt.allocations
                                ]
                            })
                        )
                        self.buffer = self.buffer[sync_pos + total_len:]
                    # Si no hay suficientes datos, mantener el buffer y esperar más

            except Exception as e:
                print(f"[ERROR] Parsing failed: {e}")
                self.buffer = self.buffer[sync_pos + 8:]

        self.consume(0, consumed)
        return 0

