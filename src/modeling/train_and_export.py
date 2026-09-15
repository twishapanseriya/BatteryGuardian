import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import m2cgen as m2c

# 1. Load the training dataset
df_train = pd.read_csv("bms_train_set.csv")

feature_cols = [
    "DURATION_S", "V_START", "V_END", "V_MIN", "V_MAX", "V_MEAN", 
    "V_DROP", "VOLTAGE_SLOPE", "V_STD", "V_SKEW", "I_MEAN", "I_MIN", 
    "I_MAX", "T_START", "T_END", "T_MIN", "T_MAX", "T_MEAN", 
    "TEMP_RISE", "TEMP_RISE_RATE", "TEMP_STD", "DC_IR", "ENERGY_WH"
]

X_train = df_train[feature_cols]
y_soh_train = df_train["Target_SoH"]
y_rul_train = df_train["Target_RUL"]

# 2. Fit the Scaler (Crucial for Ridge Regression)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

# 3. Train the Models
print("Training Ridge Regression for State of Health (SoH)...")
ridge_soh = Ridge(alpha=1.0)
ridge_soh.fit(X_train_scaled, y_soh_train)

print("Training Random Forest for Remaining Useful Life (RUL)...")
# Kept n_estimators low (30) to ensure it fits safely in ESP32 flash memory without lagging
rf_rul = RandomForestRegressor(n_estimators=10, max_depth=5, random_state=42)
rf_rul.fit(X_train, y_rul_train)

# 4. Export Models to C++ Code via m2cgen
soh_c_code = m2c.export_to_c(ridge_soh, function_name="score_soh")
rul_c_code = m2c.export_to_c(rf_rul, function_name="score_rul")

# Save SoH model header
with open("models/model_weights.h", "w") as f:
    f.write("// Auto-generated Ridge Regression model for SoH\n")
    f.write(soh_c_code)

# Save RUL model header
with open("models/rul_model.h", "w") as f:
    f.write("// Auto-generated Random Forest model for RUL\n")
    f.write(rul_c_code)

# Print Scaler Means and Scales so you can drop them into your scaler_params.h file
print("\n--- COPY THESE INTO YOUR scaler_params.h ---")
print("float feature_means[] = {", ", ".join([str(round(m, 4)) for m in scaler.mean_]), "};")
print("float feature_scales[] = {", ", ".join([str(round(s, 4)) for s in scaler.scale_]), "};")
print("---------------------------------------------")
print("\nTraining complete! C++ header files saved to the models/ directory.")
