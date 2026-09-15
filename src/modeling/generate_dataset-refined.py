import numpy as np
import pandas as pd

def generate_bms_dataset(n_samples=10000, random_state=42):
    np.random.seed(random_state)
    
    # ---------------------------------------------------------
    # 1. Class Ratios: 40% Healthy, 40% Moderate, 20% Severe
    # ---------------------------------------------------------
    n_healthy = int(n_samples * 0.40)
    n_moderate = int(n_samples * 0.40)
    n_severe = n_samples - n_healthy - n_moderate
    
    data_list = []

    def generate_batch(count, regime):
        batch = {}
        
        if regime == 'healthy':
            soh = np.random.uniform(85.0, 100.0, count)
            rul = np.random.uniform(600, 1000, count)
            dc_ir = np.random.uniform(0.010, 0.045, count) # 10 to 45 mOhm
            duration_s = np.random.uniform(300, 15000, count)
            i_mean = np.random.uniform(0.2, 3.0, count)
            imbalance_v = np.random.uniform(0.005, 0.030, count)
            t_start = np.random.uniform(15.0, 30.0, count)
            
        elif regime == 'moderate':
            soh = np.random.uniform(45.0, 84.9, count)
            rul = np.random.uniform(150, 599, count)
            dc_ir = np.random.uniform(0.045, 0.180, count) # 45 to 180 mOhm
            duration_s = np.random.uniform(60, 10000, count)
            i_mean = np.random.uniform(0.1, 4.0, count)
            imbalance_v = np.random.uniform(0.030, 0.150, count)
            t_start = np.random.uniform(10.0, 38.0, count)
            
        else: # severe collapse / abuse
            soh = np.random.uniform(0.0, 44.9, count)
            rul = np.random.uniform(0, 149, count)
            dc_ir = np.random.uniform(0.180, 0.500, count) # 180 to 500 mOhm
            duration_s = np.random.uniform(10, 3600, count) # Short fast drops
            i_mean = np.random.uniform(0.05, 5.0, count)
            imbalance_v = np.random.uniform(0.150, 1.200, count) # Severe imbalance
            t_start = np.random.uniform(5.0, 45.0, count)

        # ---------------------------------------------------------
        # 2. Enforce Real-World Physical Feature Coupling
        # ---------------------------------------------------------
        v_start = np.random.uniform(11.0, 12.60, count)
        
        # Voltage drop coupled to Ohmic drop (I * R) + Polarization drop
        v_drop_ohmic = i_mean * dc_ir
        v_drop_total = v_drop_ohmic + np.random.uniform(0.2, 2.5, count)
        v_end = np.clip(v_start - v_drop_total, 7.00, 12.60)
        v_drop = v_start - v_end
        
        # Cell voltages (3S configuration)
        v_mean = np.clip((v_start + v_end) / 2.0 / 3.0, 2.50, 4.20)
        v_min = np.clip(v_mean - (imbalance_v / 2.0), 2.00, 4.20)
        v_max = np.clip(v_mean + (imbalance_v / 2.0), 3.00, 4.25)
        
        # Joule Heating (P = I^2 * R) scaled over duration
        joule_heat = (i_mean ** 2) * dc_ir * (duration_s / 3600.0) * 15.0
        temp_rise = np.clip(joule_heat + np.random.normal(0, 0.5, count), -2.0, 30.0)
        t_end = np.clip(t_start + temp_rise, 10.0, 65.0)
        t_max = np.clip(t_end + np.random.uniform(0.0, 3.0, count), 10.0, 65.0)
        t_min = np.clip(t_start - np.random.uniform(0.0, 1.0, count), 5.0, 45.0)
        t_mean = (t_start + t_end) / 2.0
        
        # Energy coupling: Wh = V_pack_mean * I_mean * Hours
        pack_v_mean = v_mean * 3.0
        energy_wh = np.clip((pack_v_mean * i_mean * (duration_s / 3600.0)) + np.random.normal(0, 0.05, count), 0.1, 50.0)
        
        # Rates of change and statistical dispersion
        dv_dt = np.clip((-v_drop / np.maximum(duration_s, 1.0)) + np.random.normal(0, 0.0005, count), -0.0200, 0.0050)
        dt_dt = np.clip((temp_rise / np.maximum(duration_s, 1.0)) + np.random.normal(0, 0.0005, count), -0.005, 0.080)
        
        v_std = np.clip(imbalance_v / 2.0, 0.00, 1.50)
        v_skew = np.clip(np.random.normal(0, 0.8, count), -3.00, 3.00)
        
        i_min = np.clip(i_mean - np.random.uniform(0.0, i_mean), 0.00, 4.00)
        i_max = np.clip(i_mean + np.random.uniform(0.0, 1.5), 0.10, 6.00)
        di_dt = np.random.normal(0, 0.005, count)
        temp_std = np.clip(np.random.uniform(0.0, 1.0, count) * (temp_rise / 10.0), 0.00, 3.50)

        # ---------------------------------------------------------
        # 3. Assemble Feature Array (Index 0 to 22)
        # ---------------------------------------------------------
        batch['DURATION_S'] = duration_s
        batch['V_START'] = v_start
        batch['V_END'] = v_end
        batch['V_MIN'] = v_min
        batch['V_MAX'] = v_max
        batch['V_MEAN'] = v_mean
        batch['V_DROP'] = v_drop
        batch['VOLTAGE_SLOPE'] = dv_dt
        batch['V_STD'] = v_std
        batch['V_SKEW'] = v_skew
        batch['I_MEAN'] = i_mean
        batch['I_MIN'] = i_min
        batch['I_MAX'] = i_max
        batch['T_START'] = t_start
        batch['T_END'] = t_end
        batch['T_MIN'] = t_min
        batch['T_MAX'] = t_max
        batch['T_MEAN'] = t_mean
        batch['TEMP_RISE'] = temp_rise
        batch['TEMP_RISE_RATE'] = dt_dt
        batch['TEMP_STD'] = temp_std
        batch['DC_IR'] = dc_ir
        batch['ENERGY_WH'] = energy_wh
        
        # Target Labels
        batch['Target_SoH'] = soh
        batch['Target_RUL'] = np.clip(rul, 0, 1000) # RUL Ceiling Clamp at 1000
        
        return pd.DataFrame(batch)

    df_healthy = generate_batch(n_healthy, 'healthy')
    df_moderate = generate_batch(n_moderate, 'moderate')
    df_severe = generate_batch(n_severe, 'severe')

    full_df = pd.concat([df_healthy, df_moderate, df_severe], ignore_index=True)
    full_df = full_df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    
    # ---------------------------------------------------------
    # 4. Division-by-Zero Guard for C++ Scalers
    # ---------------------------------------------------------
    feature_cols = [c for c in full_df.columns if not c.startswith('Target_')]
    for col in feature_cols:
        std_val = full_df[col].std()
        assert std_val > 1e-5, f"CRITICAL: Feature {col} has zero variance! Scale division by zero will occur on ESP32."

    return full_df

if __name__ == "__main__":
    df = generate_bms_dataset(n_samples=10000)
    df.to_csv("models/bms_train_set.csv", index=False)
    print(f"Success: Generated {len(df)} samples with 23 coupled features.")
    print(f"Target SoH Range: {df['Target_SoH'].min():.2f}% to {df['Target_SoH'].max():.2f}%")
    print(f"Target RUL Range: {df['Target_RUL'].min():.0f} to {df['Target_RUL'].max():.0f} cycles")
