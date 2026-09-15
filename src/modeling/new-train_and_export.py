import pandas as pd
import numpy as np
import m2cgen as m2c
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor

# 1. Load Dataset
df = pd.read_csv("models/bms_train_set.csv")

feature_cols = [
    'DURATION_S', 'V_START', 'V_END', 'V_MIN', 'V_MAX', 'V_MEAN', 'V_DROP',
    'VOLTAGE_SLOPE', 'V_STD', 'V_SKEW', 'I_MEAN', 'I_MIN', 'I_MAX',
    'T_START', 'T_END', 'T_MIN', 'T_MAX', 'T_MEAN', 'TEMP_RISE',
    'TEMP_RISE_RATE', 'TEMP_STD', 'DC_IR', 'ENERGY_WH'
]

X = df[feature_cols].values
y_soh = df['Target_SoH'].values
y_rul = df['Target_RUL'].values

# 2. Extract Scaler Parameters for ESP32
means = np.mean(X, axis=0)
scales = np.std(X, axis=0)

# Apply manual StandardScaler transformation for Ridge Regression (SoH)
X_scaled = (X - means) / scales

# 3. Train Models
print("Training Ridge Regression for SoH...")
ridge_soh = Ridge(alpha=1.0)
ridge_soh.fit(X_scaled, y_soh)

print("Training Random Forest for RUL...")
rf_rul = RandomForestRegressor(n_estimators=10, max_depth=5, random_state=42)
rf_rul.fit(X, y_rul)

# 4. Export to C Code via m2cgen
soh_c_code = m2c.export_to_c(ridge_soh, function_name="score_soh")
rul_c_code = m2c.export_to_c(rf_rul, function_name="score_rul")

with open("models/model_weights_v2.h", "w") as f:
    f.write("// Auto-generated Ridge Regression model for SoH\n")
    f.write(soh_c_code)

with open("models/rul_model_v2.h", "w") as f:
    f.write("// Auto-generated Random Forest model for RUL\n")
    f.write(rul_c_code)

# 5. Output Scaler Arrays for C++ Code
print("\n=== COPY THESE INTO YOUR ESP32 FIRMWARE (.ino) ===")
print("const float FEATURE_MEANS[23] = {")
print("  " + ", ".join([f"{m:.4f}" for m in means]))
print("};")
print("const float FEATURE_SCALES[23] = {")
print("  " + ", ".join([f"{s:.4f}" for s in scales]))
print("};")
