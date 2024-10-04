import csv
import os

# Function to write test data to a CSV file with headers and values
def write_test_data_to_file(data_dict, filename='test_data.csv'):
    path = f"./data/test_results/{filename}" 
    file_exists = os.path.isfile(path)
    
    try:
        with open(path, mode='a', newline='') as file:  # 'a' mode for appending data
            writer = csv.writer(file)
            # Write the header only if the file does not exist
            if not file_exists:
                writer.writerow(data_dict.keys())  # Write keys as header row
            
            # Write the values
            writer.writerow(data_dict.values())  # Write values in the next row
        print(f"Data successfully written to {filename}")
    
    except Exception as e:
        print(f"An error occurred while writing to file: {e}")

# Example test data dictionary
test_data = {
    'test_name': 'Test Run 1',
    'execution_time': 45.6,
    'result': 'Success',
    'num_customers': 100,
    'total_cost': 1234.56,
    'max_time': 45,
}


    
    
    
    
    
    