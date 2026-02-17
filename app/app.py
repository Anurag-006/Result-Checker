from flask import Flask, render_template, Response, request
import requests
from bs4 import BeautifulSoup
import io
import csv
import concurrent.futures
import re
from functools import partial
import json

app = Flask(__name__)
BASE_URL = "https://vnrvjietexams.net/eduprime3exam/Results/Results"

# In-Memory Cache to prevent overloading the college server
CACHE = {}
AVAILABLE_EXAMS = {}

# Exact section mapping limits based on your Excel sheets
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

import urllib3
# Add this line at the top of your file to hide annoying SSL warnings in your terminal
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_active_exams():
    """Extracts Exam IDs directly from the hidden JSON script on the college site."""
    global AVAILABLE_EXAMS
    if AVAILABLE_EXAMS:
        return AVAILABLE_EXAMS
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        main_url = "https://vnrvjietexams.net/EduPrime3Exam/Results"
        response = requests.get(main_url, headers=headers, timeout=10, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            exams = {}
            
            # Search through all script tags on the page
            for script in soup.find_all('script'):
                if script.string and 'var data =' in script.string:
                    # Isolate the JSON part from the script text
                    json_text = script.string.split('var data =')[1].strip()
                    
                    # Remove the trailing semicolon so it becomes valid JSON
                    if json_text.endswith(';'):
                        json_text = json_text[:-1]
                        
                    # Parse the JSON string into a Python Dictionary
                    exam_list = json.loads(json_text)
                    
                    # Loop through every exam in their database
                    for exam in exam_list:
                        exam_id = str(exam.get('ExamId'))
                        exam_name = exam.get('ExamName')
                        
                        # Only grab B.Tech exams
                        if exam_id and exam_name and "B.TECH" in exam_name.upper():
                            exams[exam_id] = exam_name
            
            if exams:
                AVAILABLE_EXAMS = exams
                print(f"✅ Successfully loaded {len(exams)} dynamic exams from JSON!")
                return exams
            else:
                print("❌ Found the script, but couldn't extract the exams.")
        else:
            print(f"❌ Server Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        
    return {"7463": "Default Exam (Failed to load dynamic list)"}

def get_sequence_strings(start_idx, end_idx):
    """Generates alphanumeric sequences skipping I, L, O, and S."""
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
    rolls = []
    section = SECTION_INFO.get(section_key)
    if not section: return []

    branch_code = section["code"]
    
    # Regular
    reg_seq = get_sequence_strings(section["reg_start"], section["reg_end"])
    for seq in reg_seq:
        rolls.append(f"{year_prefix}071A{branch_code}{seq}")
    
    # Lateral Entry
    lat_prefix = str(int(year_prefix) + 1)
    lat_seq = get_sequence_strings(section["lat_start"], section["lat_end"])
    for seq in lat_seq:
        rolls.append(f"{lat_prefix}075A{branch_code}{seq}")
    
    return rolls

def get_student_data(htno, exam_id):
    # Standard 10-point scale mapping
    GRADE_POINTS = {
        'O': 10, 'A+': 9, 'A': 8, 
        'B+': 7, 'B': 6, 'C': 5, 
        'F': 0, 'AB': 0, 'ABSENT': 0
    }
    
    try:
        response = requests.get(BASE_URL, params={'htno': htno, 'examId': exam_id}, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            page_text = soup.get_text().lower()
            if "withheld" in page_text:
                return {'roll': htno, 'name': "Result Withheld", 'sgpa': "Withheld", 'subjects': []}

            name_tag = soup.find(string=lambda t: t and "Student Name" in t)
            if not name_tag: return None 
            
            name = name_tag.parent.find_next('td').get_text(strip=True).replace(":", "")
            if name == "Unknown" or not name:
                return {'roll': htno, 'name': "Result Withheld", 'sgpa': "Withheld", 'subjects': []}

            sgpa_tag = soup.find(string=lambda t: t and "SGPA" in t)
            sgpa = sgpa_tag.parent.find_next('td').get_text(strip=True).replace(":", "") if sgpa_tag else "0.00"
            if not sgpa: sgpa = "0.00"

            subjects = []
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')[1:]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 6:
                        grade_letter = cols[4].text.strip()
                        # Get the numeric point, default to "-" if it's a weird character
                        numeric_point = GRADE_POINTS.get(grade_letter.upper(), "-")
                        
                        subjects.append({
                            'code': cols[1].text.strip(),
                            'title': cols[2].text.strip(),
                            'grade': grade_letter,
                            'points': numeric_point,  # <-- NEW: Added points here!
                            'result': cols[-1].text.strip()
                        })
            return {'roll': htno, 'name': name, 'sgpa': sgpa, 'subjects': subjects}
    except Exception as e:
        pass 
    return None

def fetch_all_students(roll_numbers, exam_id):
    results = []
    fetch_func = partial(get_student_data, exam_id=exam_id)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        for data in executor.map(fetch_func, roll_numbers):
            if data: 
                results.append(data)
    return results

def safe_sgpa(student):
    """Sort helper to ensure 'Withheld' goes to the bottom."""
    try: return float(student['sgpa'])
    except: return -1.0 

@app.route('/')
def index():
    selected_section = request.args.get('section', 'CSBS') 
    year = request.args.get('year', '23')
    
    available_exams = fetch_active_exams()
    default_exam = list(available_exams.keys())[0] if available_exams else "7463"
    selected_exam = request.args.get('exam', default_exam)
    
    cache_key = f"{selected_section}_{year}_{selected_exam}"
    
    if cache_key in CACHE:
        class_results = CACHE[cache_key]
    else:
        roll_numbers = generate_roll_numbers(year, selected_section)
        class_results = fetch_all_students(roll_numbers, selected_exam)
        class_results.sort(key=safe_sgpa, reverse=True)
        CACHE[cache_key] = class_results
        
    return render_template('dashboard.html', 
                           students=class_results, 
                           sections=SECTION_INFO.keys(), 
                           selected_section=selected_section,
                           selected_year=year,
                           available_exams=available_exams,
                           selected_exam=selected_exam)

@app.route('/friends', methods=['GET', 'POST'])
def friends_leaderboard():
    rolls_input = request.form.get('roll_numbers', '')
    class_results = []
    
    available_exams = fetch_active_exams()
    default_exam = list(available_exams.keys())[0] if available_exams else "7463"
    
    # --- FIXED: Check the POST form data first, then GET args, then default ---
    selected_exam = request.form.get('exam') or request.args.get('exam') or default_exam
    
    if rolls_input:
        raw_rolls = re.findall(r'[a-zA-Z0-9]{10}', rolls_input)
        valid_rolls = list(set([r.upper() for r in raw_rolls]))
        
        if valid_rolls:
            class_results = fetch_all_students(valid_rolls, selected_exam)
            class_results.sort(key=safe_sgpa, reverse=True)

    return render_template('friends.html', 
                           students=class_results, 
                           saved_input=rolls_input,
                           available_exams=available_exams,
                           selected_exam=selected_exam)

@app.route('/report/<roll_no>')
def report_card(roll_no):
    available_exams = fetch_active_exams()
    default_exam = list(available_exams.keys())[0] if available_exams else "7463"
    selected_exam = request.args.get('exam', default_exam)
    
    student = get_student_data(roll_no, selected_exam)
    return render_template('report_card.html', student=student)

@app.route('/export')
def export_csv():
    selected_section = request.args.get('section', 'CSBS')
    year = request.args.get('year', '23')
    
    available_exams = fetch_active_exams()
    default_exam = list(available_exams.keys())[0] if available_exams else "7463"
    selected_exam = request.args.get('exam', default_exam)
    
    cache_key = f"{selected_section}_{year}_{selected_exam}"
    
    if cache_key in CACHE:
        all_student_data = CACHE[cache_key]
    else:
        roll_numbers = generate_roll_numbers(year, selected_section)
        all_student_data = fetch_all_students(roll_numbers, selected_exam)
        all_student_data.sort(key=safe_sgpa, reverse=True)

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
            
        if student['name'] == "Result Withheld":
            verdict = "WITHHELD"
        else:
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
    # Using 0.0.0.0 so anyone on the same Wi-Fi can access it using your IP Address
    app.run(host='127.0.0.1', port=5000, debug=True)