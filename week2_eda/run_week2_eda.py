"""
Week 2: Exploratory Data Analysis (EDA) and Visualization Pipeline
Dataset: NYC TLC Urban Mobility & Economic Dynamics (6,360 records, 35 features)
Author: Rohit / Applied Data Science Lab
"""

import os
import json
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats

# Set random seed
np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(BASE_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

# Styling configuration for publication-grade visualization
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
print("WEEK 2 EDA: INGESTING CLEANED DATASET & METRIC CATALOG")
print("="*80)

data_path = os.path.join(os.path.dirname(BASE_DIR), 'cleaned_taxis_data.csv')
df = pd.read_csv(data_path)
df['pickup'] = pd.to_datetime(df['pickup'])
df['dropoff'] = pd.to_datetime(df['dropoff'])
print(f"Cleaned dataset loaded. Shape: {df.shape}")

# Ensure derived columns are available
if 'speed_mph' not in df.columns:
    df['speed_mph'] = df['distance_capped'] / (np.maximum(df['duration_capped'], 0.1) / 60.0)

# Day name ordering
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
df['pickup_day_name'] = pd.Categorical(df['pickup_day_name'], categories=days_order, ordered=True)

# Time of day binning
def get_time_period(hour):
    if 6 <= hour < 10:
        return 'Morning Rush (06-10)'
    elif 10 <= hour < 16:
        return 'Midday (10-16)'
    elif 16 <= hour < 20:
        return 'Evening Rush (16-20)'
    elif 20 <= hour < 24:
        return 'Night (20-24)'
    else:
        return 'Late Night / Dawn (00-06)'

df['time_period'] = df['pickup_hour'].apply(get_time_period)
period_order = ['Late Night / Dawn (00-06)', 'Morning Rush (06-10)', 'Midday (10-16)', 'Evening Rush (16-20)', 'Night (20-24)']
df['time_period'] = pd.Categorical(df['time_period'], categories=period_order, ordered=True)

# Tip percentage for credit cards
df_credit = df[df['payment'] == 'credit card'].copy()
df_credit['tip_percentage'] = (df_credit['tip_capped'] / np.maximum(df_credit['fare_capped'], 2.5)) * 100
df_credit['tip_percentage_capped'] = np.clip(df_credit['tip_percentage'], 0, 50)

# ==============================================================================
# VISUALIZATION 1: Circadian Demand Rhythm & Speed Dynamics
# ==============================================================================
print("\n[EDA 1] Generating Circadian Demand & Kinematic Speed Curve...")
hourly_agg = df.groupby('pickup_hour').agg(
    trip_count=('fare', 'count'),
    mean_speed=('speed_mph', 'mean'),
    median_speed=('speed_mph', 'median'),
    mean_fare=('fare_capped', 'mean'),
    mean_distance=('distance_capped', 'mean')
).reset_index()

fig, ax1 = plt.subplots(figsize=(11, 5.5), dpi=300)
color1 = '#1B365D'
color2 = '#C0392B'

ax1.set_xlabel('Hour of Day (24-Hour Cycle)', fontweight='bold')
ax1.set_ylabel('Trip Demand Volume (Rides)', color=color1, fontweight='bold')
bars = ax1.bar(hourly_agg['pickup_hour'], hourly_agg['trip_count'], color=color1, alpha=0.75, width=0.6, label='Trip Volume')
ax1.tick_params(axis='y', labelcolor=color1)
ax1.set_xticks(range(0, 24))

ax2 = ax1.twinx()
ax2.set_ylabel('Average Velocity (mph)', color=color2, fontweight='bold')
line = ax2.plot(hourly_agg['pickup_hour'], hourly_agg['mean_speed'], color=color2, linewidth=3, marker='o', label='Average Speed (mph)')
ax2.tick_params(axis='y', labelcolor=color2)
ax2.grid(False)

# Annotate morning rush congestion drop
min_speed_hour = hourly_agg.loc[hourly_agg['mean_speed'].idxmin()]
ax2.annotate(f"Peak Congestion: {min_speed_hour['mean_speed']:.1f} mph ({int(min_speed_hour['pickup_hour'])}:00)",
             xy=(min_speed_hour['pickup_hour'], min_speed_hour['mean_speed']),
             xytext=(min_speed_hour['pickup_hour'] + 1, min_speed_hour['mean_speed'] - 2),
             arrowprops=dict(facecolor=color2, arrowstyle='->', lw=1.5),
             fontweight='bold', fontsize=9, bbox=dict(boxstyle="round,pad=0.3", fc="#FDEDEC", ec=color2))

# Annotate late-night free flow
max_speed_hour = hourly_agg.loc[hourly_agg['mean_speed'].idxmax()]
ax2.annotate(f"Free-Flow Traffic: {max_speed_hour['mean_speed']:.1f} mph ({int(max_speed_hour['pickup_hour'])}:00)",
             xy=(max_speed_hour['pickup_hour'], max_speed_hour['mean_speed']),
             xytext=(max_speed_hour['pickup_hour'] - 3.5, max_speed_hour['mean_speed'] + 1.5),
             arrowprops=dict(facecolor=color2, arrowstyle='->', lw=1.5),
             fontweight='bold', fontsize=9, bbox=dict(boxstyle="round,pad=0.3", fc="#FDEDEC", ec=color2))

plt.title('Figure 1: Circadian Demand Rhythm vs. Kinematic Velocity (24-Hour Profile)', pad=15)
fig.tight_layout()
fig1_path = os.path.join(FIG_DIR, 'eda_fig1_circadian_demand_speed.png')
plt.savefig(fig1_path)
plt.close()
print(f"Saved: {fig1_path}")

# ==============================================================================
# VISUALIZATION 2: Day-of-Week Mobility Economics
# ==============================================================================
print("\n[EDA 2] Generating Day-of-Week Mobility & Revenue Economics...")
dow_agg = df.groupby('pickup_day_name', observed=True).agg(
    total_trips=('fare', 'count'),
    mean_duration=('duration_capped', 'mean'),
    revenue_per_min=('fare_per_minute', 'mean'),
    mean_distance=('distance_capped', 'mean')
).reset_index()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

sns.barplot(x='pickup_day_name', y='total_trips', data=dow_agg, ax=ax1, palette='Blues_r', edgecolor='black')
ax1.set_title('A: Weekly Trip Volume Distribution', pad=10)
ax1.set_xlabel('Day of the Week')
ax1.set_ylabel('Total Trip Count')
ax1.set_xticklabels(dow_agg['pickup_day_name'], rotation=30, ha='right')
for p in ax1.patches:
    ax1.annotate(f"{int(p.get_height())}", (p.get_x() + p.get_width() / 2., p.get_height() + 10),
                 ha='center', va='bottom', fontsize=9, fontweight='bold')

sns.barplot(x='pickup_day_name', y='revenue_per_min', data=dow_agg, ax=ax2, palette='YlOrRd_r', edgecolor='black')
ax2.set_title('B: Revenue Generation Efficiency ($/minute)', pad=10)
ax2.set_xlabel('Day of the Week')
ax2.set_ylabel('Average Revenue ($/min)')
ax2.set_xticklabels(dow_agg['pickup_day_name'], rotation=30, ha='right')
for p in ax2.patches:
    ax2.annotate(f"${p.get_height():.2f}", (p.get_x() + p.get_width() / 2., p.get_height() + 0.02),
                 ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.suptitle('Figure 2: Day-of-Week Mobility Patterns: Demand Volume vs. Revenue Density', y=1.02)
plt.tight_layout()
fig2_path = os.path.join(FIG_DIR, 'eda_fig2_day_of_week_economics.png')
plt.savefig(fig2_path)
plt.close()
print(f"Saved: {fig2_path}")

# ==============================================================================
# VISUALIZATION 3: Origin-Destination Transition Heatmap
# ==============================================================================
print("\n[EDA 3] Generating Spatial Origin-Destination Flow Heatmap...")
borough_order = ['Manhattan', 'Queens', 'Brooklyn', 'Bronx', 'Unknown']
df_boroughs = df[df['pickup_borough'].isin(borough_order) & df['dropoff_borough'].isin(borough_order)].copy()
od_matrix = pd.crosstab(df_boroughs['pickup_borough'], df_boroughs['dropoff_borough'], normalize='index') * 100
od_matrix = od_matrix.reindex(index=borough_order, columns=borough_order, fill_value=0)

plt.figure(figsize=(9, 7), dpi=300)
sns.heatmap(od_matrix, annot=True, fmt='.1f', cmap='Blues', cbar_kws={'label': 'Row Transition Probability (%)'},
            linewidths=1, linecolor='white')
plt.title('Figure 3: Spatial Origin-Destination Flow Matrix (% of Origin Borough)', pad=15)
plt.xlabel('Destination Borough (Dropoff)', fontweight='bold')
plt.ylabel('Origin Borough (Pickup)', fontweight='bold')
plt.tight_layout()
fig3_path = os.path.join(FIG_DIR, 'eda_fig3_spatial_od_matrix.png')
plt.savefig(fig3_path)
plt.close()
print(f"Saved: {fig3_path}")

# ==============================================================================
# VISUALIZATION 4: Consumer Tip Propensity (Credit Transactions)
# ==============================================================================
print("\n[EDA 4] Generating Consumer Gratuity Dynamics...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

# Gratuity across time periods
sns.violinplot(x='time_period', y='tip_percentage_capped', data=df_credit, ax=ax1, palette='Set2', inner='quartile')
ax1.set_title('A: Tip Percentage Distribution Across Time Periods', pad=10)
ax1.set_xlabel('Time of Day')
ax1.set_ylabel('Tip Percentage (%)')
ax1.set_xticklabels(ax1.get_xticklabels(), rotation=25, ha='right')
ax1.axhline(20.0, color='red', linestyle='--', label='20% Benchmark')
ax1.legend(loc='upper right')

# Passenger count vs tip
sns.boxplot(x='passengers', y='tip_percentage_capped', data=df_credit[df_credit['passengers'] <= 6], 
            ax=ax2, palette='Blues', width=0.5, showmeans=True, 
            meanprops={"marker":"o", "markerfacecolor":"red", "markeredgecolor":"red"})
ax2.set_title('B: Gratuity Propensity by Passenger Party Size', pad=10)
ax2.set_xlabel('Declared Passenger Count')
ax2.set_ylabel('Tip Percentage (%)')
ax2.axhline(20.0, color='red', linestyle='--', label='20% Benchmark')
ax2.legend(loc='upper right')

plt.suptitle('Figure 4: Consumer Gratuity Behavioral Dynamics on Credit Card Transactions', y=1.02)
plt.tight_layout()
fig4_path = os.path.join(FIG_DIR, 'eda_fig4_tip_propensity_dynamics.png')
plt.savefig(fig4_path)
plt.close()
print(f"Saved: {fig4_path}")

# ==============================================================================
# VISUALIZATION 5: Yellow vs. Green Boro Taxi Disparity
# ==============================================================================
print("\n[EDA 5] Generating Yellow vs. Green Taxi Operational Disparity...")
fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), dpi=300)

palette_taxi = {'yellow': '#F4D03F', 'green': '#2ECC71'}

# Distance
sns.boxplot(x='color', y='distance_capped', data=df, ax=axes[0], palette=palette_taxi, width=0.4)
axes[0].set_title('A: Trip Distance (miles)', pad=10)
axes[0].set_ylabel('Distance (miles)')
axes[0].set_xlabel('Taxi Medallion Class')

# Duration
sns.boxplot(x='color', y='duration_capped', data=df, ax=axes[1], palette=palette_taxi, width=0.4)
axes[1].set_title('B: Trip Duration (minutes)', pad=10)
axes[1].set_ylabel('Duration (minutes)')
axes[1].set_xlabel('Taxi Medallion Class')

# Fare per Mile
sns.boxplot(x='color', y='fare_per_mile', data=df[df['fare_per_mile'] < 20], ax=axes[2], palette=palette_taxi, width=0.4)
axes[2].set_title('C: Unit Revenue ($/mile)', pad=10)
axes[2].set_ylabel('Revenue ($/mile)')
axes[2].set_xlabel('Taxi Medallion Class')

plt.suptitle('Figure 5: Operational Disparities: Yellow Medallion (Core) vs. Green Boro Taxis (Outer Boroughs)', y=1.02)
plt.tight_layout()
fig5_path = os.path.join(FIG_DIR, 'eda_fig5_yellow_vs_green_disparity.png')
plt.savefig(fig5_path)
plt.close()
print(f"Saved: {fig5_path}")

# ==============================================================================
# VISUALIZATION 6: Airport Transit Economics (JFK / LGA vs Intra-City)
# ==============================================================================
print("\n[EDA 6] Generating Airport vs Non-Airport Economics...")
df['transit_type'] = np.where(df['is_airport_trip'] == 1, 'Airport Trip (JFK/LGA)', 'Standard Intra-City Trip')

fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), dpi=300)
palette_transit = {'Airport Trip (JFK/LGA)': '#E74C3C', 'Standard Intra-City Trip': '#3498DB'}

