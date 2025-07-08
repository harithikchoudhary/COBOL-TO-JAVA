*>================================================================*
*> COMPREHENSIVE BANKING SYSTEM - CICS TRANSACTION PROGRAM        *
*> Handles Account Management, Transfers, and Transaction History *
*>================================================================*
IDENTIFICATION DIVISION.
PROGRAM-ID. BANKING.
AUTHOR.     SYSTEM-ARCHITECT.
INSTALLATION. GLOBAL-BANK.
DATE-WRITTEN. 2025-06-27.
REMARKS.    Enterprise CICS application with complex business logic.

ENVIRONMENT DIVISION.
CONFIGURATION SECTION.
SOURCE-COMPUTER. IBM-Z15.
OBJECT-COMPUTER. CICS-TS-V5R6.
SPECIAL-NAMES.
    DECIMAL-POINT IS COMMA.

FILE-CONTROL.
    SELECT ACCOUNT-FILE ASSIGN TO VSAM-ACCOUNTS
           ORGANIZATION IS INDEXED
           ACCESS IS DYNAMIC
           RECORD KEY IS ACC-KEY.
    
    SELECT TRANS-FILE ASSIGN TO VSAM-TRANSACTIONS
           ORGANIZATION IS INDEXED
           ACCESS IS DYNAMIC
           RECORD KEY IS TRANS-KEY.
    
    SELECT AUDIT-FILE ASSIGN TO AUDIT-LOG
           ORGANIZATION IS SEQUENTIAL.

DATA DIVISION.
FILE SECTION.
FD  ACCOUNT-FILE.
01  ACCOUNT-RECORD.
    05  ACC-KEY.
        10  ACC-BANK-CODE    PIC X(4).
        10  ACC-NUMBER       PIC 9(10).
    05  ACC-HOLDER-NAME      PIC X(50).
    05  ACC-TYPE             PIC X(2).
    05  ACC-BALANCE          PIC S9(13)V99 COMP-3.
    05  ACC-STATUS           PIC X.
    05  ACC-OPEN-DATE        PIC 9(8).
    05  ACC-LAST-ACTIVITY    PIC 9(8).

FD  TRANS-FILE.
01  TRANSACTION-RECORD.
    05  TRANS-KEY.
        10  TRANS-DATE       PIC 9(8).
        10  TRANS-TIME       PIC 9(6).
        10  TRANS-SEQ        PIC 9(6).
    05  TRANS-FROM-ACC       PIC 9(14).
    05  TRANS-TO-ACC         PIC 9(14).
    05  TRANS-AMOUNT         PIC S9(13)V99 COMP-3.
    05  TRANS-TYPE           PIC X(3).
    05  TRANS-STATUS         PIC X.
    05  TRANS-USER-ID        PIC X(8).
    05  TRANS-TERMINAL       PIC X(4).

FD  AUDIT-FILE.
01  AUDIT-RECORD            PIC X(200).

WORKING-STORAGE SECTION.
*> Transaction Control
01  WS-TRANSACTION-DATA.
    05  WS-TRANS-ID          PIC X(4) VALUE 'BANK'.
    05  WS-USER-ID           PIC X(8).
    05  WS-TERMINAL-ID       PIC X(4).
    05  WS-SESSION-TOKEN     PIC X(32).

*> Account Processing
01  WS-ACCOUNT-WORK.
    05  WS-FROM-ACCOUNT      PIC 9(14).
    05  WS-TO-ACCOUNT        PIC 9(14).
    05  WS-TRANSFER-AMOUNT   PIC S9(13)V99 COMP-3.
    05  WS-OLD-BALANCE       PIC S9(13)V99 COMP-3.
    05  WS-NEW-BALANCE       PIC S9(13)V99 COMP-3.

*> Error Handling
01  WS-ERROR-AREA.
    05  WS-ERROR-CODE        PIC X(8).
    05  WS-ERROR-MESSAGE     PIC X(80).
    05  WS-CICS-RESP         PIC S9(8) COMP.
    05  WS-CICS-RESP2        PIC S9(8) COMP.

*> Temporary Storage Queues
01  WS-TSQ-DATA.
    05  WS-TSQ-NAME          PIC X(8) VALUE 'BANKTSQ'.
    05  WS-TSQ-ITEM          PIC S9(4) COMP VALUE 1.
    05  WS-TSQ-LENGTH        PIC S9(4) COMP.

*> Message Queue Data
01  WS-MQ-DATA.
    05  WS-MQ-QUEUE          PIC X(8) VALUE 'BANKMQ'.
    05  WS-MQ-MESSAGE        PIC X(500).
    05  WS-MQ-LENGTH         PIC S9(4) COMP.

