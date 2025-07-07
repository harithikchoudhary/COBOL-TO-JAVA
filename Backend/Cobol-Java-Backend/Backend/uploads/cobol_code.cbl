*****************************************************************
      * PROGRAM:  DBCONNECT
      * AUTHOR:   John Doe
      * DATE:     2025-05-09
      * PURPOSE:  Database connection and operations using COBOL
      *           Demonstrates connecting to a SQL database,
      *           performing CRUD operations, and error handling
      *****************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. DBCONNECT.
       
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. IBM-PC.
       OBJECT-COMPUTER. IBM-PC.
       
       DATA DIVISION.
       FILE SECTION.
       
       WORKING-STORAGE SECTION.
       
       *-----------------------------------------------------------------
       * SQL Communication Area
       *-----------------------------------------------------------------
           EXEC SQL 
               INCLUDE SQLCA 
           END-EXEC.
           
       *-----------------------------------------------------------------
       * Employee Record Structure
       *-----------------------------------------------------------------
       01 WS-EMPLOYEE-RECORD.
          05 WS-EMP-ID                PIC 9(5).
          05 WS-EMP-FIRST-NAME        PIC X(20).
          05 WS-EMP-LAST-NAME         PIC X(20).
          05 WS-EMP-DEPT              PIC X(15).
          05 WS-EMP-POSITION          PIC X(20).
          05 WS-EMP-SALARY            PIC 9(7)V99.
          05 WS-EMP-HIRE-DATE         PIC X(10).
       
       *-----------------------------------------------------------------
       * Variables for Database Operations
       *-----------------------------------------------------------------
       01 WS-DB-CONNECTION.
          05 WS-DB-NAME               PIC X(20) VALUE "EMPLOYEE_DB".
          05 WS-DB-USER               PIC X(20) VALUE "ADMIN".
          05 WS-DB-PASSWORD           PIC X(20) VALUE "P@ssw0rd".
          05 WS-DB-SERVER             PIC X(30) VALUE "localhost:1521".
       
       01 WS-FLAGS.
          05 WS-END-OF-DATA           PIC X(1) VALUE "N".
             88 END-OF-DATA           VALUE "Y".
          05 WS-DB-CONNECTED          PIC X(1) VALUE "N".
             88 DB-CONNECTED          VALUE "Y".
       
       01 WS-COUNTERS.
          05 WS-RECORDS-FOUND         PIC 9(5) VALUE ZEROES.
          05 WS-RECORDS-UPDATED       PIC 9(5) VALUE ZEROES.
          05 WS-RECORDS-DELETED       PIC 9(5) VALUE ZEROES.
          05 WS-RECORDS-INSERTED      PIC 9(5) VALUE ZEROES.
       
       01 WS-ERROR-HANDLING.
          05 WS-SQL-STATUS            PIC X(5).
          05 WS-SQL-MSG               PIC X(70).
          05 WS-ERROR-MSG             PIC X(100).
       
       01 WS-SEARCH-CRITERIA.
          05 WS-SEARCH-DEPT           PIC X(15).
          05 WS-SEARCH-MIN-SALARY     PIC 9(7)V99.
       
       01 WS-USER-INPUT.
          05 WS-OPERATION-CHOICE      PIC 9(1).
          05 WS-CONTINUE-CHOICE       PIC X(1).
       
       01 WS-DISPLAY-VARIABLES.
          05 WS-FORMATTED-SALARY      PIC $ZZZ,ZZ9.99.
          05 WS-LINE                  PIC X(80) VALUE ALL "-".
          05 WS-HEADER                PIC X(80) VALUE 
             "ID     NAME                      DEPARTMENT    POSITION            SALARY".
       
       *-----------------------------------------------------------------
       * SQL Host Variables Declaration
       *-----------------------------------------------------------------
       EXEC SQL BEGIN DECLARE SECTION END-EXEC.
       
       01 HV-EMP-ID                   PIC 9(5).
       01 HV-EMP-FIRST-NAME           PIC X(20).
       01 HV-EMP-LAST-NAME            PIC X(20).
       01 HV-EMP-DEPT                 PIC X(15).
       01 HV-EMP-POSITION             PIC X(20).
       01 HV-EMP-SALARY               PIC 9(7)V99.
       01 HV-EMP-HIRE-DATE            PIC X(10).
       01 HV-DB-USER                  PIC X(20).
       01 HV-DB-PASSWORD              PIC X(20).
       01 HV-SEARCH-DEPT              PIC X(15).
       01 HV-MIN-SALARY               PIC 9(7)V99.
       
       EXEC SQL END DECLARE SECTION END-EXEC.
       
       *-----------------------------------------------------------------
       * Cursor Declarations
       *-----------------------------------------------------------------
       EXEC SQL
          DECLARE EMP_CURSOR CURSOR FOR
          SELECT EMP_ID, FIRST_NAME, LAST_NAME, DEPARTMENT, 
                 POSITION, SALARY, HIRE_DATE
          FROM EMPLOYEES
          ORDER BY EMP_ID
       END-EXEC.
       
       EXEC SQL
          DECLARE DEPT_CURSOR CURSOR FOR
          SELECT EMP_ID, FIRST_NAME, LAST_NAME, DEPARTMENT, 
                 POSITION, SALARY, HIRE_DATE
          FROM EMPLOYEES
          WHERE DEPARTMENT = :HV-SEARCH-DEPT
            AND SALARY >= :HV-MIN-SALARY
          ORDER BY SALARY DESC
       END-EXEC.
       
       PROCEDURE DIVISION.
       
       *-----------------------------------------------------------------
       * Main Processing Section
       *-----------------------------------------------------------------
       0000-MAIN.
           DISPLAY "COBOL DATABASE OPERATIONS PROGRAM".
           DISPLAY WS-LINE.
           
           PERFORM 1000-INITIALIZE.
           
           IF DB-CONNECTED
              PERFORM 2000-PROCESS-USER-CHOICE
              UNTIL WS-CONTINUE-CHOICE = "N" OR "n"
           END-IF.
           
           PERFORM 9000-TERMINATE.
           
           STOP RUN.
       
       *-----------------------------------------------------------------
       * Initialize Variables and Connect to Database
       *-----------------------------------------------------------------
       1000-INITIALIZE.
           INITIALIZE WS-EMPLOYEE-RECORD
                      WS-COUNTERS
                      WS-ERROR-HANDLING.
                      
           MOVE "N" TO WS-END-OF-DATA.
           MOVE "N" TO WS-DB-CONNECTED.
           
           PERFORM 1100-CONNECT-TO-DB.
       
       *-----------------------------------------------------------------
       * Database Connection Process
       *-----------------------------------------------------------------
       1100-CONNECT-TO-DB.
           DISPLAY "Connecting to database: " WS-DB-NAME.
           DISPLAY "Server: " WS-DB-SERVER.
           
           MOVE WS-DB-USER TO HV-DB-USER.
           MOVE WS-DB-PASSWORD TO HV-DB-PASSWORD.
           
           EXEC SQL
               CONNECT TO :WS-DB-NAME 
               USER :HV-DB-USER 
               USING :HV-DB-PASSWORD
           END-EXEC.
           
           PERFORM 8000-CHECK-SQL-STATUS.
           
           IF SQLCODE = 0
              MOVE "Y" TO WS-DB-CONNECTED
              DISPLAY "Successfully connected to database."
           ELSE
              DISPLAY "Failed to connect to database."
              DISPLAY "SQL Error Code: " SQLCODE
              DISPLAY "SQL Error Message: " SQLERRMC
           END-IF.
       
       *-----------------------------------------------------------------
       * Process User Menu Choices
       *-----------------------------------------------------------------
       2000-PROCESS-USER-CHOICE.
           PERFORM 2100-DISPLAY-MENU.
           ACCEPT WS-OPERATION-CHOICE.
           
           EVALUATE WS-OPERATION-CHOICE
               WHEN 1
                   PERFORM 3000-RETRIEVE-ALL-EMPLOYEES
               WHEN 2
                   PERFORM 3100-RETRIEVE-BY-CRITERIA
               WHEN 3
                   PERFORM 4000-INSERT-EMPLOYEE
               WHEN 4
                   PERFORM 5000-UPDATE-EMPLOYEE
               WHEN 5
                   PERFORM 6000-DELETE-EMPLOYEE
               WHEN 9
                   MOVE "N" TO WS-CONTINUE-CHOICE
               WHEN OTHER
                   DISPLAY "Invalid choice. Please try again."
           END-EVALUATE.
           
           IF WS-CONTINUE-CHOICE NOT = "N" AND WS-OPERATION-CHOICE NOT = 9
              DISPLAY WS-LINE
              DISPLAY "Do you want to perform another operation? (Y/N)"
              ACCEPT WS-CONTINUE-CHOICE
           END-IF.
       
       *-----------------------------------------------------------------
       * Display Main Menu
       *-----------------------------------------------------------------
       2100-DISPLAY-MENU.
           DISPLAY WS-LINE.
           DISPLAY "DATABASE OPERATIONS MENU".
           DISPLAY WS-LINE.
           DISPLAY "1. Display All Employees".
           DISPLAY "2. Search Employees by Department and Salary".
           DISPLAY "3. Add New Employee".
           DISPLAY "4. Update Employee Information".
           DISPLAY "5. Delete Employee".
           DISPLAY "9. Exit Program".
           DISPLAY WS-LINE.
           DISPLAY "Enter your choice (1-9): " WITH NO ADVANCING.
       
       *-----------------------------------------------------------------
       * Retrieve All Employee Records
       *-----------------------------------------------------------------
       3000-RETRIEVE-ALL-EMPLOYEES.
           DISPLAY WS-LINE.
           DISPLAY "RETRIEVING ALL EMPLOYEE RECORDS".
           DISPLAY WS-LINE.
           
           INITIALIZE WS-COUNTERS.
           MOVE "N" TO WS-END-OF-DATA.
           
           EXEC SQL
               OPEN EMP_CURSOR
           END-EXEC.
           
           PERFORM 8000-CHECK-SQL-STATUS.
           
           IF SQLCODE = 0
              DISPLAY WS-HEADER
              DISPLAY WS-LINE
              
              PERFORM 3050-FETCH-EMPLOYEE-RECORD
              UNTIL END-OF-DATA
              
              DISPLAY WS-LINE
              DISPLAY "Total records found: " WS-RECORDS-FOUND
              
              EXEC SQL
                  CLOSE EMP_CURSOR
              END-EXEC
           END-IF.
       
       *-----------------------------------------------------------------
       * Fetch Single Employee Record From Cursor
       *-----------------------------------------------------------------
       3050-FETCH-EMPLOYEE-RECORD.
           EXEC SQL
               FETCH EMP_CURSOR INTO 
                   :HV-EMP-ID,
                   :HV-EMP-FIRST-NAME,
                   :HV-EMP-LAST-NAME,
                   :HV-EMP-DEPT,
                   :HV-EMP-POSITION,
                   :HV-EMP-SALARY,
                   :HV-EMP-HIRE-DATE
           END-EXEC.
           
           IF SQLCODE = 0
              ADD 1 TO WS-RECORDS-FOUND
              
              MOVE HV-EMP-SALARY TO WS-FORMATTED-SALARY
              
              DISPLAY HV-EMP-ID " | "
                      FUNCTION TRIM(HV-EMP-FIRST-NAME) " "
                      FUNCTION TRIM(HV-EMP-LAST-NAME) "  | "
                      FUNCTION TRIM(HV-EMP-DEPT) " | "
                      FUNCTION TRIM(HV-EMP-POSITION) " | "
                      WS-FORMATTED-SALARY
           ELSE
              IF SQLCODE = 100
                 MOVE "Y" TO WS-END-OF-DATA
              ELSE
                 PERFORM 8000-CHECK-SQL-STATUS
              END-IF
           END-IF.
       
       *-----------------------------------------------------------------
       * Retrieve Employees by Search Criteria
       *-----------------------------------------------------------------
       3100-RETRIEVE-BY-CRITERIA.
           DISPLAY WS-LINE.
           DISPLAY "SEARCH EMPLOYEES BY DEPARTMENT AND MINIMUM SALARY".
           DISPLAY WS-LINE.
           
           DISPLAY "Enter Department Name: " WITH NO ADVANCING.
           ACCEPT WS-SEARCH-DEPT.
           
           DISPLAY "Enter Minimum Salary: " WITH NO ADVANCING.
           ACCEPT WS-SEARCH-MIN-SALARY.
           
           MOVE WS-SEARCH-DEPT TO HV-SEARCH-DEPT.
           MOVE WS-SEARCH-MIN-SALARY TO HV-MIN-SALARY.
           
           INITIALIZE WS-COUNTERS.
           MOVE "N" TO WS-END-OF-DATA.
           
           EXEC SQL
               OPEN DEPT_CURSOR
           END-EXEC.
           
           PERFORM 8000-CHECK-SQL-STATUS.
           
           IF SQLCODE = 0
              DISPLAY WS-HEADER
              DISPLAY WS-LINE
              
              PERFORM 3150-FETCH-DEPT-RECORD
              UNTIL END-OF-DATA
              
              DISPLAY WS-LINE
              DISPLAY "Total records found: " WS-RECORDS-FOUND
              
              EXEC SQL
                  CLOSE DEPT_CURSOR
              END-EXEC
           END-IF.
       
       *-----------------------------------------------------------------
       * Fetch Record From Department Search Cursor
       *-----------------------------------------------------------------
       3150-FETCH-DEPT-RECORD.
           EXEC SQL
               FETCH DEPT_CURSOR INTO 
                   :HV-EMP-ID,
                   :HV-EMP-FIRST-NAME,
                   :HV-EMP-LAST-NAME,
                   :HV-EMP-DEPT,
                   :HV-EMP-POSITION,
                   :HV-EMP-SALARY,
                   :HV-EMP-HIRE-DATE
           END-EXEC.
           
           IF SQLCODE = 0
              ADD 1 TO WS-RECORDS-FOUND
              
              MOVE HV-EMP-SALARY TO WS-FORMATTED-SALARY
              
              DISPLAY HV-EMP-ID " | "
                      FUNCTION TRIM(HV-EMP-FIRST-NAME) " "
                      FUNCTION TRIM(HV-EMP-LAST-NAME) "  | "
                      FUNCTION TRIM(HV-EMP-DEPT) " | "
                      FUNCTION TRIM(HV-EMP-POSITION) " | "
                      WS-FORMATTED-SALARY
           ELSE
              IF SQLCODE = 100
                 MOVE "Y" TO WS-END-OF-DATA
              ELSE
                 PERFORM 8000-CHECK-SQL-STATUS
              END-IF
           END-IF.
       
       *-----------------------------------------------------------------
       * Insert New Employee Record
       *-----------------------------------------------------------------
       4000-INSERT-EMPLOYEE.
           DISPLAY WS-LINE.
           DISPLAY "ADD NEW EMPLOYEE".
           DISPLAY WS-LINE.
           
           DISPLAY "Enter Employee ID: " WITH NO ADVANCING.
           ACCEPT WS-EMP-ID.
           
           DISPLAY "Enter First Name: " WITH NO ADVANCING.
           ACCEPT WS-EMP-FIRST-NAME.
           
           DISPLAY "Enter Last Name: " WITH NO ADVANCING.
           ACCEPT WS-EMP-LAST-NAME.
           
           DISPLAY "Enter Department: " WITH NO ADVANCING.
           ACCEPT WS-EMP-DEPT.
           
           DISPLAY "Enter Position: " WITH NO ADVANCING.
           ACCEPT WS-EMP-POSITION.
           
           DISPLAY "Enter Salary: " WITH NO ADVANCING.
           ACCEPT WS-EMP-SALARY.
           
           DISPLAY "Enter Hire Date (YYYY-MM-DD): " WITH NO ADVANCING.
           ACCEPT WS-EMP-HIRE-DATE.
           
           MOVE WS-EMP-ID TO HV-EMP-ID.
           MOVE WS-EMP-FIRST-NAME TO HV-EMP-FIRST-NAME.
           MOVE WS-EMP-LAST-NAME TO HV-EMP-LAST-NAME.
           MOVE WS-EMP-DEPT TO HV-EMP-DEPT.
           MOVE WS-EMP-POSITION TO HV-EMP-POSITION.
           MOVE WS-EMP-SALARY TO HV-EMP-SALARY.
           MOVE WS-EMP-HIRE-DATE TO HV-EMP-HIRE-DATE.
           
           EXEC SQL
               INSERT INTO EMPLOYEES 
               (EMP_ID, FIRST_NAME, LAST_NAME, DEPARTMENT, 
                POSITION, SALARY, HIRE_DATE)
               VALUES
               (:HV-EMP-ID, :HV-EMP-FIRST-NAME, :HV-EMP-LAST-NAME,
                :HV-EMP-DEPT, :HV-EMP-POSITION, :HV-EMP-SALARY,
                :HV-EMP-HIRE-DATE)
           END-EXEC.
           
           PERFORM 8000-CHECK-SQL-STATUS.
           
           IF SQLCODE = 0
              ADD 1 TO WS-RECORDS-INSERTED
              DISPLAY "Employee record successfully inserted."
              DISPLAY "Records inserted: " WS-RECORDS-INSERTED
              
              EXEC SQL
                  COMMIT WORK
              END-EXEC
           ELSE
              EXEC SQL
                  ROLLBACK WORK
              END-EXEC
           END-IF.
       
       *-----------------------------------------------------------------
       * Update Employee Information
       *-----------------------------------------------------------------
       5000-UPDATE-EMPLOYEE.
           DISPLAY WS-LINE.
           DISPLAY "UPDATE EMPLOYEE INFORMATION".
           DISPLAY WS-LINE.
           
           DISPLAY "Enter Employee ID to update: " WITH NO ADVANCING.
           ACCEPT WS-EMP-ID.
           
           MOVE WS-EMP-ID TO HV-EMP-ID.
           
           EXEC SQL
               SELECT FIRST_NAME, LAST_NAME, DEPARTMENT, 
                      POSITION, SALARY, HIRE_DATE
               INTO :HV-EMP-FIRST-NAME, :HV-EMP-LAST-NAME,
                    :HV-EMP-DEPT, :HV-EMP-POSITION,
                    :HV-EMP-SALARY, :HV-EMP-HIRE-DATE
               FROM EMPLOYEES
               WHERE EMP_ID = :HV-EMP-ID
           END-EXEC.
           
           PERFORM 8000-CHECK-SQL-STATUS.
           
           IF SQLCODE = 0
              MOVE HV-EMP-FIRST-NAME TO WS-EMP-FIRST-NAME
              MOVE HV-EMP-LAST-NAME TO WS-EMP-LAST-NAME
              MOVE HV-EMP-DEPT TO WS-EMP-DEPT
              MOVE HV-EMP-POSITION TO WS-EMP-POSITION
              MOVE HV-EMP-SALARY TO WS-EMP-SALARY
              MOVE HV-EMP-HIRE-DATE TO WS-EMP-HIRE-DATE
              
              DISPLAY "Current Employee Information:"
              DISPLAY "First Name: " FUNCTION TRIM(WS-EMP-FIRST-NAME)
              DISPLAY "Last Name: " FUNCTION TRIM(WS-EMP-LAST-NAME)
              DISPLAY "Department: " FUNCTION TRIM(WS-EMP-DEPT)
              DISPLAY "Position: " FUNCTION TRIM(WS-EMP-POSITION)
              DISPLAY "Salary: " WS-EMP-SALARY
              DISPLAY "Hire Date: " WS-EMP-HIRE-DATE
              
              DISPLAY WS-LINE
              DISPLAY "Enter new information (leave blank to keep current):"
              
              DISPLAY "New Department: " WITH NO ADVANCING
              ACCEPT WS-EMP-DEPT
              IF WS-EMP-DEPT = SPACES
                 MOVE HV-EMP-DEPT TO WS-EMP-DEPT
              END-IF
              
              DISPLAY "New Position: " WITH NO ADVANCING
              ACCEPT WS-EMP-POSITION
              IF WS-EMP-POSITION = SPACES
                 MOVE HV-EMP-POSITION TO WS-EMP-POSITION
              END-IF
              
              DISPLAY "New Salary: " WITH NO ADVANCING
              ACCEPT WS-EMP-SALARY
              IF WS-EMP-SALARY = ZEROES
                 MOVE HV-EMP-SALARY TO WS-EMP-SALARY
              END-IF
              
              MOVE WS-EMP-DEPT TO HV-EMP-DEPT
              MOVE WS-EMP-POSITION TO HV-EMP-POSITION
              MOVE WS-EMP-SALARY TO HV-EMP-SALARY
              
              EXEC SQL
                  UPDATE EMPLOYEES
                  SET DEPARTMENT = :HV-EMP-DEPT,
                      POSITION = :HV-EMP-POSITION,
                      SALARY = :HV-EMP-SALARY
                  WHERE EMP_ID = :HV-EMP-ID
              END-EXEC
              
              PERFORM 8000-CHECK-SQL-STATUS
              
              IF SQLCODE = 0
                 ADD 1 TO WS-RECORDS-UPDATED
                 DISPLAY "Employee record successfully updated."
                 DISPLAY "Records updated: " WS-RECORDS-UPDATED
                 
                 EXEC SQL
                     COMMIT WORK
                 END-EXEC
              ELSE
                 EXEC SQL
                     ROLLBACK WORK
                 END-EXEC
              END-IF
           ELSE
              IF SQLCODE = 100
                 DISPLAY "Employee ID " WS-EMP-ID " not found."
              ELSE
                 PERFORM 8000-CHECK-SQL-STATUS
              END-IF
           END-IF.
       
       *-----------------------------------------------------------------
       * Delete Employee Record
       *-----------------------------------------------------------------
       6000-DELETE-EMPLOYEE.
           DISPLAY WS-LINE.
           DISPLAY "DELETE EMPLOYEE".
           DISPLAY WS-LINE.
           
           DISPLAY "Enter Employee ID to delete: " WITH NO ADVANCING.
           ACCEPT WS-EMP-ID.
           
           MOVE WS-EMP-ID TO HV-EMP-ID.
           
           EXEC SQL
               SELECT FIRST_NAME, LAST_NAME
               INTO :HV-EMP-FIRST-NAME, :HV-EMP-LAST-NAME
               FROM EMPLOYEES
               WHERE EMP_ID = :HV-EMP-ID
           END-EXEC.
           
           PERFORM 8000-CHECK-SQL-STATUS.
           
           IF SQLCODE = 0
              DISPLAY "You are about to delete employee: "
              DISPLAY "ID: " HV-EMP-ID ", Name: " 
                      FUNCTION TRIM(HV-EMP-FIRST-NAME) " " 
                      FUNCTION TRIM(HV-EMP-LAST-NAME)
              DISPLAY "Are you sure? (Y/N): " WITH NO ADVANCING
              ACCEPT WS-CONTINUE-CHOICE
              
              IF WS-CONTINUE-CHOICE = "Y" OR WS-CONTINUE-CHOICE = "y"
                 EXEC SQL
                     DELETE FROM EMPLOYEES
                     WHERE EMP_ID = :HV-EMP-ID
                 END-EXEC
                 
                 PERFORM 8000-CHECK-SQL-STATUS
                 
                 IF SQLCODE = 0
                    ADD 1 TO WS-RECORDS-DELETED
                    DISPLAY "Employee record successfully deleted."
                    DISPLAY "Records deleted: " WS-RECORDS-DELETED
                    
                    EXEC SQL
                        COMMIT WORK
                    END-EXEC
                 ELSE
                    EXEC SQL
                        ROLLBACK WORK
                    END-EXEC
                 END-IF
              ELSE
                 DISPLAY "Delete operation cancelled."
              END-IF
           ELSE
              IF SQLCODE = 100
                 DISPLAY "Employee ID " WS-EMP-ID " not found."
              ELSE
                 PERFORM 8000-CHECK-SQL-STATUS
              END-IF
           END-IF.
       
       *-----------------------------------------------------------------
       * Check SQL Status and Handle Errors
       *-----------------------------------------------------------------
       8000-CHECK-SQL-STATUS.
           MOVE SQLCODE TO WS-SQL-STATUS.
           MOVE SQLERRMC TO WS-SQL-MSG.
           
           IF SQLCODE < 0
              STRING "SQL ERROR: " DELIMITED BY SIZE
                     WS-SQL-STATUS DELIMITED BY SIZE
                     " - " DELIMITED BY SIZE
                     WS-SQL-MSG DELIMITED BY SIZE
                INTO WS-ERROR-MSG
              DISPLAY WS-ERROR-MSG
           END-IF.
       
       *-----------------------------------------------------------------
       * Program Termination
       *-----------------------------------------------------------------
       9000-TERMINATE.
           IF DB-CONNECTED
              EXEC SQL
                  DISCONNECT CURRENT
              END-EXEC
              
              PERFORM 8000-CHECK-SQL-STATUS
              
              IF SQLCODE = 0
                 DISPLAY "Successfully disconnected from database."
              ELSE
                 DISPLAY "Error during database disconnect."
              END-IF
           END-IF.
           
           DISPLAY WS-LINE.
           DISPLAY "Program terminated.".
           DISPLAY WS-LINE.