from hashlib import new
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__, static_folder='../front_end')
CORS(app)

# Paths to JSON files
FLIGHTS_FILE = os.path.join(os.path.dirname(__file__), 'flights.json')
USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')

# Read flight data from JSON
def load_flights():
    if not os.path.exists(FLIGHTS_FILE):
        return []
    with open(FLIGHTS_FILE, 'r') as file:
        return json.load(file)

# Save flight data to JSON
def save_flights(flights):
    with open(FLIGHTS_FILE, 'w') as file:
        json.dump(flights, file, indent=4)

# Load user data from JSON
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r') as file:
        return json.load(file)

@app.route('/')
def home():
    return send_from_directory('../front_end', 'login.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    users = load_users()
    for user in users:
        if user['username'] == data['username'] and user['password'] == data['password']:
            return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid username or password"}), 401

@app.route('/api/flights', methods=['GET'])
def get_flights():
    flights = load_flights()
    for f in flights:
        if 'number' not in f and 'flightNumber' in f:
            f['number'] = f['flightNumber']
    return jsonify(flights)

@app.route('/api/flights/<flight_number>', methods=['DELETE'])
def delete_flight(flight_number):
    flights = load_flights()
    flights = [f for f in flights if str(f.get('number')) != str(flight_number)]
    save_flights(flights)
    return jsonify({"message": "Flight deleted successfully"})

@app.route('/api/flights', methods=['POST'])
def add_flight():
    data = request.json
    flights = load_flights()
    flight = {
        "number": data.get("flightNumber") or data.get("number"),
        "source": data.get("source"),
        "departure": data.get("departure"),
        "destination": data.get("destination"),
        "arrival": data.get("arrival"),
        "airline": data.get("airline"),
        "hallStation": data.get("hallStation", ""),
        "hallTime": data.get("hallTime", ""),
        "priority": int(data.get("priority", 5)) if "priority" in data else 5
    }
    flights.append(flight)
    save_flights(flights)
    print(f"New flight added: {flight}")
    return jsonify({"message": "Flight added successfully"}), 201

@app.route('/api/schedule', methods=['POST'])
def schedule_flights():
    data = request.json
    algorithm = data.get('algorithm', 'fcfs')
    flights = load_flights()

    # FCFS: First Come First Serve (by departure time, manual selection sort)
    if algorithm == 'fcfs':
        scheduled = []
        unscheduled = flights[:]
        while unscheduled:
            earliest = unscheduled[0]
            for flight in unscheduled:
                if flight.get('departure', '') < earliest.get('departure', ''):
                    earliest = flight
            scheduled.append(earliest)
            unscheduled.remove(earliest)
        flights = scheduled

    # SJF: Shortest Job First (by duration, manual selection sort)
    elif algorithm == 'sjf':
        def get_duration(f):
            try:
                dep = f.get('departure', '00:00')
                arr = f.get('arrival', '00:00')
                dep_h, dep_m = map(int, dep.split(':'))
                arr_h, arr_m = map(int, arr.split(':'))
                return (arr_h * 60 + arr_m) - (dep_h * 60 + dep_m)
            except Exception:
                return 0
        scheduled = []
        unscheduled = flights[:]
        while unscheduled:
            shortest = unscheduled[0]
            for flight in unscheduled:
                if get_duration(flight) < get_duration(shortest):
                    shortest = flight
            scheduled.append(shortest)
            unscheduled.remove(shortest)
        flights = scheduled

    # Priority: by priority field (lower number = higher priority, manual selection sort)
    elif algorithm == 'priority':
        scheduled = []
        unscheduled = flights[:]
        while unscheduled:
            highest = unscheduled[0]
            for flight in unscheduled:
                if int(flight.get('priority', 5)) < int(highest.get('priority', 5)):
                    highest = flight
            scheduled.append(highest)
            unscheduled.remove(highest)
        flights = scheduled

    # After scheduling, assign the SAME dateOfSchedule to all flights (e.g., today)
    MAX_FLIGHTS_PER_DAY = 3
    schedule_date = datetime.today().date()
    for idx, flight in enumerate(flights):
        flight['dateOfSchedule'] = str(schedule_date + timedelta(days=idx // MAX_FLIGHTS_PER_DAY))

    # Calculate waiting and turnaround time
    prev_arrival = None
    for idx, flight in enumerate(flights):
        dep_h, dep_m = map(int, flight['departure'].split(':'))
        arr_h, arr_m = map(int, flight['arrival'].split(':'))
        dep_minutes = dep_h * 60 + dep_m
        arr_minutes = arr_h * 60 + arr_m
        # Turnaround time = arrival - departure
        flight['turnaroundTime'] = arr_minutes - dep_minutes
        # Waiting time = time from previous arrival to this departure (for first flight, 0)
        if idx == 0:
            flight['waitingTime'] = 0
        else:
            prev_arrival_minutes = prev_arrival
            flight['waitingTime'] = max(0, dep_minutes - prev_arrival_minutes)
        prev_arrival = arr_minutes

    return jsonify(flights)

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('../front_end', filename)

if __name__ == '__main__':
    app.run(debug=True)
