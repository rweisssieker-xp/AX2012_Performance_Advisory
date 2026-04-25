# Finding Schema

The implementation should normalize every analysis result to this shape.

```json
{
  "id": "AXPA-0001",
  "title": "Batch collision correlates with InventTrans read pressure",
  "severity": "high",
  "confidence": "medium",
  "classification": "tune-now",
  "timeWindow": {
    "start": "2026-04-25T02:00:00+02:00",
    "end": "2026-04-25T02:45:00+02:00"
  },
  "businessImpact": {
    "process": "Nightly inventory processing",
    "impact": "Batch SLA risk",
    "usersAffected": "Warehouse and finance users after morning start"
  },
  "evidence": [
    {
      "source": "sql_wait_stats",
      "metric": "PAGEIOLATCH_SH",
      "value": 123456,
      "unit": "ms_delta",
      "threshold": 50000
    }
  ],
  "axContext": {
    "tables": ["InventTrans"],
    "batchJobs": ["Example batch job"],
    "aos": ["AOS01"],
    "companies": ["DAT"]
  },
  "sqlContext": {
    "queryHash": "0x0000000000000000",
    "planHash": "0x0000000000000000",
    "waitTypes": ["PAGEIOLATCH_SH"],
    "objects": ["dbo.INVENTTRANS"]
  },
  "recommendation": {
    "summary": "Review schedule overlap and validate statistics/index coverage for the recurring query pattern.",
    "owner": "AX/SQL operations",
    "requiresApproval": true
  },
  "changeReadiness": {
    "benefit": "high",
    "technicalRisk": "medium",
    "axCompatibilityRisk": "medium",
    "testEffort": "medium",
    "downtimeRisk": "low",
    "rollbackComplexity": "low",
    "approvalPath": "CAB"
  },
  "validation": {
    "successMetric": "Reduce logical reads and PAGEIOLATCH wait delta by at least 30 percent in the same batch window.",
    "baselineWindow": "previous 5 comparable runs",
    "postChangeWindow": "next 5 comparable runs",
    "rollback": "Revert schedule or remove proposed index/statistics change after approval."
  },
  "status": "proposed"
}
```
