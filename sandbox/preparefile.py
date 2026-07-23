import pandas as pd
import numpy as np
import os

def write_voltage_column_as_f32(input_csv, output_file):
    # Lee el CSV ignorando la cabecera, y selecciona la segunda columna
    df = pd.read_csv(input_csv, comment='#', header=None, usecols=[1])

    # Extrae como array numpy
    voltajes = df[1].values.astype(np.float32)

    # Guarda en formato binario plano
    voltajes.tofile(output_file)

    print(f"✅ Archivo binario float32 guardado como: {output_file}")
    print(f"📏 Número de muestras: {len(voltajes)}")
    print(f"🔎 Mínimo: {voltajes.min():.6f}, Máximo: {voltajes.max():.6f}")

if __name__ == '__main__':
    print('📥 Ingresá el nombre del archivo CSV (sin la extensión):')
    filename = input().strip()

    input_csv = f'{filename}.csv'
    output_file = f'{filename}_f32.f32'

    if not os.path.exists(input_csv):
        print(f'❌ No se encontró el archivo: {input_csv}')
        exit(1)

    write_voltage_column_as_f32(input_csv, output_file)