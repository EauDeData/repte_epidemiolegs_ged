import sqlite3
from typing import List, Dict

class ReportDatabase:
    def __init__(self, conn = None):
        if not conn:
            self.load_database()
        else:
            self.conn = conn
            self.cursor = self.conn.cursor()


    def load_database(self, db_name: str = 'tmp.sql'):
        """Loads an existing database"""
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dictionary-like row access
        self.cursor = self.conn.cursor()

    def create_database(self, db_name: str):
        """Creates a new database with the required schema"""
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Create the USER table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS USER (
                NIU TEXT PRIMARY KEY
            )
        """)

        # Create the TEAM table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS TEAM (
                team_name TEXT PRIMARY KEY,
                NIU TEXT,
                FOREIGN KEY (NIU) REFERENCES USER(NIU)
            )
        """)

        # Create the REPORT table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS REPORT (
                id_report INTEGER,
                team_name TEXT,
                reported_at TEXT,
                reported_from TEXT,
                total_error FLOAT,
                single_day_error FLOAT,
                five_days_error FLOAT,
                ten_days_error FLOAT,
                PRIMARY KEY (id_report, team_name),
                FOREIGN KEY (team_name) REFERENCES TEAM(team_name)
            )
        """)

        self.conn.commit()

    # -------------------- Data Insertion Methods --------------------
    def add_user(self, niu: str) -> str:
        """Add a user to the USER table. Return 'User exists' if the user already exists."""
        # Check if the user already exists
        query = "SELECT NIU FROM USER WHERE NIU = ?"
        self.cursor.execute(query, (niu,))
        user = self.cursor.fetchone()
        if user:
            return "User exists"

        # Insert new user if not exists
        query = "INSERT INTO USER (NIU) VALUES (?)"
        self.cursor.execute(query, (niu,))
        self.conn.commit()
        return "User added successfully"

    def add_team(self, team_name: str, niu: str) -> str:
        """Add a team to the TEAM table. Return 'Team exists' if the team already exists."""
        # Check if the team already exists
        query = "SELECT team_name FROM TEAM WHERE team_name = ?"
        self.cursor.execute(query, (team_name,))
        team = self.cursor.fetchone()
        if team:
            return "Team exists"

        # Insert new team if not exists
        query = "INSERT INTO TEAM (team_name, NIU) VALUES (?, ?)"
        self.cursor.execute(query, (team_name, niu))
        self.conn.commit()
        return "Team added successfully"

    def add_report(self, id_report: str, team_name: str, reported_at: str, reported_from: str, total_error: float = -.1,
                   single_day_error = -1., five_days_error: float = -.1, ten_days_error: float = -.1):
        """Add a report to the REPORT table"""
        query = """
        INSERT INTO REPORT (id_report, team_name, reported_at, reported_from, total_error, single_day_error, five_days_error, ten_days_error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.cursor.execute(query, (
        id_report, team_name, reported_at, reported_from, total_error, single_day_error, five_days_error, ten_days_error))
        self.conn.commit()

    # -------------------- Query Methods --------------------
    def find_teams_by_user(self, niu: str) -> List[Dict]:
        """Find all teams for a given user (NIU)"""
        query = """
        SELECT * FROM TEAM WHERE NIU = ?
        """
        self.cursor.execute(query, (niu,))
        teams = self.cursor.fetchall()
        return [dict(team) for team in teams]

    def find_reports_by_user(self, niu: str) -> List[Dict]:
        """Find all reports for teams that a user (NIU) belongs to"""
        query = """
        SELECT R.* FROM REPORT R
        INNER JOIN TEAM T ON R.team_name = T.team_name
        WHERE T.NIU = ?
        """
        self.cursor.execute(query, (niu,))
        reports = self.cursor.fetchall()
        return [dict(report) for report in reports]

    def get_all_reports(self) -> List[Dict]:
        """Return all submitted reports along with the NIU of each user associated with the report's team"""
        query = """
        SELECT R.*, T.NIU FROM REPORT R
        INNER JOIN TEAM T ON R.team_name = T.team_name
        """
        self.cursor.execute(query)
        reports = self.cursor.fetchall()
        return [dict(report) for report in reports]

    def close_connection(self):
        """Closes the database connection"""
        if self.conn:
            self.conn.close()


# -------------------- Testing the Database --------------------
if __name__ == '__main__':
    # Create the database instance and test it
    db = ReportDatabase()

    # Create a new database
    db.create_database('./test_reports.db')

    # Add some users
    print(db.add_user('user123'))  # Should add the user
    print(db.add_user('user123'))  # Should return 'User exists'
    print(db.add_user('user456'))  # Should add the user

    # Add some teams
    print(db.add_team('TeamA', 'user123'))  # Should add the team
    print(db.add_team('TeamA', 'user123'))  # Should return 'Team exists'
    print(db.add_team('TeamB', 'user123'))  # Should add the team
    print(db.add_team('TeamC', 'user456'))  # Should add the team

    # Add some reports
    db.add_report(1, 'TeamA', '2023-10-01', 'LocationA')
    db.add_report(2, 'TeamA', '2023-10-02', 'LocationB')
    db.add_report(3, 'TeamB', '2023-10-03', 'LocationC')
    db.add_report(4, 'TeamC', '2023-10-04', 'LocationD')

    # Test search methods

    # Find all teams for user 'user123'
    teams_user123 = db.find_teams_by_user('user123')
    print("Teams for user123:", teams_user123)

    # Find all reports for teams associated with 'user123'
    reports_user123 = db.find_reports_by_user('user123')
    print("Reports for user123:", reports_user123)

    # Find all reports in the database
    all_reports = db.get_all_reports()
    print("All reports:", all_reports)

    # Close the database connection
    db.close_connection()
