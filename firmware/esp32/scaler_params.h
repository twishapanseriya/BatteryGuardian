#ifndef SCALER_PARAMS_H
#define SCALER_PARAMS_H

// Number of hardware features extracted per cycle
#define NUM_HARDWARE_FEATURES 23

// Feature Array Indices
enum FeatureIndex {
    IDX_DURATION_S = 0,
    IDX_V_START = 1,
    IDX_V_END = 2,
    IDX_V_MIN = 3,
    IDX_V_MAX = 4,
    IDX_V_MEAN = 5,
    IDX_V_DROP = 6,
    IDX_V_STD = 7,
    IDX_VOLTAGE_SLOPE = 8,
    IDX_V_SKEW = 9,
    IDX_DC_IR = 10,
    IDX_I_MEAN = 11,
    IDX_I_MIN = 12,
    IDX_I_MAX = 13,
    IDX_T_START = 14,
    IDX_T_END = 15,
    IDX_T_MIN = 16,
    IDX_T_MAX = 17,
    IDX_T_MEAN = 18,
    IDX_TEMP_RISE = 19,
    IDX_TEMP_RISE_RATE = 20,
    IDX_TEMP_STD = 21,
    IDX_ENERGY_WH = 22
};

// StandardScaler Macro Definitions: z = (x - mean) / std
#define SCALE_DURATION_S(x)           (((float)(x) - (3129.523869f)) / (245.919191f))
#define SCALE_V_START(x)              (((float)(x) - (4.188906f)) / (0.008830f))
#define SCALE_V_END(x)                (((float)(x) - (3.388244f)) / (0.342185f))
#define SCALE_V_MIN(x)                (((float)(x) - (2.532358f)) / (0.130671f))
#define SCALE_V_MAX(x)                (((float)(x) - (4.188970f)) / (0.008785f))
#define SCALE_V_MEAN(x)               (((float)(x) - (3.490245f)) / (0.054828f))
#define SCALE_V_DROP(x)               (((float)(x) - (1.656550f)) / (0.123844f))
#define SCALE_V_STD(x)                (((float)(x) - (0.236506f)) / (0.009430f))
#define SCALE_VOLTAGE_SLOPE(x)        (((float)(x) - (0.000251f)) / (0.000086f))
#define SCALE_V_SKEW(x)               (((float)(x) - (-0.550564f)) / (0.250342f))
#define SCALE_DC_IR(x)                (((float)(x) - (0.108288f)) / (0.010647f))
#define SCALE_I_MEAN(x)               (((float)(x) - (-1.795647f)) / (0.116866f))
#define SCALE_I_MIN(x)                (((float)(x) - (-2.016679f)) / (0.002710f))
#define SCALE_I_MAX(x)                (((float)(x) - (0.001850f)) / (0.001649f))
#define SCALE_T_START(x)              (((float)(x) - (24.207708f)) / (0.458732f))
#define SCALE_T_END(x)                (((float)(x) - (35.520208f)) / (1.467743f))
#define SCALE_T_MIN(x)                (((float)(x) - (24.204732f)) / (0.458165f))
#define SCALE_T_MAX(x)                (((float)(x) - (39.856994f)) / (1.261407f))
#define SCALE_T_MEAN(x)               (((float)(x) - (32.791964f)) / (0.857476f))
#define SCALE_TEMP_RISE(x)            (((float)(x) - (15.649167f)) / (1.222228f))
#define SCALE_TEMP_RISE_RATE(x)       (((float)(x) - (0.005059f)) / (0.000757f))
#define SCALE_TEMP_STD(x)             (((float)(x) - (3.927295f)) / (0.411475f))
#define SCALE_ENERGY_WH(x)            (((float)(x) - (5.482469f)) / (0.864934f))

// Standardize raw feature array into scaled buffer
inline void normalize_features(const float raw[NUM_HARDWARE_FEATURES], float scaled[NUM_HARDWARE_FEATURES]) {
    scaled[IDX_DURATION_S]     = SCALE_DURATION_S(raw[IDX_DURATION_S]);
    scaled[IDX_V_START]        = SCALE_V_START(raw[IDX_V_START]);
    scaled[IDX_V_END]          = SCALE_V_END(raw[IDX_V_END]);
    scaled[IDX_V_MIN]          = SCALE_V_MIN(raw[IDX_V_MIN]);
    scaled[IDX_V_MAX]          = SCALE_V_MAX(raw[IDX_V_MAX]);
    scaled[IDX_V_MEAN]         = SCALE_V_MEAN(raw[IDX_V_MEAN]);
    scaled[IDX_V_DROP]         = SCALE_V_DROP(raw[IDX_V_DROP]);
    scaled[IDX_V_STD]          = SCALE_V_STD(raw[IDX_V_STD]);
    scaled[IDX_VOLTAGE_SLOPE]  = SCALE_VOLTAGE_SLOPE(raw[IDX_VOLTAGE_SLOPE]);
    scaled[IDX_V_SKEW]         = SCALE_V_SKEW(raw[IDX_V_SKEW]);
    scaled[IDX_DC_IR]          = SCALE_DC_IR(raw[IDX_DC_IR]);
    scaled[IDX_I_MEAN]         = SCALE_I_MEAN(raw[IDX_I_MEAN]);
    scaled[IDX_I_MIN]          = SCALE_I_MIN(raw[IDX_I_MIN]);
    scaled[IDX_I_MAX]          = SCALE_I_MAX(raw[IDX_I_MAX]);
    scaled[IDX_T_START]        = SCALE_T_START(raw[IDX_T_START]);
    scaled[IDX_T_END]          = SCALE_T_END(raw[IDX_T_END]);
    scaled[IDX_T_MIN]          = SCALE_T_MIN(raw[IDX_T_MIN]);
    scaled[IDX_T_MAX]          = SCALE_T_MAX(raw[IDX_T_MAX]);
    scaled[IDX_T_MEAN]         = SCALE_T_MEAN(raw[IDX_T_MEAN]);
    scaled[IDX_TEMP_RISE]      = SCALE_TEMP_RISE(raw[IDX_TEMP_RISE]);
    scaled[IDX_TEMP_RISE_RATE] = SCALE_TEMP_RISE_RATE(raw[IDX_TEMP_RISE_RATE]);
    scaled[IDX_TEMP_STD]       = SCALE_TEMP_STD(raw[IDX_TEMP_STD]);
    scaled[IDX_ENERGY_WH]      = SCALE_ENERGY_WH(raw[IDX_ENERGY_WH]);
}

#endif // SCALER_PARAMS_H
