# Save as: src/modeling/export_model_weights.py
import joblib
import numpy as np
import os

# Ensure target directories exist
os.makedirs('firmware/esp32', exist_ok=True)

# Load trained Ridge SoH model (adjust filename if yours differs slightly)
model_path = 'models/soh_linear_baseline.pkl'
if not os.path.exists(model_path):
    # Fallback search or check common naming
    print(f"Warning: {model_path} not found. Checking current directory...")
    
soh_model = joblib.load(model_path)

print("Loaded model successfully!")
print("Ridge Intercept:", soh_model.intercept_)
print("Ridge Coefficients count:", len(soh_model.coef_))

# Export Ridge weights to a C Header file for the ESP32
with open('firmware/esp32/model_weights.h', 'w') as f:
    f.write("#ifndef MODEL_WEIGHTS_H\n#define MODEL_WEIGHTS_H\n\n")
    f.write(f"const float RIDGE_INTERCEPT = {soh_model.intercept_:.6f}f;\n\n")
    f.write("const float RIDGE_COEFFS[23] = {\n")
    for coef in soh_model.coef_:
        f.write(f"    {coef:.6f}f,\n")
    f.write("};\n\n#endif // MODEL_WEIGHTS_H\n")

print("Exported firmware/esp32/model_weights.h successfully!")

