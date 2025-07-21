import matplotlib.pyplot as plt
from gpon_parser import extract_packets
import numpy as np
import argparse
import os

N_PACKETS = 50
PACKET_WINDOW = 19440
MICROSEC_PER_PACKET = 125  # each packet window is 125 microseconds

MIN_WIDTH_FOR_TEXT = 5  # mínimo ancho en microsegundos para mostrar texto horizontal
MIN_WIDTH_FOR_ROTATED_TEXT = 2  # mínimo ancho para mostrar texto rotado

MIN_HEIGHT = 0.7
MAX_HEIGHT = 1.0
TOTAL_HEIGHT_RANGE = MAX_HEIGHT - MIN_HEIGHT

# Agregar nuevas constantes para posiciones de texto
TEXT_POSITION_LOW_ID = 0.25  # posición para IDs < 255
TEXT_POSITION_HIGH_ID = 0.75  # posición para IDs >= 255

def time_units_to_microsec(time_units):
    return (time_units * MICROSEC_PER_PACKET) / PACKET_WINDOW

def create_timeline_view(input_file, num_packets=N_PACKETS):
    all_packets = extract_packets(input_file)   
    packets = all_packets[:num_packets]
    
    if not packets:
        print("No packets found!")
        return

    print(f"Processing {len(packets)} packets")
    
    # Create figure
    total_width = num_packets * PACKET_WINDOW
    fig_width = min(30, max(15, num_packets))
    fig, ax = plt.subplots(figsize=(fig_width, 6))
    
    # Create color map for unique alloc_ids
    unique_alloc_ids = set()
    for packet in packets:
        for alloc in packet.allocations:
            unique_alloc_ids.add(alloc.alloc_id)
    
    colors = plt.cm.tab20(np.linspace(0, 1, len(unique_alloc_ids)))
    alloc_id_colors = dict(zip(sorted(unique_alloc_ids), colors))
    
    # Create height map for alloc_ids
    heights = {}
    for idx, alloc_id in enumerate(sorted(unique_alloc_ids)):
        # Distribuir alturas uniformemente entre MIN_HEIGHT y MAX_HEIGHT
        height = MIN_HEIGHT + (TOTAL_HEIGHT_RANGE * (idx / max(1, len(unique_alloc_ids) - 1)))
        heights[alloc_id] = height

    # Plot allocations
    for packet_idx, packet in enumerate(packets):
        base_x = packet_idx * PACKET_WINDOW
        base_x_us = time_units_to_microsec(base_x)
        
        # Add vertical line to separate packets
        ax.axvline(x=base_x_us, color='gray', linestyle='--', alpha=0.3)
        
        for alloc in packet.allocations:
            if not (0 <= alloc.start_time <= alloc.stop_time):
                print(f"Invalid timing: Start={alloc.start_time}, Stop={alloc.stop_time}")
                continue
            
            width = alloc.stop_time - alloc.start_time
            if width <= 0:
                print(f"Invalid width for Alloc-ID {alloc.alloc_id}")
                continue
            
            # Convert positions to microseconds
            start_us = time_units_to_microsec(base_x + alloc.start_time)
            width_us = time_units_to_microsec(width)
            height = heights[alloc.alloc_id]
            
            # Crear rectángulo empezando desde y=0
            rect = plt.Rectangle(
                (start_us, 0),  # (x, y) - ahora siempre empieza en y=0
                width_us, height,  # width, height
                facecolor=alloc_id_colors[alloc.alloc_id],
                alpha=0.7
            )
            ax.add_patch(rect)
            
            # Centro del allocation
            center_x_us = start_us + width_us/2
            
            # Decidir cómo mostrar el texto basado en el ancho y el alloc_id
            if width_us >= MIN_WIDTH_FOR_TEXT:
                # Texto horizontal con posición basada en el alloc_id
                text_y = TEXT_POSITION_LOW_ID * height if alloc.alloc_id < 255 else TEXT_POSITION_HIGH_ID * height
                ax.text(center_x_us, text_y,
                       f'ID:{alloc.alloc_id}',
                       ha='center', va='center',
                       fontsize=9, fontweight='bold',
                       color='black')
            elif width_us >= MIN_WIDTH_FOR_ROTATED_TEXT:
                # Texto rotado con posición basada en el alloc_id
                text_y = TEXT_POSITION_LOW_ID * height if alloc.alloc_id < 255 else TEXT_POSITION_HIGH_ID * height
                ax.text(center_x_us, text_y,
                       f'ID:{alloc.alloc_id}',
                       ha='center', va='center',
                       fontsize=8, fontweight='bold',
                       color='black',
                       rotation=90)
            else:
                # Para allocations muy angostos, mostrar arriba o abajo según el ID
                if alloc.alloc_id < 255:
                    text_y = -0.05  # debajo del rectángulo
                    va_align = 'top'
                else:
                    text_y = MAX_HEIGHT + 0.05  # arriba del rectángulo
                    va_align = 'bottom'
                    
                ax.text(center_x_us, text_y,
                       f'ID:{alloc.alloc_id}',
                       ha='center', va=va_align,
                       fontsize=7, fontweight='bold',
                       color=alloc_id_colors[alloc.alloc_id])
    
    # Modificar la leyenda para mostrar las alturas correctas
    legend_elements = [plt.Rectangle((0,0), 1, heights[alloc_id], facecolor=color, alpha=0.7,
                                   label=f'Alloc-ID: {alloc_id}')
                      for alloc_id, color in alloc_id_colors.items()]
    ax.legend(handles=legend_elements, loc='upper right',
             bbox_to_anchor=(1.15, 1), title='Allocation IDs')

    # Set axis limits and labels in microseconds
    total_width_us = time_units_to_microsec(total_width)
    ax.set_xlim(-total_width_us*0.05, total_width_us*1.05)
    
    # Ajustar límites Y para dar espacio a ambas etiquetas (arriba y abajo)
    ax.set_ylim(-0.2, MAX_HEIGHT + 0.2)  # dar espacio extra arriba para etiquetas
    
    # X axis configuration
    ax.set_xlabel('Time (μs)')
    
    # Add major ticks every 125 microseconds (packet boundary)
    major_ticks = np.arange(0, total_width_us + 125, 125)
    ax.set_xticks(major_ticks)
    
    # Add minor ticks every 25 microseconds
    minor_ticks = np.arange(0, total_width_us + 25, 25)
    ax.set_xticks(minor_ticks, minor=True)
    
    # Remove y-axis ticks since height is fixed
    ax.set_yticks([])
    
    ax.set_title('GPON Bandwidth Map (Timeline View)')
    
    # Add grid for major and minor ticks
    ax.grid(True, which='major', linestyle='-', alpha=0.7)
    ax.grid(True, which='minor', linestyle=':', alpha=0.4)
    
    plt.tight_layout()
    plt.savefig('bwmap_timeline_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

def create_timing_grid(input_file, num_packets=N_PACKETS):
    all_packets = extract_packets(input_file)   
    packets = all_packets[:num_packets]
    
    if not packets:
        print("No packets found!")
        return
        
    print(f"Processing {len(packets)} packets")
    
    # Debug info for timing values
    min_start = float('inf')
    max_stop = 0
    for i, packet in enumerate(packets):
        if not packet.allocations:
            print(f"Warning: Packet {i+1} has no allocations")
            continue
            
        for alloc in packet.allocations:
            print(f"Packet {i+1}, Alloc-ID {alloc.alloc_id}: "
                  f"Start={alloc.start_time}, Stop={alloc.stop_time}")
            min_start = min(min_start, alloc.start_time)
            max_stop = max(max_stop, alloc.stop_time)
    
    print(f"Time range: {min_start} to {max_stop}")
    
    # Adjust figure size more conservatively
    fig_width = min(30, max(15, num_packets))  # Limit max width
    fig, ax = plt.subplots(figsize=(fig_width, 12))
    
    # Create color map for unique alloc_ids
    unique_alloc_ids = set()
    for packet in packets:
        for alloc in packet.allocations:
            unique_alloc_ids.add(alloc.alloc_id)
    
    # Create a color map using a different colormap (you can try 'tab20', 'Set3', 'Paired', etc)
    colors = plt.cm.tab20(np.linspace(0, 1, len(unique_alloc_ids)))
    alloc_id_colors = dict(zip(sorted(unique_alloc_ids), colors))
    
    # Plot allocations with error checking and unique colors
    for packet_idx, packet in enumerate(packets):
        if packet_idx >= num_packets:
            break
            
        for alloc in packet.allocations:
            if not (0 <= alloc.start_time <= alloc.stop_time):
                print(f"Invalid timing: Start={alloc.start_time}, Stop={alloc.stop_time}")
                continue
                
            height = alloc.stop_time - alloc.start_time
            if height <= 0:
                print(f"Invalid height for Alloc-ID {alloc.alloc_id}")
                continue
                
            # Use the color associated with this alloc_id
            rect = plt.Rectangle(
                (packet_idx - 0.4, alloc.start_time),
                0.8, height,
                facecolor=alloc_id_colors[alloc.alloc_id],
                alpha=0.7
            )
            ax.add_patch(rect)
            
            center_y = (alloc.start_time + alloc.stop_time) / 2
            ax.text(packet_idx, center_y,
                   f'ID:{alloc.alloc_id}',
                   ha='center', va='center',
                   fontsize=9, fontweight='bold',
                   color='black')
    
    # Add legend
    legend_elements = [plt.Rectangle((0,0),1,1, facecolor=color, alpha=0.7, 
                                   label=f'Alloc-ID: {alloc_id}')
                      for alloc_id, color in alloc_id_colors.items()]
    ax.legend(handles=legend_elements, loc='upper right', 
             bbox_to_anchor=(1.15, 1), title='Allocation IDs')

    # Ensure axis limits are set correctly
    ax.set_xlim(-0.5, num_packets - 0.5)
    y_padding = (max_stop - min_start) * 0.1  # 10% padding
    ax.set_ylim(min_start - y_padding, max_stop + y_padding)
    
    # X axis configuration for dynamic packet count
    ax.set_xticks(range(num_packets))
    ax.set_xticklabels([f'{i+1}' for i in range(num_packets)])
    ax.set_xlabel('NºPckt')
    
    # Y axis configuration
    ax.set_ylabel('Time Units')
    ax.set_title('GPON Bandwidth Map')
    
    # Add grid for better readability
    ax.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig('bwmap_timing_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

def main():
    parser = argparse.ArgumentParser(description='Analyze GPON bandwidth map from raw capture file.')
    parser.add_argument('input_file', help='Name of the raw.gpon file in raw_captures directory')
    parser.add_argument('-n', '--num_packets', type=int, default=N_PACKETS,
                        help=f'Number of packets to analyze (default: {N_PACKETS})')
    parser.add_argument('-t', '--type', type=int, choices=[0, 1], default=0,
                        help='Visualization type: 0=vertical view, 1=timeline view')

    args = parser.parse_args()

    input_path = os.path.join('raw_captures', args.input_file)
    
    if not os.path.exists(input_path):
        print(f"Error: File {input_path} not found!")
        return

    if args.type == 0:
        create_timing_grid(input_path, args.num_packets)
    else:
        create_timeline_view(input_path, args.num_packets)

if __name__ == "__main__":
    main()
