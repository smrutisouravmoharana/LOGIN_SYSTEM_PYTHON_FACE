import cv2
import os
import face_recognition
import datetime
from connection import conn
from flask import Flask, render_template, request, jsonify

UPLOAD_FOLDER = 'static/faces'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load known faces and their names from the 'faces' folder
known_faces = []
known_names = []

today = datetime.date.today().strftime("%d_%m_%y")

def get_known_encodings():
    global known_faces, known_names
    known_faces = []
    known_names = []

    for filename in os.listdir('static/faces'):
        image = face_recognition.load_image_file(os.path.join('static/faces', filename))
        face_encodings = face_recognition.face_encodings(image)

        # Check if any faces are detected
        if face_encodings:
            encodings = face_encodings[0]  # Use the first face if detected
            known_faces.append(encodings)
            known_names.append(os.path.splitext(filename)[0])

def totalreg():
    return len(os.listdir('static/faces/'))
# def extract_attendance():
#     results = conn.read(f"SELECT * FROM common_attendance WHERE date = '{today}'")
#     # Assuming the result is a tuple of tuples
#     attendance_data = [{'date': entry[0], 'name': entry[1], 'roll_no': entry[2], 'time': entry[3]} for entry in results]
#     return attendance_data

def extract_attendance():
    results = conn.read(f"SELECT * FROM common_attendance WHERE date = '{today}'")
    return results

def mark_attendance(person):
    name = person.split('_')[0]
    roll_no = int(person.split('_')[1])
    current_time = datetime.datetime.now().strftime('%H:%M:%S')

    exists = conn.read(f"SELECT * FROM common_attendance WHERE date = '{today}' AND roll_no = {roll_no}")
    if len(exists) == 0:
        try:
            conn.insert(f"INSERT INTO common_attendance (date, name, roll_no, time) VALUES (%s, %s, %s, %s)",
                        (today, name, roll_no, current_time))
        except Exception as e:
            print(e)

def identify_person():
    video_capture = cv2.VideoCapture(0)
    attendance_marked = False
    while True:
        ret, frame = video_capture.read()

        if not ret:
            print("Error reading frame from the camera.")
            break

        rgb_frame = frame[:, :, ::-1]

        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        face_encodings = face_recognition.face_encodings(rgb_frame, known_face_locations=face_locations, model="large")

        recognized_names = []

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_faces, face_encoding)
            name = 'Unknown'

            if True in matches:
                matched_indices = [i for i, match in enumerate(matches) if match]
                for index in matched_indices:
                    name = known_names[index]
                    recognized_names.append(name)

        if len(recognized_names) > 0:
            for name in recognized_names:
                mark_attendance(name)
            attendance_marked = True

        cv2.imshow('Camera', frame)

        if cv2.waitKey(1) & 0xFF == ord('q') or attendance_marked:
            break

    video_capture.release()
    cv2.destroyAllWindows()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        name = request.form['username']
        empid = request.form['empid']
        if 'file' not in request.files:
            return jsonify({"error": True, "msg": "No file found"})
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": True, "msg": "No file found"})
        if file and allowed_file(file.filename):
            filename = name+"_"+empid+".jpg"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            get_known_encodings()
            return jsonify({"error": False, "msg": "User Upload"})
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

@app.route('/')
def home():
    conn.create(f"CREATE TABLE IF NOT EXISTS common_attendance (date VARCHAR(8), name VARCHAR(30), roll_no INT, time VARCHAR(10))")
    userDetails = extract_attendance()
    get_known_encodings()
    return render_template('home.html', l=len(userDetails), today=today.replace("_", "-"), totalreg=totalreg(), userDetails=userDetails)

@app.route('/video_feed', methods=['GET'])
def video_feed():
    identify_person()
    userDetails = extract_attendance()
    return render_template('home.html', l=len(userDetails), today=today.replace("_", "-"), totalreg=totalreg(),
                           userDetails=userDetails)

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    name = request.form['newusername']
    roll_no = request.form['newrollno']
    userimagefolder = 'static/faces'
    if not os.path.isdir(userimagefolder):
        os.makedirs(userimagefolder)
    video_capture = cv2.VideoCapture(0)

    while True:
        ret, frame = video_capture.read()

        if not ret:
            print("Error reading frame from the camera.")
            break

        flipped_frame = cv2.flip(frame, 1)
        text = "Press q to capture & save the image"
        font = cv2.FONT_HERSHEY_COMPLEX
        font_scale = 0.9
        font_color = (0, 0, 200)
        thickness = 2

        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = (frame.shape[0] - 450)

        cv2.putText(flipped_frame, text, (text_x, text_y), font, font_scale, font_color, thickness, cv2.LINE_AA)
        cv2.imshow('Camera', flipped_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            img_name = name + '_' + str(roll_no) + '.jpg'
            cv2.imwrite(userimagefolder + '/' + img_name, flipped_frame)
            break

    video_capture.release()
    cv2.destroyAllWindows()

    userDetails = extract_attendance()
    get_known_encodings()
    return render_template('home.html', l=len(userDetails), today=today.replace("_", "-"), totalreg=totalreg(),
                           userDetails=userDetails)


@app.route('/api/data', methods=['GET'])
def get_attendance_data():
    attendance_data = extract_attendance()

    # Convert the data to a list of dictionaries for JSON serialization
    formatted_data = []
    for entry in attendance_data:
        formatted_entry = {
            'date': entry['date'],
            'name': entry['name'],
            'roll_no': entry['roll_no'],
            'time': entry['time']
        }
        formatted_data.append(formatted_entry)

    return jsonify({'data': formatted_data})
@app.route('/api/get_all_data', methods=['GET'])
def get_all_data():
    # Extract all data from the common_attendance table
    results = conn.read("SELECT * FROM common_attendance")

    # Assuming the result is a list of tuples
    attendance_data = [
        {'date': entry[0], 'name': entry[1], 'roll_no': entry[2], 'time': entry[3]} for entry in results
    ]

    return jsonify({'data': attendance_data})
if __name__ == '__main__':
    app.run(port=81, debug=True)


