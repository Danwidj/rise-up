import sqlite3
import os
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent.parent.parent / "reports"
DB_PATH = DB_DIR / "incidents.db"

def get_connection():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_key TEXT NOT NULL,
            incident_type TEXT NOT NULL,
            start_timestamp TEXT NOT NULL,
            end_timestamp TEXT NOT NULL,
            severity INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 5),
            confidence_score REAL NOT NULL CHECK (confidence_score BETWEEN 0 AND 100),
            summary TEXT NOT NULL,
            poi_detected TEXT NOT NULL,
            instruments_detected TEXT NOT NULL,
            location TEXT NOT NULL,
            verification_status TEXT NOT NULL CHECK (verification_status IN ('Verified', 'Under Review', 'Unreviewed')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if we need to insert mock data
    cursor.execute("SELECT COUNT(*) FROM incidents")
    count = cursor.fetchone()[0]
    
    if count == 0:
        mock_data = [
            (
                "anomaly/abuse/Abuse001_x264.mp4",
                "Abuse",
                "00:12",
                "00:45",
                3,
                92.5,
                "A verbal altercation escalates into physical pushing between two individuals near the customer service desk. The suspect, wearing a red cap and a grey jacket, aggressively confronts the victim. No weapons were visible.",
                "Male, red cap, grey jacket, jeans",
                "None",
                "Customer Service Lobby",
                "Verified"
            ),
            (
                "anomaly/shooting/Shooting002_x264.mp4",
                "Shooting",
                "00:05",
                "00:30",
                5,
                98.0,
                "Armed individual enters from the west corridor and fires multiple rounds at the security door. The suspect immediately flees the scene. Tactical security response team was dispatched within 12 seconds.",
                "Male, black tactical gear, ski mask",
                "Handgun",
                "West Corridor / Loading Bay",
                "Under Review"
            ),
            (
                "anomaly/stealing/Stealing002_x264.mp4",
                "Stealing",
                "00:20",
                "01:20",
                2,
                89.4,
                "Suspect is seen shoplifting electronics from the display shelves. The individual slips three items into a large yellow handbag while blocking the view of the nearby camera with their body.",
                "Female, yellow coat, dark hair, large tote bag",
                "None",
                "Electronics Aisle 4",
                "Unreviewed"
            ),
            (
                "anomaly/fighting/Fighting003_x264.mp4",
                "Fighting",
                "00:15",
                "00:50",
                4,
                95.0,
                "A group fight involving four individuals breaks out in the middle of the parking lot. Security personnel arrive on site to disperse the crowd. Local police notified.",
                "Group of 4 young adult males in dark clothing",
                "Baseball Bat",
                "East Parking Lot",
                "Verified"
            ),
            (
                "anomaly/vandalism/Vandalism001_x264.mp4",
                "Vandalism",
                "00:30",
                "01:10",
                3,
                87.2,
                "Two suspects spray paint graffiti on the storefront glass windows during early morning hours. They fled when the exterior floodlights activated.",
                "Two individuals, hoods up, carrying backpacks",
                "Spray Paint Can",
                "Front Storefront Window",
                "Unreviewed"
            ),
            (
                "anomaly/robbery/Robbery001_x264.mp4",
                "Robbery",
                "00:10",
                "00:40",
                5,
                97.5,
                "Armed robbery at the main jewelry counter. A masked suspect wielding a hammer smashes the showcase glass and grabs several high-value items before exiting through the north door.",
                "Male, black hoodie, white sneakers, face mask",
                "Hammer",
                "Jewelry Counter A",
                "Verified"
            )
        ]
        cursor.executemany("""
            INSERT INTO incidents (
                video_key, incident_type, start_timestamp, end_timestamp,
                severity, confidence_score, summary, poi_detected,
                instruments_detected, location, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, mock_data)
        conn.commit()
        
    conn.close()

def get_all_reports():
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_report_by_id(report_id):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_report(video_key, incident_type, start_timestamp, end_timestamp, severity, confidence_score, summary, poi_detected, instruments_detected, location, verification_status):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO incidents (
            video_key, incident_type, start_timestamp, end_timestamp,
            severity, confidence_score, summary, poi_detected,
            instruments_detected, location, verification_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (video_key, incident_type, start_timestamp, end_timestamp, severity, confidence_score, summary, poi_detected, instruments_detected, location, verification_status))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def update_report(report_id, incident_type, start_timestamp, end_timestamp, severity, confidence_score, summary, poi_detected, instruments_detected, location, verification_status):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE incidents
        SET incident_type = ?,
            start_timestamp = ?,
            end_timestamp = ?,
            severity = ?,
            confidence_score = ?,
            summary = ?,
            poi_detected = ?,
            instruments_detected = ?,
            location = ?,
            verification_status = ?
        WHERE id = ?
    """, (incident_type, start_timestamp, end_timestamp, severity, confidence_score, summary, poi_detected, instruments_detected, location, verification_status, report_id))
    conn.commit()
    conn.close()

def delete_report(report_id):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM incidents WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
