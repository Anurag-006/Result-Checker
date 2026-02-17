from flask import Flask, render_template, Response, request
import requests
from bs4 import BeautifulSoup
import io
import csv
import concurrent.futures

app = Flask(__name__)

EXAM_ID = "7463"
BASE_URL = "https://vnrvjietexams.net/eduprime3exam/Results/Results"

# Maps EXACTLY to the individual sheets in your Excel file
# We define the start and end indices so it limits the scraping to just that section.
SECTION_INFO = {
    "AE": {"code": "24", "reg_start": 1, "reg_end": 66, "lat_start": 1, "lat_end": 6},
    "AIDS": {"code": "72", "reg_start": 1, "reg_end": 66, "lat_start": 1, "lat_end": 6},
    "CE-1": {"code": "01", "reg_start": 1, "reg_end": 64, "lat_start": 1, "lat_end": 6},
    "CE-2": {"code": "01", "reg_start": 65, "reg_end": 128, "lat_start": 7, "lat_end": 12},
    "CSBS": {"code": "32", "reg_start": 1, "reg_end": 66, "lat_start": 1, "lat_end": 9},
    "CSE-1": {"code": "05", "reg_start": 1, "reg_end": 68, "lat_start": 1, "lat_end": 6},
    "CSE-2": {"code": "05", "reg_start": 69, "reg_end": 136, "lat_start": 7, "lat_end": 12},
    "CSE-3": {"code": "05", "reg_start": 137, "reg_end": 204, "lat_start": 13, "lat_end": 18},
    "CSE-4": {"code": "05", "reg_start": 205, "reg_end": 272, "lat_start": 19, "lat_end": 24},
    "CSE-AIML-1": {"code": "66", "reg_start": 1, "reg_end": 66, "lat_start": 1, "lat_end": 6},
    "CSE-AIML-2": {"code": "66", "reg_start": 67, "reg_end": 132, "lat_start": 7, "lat_end": 12},
    "CSE-AIML-3": {"code": "66", "reg_start": 133, "reg_end": 198, "lat_start": 13, "lat_end": 18},
    "CSE-CYS": {"code": "62", "reg_start": 1, "reg_end": 66, "lat_start": 1, "lat_end": 6},
    "CSE-DS-1": {"code": "67", "reg_start": 1, "reg_end": 66, "lat_start": 1, "lat_end": 6},
    "CSE-DS-2": {"code": "67", "reg_start": 67, "reg_end": 132, "lat_start": 7, "lat_end": 12},
    "CSE-DS-3": {"code": "67", "reg_start": 133, "reg_end": 198, "lat_start": 13, "lat_end": 18},
    "CSE-IoT": {"code": "69", "reg_start": 1, "reg_end": 66, "lat_start": 1, "lat_end": 6},
    "ECE-1": {"code": "04", "reg_start": 1, "reg_end": 64, "lat_start": 1, "lat_end": 6},
    "ECE-2": {"code": "04", "reg_start": 65, "reg_end": 128, "lat_start": 7, "lat_end": 12},
    "ECE-3": {"code": "04", "reg_start": 129, "reg_end": 192, "lat_start": 13, "lat_end": 18},
    "ECE-4": {"code": "04", "reg_start": 193, "reg_end": 256, "lat_start": 19, "lat_end": 24},
    "EEE-1": {"code": "02", "reg_start": 1, "reg_end": 66, "lat_start": 1, "lat_end": 6},
    "EEE-2": {"code": "02", "reg_start": 67, "reg_end": 132, "lat_start": 7, "lat_end": 12},
    "EIE-1": {"code": "10", "reg_start": 1, "reg_end": 64, "lat_start": 1, "lat_end": 6},
    "EIE-2": {"code": "10", "reg_start": 65, "reg_end": 128, "lat_start": 7, "lat_end": 12},
    "IT-1": {"code": "12", "reg_start": 1, "reg_end": 66, "lat_start": 1, "lat_end": 6},
    "IT-2": {"code": "12", "reg_start": 67, "reg_end": 132, "lat_start": 7, "lat_end": 12},
    "IT-3": {"code": "12", "reg_start": 133, "reg_end": 200, "lat_start": 13, "lat_end": 18},
    "ME-1": {"code": "03", "reg_start": 1, "reg_end": 64, "lat_start": 1, "lat_end": 6},
    "ME-2": {"code": "03", "reg_start": 65, "reg_end": 128, "lat_start": 7, "lat_end": 12}
}

