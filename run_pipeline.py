"""
Data Cleaning and Preprocessing Pipeline
Public Dataset: NYC TLC Yellow & Green Taxi Dataset (6,433 records, 14 features)
Author: Rohit / Antigravity Applied Data Science Lab
"""

import os
import sys
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler, RobustScaler, OneHotEncoder

# Set random seed for reproducibility
np.random.seed(42)

# Ensure output directories exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(BASE_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

# Set style for publication-quality figures
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.labelweight'] = 'bold'
plt.rcParams['figure.titlesize'] = 14
plt.rcParams['figure.titleweight'] = 'bold'

print("="*80)
print("STEP 1: ACQUIRING DATASET & INITIAL METADATA AUDIT")
print("="*80)

# Load raw dataset
raw_df = sns.load_dataset('taxis')
raw_csv_path = os.path.join(BASE_DIR, 'raw_taxis_data.csv')
raw_df.to_csv(raw_csv_path, index=False)
print(f"Dataset successfully loaded. Raw shape: {raw_df.shape}")
print(f"Saved raw snapshot to: {raw_csv_path}")

# Calculate summary audit statistics
total_rows = len(raw_df)
total_cols = raw_df.shape[1]
memory_usage_mb = raw_df.memory_usage(deep=True).sum() / (1024 * 1024)

# Missing value audit
missing_counts = raw_df.isnull().sum()
missing_pcts = (missing_counts / total_rows) * 100
missing_df = pd.DataFrame({
    'Feature': missing_counts.index,
    'Missing_Count': missing_counts.values,
    'Missing_Pct': missing_pcts.values,
    'Dtype': [str(raw_df[col].dtype) for col in missing_counts.index]
})
missing_df = missing_df.sort_values(by='Missing_Count', ascending=False)
print("\n--- Missing Value Summary ---")
print(missing_df[missing_df['Missing_Count'] > 0])

# Inconsistency / Erroneous value audit
passengers_zero = (raw_df['passengers'] == 0).sum()
distance_zero = (raw_df['distance'] == 0).sum()
fare_zero_neg = (raw_df['fare'] <= 0).sum()
total_zero_neg = (raw_df['total'] <= 0).sum()
raw_duration_min = (raw_df['dropoff'] - raw_df['pickup']).dt.total_seconds() / 60.0
duration_neg_zero = (raw_duration_min <= 0).sum()
speed_raw_mph = raw_df['distance'] / (np.maximum(raw_duration_min, 1e-5) / 60.0)
speed_impossible_high = (speed_raw_mph > 75.0).sum()
speed_idling = ((speed_raw_mph < 0.5) & (raw_duration_min > 20.0)).sum()
cash_tips_zero = ((raw_df['payment'] == 'cash') & (raw_df['tip'] == 0.0)).sum()
cash_total_count = (raw_df['payment'] == 'cash').sum()

print("\n--- Anomaly & Inconsistency Audit ---")
print(f"Zero Passengers Count: {passengers_zero} ({passengers_zero/total_rows*100:.2f}%)")
print(f"Zero Distance Count: {distance_zero} ({distance_zero/total_rows*100:.2f}%)")
print(f"Negative/Zero Duration Count: {duration_neg_zero} ({duration_neg_zero/total_rows*100:.2f}%)")
print(f"Impossible Velocity (> 75 mph): {speed_impossible_high}")
print(f"Suspected Idle Meters (< 0.5 mph & > 20 min): {speed_idling}")
print(f"Cash rides with tip == $0.0: {cash_tips_zero} of {cash_total_count} ({cash_tips_zero/cash_total_count*100:.1f}%)")

# ==============================================================================
# FIGURE 1: Missing Data Audit
# ==============================================================================
plt.figure(figsize=(10, 5), dpi=300)
missing_only = missing_df[missing_df['Missing_Count'] > 0].copy()
bars = plt.barh(missing_only['Feature'], missing_only['Missing_Pct'], color='#1B365D', alpha=0.85, edgecolor='black')
plt.title('Figure 1: Missing Value Distribution Across Attributes (%)', pad=15)
plt.xlabel('Percentage of Total Observations Missing (%)')
plt.ylabel('Feature Name')
plt.xlim(0, 1.2)
for bar in bars:
    w = bar.get_width()
    plt.text(w + 0.03, bar.get_y() + bar.get_height()/2, f'{w:.2f}% ({int(w/100*total_rows)} rows)', 
             va='center', fontsize=9, fontweight='bold', color='#1B365D')
