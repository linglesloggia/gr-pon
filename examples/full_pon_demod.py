#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: gr-pon
# Author: Lucas Inglés
# GNU Radio version: 3.10.12.0

import signal
import sys
import threading
from argparse import ArgumentParser

import pmt
import sip
from gnuradio import blocks, digital, eng_notation, filter, gr, pdu, qtgui
from gnuradio.eng_arg import eng_float, intx
from gnuradio.fft import window
from gnuradio.filter import firdes
from pon import gpon_bwmap_parser
from PyQt5 import Qt


class full_pon_demod(gr.top_block, Qt.QWidget):
    def __init__(self):
        gr.top_block.__init__(self, "gr-pon", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("gr-pon")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme("gnuradio-grc"))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "full_pon_demod")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.sps = sps = 2
        self.samp_rate = samp_rate = 5e9

        ##################################################
        # Blocks
        ##################################################

        self.rational_resampler_xxx_0 = filter.rational_resampler_fff(
            interpolation=(972 * 32), decimation=31250, taps=[], fractional_bw=0
        )
        self.qtgui_time_sink_x_2 = qtgui.time_sink_f(
            1024,  # size
            samp_rate,  # samp_rate
            "",  # name
            1,  # number of inputs
            None,  # parent
        )
        self.qtgui_time_sink_x_2.set_update_time(0.10)
        self.qtgui_time_sink_x_2.set_y_axis(-1, 1)

        self.qtgui_time_sink_x_2.set_y_label("Amplitude", "")

        self.qtgui_time_sink_x_2.enable_tags(True)
        self.qtgui_time_sink_x_2.set_trigger_mode(
            qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, ""
        )
        self.qtgui_time_sink_x_2.enable_autoscale(False)
        self.qtgui_time_sink_x_2.enable_grid(False)
        self.qtgui_time_sink_x_2.enable_axis_labels(True)
        self.qtgui_time_sink_x_2.enable_control_panel(False)
        self.qtgui_time_sink_x_2.enable_stem_plot(False)

        labels = [
            "Signal 1",
            "Signal 2",
            "Signal 3",
            "Signal 4",
            "Signal 5",
            "Signal 6",
            "Signal 7",
            "Signal 8",
            "Signal 9",
            "Signal 10",
        ]
        widths = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        colors = [
            "blue",
            "red",
            "green",
            "black",
            "cyan",
            "magenta",
            "yellow",
            "dark red",
            "dark green",
            "dark blue",
        ]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_x_2.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_2.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_2.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_2.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_2.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_2.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_2.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_2_win = sip.wrapinstance(
            self.qtgui_time_sink_x_2.qwidget(), Qt.QWidget
        )
        self.top_layout.addWidget(self._qtgui_time_sink_x_2_win)
        self.qtgui_time_sink_x_1_0 = qtgui.time_sink_f(
            1024,  # size
            samp_rate,  # samp_rate
            "",  # name
            1,  # number of inputs
            None,  # parent
        )
        self.qtgui_time_sink_x_1_0.set_update_time(0.10)
        self.qtgui_time_sink_x_1_0.set_y_axis(-1, 1)

        self.qtgui_time_sink_x_1_0.set_y_label("Amplitude", "")

        self.qtgui_time_sink_x_1_0.enable_tags(True)
        self.qtgui_time_sink_x_1_0.set_trigger_mode(
            qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, ""
        )
        self.qtgui_time_sink_x_1_0.enable_autoscale(False)
        self.qtgui_time_sink_x_1_0.enable_grid(False)
        self.qtgui_time_sink_x_1_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_1_0.enable_control_panel(False)
        self.qtgui_time_sink_x_1_0.enable_stem_plot(False)

        labels = [
            "Signal 1",
            "Signal 2",
            "Signal 3",
            "Signal 4",
            "Signal 5",
            "Signal 6",
            "Signal 7",
            "Signal 8",
            "Signal 9",
            "Signal 10",
        ]
        widths = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        colors = [
            "blue",
            "red",
            "green",
            "black",
            "cyan",
            "magenta",
            "yellow",
            "dark red",
            "dark green",
            "dark blue",
        ]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_x_1_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_1_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_1_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_1_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_1_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_1_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_1_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_1_0_win = sip.wrapinstance(
            self.qtgui_time_sink_x_1_0.qwidget(), Qt.QWidget
        )
        self.top_layout.addWidget(self._qtgui_time_sink_x_1_0_win)
        self.qtgui_time_sink_x_1 = qtgui.time_sink_f(
            1024,  # size
            samp_rate,  # samp_rate
            "",  # name
            1,  # number of inputs
            None,  # parent
        )
        self.qtgui_time_sink_x_1.set_update_time(0.10)
        self.qtgui_time_sink_x_1.set_y_axis(-1, 1)

        self.qtgui_time_sink_x_1.set_y_label("Amplitude", "")

        self.qtgui_time_sink_x_1.enable_tags(True)
        self.qtgui_time_sink_x_1.set_trigger_mode(
            qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, ""
        )
        self.qtgui_time_sink_x_1.enable_autoscale(False)
        self.qtgui_time_sink_x_1.enable_grid(False)
        self.qtgui_time_sink_x_1.enable_axis_labels(True)
        self.qtgui_time_sink_x_1.enable_control_panel(False)
        self.qtgui_time_sink_x_1.enable_stem_plot(False)

        labels = [
            "Signal 1",
            "Signal 2",
            "Signal 3",
            "Signal 4",
            "Signal 5",
            "Signal 6",
            "Signal 7",
            "Signal 8",
            "Signal 9",
            "Signal 10",
        ]
        widths = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        colors = [
            "blue",
            "red",
            "green",
            "black",
            "cyan",
            "magenta",
            "yellow",
            "dark red",
            "dark green",
            "dark blue",
        ]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_x_1.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_1.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_1.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_1.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_1.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_1.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_1.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_1_win = sip.wrapinstance(
            self.qtgui_time_sink_x_1.qwidget(), Qt.QWidget
        )
        self.top_layout.addWidget(self._qtgui_time_sink_x_1_win)
        self.pon_gpon_bwmap_parser_0 = gpon_bwmap_parser()
        self.pdu_pdu_to_tagged_stream_0 = pdu.pdu_to_tagged_stream(
            gr.types.byte_t, "packet_len"
        )
        self.low_pass_filter_0 = filter.interp_fir_filter_fff(
            1, firdes.low_pass(1, samp_rate, 2.5e9, 0.2e9, window.WIN_HAMMING, 6.76)
        )
        self.digital_symbol_sync_xx_0 = digital.symbol_sync_ff(
            digital.TED_MUELLER_AND_MULLER,
            sps,
            0.045,
            1.0,
            1.0,
            1.5,
            1,
            digital.constellation_bpsk().base(),
            digital.IR_PFB_NO_MF,
            128,
            [],
        )
        self.blocks_throttle2_0 = blocks.throttle(
            gr.sizeof_float * 1,
            samp_rate,
            True,
            0
            if "auto" == "auto"
            else max(int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1),
        )
        self.blocks_threshold_ff_0 = blocks.threshold_ff(0, 0, 0)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_ff((-1))
        import os

        # Allow overriding input file and output directory via environment variables.
        # Default values preserve previous hardcoded paths for backward compatibility.
        in_file = os.environ.get(
            "GPON_IN_FILE",
            "/home/4moulins/projects/exp_20260401_171520_54/scope_captures/captura_pon_us_ch2_20260401_171554_f32.f32",
        )
        out_dir = os.environ.get("GPON_OUT_DIR", "/home/4moulins/projects/ecoc2026")
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            pass
        out_file = os.path.join(out_dir, "output")

        self.blocks_message_debug_0 = blocks.message_debug(True, gr.log_levels.info)
        self.blocks_float_to_char_0 = blocks.float_to_char(1, 1)
        self.blocks_file_source_0 = blocks.file_source(
            gr.sizeof_float * 1, in_file, False, 0, 0
        )
        self.blocks_file_source_0.set_begin_tag(pmt.PMT_NIL)
        self.blocks_file_sink_1 = blocks.file_sink(gr.sizeof_char * 1, out_file, False)
        self.blocks_file_sink_1.set_unbuffered(False)

        ##################################################
        # Connections
        ##################################################
        self.msg_connect(
            (self.pon_gpon_bwmap_parser_0, "out"),
            (self.blocks_message_debug_0, "print"),
        )
        self.msg_connect(
            (self.pon_gpon_bwmap_parser_0, "out"),
            (self.pdu_pdu_to_tagged_stream_0, "pdus"),
        )
        self.connect(
            (self.blocks_file_source_0, 0), (self.blocks_multiply_const_vxx_0, 0)
        )
        self.connect(
            (self.blocks_float_to_char_0, 0), (self.pon_gpon_bwmap_parser_0, 0)
        )
        self.connect(
            (self.blocks_multiply_const_vxx_0, 0), (self.blocks_throttle2_0, 0)
        )
        self.connect((self.blocks_threshold_ff_0, 0), (self.blocks_float_to_char_0, 0))
        self.connect((self.blocks_threshold_ff_0, 0), (self.qtgui_time_sink_x_2, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.low_pass_filter_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.qtgui_time_sink_x_1, 0))
        self.connect(
            (self.digital_symbol_sync_xx_0, 0), (self.blocks_threshold_ff_0, 0)
        )
        self.connect((self.low_pass_filter_0, 0), (self.qtgui_time_sink_x_1_0, 0))
        self.connect((self.low_pass_filter_0, 0), (self.rational_resampler_xxx_0, 0))
        self.connect((self.pdu_pdu_to_tagged_stream_0, 0), (self.blocks_file_sink_1, 0))
        self.connect(
            (self.rational_resampler_xxx_0, 0), (self.digital_symbol_sync_xx_0, 0)
        )

    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "full_pon_demod")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.digital_symbol_sync_xx_0.set_sps(self.sps)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)
        self.low_pass_filter_0.set_taps(
            firdes.low_pass(1, self.samp_rate, 2.5e9, 0.2e9, window.WIN_HAMMING, 6.76)
        )
        self.qtgui_time_sink_x_1.set_samp_rate(self.samp_rate)
        self.qtgui_time_sink_x_1_0.set_samp_rate(self.samp_rate)
        self.qtgui_time_sink_x_2.set_samp_rate(self.samp_rate)


def main(top_block_cls=full_pon_demod, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()


if __name__ == "__main__":
    main()
