import joblib
import m2cgen as m2c
import os

# Ensure target directory exists
os.makedirs('firmware/esp32', exist_ok=True)

# Load your trained RUL Random Forest model
model_path = 'models/rul_random_forest.pkl'
print(f"Loading RUL model from {model_path}...")
rul_model = joblib.load(model_path)

print("Converting Random Forest trees to native C code (this may take a few seconds)...")
# Generate C code for the model
code = m2c.export_to_c(rul_model)

# Save it as a header file for the ESP32
output_path = 'firmware/esp32/rul_model.h'
with open(output_path, 'w') as f:
    f.write("#ifndef RUL_MODEL_H\n#define RUL_MODEL_H\n\n")
    f.write(code)
    f.write("\n\n#endif // RUL_MODEL_H\n")

print(f"Exported {output_path} successfully!")