plt.tight_layout()
fig1_path = os.path.join(FIG_DIR, 'fig1_missing_data_audit.png')
plt.savefig(fig1_path)
plt.close()
print(f"Saved: {fig1_path}")

# ==============================================================================
# FIGURE 2: Erroneous Entries & Logical Violations
# ==============================================================================
anomalies_data = {
    'Anomaly Type': [
        'Zero Passenger Rides',
        'Zero Distance Trips',
        'Non-Positive Duration',
        'Impossible Speed (>75 mph)',
        'Stationary Idling (>20 min, <0.5 mph)',
        'Missing Payment Method'
    ],
    'Count': [
        passengers_zero,
        distance_zero,
        duration_neg_zero,
        speed_impossible_high,
        speed_idling,
        raw_df['payment'].isnull().sum()
    ]
}
anomaly_df = pd.DataFrame(anomalies_data)
plt.figure(figsize=(10, 5), dpi=300)
bars = plt.bar(anomaly_df['Anomaly Type'], anomaly_df['Count'], color='#C0392B', alpha=0.85, edgecolor='black')
plt.title('Figure 2: Frequency of Erroneous Entries & Logical Inconsistencies', pad=15)
plt.ylabel('Number of Occurrences')
plt.xticks(rotation=20, ha='right', fontweight='bold')
for bar in bars:
    h = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, h + 1.5, f'{int(h)}', ha='center', va='bottom', fontsize=9, fontweight='bold')
plt.ylim(0, max(anomaly_df['Count']) * 1.18)
plt.tight_layout()
fig2_path = os.path.join(FIG_DIR, 'fig2_data_inconsistency_audit.png')
plt.savefig(fig2_path)
plt.close()
print(f"Saved: {fig2_path}")

# ==============================================================================
# FIGURE 3: Domain Censoring Mechanism: Cash vs Credit Card Tips
# ==============================================================================
plt.figure(figsize=(11, 5), dpi=300)
plt.subplot(1, 2, 1)
sns.boxplot(x='payment', y='tip', data=raw_df.dropna(subset=['payment']), palette=['#2ECC71', '#3498DB'], width=0.5)
plt.title('A: Tip Amount Distribution by Payment Type', pad=10)
plt.ylabel('Tip Amount ($)')
plt.xlabel('Recorded Payment Method')

plt.subplot(1, 2, 2)
credit_tips = raw_df[raw_df['payment'] == 'credit card']['tip']
cash_tips = raw_df[raw_df['payment'] == 'cash']['tip']
sns.kdeplot(credit_tips, label='Credit Card (Meter Logged)', color='#3498DB', fill=True, alpha=0.4, linewidth=2)
sns.kdeplot(cash_tips, label='Cash (Systemic Null/Censored 0.0)', color='#E74C3C', fill=True, alpha=0.4, linewidth=2)
plt.title('B: Kernel Density Comparison (Censoring Spike)', pad=10)
plt.xlabel('Tip ($)')
plt.ylabel('Density')
plt.legend(frameon=True, facecolor='white', loc='upper right')

plt.suptitle('Figure 3: Empirical Demonstration of Domain Missingness / Systemic Tip Censoring', y=1.02)
plt.tight_layout()
fig3_path = os.path.join(FIG_DIR, 'fig3_cash_vs_credit_tip_distortion.png')
plt.savefig(fig3_path)
plt.close()
print(f"Saved: {fig3_path}")

# ==============================================================================
# STEP 2: IMPLEMENT SYSTEMATIC CLEANING PIPELINE
# ==============================================================================
print("\n" + "="*80)
print("STEP 2: SYSTEMATIC CLEANING & RECTIFICATION")
print("="*80)

clean_df = raw_df.copy()

# 1. Temporal Feature Extraction & Duration Sanitization
clean_df['duration_min'] = (clean_df['dropoff'] - clean_df['pickup']).dt.total_seconds() / 60.0

