import pandas as pd

# Leer el archivo CSV como texto plano para detectar los bloques de captura
with open("../examples/gpon.csv", "r") as f:
    lines = f.readlines()

alloc_bytes = {}
num_captures = 0

i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith("Capture "):
        num_captures += 1
        # Buscar el siguiente bloque de datos (3 líneas: encabezados + datos)
        header1 = lines[i+1].strip()
        header2 = lines[i+2].strip()
        i += 3
        # Leer filas de datos hasta encontrar una línea vacía o el final
        data_rows = []
        while i < len(lines) and lines[i].strip():
            data_rows.append(lines[i].strip())
            i += 1
        # Crear DataFrame temporal para este bloque
        if data_rows:
            # Unir encabezados para MultiIndex
            from io import StringIO
            csv_block = header1 + "\n" + header2 + "\n" + "\n".join(data_rows)
            df = pd.read_csv(StringIO(csv_block), header=[0,1])
            # Procesar filas
            for _, row in df.iterrows():
                try:
                    alloc_id = int(row[("alloc", "alloc_id")])
                    start_val = int(row[("alloc", "start")])
                    stop_val = int(row[("alloc", "stop")])
                    bytes_assigned = stop_val - start_val
                    if alloc_id not in alloc_bytes:
                        alloc_bytes[alloc_id] = 0
                    alloc_bytes[alloc_id] += bytes_assigned
                except Exception:
                    continue
    else:
        i += 1

# Imprimir resultados
print("Tasa por alloc_id (bytes/s y bps):")
for alloc_id, total_bytes in alloc_bytes.items():
    # 125e-6 s por paquete, num_captures paquetes
    rate_bytes_per_s = total_bytes / (num_captures * 125e-6)
    rate_bits_per_s = rate_bytes_per_s * 8
    print(f"alloc_id={alloc_id}: {rate_bytes_per_s:.2f} bytes/s, {rate_bits_per_s:.2f} bps (total_bytes={total_bytes}, capturas={num_captures})")