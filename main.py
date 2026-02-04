import requests
from bs4 import BeautifulSoup
import csv
import time

# Configuration
EXAM_ID = "7460"
BASE_URL = "https://vnrvjietexams.net/eduprime3exam/Results/Results"
roll_numbers = [f"24071A32{str(i).zfill(2)}" for i in range(1, 65)]

# Define the filename
filename = "Class_Results.csv"

# Open the file in 'write' mode
with open(filename, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    
    # Write the Header Row
    writer.writerow(["Roll No", "Subject", "Grade", "Result"])

    for htno in roll_numbers:
        print(f"Fetching: {htno}")
        params = {'htno': htno, 'examId': EXAM_ID}
        
        try:
            response = requests.get(BASE_URL, params=params)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table')
                
                if table:
                    rows = table.find_all('tr')[1:]
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 6:
                            # Extract data directly into a list
                            subject = cols[2].get_text(strip=True)
                            grade = cols[4].get_text(strip=True)
                            result = cols[-1].get_text(strip=True)
                            
                            # Write the row immediately to the CSV
                            writer.writerow([htno, subject, grade, result])
                else:
                    print(f"No data for {htno}")
            
            # Anti-block delay
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"Failed {htno}: {e}")

print(f"\nDone! You can now open '{filename}' in Excel.")