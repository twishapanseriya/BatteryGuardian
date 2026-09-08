#ifndef MODEL_INFERENCE_H
#define MODEL_INFERENCE_H

#include "scaler_params.h"
#include "model_weights.h"

// Predict State of Health (SoH %) from raw 23 hardware features
inline float predict_soh_pct(const float raw_features[NUM_HARDWARE_FEATURES]) {
    float scaled_features[NUM_HARDWARE_FEATURES];
    
    // 1. On-device standardization
    normalize_features(raw_features, scaled_features);
    
    // 2. Linear combination: y = intercept + sum(w_i * x_i)
    float soh_pred = RIDGE_INTERCEPT;
    for (int i = 0; i < NUM_HARDWARE_FEATURES; i++) {
        soh_pred += RIDGE_COEFFS[i] * scaled_features[i];
    }
    
    // Clamping output between 0% and 100%
    if (soh_pred > 100.0f) soh_pred = 100.0f;
    if (soh_pred < 0.0f)   soh_pred = 0.0f;
    
    return soh_pred;
}

#endif // MODEL_INFERENCE_H
