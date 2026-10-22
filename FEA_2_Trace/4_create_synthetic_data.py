import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from itertools import product


data_file = 'results/grouped_avg_results_v4.csv'
output_filename = 'results/synthetic_heliostat_data_v4.csv'

# --- 1. Load Your Data ---
# Make sure the file 'grouped_avg_results_v2.csv' is in the same directory
try:
    df_orig = pd.read_csv(data_file)
except FileNotFoundError:
    print(f"Error: '{data_file}' not found.")
    print("Please make sure the file is in the same directory as the script.")
    exit()

# --- 2. Define the Full Experimental Design ---
elevation = np.arange(0, 90 + 15, 15)
azimuth = np.arange(0, 180 + 15, 15)
wind_speed = np.arange(4, 16 + 4, 4)

full_design = pd.DataFrame(
    product(elevation, azimuth, wind_speed),
    columns=['expected_elevation_angle_deg', 'expected_azimuth_angle_deg', 'wind_speed_mps']
)

# --- 3. Identify Missing Data ---
# These are the columns used to identify unique experimental conditions
input_cols = ['expected_elevation_angle_deg', 'expected_azimuth_angle_deg', 'wind_speed_mps']

# These are the columns that the model will predict
output_cols = [
    'avg_facet_normal_x', 'avg_facet_normal_y', 'avg_facet_normal_z',
    'elevation_angle_deg', 'el_tracking_error_mrad', 'azimuth_angle_deg',
    'az_tracking_error_mrad', 'total_tracking_error_mrad',
    'slope_error_mean_mrad', 'slope_error_std_mrad',
    'slope_error_mean_weighted_mrad', 'slope_error_std_weighted_mrad'
]

merged_df = pd.merge(
    full_design,
    df_orig,
    on=input_cols,
    how='left',
    indicator=True
)

missing_cases = merged_df[merged_df['_merge'] == 'left_only'][input_cols]

# --- 4. Train Models and Predict ---
# Prepare the training data
X_train = df_orig[input_cols]

# Create a copy to store the new synthetic data
synthetic_data = missing_cases.copy()

print("Training models and generating synthetic data...")

# Train a separate model for each output column
for col in output_cols:
    print(f"  - Predicting column: {col}")
    y_train = df_orig[col]
    
    # Initialize and train the Random Forest model
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    # Predict the values for the missing cases
    predictions = model.predict(missing_cases)
    synthetic_data[col] = predictions

print("Synthetic data generation complete.")

# --- 5. Combine and Save the Final Dataset ---
# Combine your original data with the newly generated synthetic data
final_df = pd.concat([df_orig, synthetic_data], ignore_index=True)
final_df = final_df.sort_values(by=input_cols).reset_index(drop=True)

# Save the complete dataset to a new CSV file
final_df.to_csv(output_filename, index=False)

print(f"\nSuccessfully created the final dataset: '{output_filename}'")