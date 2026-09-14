import pandas as pd

# 1. Load your generated dataset
df = pd.read_csv("hardware_anchored_bms_data.csv")

# Separate features (X) and targets (y)
feature_cols = [
    "DURATION_S", "V_START", "V_END", "V_MIN", "V_MAX", "V_MEAN", 
    "V_DROP", "VOLTAGE_SLOPE", "V_STD", "V_SKEW", "I_MEAN", "I_MIN", 
    "I_MAX", "T_START", "T_END", "T_MIN", "T_MAX", "T_MEAN", 
    "TEMP_RISE", "TEMP_RISE_RATE", "TEMP_STD", "DC_IR", "ENERGY_WH"
]

X = df[feature_cols]
y_soh = df["Target_SoH"]
y_rul = df["Target_RUL"]

# 2. Chronological Split (No random shuffling!)
train_end = int(len(df) * 0.70)  # First 70%
val_end = int(len(df) * 0.85)    # Next 15%

# Training Set (Healthy to Mid-life)
X_train, y_soh_train, y_rul_train = X.iloc[:train_end], y_soh.iloc[:train_end], y_rul.iloc[:train_end]

# Validation Set (Mid-life to Late-life)
X_val, y_soh_val, y_rul_val = X.iloc[train_end:val_end], y_soh.iloc[train_end:val_end], y_rul.iloc[train_end:val_end]

# Test Set (End-of-life / Degradation zone)
X_test, y_soh_test, y_rul_test = X.iloc[val_end:], y_soh.iloc[val_end:], y_rul.iloc[val_end:]

print(f"Training samples: {len(X_train)}")
print(f"Validation samples: {len(X_val)}")
print(f"Test samples: {len(X_test)}")


# 3. Export the splits to individual CSV files
pd.concat([X_train, y_soh_train, y_rul_train], axis=1).to_csv("bms_train_set.csv", index=False)
pd.concat([X_val, y_soh_val, y_rul_val], axis=1).to_csv("bms_val_set.csv", index=False)
pd.concat([X_test, y_soh_test, y_rul_test], axis=1).to_csv("bms_test_set.csv", index=False)

print("Split files successfully saved to disk!")
