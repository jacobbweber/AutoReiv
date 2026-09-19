# Nested Complete Context Cap

## REQ-ORCH-028
run_turn complete() uses num_ctx=min(resolved,32768) and max_tokens=1024.

## REQ-ORCH-029
complete() sends think=false. Chat stream_turn is unchanged.
