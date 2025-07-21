import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import glob
import time

class GPONDemodulator:
    def __init__(self, samples_per_bit=2, invert_signal=True, fixed_threshold=0.4):
        self.samples_per_bit = samples_per_bit
        self.bit_rate = 1.25e9  # GPON upstream rate
        self.invert_signal = invert_signal
        self.fixed_threshold = fixed_threshold
        self.use_fixed_threshold = True  # Usar umbral fijo en lugar de K-means
    
    def normalize_signal(self, signal):
        """Normaliza la señal entre -1 y 1"""
        normalized = (signal - np.mean(signal)) / (np.max(np.abs(signal)) * 1.1)
        return -normalized if self.invert_signal else normalized

    def find_threshold(self, signal):
        """Encuentra el umbral óptimo usando valor fijo o K-means"""
        if self.use_fixed_threshold:
            return self.fixed_threshold
        else:
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=2, random_state=0).fit(signal.reshape(-1, 1))
            return np.mean(kmeans.cluster_centers_)

    def clock_recovery(self, signal, samples):
        """Recupera el reloj y encuentra el mejor punto de muestreo"""
        # Calcular la energía para diferentes offsets
        energy = []
        for i in range(self.samples_per_bit):
            # Tomar muestras cada samples_per_bit comenzando en i
            sampled = signal[i::self.samples_per_bit]
            # La energía será mayor cuando muestreemos en el centro del bit
            energy.append(np.sum(np.abs(sampled)))  # Usar valores absolutos para evitar sesgo por ceros iniciales
        
        # El mejor offset es el que da la mayor energía
        best_offset = np.argmax(energy)
        return best_offset

    def sync_to_frame(self, signal, pattern="01010101"):
        """Sincroniza la señal al inicio de una trama buscando un patrón binario"""
        # Convertir el patrón a valores binarios
        pattern_bits = np.array([int(b) for b in pattern], dtype=bool)
        pattern_length = len(pattern_bits)
        
        # Buscar el patrón en la señal
        for i in range(len(signal) - pattern_length):
            if np.array_equal(signal[i:i+pattern_length], pattern_bits):
                print(f"Patrón encontrado en el índice: {i}")
                return signal[i:]  # Recortar la señal desde el inicio del patrón
        
        print("Patrón no encontrado, usando señal completa.")
        return signal  # Si no se encuentra el patrón, usar la señal completa

    def demodulate(self, filename):
        """Demodula una señal GPON desde un archivo CSV"""
        # Cargar datos
        data = np.loadtxt(filename, delimiter=',', skiprows=1)
        tiempo = data[:,0]
        voltaje = data[:,1]
        
        # Normalizar señal
        signal_norm = self.normalize_signal(voltaje)
        
        # Sincronizar al inicio de la trama
        signal_sync = self.sync_to_frame(signal_norm > self.fixed_threshold)
        
        # Encontrar umbral
        threshold = self.find_threshold(signal_sync)
        
        # Recuperación de reloj
        best_offset = self.clock_recovery(signal_sync, self.samples_per_bit)
        
        # Muestreo en los puntos óptimos
        bits = signal_sync[best_offset::self.samples_per_bit] > threshold
        
        # Calcular tiempo por bit
        tiempo_por_bit = (tiempo[-1] - tiempo[0]) / (len(bits))
        print(f"Tiempo por bit: {tiempo_por_bit*1e9:.2f} ns")
        
        return bits, tiempo, signal_sync, threshold

    def save_bits(self, bits, filename_base):
        """Guarda los bits en varios formatos"""
        # Convertir bits a bytes
        bits_array = np.packbits(bits)
        
        # Guardar en archivo binario
        bin_filename = f"{filename_base}.bin"
        bits_array.tofile(bin_filename)
        
        # Guardar vista hexadecimal en archivo de texto
        hex_filename = f"{filename_base}.hex"
        with open(hex_filename, 'w') as f:
            # Escribir cabecera
            f.write(f"Total bits: {len(bits)}\n")
            f.write(f"Total bytes: {len(bits_array)}\n")
            f.write("Offset    Hexadecimal                                 ASCII\n")
            f.write("-" * 70 + "\n")
            
            # Escribir datos en formato hexdump
            for i in range(0, len(bits_array), 16):
                # Obtener chunk de 16 bytes
                chunk = bits_array[i:i+16]
                
                # Escribir offset
                f.write(f"{i:08x}  ")
                
                # Escribir hexadecimal
                hex_values = [f"{b:02x}" for b in chunk]
                f.write(" ".join(hex_values))
                f.write(" " * (3 * (16 - len(chunk))))  # Padding
                
                # Escribir ASCII (si es printable)
                f.write("  ")
                for b in chunk:
                    if 32 <= b <= 126:  # Caracteres imprimibles ASCII
                        f.write(chr(b))
                    else:
                        f.write('.')
                f.write('\n')
        
        print(f"\nArchivos guardados:")
        print(f"- Binario: {bin_filename}")
        print(f"- Hexadecimal: {hex_filename}")
        
        return bin_filename, hex_filename

    def plot_results(self, bits, tiempo, signal_norm, threshold):
        """Visualiza los resultados de la demodulación"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Plot señal normalizada
        ax1.plot(tiempo*1e6, signal_norm, 'b-', label='Señal normalizada')
        ax1.axhline(y=threshold, color='r', linestyle='--', label='Umbral')
        ax1.set_xlabel('Tiempo (μs)')
        ax1.set_ylabel('Amplitud normalizada')
        ax1.grid(True)
        ax1.legend()
        
        # Plot bits demodulados
        tiempo_bits = np.linspace(tiempo[0], tiempo[-1], len(bits))
        ax2.step(tiempo_bits*1e6, bits, 'g-', label='Bits demodulados', where='post')
        ax2.set_xlabel('Tiempo (μs)')
        ax2.set_ylabel('Bit')
        ax2.grid(True)
        ax2.set_ylim(-0.2, 1.2)
        ax2.legend()
        
        plt.tight_layout()
        return fig

def main():
    # Encontrar el archivo más reciente
    files = glob.glob('captura_pon_us_*.csv')
    if not files:
        print("No se encontraron archivos de captura PON")
        return
    filename = max(files, key=lambda x: Path(x).stat().st_mtime)
    
    # Crear demodulador con umbral fijo de 0.4
    demod = GPONDemodulator(samples_per_bit=2, invert_signal=True, fixed_threshold=0.4)
    
    # Demodular
    bits, tiempo, signal_norm, threshold = demod.demodulate(filename)
    
    # Guardar bits en archivos
    base_filename = f'bits_pon_us_{time.strftime("%Y%m%d_%H%M%S")}'
    bin_file, hex_file = demod.save_bits(bits, base_filename)
    
    # Análisis básico
    print(f"\nAnálisis de la trama:")
    print(f"Total de bits: {len(bits)}")
    print(f"Unos: {np.sum(bits)} ({np.sum(bits)/len(bits)*100:.1f}%)")
    print(f"Ceros: {len(bits)-np.sum(bits)} ({(1-np.sum(bits)/len(bits))*100:.1f}%)")
    
    # Buscar secuencias largas de ceros (posibles gaps)
    zero_runs = np.split(np.arange(len(bits)), np.where(bits)[0])
    max_zeros = max(len(run) for run in zero_runs)
    print(f"Secuencia más larga de ceros: {max_zeros} bits")
    
    # Visualizar
    fig = demod.plot_results(bits, tiempo, signal_norm, threshold)
    plt.show()

if __name__ == '__main__':
    main()