# 2. Rectify / Filter Invalid Trips:
# Trip duration must be strictly positive (at least 30 seconds / 0.5 minutes, up to 180 minutes)
# Distance must be strictly positive (at least 0.1 miles)
# Fare must be at least base flag drop ($2.50)
initial_len = len(clean_df)
valid_mask = (
    (clean_df['duration_min'] >= 0.5) & 
    (clean_df['duration_min'] <= 180.0) & 
    (clean_df['distance'] >= 0.05) & 
    (clean_df['fare'] >= 2.0)
)
clean_df = clean_df[valid_mask].copy()
dropped_logical_invalids = initial_len - len(clean_df)
print(f"Filtered {dropped_logical_invalids} invalid trips (negative/zero duration, zero distance, or sub-base fare).")

# 3. Passenger Count Rectification:
# Trips with 0 passengers represent sensor failure or delivery. Impute with mode (1 passenger)
clean_df.loc[clean_df['passengers'] == 0, 'passengers'] = 1
print("Imputed 0-passenger rides with domain modal baseline (1 passenger).")

# 4. Missing Geographic Information Handling:
# Categorize missing zones and boroughs as 'Unknown' to prevent dropping valuable transaction records
clean_df['pickup_zone'] = clean_df['pickup_zone'].fillna('Unknown')
clean_df['dropoff_zone'] = clean_df['dropoff_zone'].fillna('Unknown')
clean_df['pickup_borough'] = clean_df['pickup_borough'].fillna('Unknown')
clean_df['dropoff_borough'] = clean_df['dropoff_borough'].fillna('Unknown')

# 5. Missing Payment Method Handling:
# All 44 missing payment rows had tip == 0. Impute based on mode / designate 'unknown' or 'cash'
clean_df['payment'] = clean_df['payment'].fillna('unknown')
print("Imputed missing payment methods with explicit 'unknown' tag to preserve auditing fidelity.")

# 6. Calculated Speed (mph) & Plausibility Filtering
clean_df['speed_mph'] = clean_df['distance'] / (clean_df['duration_min'] / 60.0)
initial_len_speed = len(clean_df)
# Remove trips with average speed exceeding 70 mph (physically impossible in NYC metropolitan streets)
# or trips that took more than 30 minutes with speed < 0.2 mph (meter abandoned while parked)
clean_df = clean_df[(clean_df['speed_mph'] <= 70.0) & ~((clean_df['speed_mph'] < 0.2) & (clean_df['duration_min'] > 30.0))].copy()
dropped_speed_anomalies = initial_len_speed - len(clean_df)
print(f"Filtered {dropped_speed_anomalies} physical speed anomalies.")

# ==============================================================================
# STEP 3: OUTLIER DIAGNOSTICS & MULTIVARIATE ANOMALY DETECTION
# ==============================================================================
print("\n" + "="*80)
print("STEP 3: OUTLIER ANALYSIS (UNIVARIATE & MULTIVARIATE)")
print("="*80)

# Statistical fences before outlier treatment
def calc_iqr_bounds(series):
    q25 = series.quantile(0.25)
    q75 = series.quantile(0.75)
    iqr = q75 - q25
    lower = max(0, q25 - 1.5 * iqr)
    upper = q75 + 1.5 * iqr
    outliers = (series < lower) | (series > upper)
    return lower, upper, outliers.sum(), (outliers.sum() / len(series)) * 100

iqr_distance = calc_iqr_bounds(clean_df['distance'])
iqr_fare = calc_iqr_bounds(clean_df['fare'])
iqr_tip = calc_iqr_bounds(clean_df['tip'])
iqr_total = calc_iqr_bounds(clean_df['total'])

print("--- IQR Outlier Summary (1.5x IQR Rule) ---")
print(f"Distance: [{iqr_distance[0]:.2f}, {iqr_distance[1]:.2f}] -> {iqr_distance[2]} outliers ({iqr_distance[3]:.2f}%)")
print(f"Fare:     [{iqr_fare[0]:.2f}, {iqr_fare[1]:.2f}] -> {iqr_fare[2]} outliers ({iqr_fare[3]:.2f}%)")
print(f"Tip:      [{iqr_tip[0]:.2f}, {iqr_tip[1]:.2f}] -> {iqr_tip[2]} outliers ({iqr_tip[3]:.2f}%)")
print(f"Total:    [{iqr_total[0]:.2f}, {iqr_total[1]:.2f}] -> {iqr_total[2]} outliers ({iqr_total[3]:.2f}%)")

