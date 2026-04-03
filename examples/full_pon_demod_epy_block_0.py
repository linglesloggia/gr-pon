"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import csv
import time

class csv_sink(gr.sync_block):
    def __init__(self, filename="output.csv", sample_rate=2000):
        gr.sync_block.__init__(
            self,
            name="csv_sink",
            in_sig=[np.float32],
            out_sig=None
        )
        self.filename = 'output_fec'
        self.sample_rate = 200e9
        self.sample_count = 0
        
        # Crear archivo CSV con headers
        with open(self.filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Sample', 'Time(s)', 'Value'])

    def work(self, input_items, output_items):
        in0 = input_items[0]
        
        # Escribir datos al CSV
        with open(self.filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for i, value in enumerate(in0):
                time_sec = (self.sample_count + i) / self.sample_rate
                writer.writerow([self.sample_count + i, f"{time_sec:.6f}", f"{value:.3f}"])
        
        self.sample_count += len(in0)
        return len(input_items[0])
