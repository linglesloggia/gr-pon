import binascii
import struct

class AllocationStructure:
    def __init__(self, data):
        # Alloc-ID (12 MSB) | Flags (12 LSB)
        first_three_bytes = int.from_bytes(data[0:3], byteorder='big')
        self.alloc_id = first_three_bytes >> 12
        self.flags = first_three_bytes & 0xFFF
        
        self.start_time = int.from_bytes(data[3:5], byteorder='big')
        self.stop_time = int.from_bytes(data[5:7], byteorder='big')
        self.crc = data[7]

    def __str__(self):
        return (f"\n        Alloc-ID: {self.alloc_id}"
                f"\n        Flags: {self.flags:012b}"  # Print flags in binary
                f"\n        StartTime: {self.start_time}"
                f"\n        StopTime: {self.stop_time}"
                f"\n        CRC: 0x{self.crc:02x}")

class GponPacket:
    def __init__(self, raw_data):
        self.raw_data = raw_data
        # Calculate BWmap length first from Plend1 field
        if len(raw_data) >= 50:  # Make sure we have enough data for plend1
            plend1 = raw_data[46:50]  # Plend1 está en offset 46-50
            plend1_value = int.from_bytes(plend1, byteorder='big')
            self.bwmap_length = (plend1_value >> 20) * 8
        else:
            self.bwmap_length = 0
            
        # Initialize other fields
        self.sync_word = None
        self.ident = None
        self.ploamd = None
        self.bip = None
        self.plend1 = None
        self.plend2 = None
        self.bwmap = None
        self.allocations = []
        
        # Now parse the packet
        self.parse()

    def parse(self):
        current_pos = 24
        # PCBd fields
        self.ident = self.raw_data[current_pos:current_pos+4]
        current_pos += 4
        self.ploamd = self.raw_data[current_pos:current_pos+13]
        current_pos += 13
        self.bip = self.raw_data[current_pos:current_pos+1]
        current_pos += 1
        
        self.plend1 = self.raw_data[current_pos:current_pos+4]
        current_pos += 4
        self.plend2 = self.raw_data[current_pos:current_pos+4]
        current_pos += 4
        
        # BWmap length ya está calculado en __init__
        if current_pos + self.bwmap_length <= len(self.raw_data):
            self.bwmap = self.raw_data[current_pos:current_pos+self.bwmap_length]
            
            # Debug: imprimir información del BWmap
            #print(f"BWmap length: {self.bwmap_length}")
            #print(f"BWmap data: {self.bwmap.hex()}")
            
            # Si el BWmap tiene exactamente 8 bytes, procesarlo directamente
            if self.bwmap_length == 8:
                try:
                    alloc = AllocationStructure(self.bwmap)
                    self.allocations.append(alloc)
                except Exception as e:
                    print(f"Error parsing single allocation: {e}")
            else:
                # Parse multiple 8-byte allocation structures
                for i in range(0, self.bwmap_length, 8):
                    allocation_data = self.bwmap[i:i+8]
                    if len(allocation_data) == 8:
                        try:
                            alloc = AllocationStructure(allocation_data)
                            self.allocations.append(alloc)
                        except Exception as e:
                            print(f"Error parsing allocation at offset {i}: {e}")
        else:
            print(f"Warning: Invalid BWmap length. Expected {self.bwmap_length} bytes but only have {len(self.raw_data) - current_pos}")
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
        """Calculate total packet length including sync word and BWmap"""
        sync_word_size = 8  # cafe55b6ab31e0 is 8 bytes
        pcbd_headers = (
            4 +  # IDENT
            13 + # PLOAMd
            1 +  # BIP
            4 +  # Plend1
            4    # Plend2
        )
        return sync_word_size + pcbd_headers + self.bwmap_length

    @staticmethod
    def is_downlink_packet(data):
        """
        Check if packet is downlink by comparing bytes at offset 13 and 17 after sync word
        Returns True if the 4-byte sequences match (indicating downlink)
        """
        if len(data) < 21:  # Need at least sync word + 13 + 4 + 4 bytes
            return False
        
        first_seq = data[20:24]   # 4 bytes at offset 13
        second_seq = data[24:28]  # next 4 bytes
        #print(first_seq, '\n', second_seq)
        return first_seq == second_seq

def find_sync_word(data, start=0):
    SYNC_WORD = bytes.fromhex('cafe55b6ab31e0')
    pos = data.find(SYNC_WORD, start)
    return pos

def extract_packets(input_file):
    packets = []
    
    with open(input_file, 'rb') as f:
        data = f.read()
    
    current_pos = 0
    while current_pos < len(data):
        sync_pos = find_sync_word(data, current_pos)
        if (sync_pos == -1):
            break
            
        try:
            # Checkear si es downlink (segun MT2)
            if not GponPacket.is_downlink_packet(data[sync_pos:]):
                current_pos = sync_pos + 8
                continue

            # Asegurarnos que tenemos suficientes datos para leer Plend1
            if sync_pos + 50 > len(data):
                current_pos = sync_pos + 8
                continue
                
            packet = GponPacket(data[sync_pos:])
            total_length = packet.get_total_length()
            
            if sync_pos + total_length <= len(data):
                packets.append(packet)
                current_pos = sync_pos + total_length
            else:
                current_pos = sync_pos + 8
            
        except Exception as e:
            print(f"Error parsing packet at position {sync_pos}: {e}")
            current_pos = sync_pos + 8
    
    return packets

def main():
    input_file = 'raw_1onuTCONT1.gpon'
    #input_file = 'raw_16onus.gpon'  
    input_file = 'raw_1onuTCONT1MAXBW.gpon'  
    packets = extract_packets(input_file)
    
    print(f"Found {len(packets)} packets")
    for i, packet in enumerate(packets, 1):
        print(f"\nPacket {i}:")
        print(packet)

if __name__ == "__main__":
    main()
