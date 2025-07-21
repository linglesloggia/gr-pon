import numpy as np
import pandas as pd

# Leer el CSV
df = pd.read_csv("captura_osc.csv")

# Extraer tiempo y voltaje
t = df["Tiempo (s)"].values
y = df["Voltaje (V)"].values

# Guardar solo los valores de voltaje (para Vector Source)
np.savetxt("voltaje_only.csv", y, delimiter=",")