*> Channel/Container Data
01  WS-CHANNEL-DATA.
    05  WS-CHANNEL-NAME      PIC X(16) VALUE 'BANK-CHANNEL'.
    05  WS-CONTAINER-NAME    PIC X(16) VALUE 'ACCOUNT-DATA'.
    05  WS-CONTAINER-DATA    PIC X(1000).
    05  WS-CONTAINER-LENGTH  PIC S9(8) COMP.

*> BMS Map Control
01  WS-MAP-CONTROL.
    05  WS-MAPSET            PIC X(8) VALUE 'BANKMAP'.
    05  WS-MAP-NAME          PIC X(8) VALUE 'ACCFORM'.
    05  WS-CURSOR-POS        PIC S9(4) COMP.

*> Counters and Flags
01  WS-COUNTERS.
    05  WS-RECORD-COUNT      PIC S9(8) COMP VALUE ZERO.
    05  WS-ERROR-COUNT       PIC S9(4) COMP VALUE ZERO.
    05  WS-RETRY-COUNT       PIC S9(2) COMP VALUE ZERO.

01  WS-FLAGS.
    05  WS-EOF-FLAG          PIC X VALUE 'N'.
    05  WS-VALID-TRANS-FLAG  PIC X VALUE 'Y'.
    05  WS-AUDIT-FLAG        PIC X VALUE 'Y'.
    05  WS-DEBUG-FLAG        PIC X VALUE 'N'.

LINKAGE SECTION.
01  DFHCOMMAREA.
    05  LK-FUNCTION-CODE     PIC X(2).
    05  LK-FROM-ACCOUNT      PIC 9(14).
    05  LK-TO-ACCOUNT        PIC 9(14).
    05  LK-AMOUNT            PIC S9(13)V99 COMP-3.
    05  LK-USER-ID           PIC X(8).
    05  LK-RETURN-CODE       PIC X(2).
    05  LK-ERROR-MESSAGE     PIC X(80).

*> Include copybooks
COPY ACCOUNT-VALIDATION.
COPY TRANSACTION-TYPES.
COPY ERROR-CODES.
COPY SECURITY-CONTROL.

PROCEDURE DIVISION.
MAIN-PROCESSING.
    *> Initialize transaction environment
    PERFORM INITIALIZE-TRANSACTION
    
    *> Validate user session
    PERFORM VALIDATE-USER-SESSION
    
    *> Process based on function code
    EVALUATE LK-FUNCTION-CODE
        WHEN '01' PERFORM ACCOUNT-INQUIRY
        WHEN '02' PERFORM ACCOUNT-TRANSFER
        WHEN '03' PERFORM TRANSACTION-HISTORY
        WHEN '04' PERFORM ACCOUNT-BALANCE-UPDATE
        WHEN '05' PERFORM BATCH-PROCESSING
        WHEN OTHER PERFORM INVALID-FUNCTION
    END-EVALUATE
    
    *> Finalize transaction
    PERFORM FINALIZE-TRANSACTION
    
    *> Return to CICS
    EXEC CICS RETURN
        TRANSID('BANK')
        COMMAREA(DFHCOMMAREA)
    END-EXEC.

INITIALIZE-TRANSACTION.
    *> Get terminal and user information
    EXEC CICS ASSIGN
        USERID(WS-USER-ID)
        TERMID(WS-TERMINAL-ID)
    END-EXEC
    
    *> Start audit logging
    IF WS-AUDIT-FLAG = 'Y'
        PERFORM START-AUDIT-LOG
    END-IF
    
    *> Initialize temporary storage
    PERFORM INITIALIZE-TEMP-STORAGE
    
    *> Set up error handling
    MOVE ZERO TO WS-ERROR-COUNT.

VALIDATE-USER-SESSION.
    *> Check user authorization
    EXEC CICS LINK
        PROGRAM('AUTHCHK')
        COMMAREA(LK-USER-ID)
        LENGTH(8)
    END-EXEC
    
    *> Validate session token through external service
    EXEC CICS LINK
        PROGRAM('SESSVAL')
        CHANNEL(WS-CHANNEL-NAME)
        CONTAINER(WS-CONTAINER-NAME)
    END-EXEC.

ACCOUNT-INQUIRY.
    *> Read account information
    MOVE LK-FROM-ACCOUNT TO ACC-NUMBER
    
    EXEC CICS READ
        FILE('ACCOUNTS')
        INTO(ACCOUNT-RECORD)
        RIDFLD(ACC-KEY)
        RESP(WS-CICS-RESP)
    END-EXEC
    
    IF WS-CICS-RESP = DFHRESP(NORMAL)
        *> Store in temporary storage for session
        PERFORM STORE-ACCOUNT-IN-TSQ
        *> Send account data to terminal
        PERFORM SEND-ACCOUNT-MAP
    ELSE
        PERFORM HANDLE-FILE-ERROR
    END-IF.