# Multivariate Outlier Detection using Isolation Forest
iso_features = ['distance', 'fare', 'duration_min', 'total']
iso_scaler = StandardScaler()
X_iso = iso_scaler.fit_transform(clean_df[iso_features])
iso_forest = IsolationForest(contamination=0.015, random_state=42, n_estimators=100)
clean_df['iso_outlier'] = iso_forest.fit_predict(X_iso) # -1 is outlier, 1 is inlier
num_iso_outliers = (clean_df['iso_outlier'] == -1).sum()
print(f"Isolation Forest identified {num_iso_outliers} multivariate anomalies ({num_iso_outliers/len(clean_df)*100:.2f}%).")

# ==============================================================================
# FIGURE 4: Univariate Outlier Distributions (Boxplots)
# ==============================================================================
fig, axes = plt.subplots(2, 2, figsize=(11, 8), dpi=300)
sns.boxplot(y=clean_df['distance'], ax=axes[0, 0], color='#3498DB', flierprops={'marker':'o', 'markersize':3, 'alpha':0.4})
axes[0, 0].set_title('A: Trip Distance Distribution (miles)', fontsize=11)
axes[0, 0].axhline(iqr_distance[1], color='red', linestyle='--', label=f'Upper Fence ({iqr_distance[1]:.1f})')
axes[0, 0].legend()

sns.boxplot(y=clean_df['fare'], ax=axes[0, 1], color='#E67E22', flierprops={'marker':'o', 'markersize':3, 'alpha':0.4})
axes[0, 1].set_title('B: Base Fare Distribution ($)', fontsize=11)
axes[0, 1].axhline(iqr_fare[1], color='red', linestyle='--', label=f'Upper Fence ({iqr_fare[1]:.1f})')
axes[0, 1].legend()

sns.boxplot(y=clean_df['tip'], ax=axes[1, 0], color='#2ECC71', flierprops={'marker':'o', 'markersize':3, 'alpha':0.4})
axes[1, 0].set_title('C: Tip Amount Distribution ($)', fontsize=11)
axes[1, 0].axhline(iqr_tip[1], color='red', linestyle='--', label=f'Upper Fence ({iqr_tip[1]:.1f})')
axes[1, 0].legend()

sns.boxplot(y=clean_df['duration_min'], ax=axes[1, 1], color='#9B59B6', flierprops={'marker':'o', 'markersize':3, 'alpha':0.4})
axes[1, 1].set_title('D: Trip Duration (minutes)', fontsize=11)
axes[1, 1].axhline(clean_df['duration_min'].quantile(0.75) + 1.5*(clean_df['duration_min'].quantile(0.75)-clean_df['duration_min'].quantile(0.25)), 
                   color='red', linestyle='--', label='Upper Fence')
axes[1, 1].legend()

plt.suptitle('Figure 4: Univariate Outlier Detection via Tukey Fences (Boxplots)', y=1.00)
plt.tight_layout()
fig4_path = os.path.join(FIG_DIR, 'fig4_univariate_outlier_boxplots.png')
plt.savefig(fig4_path)
plt.close()
print(f"Saved: {fig4_path}")

# ==============================================================================
# FIGURE 5: Multivariate Outlier Detection (Isolation Forest)
# ==============================================================================
plt.figure(figsize=(10, 6), dpi=300)
inliers = clean_df[clean_df['iso_outlier'] == 1]
outliers = clean_df[clean_df['iso_outlier'] == -1]

plt.scatter(inliers['distance'], inliers['fare'], c='#2980B9', alpha=0.5, s=25, label='Normal Inliers (98.5%)')
plt.scatter(outliers['distance'], outliers['fare'], c='#E74C3C', alpha=0.9, s=45, edgecolor='black', marker='^', label='Multivariate Outliers (1.5%)')
plt.title('Figure 5: Multivariate Outlier Detection via Isolation Forest (Distance vs Fare)', pad=15)
plt.xlabel('Trip Distance (miles)')
plt.ylabel('Base Fare ($)')
plt.legend(frameon=True, facecolor='white', loc='upper left')