sns.boxplot(x='transit_type', y='fare_capped', data=df, ax=axes[0], palette=palette_transit, width=0.4)
axes[0].set_title('A: Base Fare Comparison ($)', pad=10)
axes[0].set_ylabel('Base Fare ($)')
axes[0].set_xlabel('')

sns.boxplot(x='transit_type', y='tolls', data=df, ax=axes[1], palette=palette_transit, width=0.4)
axes[1].set_title('B: Highway & Bridge Tolls ($)', pad=10)
axes[1].set_ylabel('Toll Surcharges ($)')
axes[1].set_xlabel('')

sns.boxplot(x='transit_type', y='total', data=df, ax=axes[2], palette=palette_transit, width=0.4)
axes[2].set_title('C: Total Financial Expenditure ($)', pad=10)
axes[2].set_ylabel('Total Fare ($)')
axes[2].set_xlabel('')

plt.suptitle('Figure 6: Economic Profiling of Airport Transit vs. Standard Metropolitan Trips', y=1.02)
plt.tight_layout()
fig6_path = os.path.join(FIG_DIR, 'eda_fig6_airport_transit_economics.png')
plt.savefig(fig6_path)
plt.close()
print(f"Saved: {fig6_path}")

# ==============================================================================
# VISUALIZATION 7: Distance vs Fare Regression with Hexbin & Loess
# ==============================================================================
print("\n[EDA 7] Generating Distance vs. Fare Regression & Density...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

# Hexbin density
hb = ax1.hexbin(df['distance_capped'], df['fare_capped'], gridsize=35, cmap='Blues', mincnt=1)
ax1.set_title('A: Bivariate Density Hexbin Plot', pad=10)
ax1.set_xlabel('Trip Distance (miles)')
ax1.set_ylabel('Base Fare ($)')
cb = fig.colorbar(hb, ax=ax1)
cb.set_label('Trip Count Density')

# Scatter with linear and polynomial fits
sample_df = df.sample(min(1500, len(df)), random_state=42)
sns.regplot(x='distance_capped', y='fare_capped', data=sample_df, ax=ax2, 
            scatter_kws={'alpha': 0.35, 'color': '#2C3E50', 's': 18},
            line_kws={'color': '#E74C3C', 'linewidth': 2.5, 'label': 'Linear Tariff Trend'})
ax2.set_title('B: Metered Pricing Trajectory & Tariff Elasticity', pad=10)
ax2.set_xlabel('Trip Distance (miles)')
ax2.set_ylabel('Base Fare ($)')
ax2.legend(loc='lower right')

plt.suptitle('Figure 7: Empirical Pricing Trajectory: Distance vs. Fare Density and Linear Elasticity', y=1.02)
plt.tight_layout()
fig7_path = os.path.join(FIG_DIR, 'eda_fig7_distance_fare_trajectory.png')
plt.savefig(fig7_path)
plt.close()
print(f"Saved: {fig7_path}")

# ==============================================================================
# VISUALIZATION 8: Faceted Analysis: Distance vs Fare by Borough & Rush Hour
# ==============================================================================
print("\n[EDA 8] Generating Faceted Spatial-Temporal Breakdown...")
major_boroughs = ['Manhattan', 'Queens', 'Brooklyn']
df_facet = df[df['pickup_borough'].isin(major_boroughs)].copy()
df_facet['rush_hour_label'] = np.where(df_facet['is_rush_hour'] == 1, 'Peak Rush Hour', 'Off-Peak')

g = sns.FacetGrid(df_facet, col='pickup_borough', row='rush_hour_label', 
                  hue='rush_hour_label', palette={'Peak Rush Hour': '#E74C3C', 'Off-Peak': '#3498DB'},
                  height=3.5, aspect=1.3, margin_titles=True)
g.map(sns.scatterplot, 'distance_capped', 'fare_capped', alpha=0.45, s=20)
g.add_legend(title='Commute Status')
g.fig.suptitle('Figure 8: Faceted Spatial-Temporal Interaction: Distance vs. Fare by Origin Borough & Rush Hour', y=1.03)
g.set_axis_labels('Trip Distance (miles)', 'Base Fare ($)')
fig8_path = os.path.join(FIG_DIR, 'eda_fig8_faceted_borough_rush_hour.png')
g.savefig(fig8_path, dpi=300)
plt.close()
print(f"Saved: {fig8_path}")

# ==============================================================================
# VISUALIZATION 9: Clustered Correlation Dendrogram
# ==============================================================================
print("\n[EDA 9] Generating Clustered Heatmap Dendrogram...")
num_cols = ['distance_capped', 'duration_capped', 'fare_capped', 'tip_capped', 
            'tolls', 'total', 'speed_mph', 'fare_per_minute', 'fare_per_mile']
corr = df[num_cols].corr()

cg = sns.clustermap(corr, cmap='vlag', vmin=-0.6, vmax=1.0, annot=True, fmt='.2f',
                    figsize=(9, 8), dendrogram_ratio=(.15, .15), cbar_pos=(0.02, 0.8, 0.04, 0.18),
                    linewidths=0.5)
cg.fig.suptitle('Figure 9: Hierarchically Clustered Correlation Matrix of Kinematic and Financial Features', y=1.02)
fig9_path = os.path.join(FIG_DIR, 'eda_fig9_clustered_correlation_heatmap.png')
cg.savefig(fig9_path, dpi=300)
plt.close()
print(f"Saved: {fig9_path}")

# ==============================================================================
# VISUALIZATION 10: Multi-Passenger Party Size Analysis
# ==============================================================================
print("\n[EDA 10] Generating Multi-Passenger Behavioral Dynamics...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

passenger_counts = df['passengers'].value_counts().sort_index()
sns.barplot(x=passenger_counts.index, y=passenger_counts.values, ax=ax1, palette='Blues_d', edgecolor='black')
ax1.set_title('A: Party Size Frequency Distribution', pad=10)
ax1.set_xlabel('Passenger Count')
ax1.set_ylabel('Number of Trips')
for p in ax1.patches:
    pct = (p.get_height() / len(df)) * 100
    ax1.annotate(f"{int(p.get_height())}\n({pct:.1f}%)", (p.get_x() + p.get_width() / 2., p.get_height() + 25),
                 ha='center', va='bottom', fontsize=8.5, fontweight='bold')

# Mean distance and fare by party size
pass_economics = df.groupby('passengers').agg(mean_distance=('distance_capped', 'mean'), mean_fare=('fare_capped', 'mean')).reset_index()
ax2_twin = ax2.twinx()
b1 = ax2.bar(pass_economics['passengers'] - 0.15, pass_economics['mean_distance'], width=0.3, color='#3498DB', label='Mean Distance (miles)')
b2 = ax2_twin.bar(pass_economics['passengers'] + 0.15, pass_economics['mean_fare'], width=0.3, color='#E67E22', label='Mean Fare ($)')
ax2.set_xlabel('Passenger Count')
ax2.set_ylabel('Distance (miles)', color='#3498DB')
ax2_twin.set_ylabel('Base Fare ($)', color='#E67E22')
ax2.set_title('B: Trip Distance and Fare by Party Size', pad=10)
ax2.set_xticks(pass_economics['passengers'])
ax2.grid(False)

plt.suptitle('Figure 10: Socio-Demographic Travel Patterns: Solo Commuters vs. Shared Group Mobility', y=1.02)
plt.tight_layout()
fig10_path = os.path.join(FIG_DIR, 'eda_fig10_passenger_party_size_dynamics.png')
plt.savefig(fig10_path)
plt.close()
print(f"Saved: {fig10_path}")

# ==============================================================================
# STATISTICAL HYPOTHESIS TESTING & METRIC EXPORT
# ==============================================================================
print("\n" + "="*80)
print("STATISTICAL HYPOTHESIS TESTING")
print("="*80)

# Test 1: Does velocity significantly differ between Rush Hour and Off-Peak?
speed_rush = df[df['is_rush_hour'] == 1]['speed_mph']
speed_offpeak = df[df['is_rush_hour'] == 0]['speed_mph']
t_stat_speed, p_val_speed = stats.ttest_ind(speed_rush, speed_offpeak, equal_var=False)
print(f"Rush Hour Speed: {speed_rush.mean():.2f} mph vs Off-Peak: {speed_offpeak.mean():.2f} mph (t={t_stat_speed:.3f}, p={p_val_speed:.4e})")

# Test 2: Does tip percentage differ across party sizes on credit cards?
groups_tip = [group['tip_percentage_capped'].values for name, group in df_credit.groupby('passengers') if len(group) > 30]
kruskal_tip, p_val_tip = stats.kruskal(*groups_tip)
print(f"Kruskal-Wallis Tip % by Party Size: H={kruskal_tip:.3f}, p={p_val_tip:.4f}")

# Test 3: Yellow vs Green unit revenue ($/mile)
fare_mile_yellow = df[df['color'] == 'yellow']['fare_per_mile'].dropna()
fare_mile_green = df[df['color'] == 'green']['fare_per_mile'].dropna()
mwu_stat, p_val_mwu = stats.mannwhitneyu(fare_mile_yellow, fare_mile_green)
print(f"Mann-Whitney U Yellow vs Green Fare/Mile: U={mwu_stat:.1f}, p={p_val_mwu:.4e}")

# Export EDA summary metrics
eda_metrics = {
    'total_records': len(df),
    'mean_distance': float(df['distance_capped'].mean()),
    'median_distance': float(df['distance_capped'].median()),
    'mean_fare': float(df['fare_capped'].mean()),
    'median_fare': float(df['fare_capped'].median()),
    'mean_duration': float(df['duration_capped'].mean()),
    'mean_speed': float(df['speed_mph'].mean()),
    'rush_speed_mean': float(speed_rush.mean()),
    'offpeak_speed_mean': float(speed_offpeak.mean()),
    'p_val_speed_ttest': float(p_val_speed),
    'credit_card_count': int(len(df_credit)),
    'mean_credit_tip_pct': float(df_credit['tip_percentage_capped'].mean()),
    'median_credit_tip_pct': float(df_credit['tip_percentage_capped'].median()),
    'p_val_tip_kruskal': float(p_val_tip),
    'airport_trip_count': int((df['is_airport_trip'] == 1).sum()),
    'airport_mean_fare': float(df[df['is_airport_trip'] == 1]['fare_capped'].mean()),
    'non_airport_mean_fare': float(df[df['is_airport_trip'] == 0]['fare_capped'].mean()),
    'airport_mean_toll': float(df[df['is_airport_trip'] == 1]['tolls'].mean()),
    'non_airport_mean_toll': float(df[df['is_airport_trip'] == 0]['tolls'].mean()),
    'solo_rider_pct': float((df['passengers'] == 1).sum() / len(df) * 100),
    'yellow_cab_count': int((df['color'] == 'yellow').sum()),
    'green_cab_count': int((df['color'] == 'green').sum()),
    'yellow_mean_fare_mile': float(fare_mile_yellow.mean()),
    'green_mean_fare_mile': float(fare_mile_green.mean()),
}

metrics_json_path = os.path.join(BASE_DIR, 'week2_eda_metrics.json')
with open(metrics_json_path, 'w') as f:
    json.dump(eda_metrics, f, indent=4)
print(f"Saved EDA metrics JSON to: {metrics_json_path}")
print("WEEK 2 EDA EXECUTION COMPLETE!")