ACCOUNT-TRANSFER.
    *> Complex transfer logic with rollback capability
    PERFORM VALIDATE-TRANSFER-REQUEST
    
    IF WS-VALID-TRANS-FLAG = 'Y'
        *> Start transaction unit of work
        EXEC CICS SYNCPOINT ROLLBACK END-EXEC
        
        PERFORM DEBIT-FROM-ACCOUNT
        IF WS-CICS-RESP = DFHRESP(NORMAL)
            PERFORM CREDIT-TO-ACCOUNT
            IF WS-CICS-RESP = DFHRESP(NORMAL)
                PERFORM LOG-TRANSACTION
                EXEC CICS SYNCPOINT END-EXEC
                PERFORM NOTIFY-TRANSFER-COMPLETE
            ELSE
                EXEC CICS SYNCPOINT ROLLBACK END-EXEC
                PERFORM HANDLE-CREDIT-ERROR
            END-IF
        ELSE
            EXEC CICS SYNCPOINT ROLLBACK END-EXEC
            PERFORM HANDLE-DEBIT-ERROR
        END-IF
    END-IF.

DEBIT-FROM-ACCOUNT.
    MOVE LK-FROM-ACCOUNT TO ACC-NUMBER
    
    EXEC CICS READ UPDATE
        FILE('ACCOUNTS')
        INTO(ACCOUNT-RECORD)
        RIDFLD(ACC-KEY)
        RESP(WS-CICS-RESP)
    END-EXEC
    
    IF WS-CICS-RESP = DFHRESP(NORMAL)
        MOVE ACC-BALANCE TO WS-OLD-BALANCE
        SUBTRACT LK-AMOUNT FROM ACC-BALANCE
        
        IF ACC-BALANCE >= ZERO
            EXEC CICS REWRITE
                FILE('ACCOUNTS')
                FROM(ACCOUNT-RECORD)
                RESP(WS-CICS-RESP)
            END-EXEC
        ELSE
            MOVE 'INSUFFICIENT_FUNDS' TO WS-ERROR-CODE
            MOVE DFHRESP(ERROR) TO WS-CICS-RESP
        END-IF
    END-IF.

CREDIT-TO-ACCOUNT.
    MOVE LK-TO-ACCOUNT TO ACC-NUMBER
    
    EXEC CICS READ UPDATE
        FILE('ACCOUNTS')
        INTO(ACCOUNT-RECORD)
        RIDFLD(ACC-KEY)
        RESP(WS-CICS-RESP)
    END-EXEC
    
    IF WS-CICS-RESP = DFHRESP(NORMAL)
        ADD LK-AMOUNT TO ACC-BALANCE
        
        EXEC CICS REWRITE
            FILE('ACCOUNTS')
            FROM(ACCOUNT-RECORD)
            RESP(WS-CICS-RESP)
        END-EXEC
    END-IF.

LOG-TRANSACTION.
    *> Create transaction record
    EXEC CICS ASKTIME ABSTIME(TRANS-DATE) END-EXEC
    MOVE FUNCTION CURRENT-DATE(1:8) TO TRANS-DATE
    MOVE FUNCTION CURRENT-DATE(9:6) TO TRANS-TIME
    ADD 1 TO WS-RECORD-COUNT
    MOVE WS-RECORD-COUNT TO TRANS-SEQ
    MOVE LK-FROM-ACCOUNT TO TRANS-FROM-ACC
    MOVE LK-TO-ACCOUNT TO TRANS-TO-ACC
    MOVE LK-AMOUNT TO TRANS-AMOUNT
    MOVE 'TRF' TO TRANS-TYPE
    MOVE 'C' TO TRANS-STATUS
    MOVE WS-USER-ID TO TRANS-USER-ID
    MOVE WS-TERMINAL-ID TO TRANS-TERMINAL
    
    EXEC CICS WRITE
        FILE('TRANSACTIONS')
        FROM(TRANSACTION-RECORD)
        RIDFLD(TRANS-KEY)
        RESP(WS-CICS-RESP)
    END-EXEC
    
    *> Send notification via message queue
    PERFORM SEND-MQ-NOTIFICATION.

TRANSACTION-HISTORY.
    *> Browse transaction history for account
    EXEC CICS STARTBR
        FILE('TRANSACTIONS')
        RIDFLD(LK-FROM-ACCOUNT)
        RESP(WS-CICS-RESP)
    END-EXEC
    
    IF WS-CICS-RESP = DFHRESP(NORMAL)
        PERFORM READ-TRANSACTION-HISTORY
        EXEC CICS ENDBR FILE('TRANSACTIONS') END-EXEC
    END-IF.

