Per-submission decision workflow overrides are stored here.

Computed workflow gates are generated from submission metadata, underwriting
signals, claims, tasks, stages, and model outputs. If an underwriter records a
manual gate decision, the backend writes `{submission_id}.json` in this folder
and merges that decision back into the computed workflow.
