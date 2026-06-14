# L2 ingest log

*Public FDA data. Educational, not regulatory advice.*

| Source | Access | Records | File |
|---|---|---:|---|
| openFDA drug enforcement (recalls) | keyless API | **3000** (644 CGMP/manufacturing-related) | recalls.json |
| openFDA drug shortages | keyless API | **1678** | shortages.json |
| Import Alert 66-40 (DWPE red list) | HTML scrape (div-info blocks) | **443** firms | import_alert_6640.json |
| FDA Debarment List | HTML scrape | **272** entries | debarment.json |
| Inspection Classification (OAI/VAI/NAI) | Data Dashboard — needs OII Unified Logon API key (not held) | deferred | see INGEST_LOG note |
| Warning Letters (structured) | Data Dashboard — needs OII logon; WL full-text scrape is a v2 enhancement | deferred | — |

**Note:** the FDA Data Dashboard's Inspection Classification and structured Compliance-Actions feeds require an OII Unified Logon API key we do not hold. v1 uses the keyless watch lists (Import Alert 66-40 = the strongest red flag, recalls, shortages, debarment). Adding the OAI/WL feeds (with a logon key) is a documented v2 upgrade.