READ-TRANSACTION-HISTORY.
    MOVE 'N' TO WS-EOF-FLAG
    MOVE 1 TO WS-TSQ-ITEM
    
    PERFORM UNTIL WS-EOF-FLAG = 'Y'
        EXEC CICS READNEXT
            FILE('TRANSACTIONS')
            INTO(TRANSACTION-RECORD)
            RIDFLD(TRANS-KEY)
            RESP(WS-CICS-RESP)
        END-EXEC
        
        IF WS-CICS-RESP = DFHRESP(NORMAL)
            PERFORM STORE-TRANSACTION-IN-TSQ
            ADD 1 TO WS-TSQ-ITEM
        ELSE
            MOVE 'Y' TO WS-EOF-FLAG
        END-IF
    END-PERFORM
    
    *> Send history data to terminal
    PERFORM SEND-HISTORY-MAP.

BATCH-PROCESSING.
    *> Process multiple transactions via container
    EXEC CICS GET CONTAINER(WS-CONTAINER-NAME)
        CHANNEL(WS-CHANNEL-NAME)
        INTO(WS-CONTAINER-DATA)
        FLENGTH(WS-CONTAINER-LENGTH)
    END-EXEC
    
    *> Link to batch processor
    EXEC CICS LINK
        PROGRAM('BATCHPRC')
        CHANNEL(WS-CHANNEL-NAME)
    END-EXEC.

*> SQL Operations for reporting
GENERATE-ACCOUNT-REPORT.
    EXEC SQL
        DECLARE ACCOUNT-CURSOR CURSOR FOR
        SELECT ACC_NUMBER, ACC_HOLDER_NAME, ACC_BALANCE, ACC_TYPE
        FROM ACCOUNTS
        WHERE ACC_STATUS = 'A'
        ORDER BY ACC_BALANCE DESC
    END-EXEC
    
    EXEC SQL OPEN ACCOUNT-CURSOR END-EXEC
    
    PERFORM PROCESS-REPORT-RECORDS UNTIL WS-EOF-FLAG = 'Y'
    
    EXEC SQL CLOSE ACCOUNT-CURSOR END-EXEC.

PROCESS-REPORT-RECORDS.
    EXEC SQL
        FETCH ACCOUNT-CURSOR
        INTO :ACC-NUMBER, :ACC-HOLDER-NAME, :ACC-BALANCE, :ACC-TYPE
    END-EXEC
    
    IF SQLCODE = 0
        PERFORM FORMAT-REPORT-LINE
        PERFORM WRITE-REPORT-LINE
    ELSE
        MOVE 'Y' TO WS-EOF-FLAG
    END-IF.

*> Utility procedures
INITIALIZE-TEMP-STORAGE.
    EXEC CICS WRITEQ TS
        QUEUE(WS-TSQ-NAME)
        FROM('SESSION-START')
        LENGTH(13)
        ITEM(WS-TSQ-ITEM)
        RESP(WS-CICS-RESP)
    END-EXEC.

STORE-ACCOUNT-IN-TSQ.
    ADD 1 TO WS-TSQ-ITEM
    MOVE LENGTH OF ACCOUNT-RECORD TO WS-TSQ-LENGTH
    
    EXEC CICS WRITEQ TS
        QUEUE(WS-TSQ-NAME)
        FROM(ACCOUNT-RECORD)
        LENGTH(WS-TSQ-LENGTH)
        ITEM(WS-TSQ-ITEM)
    END-EXEC.

SEND-MQ-NOTIFICATION.
    MOVE 'TRANSFER-COMPLETE' TO WS-MQ-MESSAGE
    MOVE 100 TO WS-MQ-LENGTH
    
    EXEC CICS WRITEQ TD
        QUEUE(WS-MQ-QUEUE)
        FROM(WS-MQ-MESSAGE)
        LENGTH(WS-MQ-LENGTH)
    END-EXEC.

SEND-ACCOUNT-MAP.
    EXEC CICS SEND
        MAPSET(WS-MAPSET)
        MAP(WS-MAP-NAME)
        FROM(ACCOUNT-RECORD)
        ERASE
        CURSOR(WS-CURSOR-POS)
    END-EXEC.

HANDLE-FILE-ERROR.
    ADD 1 TO WS-ERROR-COUNT
    MOVE 'FILE-ERROR' TO WS-ERROR-CODE
    PERFORM LOG-ERROR.

START-AUDIT-LOG.
    EXEC CICS WRITEQ TD
        QUEUE('AUDIT')
        FROM('TRANSACTION-START')
        LENGTH(17)
    END-EXEC.

FINALIZE-TRANSACTION.
    EXEC CICS DELETEQ TS
        QUEUE(WS-TSQ-NAME)
    END-EXEC
    
    IF WS-AUDIT-FLAG = 'Y'
        PERFORM END-AUDIT-LOG
    END-IF.

END PROGRAM BANKING.