def get_sequence_strings(start_idx, end_idx):
    """Generates standard university sequences skipping I, L, O, and S for a specific slice."""
    valid_chars = "ABCDEFGHJKMNPQRTUVWXYZ"
    seq = []
    for i in range(start_idx, end_idx + 1):
        if i <= 99:
            seq.append(f"{i:02d}")
        else:
            offset = i - 100
            char = valid_chars[offset // 10]
            digit = offset % 10
            seq.append(f"{char}{digit}")
    return seq

def generate_roll_numbers(year_prefix, section_key):
    """Generates all roll combinations for a specific section."""
    rolls = []
    section = SECTION_INFO.get(section_key)
    if not section: return []

    branch_code = section["code"]
    
    # 1. Generate Regular Students for this section
    reg_seq = get_sequence_strings(section["reg_start"], section["reg_end"])
    for seq in reg_seq:
        rolls.append(f"{year_prefix}071A{branch_code}{seq}")
    
    # 2. Generate Lateral Entry Students for this section
    lat_prefix = str(int(year_prefix) + 1)
    lat_seq = get_sequence_strings(section["lat_start"], section["lat_end"])
    for seq in lat_seq:
        rolls.append(f"{lat_prefix}075A{branch_code}{seq}")
    
    return rolls

def get_student_data(htno):
    """Helper to scrape data for a single student."""
    try:
        response = requests.get(BASE_URL, params={'htno': htno, 'examId': EXAM_ID}, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- NEW: Check for withheld BEFORE checking for the name table ---
            page_text = soup.get_text().lower()
            if "withheld" in page_text:
                return {'roll': htno, 'name': "Result Withheld", 'sgpa': "Withheld", 'subjects': []}

            name_tag = soup.find(text=lambda t: "Student Name" in t)
            
            # If the name tag is missing and it's NOT withheld, the student doesn't exist.
            if not name_tag: 
                return None 
            
            name = name_tag.parent.find_next('td').get_text(strip=True).replace(":", "")
            
            if name == "Unknown" or not name:
                return {'roll': htno, 'name': "Result Withheld", 'sgpa': "Withheld", 'subjects': []}

            sgpa_tag = soup.find(text=lambda t: "SGPA" in t)
            sgpa = sgpa_tag.parent.find_next('td').get_text(strip=True).replace(":", "") if sgpa_tag else "0.00"
            if not sgpa: sgpa = "0.00"

            subjects = []
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')[1:]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 6:
                        subjects.append({
                            'code': cols[1].text.strip(),
                            'title': cols[2].text.strip(),
                            'grade': cols[4].text.strip(),
                            'result': cols[-1].text.strip()
                        })
            return {'roll': htno, 'name': name, 'sgpa': sgpa, 'subjects': subjects}
    except Exception as e:
        pass 
    return None

def fetch_all_students(roll_numbers):
    """Uses Multi-Threading to scrape results almost instantly."""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        for data in executor.map(get_student_data, roll_numbers):
            # We now keep ALL valid data objects, including withheld ones
            if data: 
                results.append(data)
    return results

@app.route('/')
def index():
    selected_section = request.args.get('section', 'CSBS') 
    year = request.args.get('year', '23')
    
    roll_numbers = generate_roll_numbers(year, selected_section)
    class_results = fetch_all_students(roll_numbers)
    
    # Safe sorting: Puts Withheld students at the bottom (treated as -1 SGPA)
    def safe_sgpa(student):
        try:
            return float(student['sgpa'])
        except (ValueError, TypeError):
            return -1.0 # Puts "Withheld" or "N/A" at the bottom of the list
            
    class_results.sort(key=safe_sgpa, reverse=True)
    
    return render_template('dashboard.html', 
                           students=class_results, 
                           sections=SECTION_INFO.keys(), 
                           selected_section=selected_section,
                           selected_year=year)

@app.route('/report/<roll_no>')
def report_card(roll_no):
    student = get_student_data(roll_no)
    return render_template('report_card.html', student=student)

@app.route('/export')
def export_csv():
    selected_section = request.args.get('section', 'CSBS')
    year = request.args.get('year', '23')
    roll_numbers = generate_roll_numbers(year, selected_section)
    
    all_student_data = fetch_all_students(roll_numbers)
    all_subject_titles = set()

    for data in all_student_data:
        if data['subjects']:
            for sub in data['subjects']:
                all_subject_titles.add(sub['title'])
    
    sorted_subjects = sorted(list(all_subject_titles))
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    header = ['Roll Number', 'Name'] + sorted_subjects + ['SGPA', 'Final Result']
    writer.writerow(header)
    
    for student in all_student_data:
        grade_map = {sub['title']: sub['grade'] for sub in student['subjects']}
        row = [student['roll'], student['name']]
        for subject in sorted_subjects:
            row.append(grade_map.get(subject, "N/A"))
            
        failed = any(sub['result'] == 'FAIL' for sub in student['subjects'])
        verdict = "FAIL" if failed else "PASS"
        
        row.extend([student['sgpa'], verdict])
        writer.writerow(row)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={selected_section}_Results.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True)