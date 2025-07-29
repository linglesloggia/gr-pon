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
import pprint
from .gpon_parser import GponPacket, find_sync_word_bitwise



class gpon_bwmap_parser(gr.basic_block):
    def __init__(self):
        gr.basic_block.__init__(
            self,
            name="gpon_bwmap_parser",
            in_sig=[np.uint8],  # cada entrada es un bit (0 o 1)
            out_sig=[]
        )

        self.bit_buffer = []
        self.message_port_register_out(pmt.intern("out"))

    def general_work(self, input_items, output_items):
        in_bits = input_items[0].tolist()
        self.bit_buffer.extend(in_bits)
        consumed = len(in_bits)

        # print(f"[DEBUG] Received {len(in_bits)} bits. Buffer size: {len(self.bit_buffer)} bits")

        sync_bit_pos = find_sync_word_bitwise(self.bit_buffer)

        if sync_bit_pos != -1 and len(self.bit_buffer) - sync_bit_pos >= 30 * 8:
            POSTSYNC_START = sync_bit_pos + 32  # saltear el SYNC_WORD
            postsync_data = self.bit_buffer[POSTSYNC_START:]
            #print('SYNC WORD: ',self.bit_buffer[POSTSYNC_START-32:POSTSYNC_START+32])
            try:
                pkt = GponPacket(postsync_data)
                total_len = pkt.get_total_length()

                if len(postsync_data) >= total_len:
                    #print("[DEBUG] Sync found, packet total length:", total_len)

                    
                    msg = {
                        "ident": [
                            {
                                "fec_ind": pkt.FEC_Ind,
                                "reserved": pkt.Reserved,
                                "superframe_counter": str(pkt.Superframe_counter)
                            }
                        ],
                        "ploamd":[{
                                "onud_id": pkt.ONU_ID,
                                "message_id": pkt.Message_ID,
                                "ploamd_data": str(pkt.Data),
                                "ploamd_crc": pkt.ploamdCRC
                        }],
                        "bwmap_len": pkt.bwmap_length,
                        "allocs": [
                            {
                                "alloc_id": a.alloc_id,
                                "start": a.start_time,
                                "stop": a.stop_time
                            } for a in pkt.allocations
                        ]
                    }


                    #pretty_headers = pprint.pformat()

                    # Usar pprint para dar formato bonito con saltos de línea
                    pretty_msg = pprint.pformat(msg, indent=2)



                    # Enviar como string PMT para verlo legible en Message Debug
                    self.message_port_pub(
                        pmt.intern("out"),
                        pmt.to_pmt(pretty_msg)
                    )

                    # Eliminar los bits ya procesados
                    self.bit_buffer = self.bit_buffer[sync_bit_pos + total_len:]
                else:
                    print("[DEBUG] Sync found, but not enough data yet.")

            except Exception as e:
                print(f"[ERROR] Packet parsing failed: {e}")
                self.bit_buffer = self.bit_buffer[sync_bit_pos + 8 * 8:]  # saltar 8 bytes

        self.consume(0, consumed)
        return 0