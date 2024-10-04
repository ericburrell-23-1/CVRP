import pandas as pd

def generate_report(input_csv, output_csv, agg_funcs=None):
    # Read the input CSV into a pandas DataFrame
    df = pd.read_csv(input_csv)

    # Default aggregation functions for common columns
    if agg_funcs is None:
        agg_funcs = {
            'Num_customers': 'first',   # Keep the first value (since it should be the same across experiments)
            'Time_limit': 'mean',       # Use mean as an example, adjust as needed
            'LP_solve_time': 'mean',
            'ILP_solve_time': 'mean',
            # 'PGM_time': 'mean',
            'Pricing_time': 'mean',
            'Model_update_time': 'mean',
            'Preprocessing_time': 'mean',
            'LP_obj_val': 'mean',
            'ILP_obj_val': 'mean',
            'Total_time': 'mean',
            'CG_iterations': 'mean',
            # 'PGM_iterations': 'mean',
            #'RCI_constrs_added': 'mean'
        }

    # Group data by Data_set and Capacity_divisor and apply aggregation functions
    grouped = df.groupby(['Data_set', 'Capacity_divisor']).agg(agg_funcs).reset_index()

    # If Algorithm is present, make it the header for the table (since it's the same for all entries)
    if 'Algorithm' in df.columns:
        algorithm = df['Algorithm'].iloc[0]  # Assume the Algorithm is the same for all rows in the file
        print(f"Generating report for Algorithm: {algorithm}")

    # Save the output CSV
    grouped.to_csv(output_csv, index=False)

    # Print to check the report
    print(f"Report saved to {output_csv}")
    print(grouped)

# Example usage