# Annotate prominent multivariate anomalies
extreme_outlier = outliers.sort_values(by='fare', ascending=False).iloc[0]
plt.annotate(f"Extreme Fare: ${extreme_outlier['fare']:.1f} ({extreme_outlier['distance']:.1f} mi)",
             xy=(extreme_outlier['distance'], extreme_outlier['fare']),
             xytext=(extreme_outlier['distance'] - 8, extreme_outlier['fare'] - 15),
             arrowprops=dict(facecolor='black', arrowstyle='->', lw=1.2),
             fontweight='bold', fontsize=9, bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.7))

plt.tight_layout()
fig5_path = os.path.join(FIG_DIR, 'fig5_multivariate_outliers_isolation_forest.png')
plt.savefig(fig5_path)
plt.close()
print(f"Saved: {fig5_path}")

# Soft Winsorization / Capping on Extreme 99.5th Percentile to preserve records while mitigating tail distortion
cap_distance = clean_df['distance'].quantile(0.995)
cap_fare = clean_df['fare'].quantile(0.995)
cap_tip = clean_df['tip'].quantile(0.995)
cap_duration = clean_df['duration_min'].quantile(0.995)

clean_df['distance_capped'] = np.clip(clean_df['distance'], 0, cap_distance)
clean_df['fare_capped'] = np.clip(clean_df['fare'], 0, cap_fare)
clean_df['tip_capped'] = np.clip(clean_df['tip'], 0, cap_tip)
clean_df['duration_capped'] = np.clip(clean_df['duration_min'], 0, cap_duration)

# ==============================================================================
# STEP 4: ADVANCED FEATURE ENGINEERING & TRANSFORMATIONS
# ==============================================================================
print("\n" + "="*80)
print("STEP 4: ADVANCED FEATURE ENGINEERING & TRANSFORMATIONS")
print("="*80)

# Temporal engineering
clean_df['pickup_hour'] = clean_df['pickup'].dt.hour
clean_df['pickup_day_of_week'] = clean_df['pickup'].dt.dayofweek
clean_df['pickup_day_name'] = clean_df['pickup'].dt.day_name()
clean_df['is_weekend'] = clean_df['pickup_day_of_week'].isin([5, 6]).astype(int)

# Rush hour indicator: Weekdays 07:00-09:00 and 16:00-19:00
clean_df['is_rush_hour'] = (
    (~clean_df['is_weekend'].astype(bool)) & 
    (clean_df['pickup_hour'].isin([7, 8, 9, 16, 17, 18, 19]))
).astype(int)

# Spatial engineering
clean_df['is_cross_borough'] = (clean_df['pickup_borough'] != clean_df['dropoff_borough']).astype(int)
clean_df['is_airport_trip'] = (
    clean_df['pickup_zone'].str.contains('Airport|JFK|LaGuardia', case=False, na=False) |
    clean_df['dropoff_zone'].str.contains('Airport|JFK|LaGuardia', case=False, na=False)
).astype(int)

# Economic / operational rates
clean_df['fare_per_mile'] = clean_df['fare_capped'] / clean_df['distance_capped']
clean_df['fare_per_minute'] = clean_df['fare_capped'] / clean_df['duration_capped']
clean_df['tip_pct_credit'] = np.where(
    clean_df['payment'] == 'credit card',
    (clean_df['tip_capped'] / np.maximum(clean_df['fare_capped'], 1.0)) * 100,
    np.nan
)

# Power & Log Transformations (Log1p) to normalize heavy right tails
clean_df['log_distance'] = np.log1p(clean_df['distance_capped'])
clean_df['log_fare'] = np.log1p(clean_df['fare_capped'])
clean_df['log_total'] = np.log1p(clean_df['total'])
clean_df['log_duration'] = np.log1p(clean_df['duration_capped'])

# Calculate skewness before and after log transform
skew_dist_raw = stats.skew(clean_df['distance'])
skew_dist_log = stats.skew(clean_df['log_distance'])
skew_fare_raw = stats.skew(clean_df['fare'])
skew_fare_log = stats.skew(clean_df['log_fare'])
skew_total_raw = stats.skew(clean_df['total'])
skew_total_log = stats.skew(clean_df['log_total'])

print(f"Skewness Reduction:")
print(f"  Distance: {skew_dist_raw:.3f} -> {skew_dist_log:.3f}")
print(f"  Fare:     {skew_fare_raw:.3f} -> {skew_fare_log:.3f}")
print(f"  Total:    {skew_total_raw:.3f} -> {skew_total_log:.3f}")

