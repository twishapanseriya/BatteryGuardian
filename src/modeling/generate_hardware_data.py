import csv
import random

# Set random seed for exact reproducibility
random.seed(42)

def generate_custom_hardware_dataset(num_cycles=800):
    fieldnames = [
        "DURATION_S", "V_START", "V_END", "V_MIN", "V_MAX", "V_MEAN", 
        "V_DROP", "VOLTAGE_SLOPE", "V_STD", "V_SKEW", "I_MEAN", "I_MIN", 
        "I_MAX", "T_START", "T_END", "T_MIN", "T_MAX", "T_MEAN", 
        "TEMP_RISE", "TEMP_RISE_RATE", "TEMP_STD", "DC_IR", "ENERGY_WH",
        "Target_SoH", "Target_RUL"
    ]
    
    # Baselines extracted from your ESP32 hardware screenshots
    base_ir = 0.045         # ~45mOhm total for a healthy 3S pack
    base_t_start = 22.5     # From DS18B20 screenshots (22.5C - 22.6C)
    base_i_mean = 0.73      # From INA219 screenshots (0.73A load)
    base_temp_rise = 3.5    # Temperature rise under light load
    base_capacity_wh = 40.0 # Standard energy for 3S 18650s

    with open("hardware_anchored_bms_data.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for cycle in range(num_cycles):
            # 1. Simulate Degradation (SoH goes 100% -> 60%)
            soh = 100.0 - (cycle * (40.0 / num_cycles))
            soh = max(0.0, soh + random.gauss(0, 0.5))
            rul = max(0, num_cycles - cycle)

            # 2. Physics shifts as battery degrades
            current_ir = base_ir + (cycle * 0.00015) + random.gauss(0, 0.002)
            current_temp_rise = base_temp_rise + (cycle * 0.015)
            energy_wh = base_capacity_wh * (soh / 100.0) + random.gauss(0, 0.5)

            # 3. Generate the 23 Features
            duration_s = random.uniform(10800, 14400) * (soh / 100.0)
            v_start = random.uniform(12.5, 12.6)
            v_end = random.uniform(9.0, 9.5)
            v_drop = v_start - v_end
            
            voltage_sag = base_i_mean * current_ir
            v_min = v_end - voltage_sag - random.uniform(0.05, 0.1)

            i_mean = base_i_mean + random.gauss(0, 0.05)
            i_max = i_mean + random.uniform(0.1, 0.3)
            i_min = max(0.0, i_mean - random.uniform(0.1, 0.2))

            t_start = base_t_start + random.gauss(0, 0.5)
            t_end = t_start + current_temp_rise + random.gauss(0, 0.5)
            t_max = t_end + random.uniform(0.0, 0.5)

            row = {
                "DURATION_S": round(duration_s, 2),
                "V_START": round(v_start, 3),
                "V_END": round(v_end, 3),
                "V_MIN": round(v_min, 3),
                "V_MAX": round(v_start, 3),
                "V_MEAN": round((v_start + v_end) / 2, 3),
                "V_DROP": round(v_drop, 3),
                "VOLTAGE_SLOPE": round(v_drop / max(1.0, duration_s), 6),
                "V_STD": round(random.uniform(0.8, 1.2), 3),
                "V_SKEW": round(random.uniform(-0.5, 0.5), 3),
                "I_MEAN": round(i_mean, 3),
                "I_MIN": round(i_min, 3),
                "I_MAX": round(i_max, 3),
                "T_START": round(t_start, 1),
                "T_END": round(t_end, 1),
                "T_MIN": round(t_start, 1),
                "T_MAX": round(t_max, 1),
                "T_MEAN": round((t_start + t_end) / 2, 1),
                "TEMP_RISE": round(t_max - t_start, 2),
                "TEMP_RISE_RATE": round((t_max - t_start) / max(1.0, duration_s), 6),
                "TEMP_STD": round(random.uniform(0.5, 1.5), 3),
                "DC_IR": round(current_ir, 4),
                "ENERGY_WH": round(energy_wh, 2),
                "Target_SoH": round(soh, 2),
                "Target_RUL": int(rul)
            }
            writer.writerow(row)

generate_custom_hardware_dataset(800)
print("Successfully generated hardware_anchored_bms_data.csv without pandas!")
