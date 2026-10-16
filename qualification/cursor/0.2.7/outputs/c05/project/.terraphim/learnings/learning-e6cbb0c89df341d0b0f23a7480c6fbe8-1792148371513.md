---
id: e6cbb0c89df341d0b0f23a7480c6fbe8-1792148371513
command: python3 validate_brief.py --chek --output outputs/native-cli-correction.json
exit_code: 2
source: Project
captured_at: 2026-10-16T10:59:31.513261+00:00
working_dir: /private/tmp/terraphim-cursor-validation-20261016/native-cli-run/project
correction: python3 validate_brief.py --check --output outputs/native-cli-correction.json
tags:
  - learning
  - exit-2
importance_total: 0.3200
importance_severity: 0.4000
importance_repetition: 0
importance_recency: 1.0000
importance_has_correction: false
---

## Command

`python3 validate_brief.py --chek --output outputs/native-cli-correction.json`

## Error Output

```
usage: validate_brief.py [-h] --check --output OUTPUT
validate_brief.py: error: the following arguments are required: --check

```

## Suggested Correction

`python3 validate_brief.py --check --output outputs/native-cli-correction.json`