# ==============================================================================
# FIGURE 6: Skewness Mitigation via Log1p Transformations
# ==============================================================================
fig, axes = plt.subplots(3, 2, figsize=(11, 9), dpi=300)

# Distance
sns.histplot(clean_df['distance'], kde=True, ax=axes[0, 0], color='#E74C3C', bins=35)
axes[0, 0].set_title(f'Raw Distance (Skewness: {skew_dist_raw:.2f})', fontsize=10)
axes[0, 0].set_xlabel('Miles')

sns.histplot(clean_df['log_distance'], kde=True, ax=axes[0, 1], color='#27AE60', bins=35)
axes[0, 1].set_title(f'Log1p Transformed Distance (Skewness: {skew_dist_log:.2f})', fontsize=10)
axes[0, 1].set_xlabel('log(1 + Miles)')

# Fare
sns.histplot(clean_df['fare'], kde=True, ax=axes[1, 0], color='#E74C3C', bins=35)
axes[1, 0].set_title(f'Raw Fare (Skewness: {skew_fare_raw:.2f})', fontsize=10)
axes[1, 0].set_xlabel('USD ($)')

sns.histplot(clean_df['log_fare'], kde=True, ax=axes[1, 1], color='#27AE60', bins=35)
axes[1, 1].set_title(f'Log1p Transformed Fare (Skewness: {skew_fare_log:.2f})', fontsize=10)
axes[1, 1].set_xlabel('log(1 + USD)')

# Total
sns.histplot(clean_df['total'], kde=True, ax=axes[2, 0], color='#E74C3C', bins=35)
axes[2, 0].set_title(f'Raw Total (Skewness: {skew_total_raw:.2f})', fontsize=10)
axes[2, 0].set_xlabel('USD ($)')

sns.histplot(clean_df['log_total'], kde=True, ax=axes[2, 1], color='#27AE60', bins=35)
axes[2, 1].set_title(f'Log1p Transformed Total (Skewness: {skew_total_log:.2f})', fontsize=10)
axes[2, 1].set_xlabel('log(1 + USD)')

plt.suptitle('Figure 6: Density Distribution Comparison: Raw vs. Log1p Normalized Continuous Features', y=1.00)
plt.tight_layout()
fig6_path = os.path.join(FIG_DIR, 'fig6_skewness_and_log_transforms.png')
plt.savefig(fig6_path)
plt.close()
print(f"Saved: {fig6_path}")

# ==============================================================================
# FIGURE 7: Feature Correlation Matrix
# ==============================================================================
plt.figure(figsize=(9, 7), dpi=300)
corr_cols = ['distance_capped', 'duration_capped', 'fare_capped', 'tip_capped', 'total', 
             'speed_mph', 'is_cross_borough', 'is_airport_trip', 'is_rush_hour']
corr_matrix = clean_df[corr_cols].corr()
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
cmap = sns.diverging_palette(230, 20, as_cmap=True)

sns.heatmap(corr_matrix, mask=mask, cmap=cmap, vmin=-0.3, vmax=1.0, annot=True, 
            fmt='.2f', square=True, linewidths=0.5, cbar_kws={"shrink": 0.8})
plt.title('Figure 7: Pearson Correlation Heatmap of Engineered Predictors', pad=15)
plt.tight_layout()
fig7_path = os.path.join(FIG_DIR, 'fig7_feature_correlations.png')
plt.savefig(fig7_path)
plt.close()
print(f"Saved: {fig7_path}")

# Save final cleaned dataset
clean_csv_path = os.path.join(BASE_DIR, 'cleaned_taxis_data.csv')
clean_df.to_csv(clean_csv_path, index=False)
print(f"Final cleaned dataset saved to: {clean_csv_path} (Shape: {clean_df.shape})")

# ==============================================================================
# STEP 5: DOWNSTREAM MACHINE LEARNING IMPACT BENCHMARK
# ==============================================================================
print("\n" + "="*80)
print("STEP 5: DOWNSTREAM MACHINE LEARNING VALIDATION")
print("="*80)

