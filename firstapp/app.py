from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import time

app = Flask(__name__)

EXAM_ID = "7489"
BASE_URL = "https://vnrvjietexams.net/eduprime3exam/Results/Results"

def get_student_data(htno):
    """Helper to scrape data for a single student."""
    try:
        response = requests.get(BASE_URL, params={'htno': htno, 'examId': EXAM_ID}, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract basic info
            name_tag = soup.find(text=lambda t: "Student Name" in t)
            name = name_tag.parent.find_next('td').get_text(strip=True).replace(":", "") if name_tag else "Unknown"
            
            sgpa_tag = soup.find(text=lambda t: "SGPA" in t)
            sgpa = sgpa_tag.parent.find_next('td').get_text(strip=True).replace(":", "") if sgpa_tag else "N/A"

            # Extract subjects table
            if (name == "Unknown"):
                return None
            if (not sgpa):
                sgpa = "0.00"

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
        print(f"Error scraping {htno}: {e}")
    return None

def getCsbsRollNumbers(year):
    roll_numbers = []
    baseString = "2"+str(year)+"071A32"

    # Regular students.
    for i in range(1, 10):
        curr = baseString + "0" + str(i)
        roll_numbers.append(curr)
    
    for i in range(10, 65):
        curr = baseString + str(i)
        roll_numbers.append(curr)
    
    # Lateral Entry.
    for i in range(1, 9):
        curr = "2"+str(year+1)+"075A320"+str(i)
        roll_numbers.append(curr)

    return roll_numbers

@app.route('/')
def index():
    roll_numbers = getCsbsRollNumbers(3)
    class_results = []
    
    for htno in roll_numbers:
        data = get_student_data(htno)
        if data:
            class_results.append(data)
    
    class_results.sort(key=lambda x: x['sgpa'], reverse=True)
    return render_template('dashboard.html', students=class_results)

@app.route('/report/<roll_no>')
def report_card(roll_no):
    # This route handles the detailed view for a single student
    student = get_student_data(roll_no)
    return render_template('report_card.html', student=student)

if __name__ == '__main__':
    app.run(debug=True)