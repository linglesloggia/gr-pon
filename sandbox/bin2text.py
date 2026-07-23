def binary_to_bitstring(input_filename, output_filename):
    with open(input_filename, 'rb') as f_in, open(output_filename, 'w') as f_out:
        while (byte := f_in.read(1)):
            bits = format(byte[0], '08b')  # convierte a 8 bits
            f_out.write(bits)

    print(f"✅ Archivo de texto generado: {output_filename}")


if __name__ == '__main__':
    print("📂 Ruta del archivo binario de entrada:")
    input_file = input().strip()

    output_file = f"{input_file}_bits.txt"

    binary_to_bitstring(input_file, output_file)