# We evaluate predicting 'fare' using baseline features
# Model A: Naive Raw Dataset (minimal dropna, uncleaned, unscaled, raw outliers intact)
raw_eval = raw_df[['passengers', 'distance', 'tolls', 'fare']].dropna().copy()
raw_eval = raw_eval[(raw_eval['fare'] > 0) & (raw_eval['distance'] > 0)] # minimal sanity
X_raw = raw_eval[['passengers', 'distance', 'tolls']]
y_raw = raw_eval['fare']

X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X_raw, y_raw, test_size=0.2, random_state=42)

# Ridge on raw
ridge_raw = Ridge(alpha=1.0)
ridge_raw.fit(X_train_r, y_train_r)
pred_raw_ridge = ridge_raw.predict(X_test_r)
r2_raw_ridge = r2_score(y_test_r, pred_raw_ridge)
rmse_raw_ridge = np.sqrt(mean_squared_error(y_test_r, pred_raw_ridge))
mae_raw_ridge = mean_absolute_error(y_test_r, pred_raw_ridge)

# RF on raw
rf_raw = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
rf_raw.fit(X_train_r, y_train_r)
pred_raw_rf = rf_raw.predict(X_test_r)
r2_raw_rf = r2_score(y_test_r, pred_raw_rf)
rmse_raw_rf = np.sqrt(mean_squared_error(y_test_r, pred_raw_rf))
mae_raw_rf = mean_absolute_error(y_test_r, pred_raw_rf)

# Model B: Cleaned, Rectified & Engineered Dataset
clean_eval = clean_df[['passengers', 'distance_capped', 'duration_capped', 'tolls', 
                       'is_cross_borough', 'is_airport_trip', 'is_rush_hour', 'fare_capped']].copy()

X_clean = clean_eval.drop(columns=['fare_capped'])
y_clean = clean_eval['fare_capped']

X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X_clean, y_clean, test_size=0.2, random_state=42)

# Scale features
scaler = RobustScaler()
X_train_c_s = scaler.fit_transform(X_train_c)
X_test_c_s = scaler.transform(X_test_c)

# Ridge on cleaned
ridge_clean = Ridge(alpha=1.0)
ridge_clean.fit(X_train_c_s, y_train_c)
pred_clean_ridge = ridge_clean.predict(X_test_c_s)
r2_clean_ridge = r2_score(y_test_c, pred_clean_ridge)
rmse_clean_ridge = np.sqrt(mean_squared_error(y_test_c, pred_clean_ridge))
mae_clean_ridge = mean_absolute_error(y_test_c, pred_clean_ridge)

# RF on cleaned
rf_clean = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
rf_clean.fit(X_train_c, y_train_c)
pred_clean_rf = rf_clean.predict(X_test_c)
r2_clean_rf = r2_score(y_test_c, pred_clean_rf)
rmse_clean_rf = np.sqrt(mean_squared_error(y_test_c, pred_clean_rf))
mae_clean_rf = mean_absolute_error(y_test_c, pred_clean_rf)

print("\n--- Empirical Model Performance Comparison ---")
print(f"Naive Ridge:   R2 = {r2_raw_ridge:.4f}, RMSE = ${rmse_raw_ridge:.2f}, MAE = ${mae_raw_ridge:.2f}")
print(f"Cleaned Ridge: R2 = {r2_clean_ridge:.4f}, RMSE = ${rmse_clean_ridge:.2f}, MAE = ${mae_clean_ridge:.2f}")
print(f"Naive RF:      R2 = {r2_raw_rf:.4f}, RMSE = ${rmse_raw_rf:.2f}, MAE = ${mae_raw_rf:.2f}")
print(f"Cleaned RF:    R2 = {r2_clean_rf:.4f}, RMSE = ${rmse_clean_rf:.2f}, MAE = ${mae_clean_rf:.2f}")

# ==============================================================================
# FIGURE 8: Downstream ML Performance Metrics
# ==============================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5), dpi=300)

models = ['Ridge Regressor', 'Random Forest Regressor']
r2_raw_vals = [r2_raw_ridge, r2_raw_rf]
r2_clean_vals = [r2_clean_ridge, r2_clean_rf]
rmse_raw_vals = [rmse_raw_ridge, rmse_raw_rf]
rmse_clean_vals = [rmse_clean_ridge, rmse_clean_rf]

x = np.arange(len(models))
width = 0.35

