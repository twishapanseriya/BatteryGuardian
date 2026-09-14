import numpy as np
import pandas as pd

# Number of samples (e.g., 800 prototype rows)
n_samples = 800

# 1. Shift ambient starting temperature to simulate a hot Indian climate (35°C to 40°C)
t_start = np.random.uniform(35.0, 40.0, n_samples)

# 2. Simulate thermal rise under load (current stress adds 6°C to 12°C)
temp_rise = np.random.uniform(6.0, 12.0, n_samples)
t_end = t_start + temp_rise

# 3. Derive other thermal metrics required by your 23-feature model
t_min = t_start - np.random.uniform(0.0, 0.5, n_samples)
t_max = t_end + np.random.uniform(0.0, 1.0, n_samples)
t_mean = (t_start + t_end) / 2.0
temp_rise_rate = temp_rise / np.random.uniform(300, 3600, n_samples) # rise per second/minute window
temp_std = temp_rise / 4.0 # variance during the cycle

# Print out a check of your new thermal profile
print(f"New Simulated T_START range: {t_start.min():.1f}°C to {t_start.max():.1f}°C")
print(f"New Simulated T_MAX peak range: {t_max.min():.1f}°C to {t_max.max():.1f}°C")
