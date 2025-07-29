import binascii
import struct

class AllocationStructure:
    def __init__(self, bits):
        """
        bits: lista de enteros (0 o 1), al menos 64 bits
        Formato:
        - 24 bits: Alloc-ID (12 MSB) + Flags (12 LSB)
        - 16 bits: Start Time
        - 16 bits: Stop Time
        - 8 bits: CRC
        """

        #print('len bits. ' , len(bits))
        if len(bits) < 64:
            raise ValueError("Se requieren al menos 64 bits para el AllocationStructure")

        # Convertir sublistas de bits a enteros
        def bits_to_int(b):
            return int("".join(str(bit) for bit in b), 2)

        self.alloc_id = bits_to_int(bits[0:12])
        self.flags = bits_to_int(bits[12:24])
        self.start_time = bits_to_int(bits[24:40])
        self.stop_time = bits_to_int(bits[40:56])
        self.crc = bits_to_int(bits[56:64])

    def __str__(self):
        return (f"\n        Alloc-ID: {self.alloc_id}"
                f"\n        Flags: {self.flags:012b}"
                f"\n        StartTime: {self.start_time}"
                f"\n        StopTime: {self.stop_time}"
                f"\n        CRC: 0x{self.crc:02x}")

class GponPacket:
    def __init__(self, raw_data):

        self.PostSync_d = self.descrambler(raw_data)

        self.ident = None
        self.ploamd = None
        self.bip = None
        self.plend1 = None
        self.plend2 = None
        self.bwmap = None
        self.allocations = []

        self.FEC_Ind = None
        self.Reserved = None
        self.Superframe_counter = None

        self.ONU_ID = None
        self.Message_ID = None
        self.Data = None
        self.ploamdCRC = None

        self.Alen = None 
        self.crc =  None

        # Now parse the packet
        self.parse()

    def descrambler(self, input_bits):
        reg = [1] * 7
        output_bits = []

        for b_in in input_bits:
            scramble_bit = reg[6]
            b_out = b_in ^ scramble_bit
            output_bits.append(b_out)

            feedback = reg[6] ^ reg[5]
            reg = [feedback] + reg[:-1]

        return output_bits

    def parse(self):
        current_pos = 0

        self.ident = self.PostSync_d[current_pos:current_pos+4*8]
        current_pos += 4*8

        self.FEC_Ind = self.ident[0]
        self.Reserved = self.ident[1]
        self.Superframe_counter = self.ident[2:]

        self.ploamd = self.PostSync_d[current_pos:current_pos+13*8]
        current_pos += 13*8

        self.ONU_ID = self.ploamd[:8]
        self.Message_ID = self.ploamd[8:16]
        self.Data = self.ploamd[16:96]
        self.ploamdCRC = self.ploamd[96:104]

        self.bip = self.PostSync_d[current_pos:current_pos+1*8]
        current_pos += 1*8
        
        self.plend1 = self.PostSync_d[current_pos:current_pos+4*8]
        current_pos += 4*8
        self.plend2 = self.PostSync_d[current_pos:current_pos+4*8]
        current_pos += 4*8


        # Relativo al BWMap:
        bit_str = ''.join(str(b) for b in self.plend1[:12])
        self.bwmap_length = int(bit_str, 2) * 8 *8

        #self.Blen = int(self.plend1[:12], 2)
        self.Alen = self.plend1[12:24]  # Alen es el largo del ATM partition, que debería ser 0
        self.crc = self.plend1[24:32]

        # BWmap length ya está calculado en __init__
        if current_pos + self.bwmap_length <= len(self.PostSync_d):
            self.bwmap = self.PostSync_d[current_pos:current_pos+self.bwmap_length]
            
            if self.bwmap_length == 64:
                try:
                    alloc = AllocationStructure(self.bwmap)
                    self.allocations.append(alloc)
                except Exception as e:
                    print(f"Error parsing single allocation: {e}")
            else:
                # Parse multiple 8-byte allocation structures
                for i in range(0, self.bwmap_length, 8*8):
                    allocation_data = self.bwmap[i:i+8*8]
                    if len(allocation_data) == 8*8:
                        try:
                            alloc = AllocationStructure(allocation_data)
                            self.allocations.append(alloc)
                        except Exception as e:
                            print(f"Error parsing allocation at offset {i}: {e}")
        else:
            print(f"Warning: Invalid BWmap length. Expected {self.bwmap_length} bytes but only have {len(self.PostSync_d) - current_pos}")
            self.bwmap = bytes()

    def __str__(self):
        base_info = (f"GPON Packet:\n"
                    f"  IDENT: {self.ident.hex()}\n"
                    f"  PLOAMd: {self.ploamd.hex()}\n"
                    f"  BIP: {self.bip.hex()}\n"
                    f"  Plend1: {self.plend1.hex()} (BWmap length: {self.bwmap_length} bytes)\n"
                    f"  Plend2: {self.plend2.hex()}\n"
                    f"  BWmap:")
        
        # Add allocation structures
        allocations_info = ""
        for i, alloc in enumerate(self.allocations, 1):
            allocations_info += f"\n    Allocation {i}:{alloc}"
        
        return base_info + allocations_info

    def get_total_length(self):
        """Calculate total packet length including BWmap"""
        
        pcbd_headers = (
            4*8 +  # IDENT
            13*8 + # PLOAMd
            1*8 +  # BIP
            4*8 +  # Plend1
            4*8    # Plend2
        )
        return pcbd_headers + self.bwmap_length



SYNC_WORD = '10110110101010110011000111100000'

def find_sync_word_bitwise(bit_buffer):
    # Convierte bits a bytes y busca la palabra de sincronización

    bit_string = ''.join(str(b) for b in bit_buffer)

    pos = bit_string.find(SYNC_WORD)
    if pos != -1:
        return pos  # devolver posición en bits
    return -1