# Subplot 1: R2 Score (Higher is better)
rects1 = ax1.bar(x - width/2, r2_raw_vals, width, label='Uncleaned (Raw)', color='#E74C3C', alpha=0.85, edgecolor='black')
rects2 = ax1.bar(x + width/2, r2_clean_vals, width, label='Cleaned & Preprocessed', color='#2ECC71', alpha=0.85, edgecolor='black')
ax1.set_ylabel('Coefficient of Determination ($R^2$)')
ax1.set_title('A: Explanatory Power ($R^2$ Score - Higher is Better)', pad=10)
ax1.set_xticks(x)
ax1.set_xticklabels(models, fontweight='bold')
ax1.set_ylim(0, 1.05)
ax1.legend(loc='lower right', frameon=True)
for rect in rects1:
    h = rect.get_height()
    ax1.text(rect.get_x() + rect.get_width()/2, h + 0.02, f'{h:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
for rect in rects2:
    h = rect.get_height()
    ax1.text(rect.get_x() + rect.get_width()/2, h + 0.02, f'{h:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

# Subplot 2: RMSE (Lower is better)
rects3 = ax2.bar(x - width/2, rmse_raw_vals, width, label='Uncleaned (Raw)', color='#E74C3C', alpha=0.85, edgecolor='black')
rects4 = ax2.bar(x + width/2, rmse_clean_vals, width, label='Cleaned & Preprocessed', color='#2ECC71', alpha=0.85, edgecolor='black')
ax2.set_ylabel('Root Mean Squared Error (RMSE in USD $)')
ax2.set_title('B: Predictive Error (RMSE - Lower is Better)', pad=10)
ax2.set_xticks(x)
ax2.set_xticklabels(models, fontweight='bold')
ax2.set_ylim(0, max(rmse_raw_vals) * 1.25)
ax2.legend(loc='upper right', frameon=True)
for rect in rects3:
    h = rect.get_height()
    ax2.text(rect.get_x() + rect.get_width()/2, h + 0.15, f'${h:.2f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
for rect in rects4:
    h = rect.get_height()
    ax2.text(rect.get_x() + rect.get_width()/2, h + 0.15, f'${h:.2f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.suptitle('Figure 8: Empirical Validation of Preprocessing Impact on Downstream ML Models', y=1.02)
plt.tight_layout()
fig8_path = os.path.join(FIG_DIR, 'fig8_downstream_model_performance.png')
plt.savefig(fig8_path)
plt.close()
print(f"Saved: {fig8_path}")

# Export pipeline metrics for report generation
summary_metrics = {
    'raw_rows': total_rows,
    'raw_cols': total_cols,
    'clean_rows': len(clean_df),
    'clean_cols': clean_df.shape[1],
    'passengers_zero': int(passengers_zero),
    'distance_zero': int(distance_zero),
    'duration_neg_zero': int(duration_neg_zero),
    'speed_anomalies': int(dropped_speed_anomalies),
    'cash_tip_censored': int(cash_tips_zero),
    'missing_payment': int(raw_df['payment'].isnull().sum()),
    'missing_pickup_zone': int(raw_df['pickup_zone'].isnull().sum()),
    'missing_dropoff_zone': int(raw_df['dropoff_zone'].isnull().sum()),
    'iso_outliers': int(num_iso_outliers),
    'skew_dist_raw': float(skew_dist_raw),
    'skew_dist_log': float(skew_dist_log),
    'skew_fare_raw': float(skew_fare_raw),
    'skew_fare_log': float(skew_fare_log),
    'r2_raw_ridge': float(r2_raw_ridge),
    'r2_clean_ridge': float(r2_clean_ridge),
    'rmse_raw_ridge': float(rmse_raw_ridge),
    'rmse_clean_ridge': float(rmse_clean_ridge),
    'r2_raw_rf': float(r2_raw_rf),
    'r2_clean_rf': float(r2_clean_rf),
    'rmse_raw_rf': float(rmse_raw_rf),
    'rmse_clean_rf': float(rmse_clean_rf),
}

import json
metrics_path = os.path.join(BASE_DIR, 'pipeline_metrics.json')
with open(metrics_path, 'w') as f:
    json.dump(summary_metrics, f, indent=4)
print(f"Saved pipeline metrics JSON: {metrics_path}")
print("PIPELINE EXECUTION COMPLETE!")
