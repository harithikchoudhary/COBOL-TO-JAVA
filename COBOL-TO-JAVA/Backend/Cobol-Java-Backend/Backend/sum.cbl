       IDENTIFICATION DIVISION.
       PROGRAM-ID. ADDNUMS.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 NUM1         PIC 9(4) VALUE 100.
       01 NUM2         PIC 9(4) VALUE 250.
       01 RESULT       PIC 9(5) VALUE 0.

       PROCEDURE DIVISION.
       BEGIN.
           ADD NUM1 TO NUM2 GIVING RESULT
           DISPLAY "The sum of " NUM1 " and " NUM2 " is " RESULT
           STOP RUN.
