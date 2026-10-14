# Architecture and measurements

## Iteration engine

`engine.py` freezes the run settings, generates a candidate and invokes `validator.py`. The next request receives the unchanged system description, the previous complete candidate and bounded feedback. Earlier conversation history is omitted. The loop preserves all returned candidates, validation diagnostics and available provider usage.

Transient or malformed responses receive one response retry in addition to the SDK's transport retry. If both attempts fail, the next loop retains the last real candidate. Authentication, access, refusal and exhausted empty-output-budget errors stop generation. Failed slots have no validation score. Early stopping occurs only when enabled and all configured automated checks pass.

The default completion budget is 8,192 tokens. Providers may count reasoning inside that budget. Input is limited to a 20,000-character description, an 8,000-character custom prompt, 30 expected identifiers and 12 review requirements. Generated candidates are limited to 60,000 characters.

## Validation

The adapter runs the `sysmlpy==0.96.4` ANTLR SysML v2 grammar and partial static analyzer in a bounded worker. It validates the original candidate after removing an optional outer code fence and disables natural-language constraint rescue. Supplementary checks catch port usages typed by known scalar or local non-port types.

| Measurement | Definition |
| --- | --- |
| Syntax | 100 for parser acceptance; 0 for syntax failure; N/A if unavailable. |
| Static semantics | 100 when implemented checks complete without errors; 0 for detected errors; N/A for unsupported or unavailable analysis. |
| Identifier presence | Percentage of configured whole identifiers present outside comments and strings. |
| Automated pass | Valid parsing, valid implemented semantics and all configured identifiers present. |
| Diagnostic changes | Resolved and new diagnostic identities between comparable checked versions. |
| Source changed | Text differs from the preceding candidate. |
| Cumulative pass rate | Passing checked versions divided by all generated, checked versions. |

Modeling observations highlight possible missing ownership, action performance or architectural connections. They are review prompts and do not change language scores. A known local conjugated-port analyzer limitation is marked unavailable rather than valid or a confirmed semantic failure.

Historical records and exports retain an internal weighted check-point field: with expected names, Q = 0.25S + 0.40M + 0.35E; otherwise Q = 0.40S + 0.60M. Syntax failure forces Q to zero, and unavailable required checks make it N/A. This field is omitted from the interface. It is retained for record compatibility and best-candidate tie-breaking; its weights are prototype choices.

## Human review

`review.py` records Pass, Partial, Fail or Not applicable for each criterion, with evidence. Criteria cover composition, directed communication, connected behavior and configured requirements. A category's percentage remains N/A until every criterion is reviewed; only Pass earns credit and Not applicable is excluded. Human assessments do not alter automated acceptance or best-version selection.

## Records and configuration

CSV, JSON and charts use the same canonical measurement rows. Provider-reported token totals include recorded attempts when every count is available. Unknown counts remain null, blank or N/A. Hidden SDK retries may have unreported usage, so the totals are not billing estimates.

`config.py` loads `LLM_API_KEY`, `LLM_MODEL` and `LLM_BASE_URL` from process settings or `.env`. Legacy `OPENAI_*` variables are supported; explicit canonical fields take precedence. A legacy-only configuration retains direct-OpenAI defaults. The sidebar can override values for the next run without changing an existing run's stored settings.

Credentials are excluded from run records and exports. Credential-echoed candidates are rejected; raw provider response bodies are not retained. Generated source is displayed and validated, never executed.
