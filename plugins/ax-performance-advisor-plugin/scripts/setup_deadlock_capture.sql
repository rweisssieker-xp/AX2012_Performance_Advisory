IF NOT EXISTS (SELECT 1 FROM sys.server_event_sessions WHERE name = N'AXPA_Deadlocks')
BEGIN
    CREATE EVENT SESSION [AXPA_Deadlocks] ON SERVER
    ADD EVENT sqlserver.xml_deadlock_report
    ADD TARGET package0.event_file
    (
        SET filename = N'C:\AXPA\deadlocks.xel',
            max_file_size = 25,
            max_rollover_files = 4
    )
    WITH
    (
        MAX_MEMORY = 4096 KB,
        EVENT_RETENTION_MODE = ALLOW_SINGLE_EVENT_LOSS,
        MAX_DISPATCH_LATENCY = 30 SECONDS,
        STARTUP_STATE = ON
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.dm_xe_sessions
    WHERE name = N'AXPA_Deadlocks'
)
BEGIN
    ALTER EVENT SESSION [AXPA_Deadlocks] ON SERVER STATE = START;
END;
