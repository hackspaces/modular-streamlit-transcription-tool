import hashlib
import csv
import os

#Calculate file hash
def calculate_file_hash(file_data):
    hasher = hashlib.sha256()
    hasher.update(file_data)
    return hasher.hexdigest()

# Write file hash to CSV
def write_hash_to_csv(file_hash, filename):
    with open('file_hashes.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([file_hash, filename])

# Read file hashes from CSV
def read_hashes_from_csv():
    if not os.path.exists('file_hashes.csv'):
        return set()
    with open('file_hashes.csv', 'r', newline='') as file:
        reader = csv.reader(file)
        return {row[0] for row in reader if len(row) > 0}
    
# Delete file hash from CSV
def delete_hash_from_csv():
    """
    Clears all the file hash from file_hashes.csv.
    """
    # Read all rows except the one with the matching hash
    # Rewrite file_hashes.csv without the deleted file's hash
    with open('file_hashes.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["hash", "filename"])  # Writing only the headers