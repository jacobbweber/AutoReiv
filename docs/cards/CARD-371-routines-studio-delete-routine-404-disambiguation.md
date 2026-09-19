# [CARD-371] Routines Studio Delete Routine 404 Disambiguation

> **Status**: In Review  
> **Created**: 2026-09-19  
> **Spec Reference**: none  
> **Labels**: `type:bugfix`, `backend`, `routines-studio`, `api-honesty`

---

## 1. Why / Intent
Disambiguate failure cases in Routines Studio deletion (`src/web/routers/routines.py`) so that attempting to delete a non-existent routine returns an honest HTTP 404 Not Found rather than conflating missing routines and deletion failures under a generic HTTP 400 Bad Request.

---

## 2. Three Beats

### Beat 1: What Jacob Means
When an operator or client deletes a routine by ID, if the routine does not exist in the database, the API must return HTTP 404 Not Found. If the routine exists but deletion fails, the API must return HTTP 400 Bad Request with a clear message indicating deletion failed.

### Beat 2: What AutoReiv Does Now
In `src/web/routers/routines.py` lines 162–171:
```python
@router.delete("/api/routines/{routine_id}")
async def delete_routine(request: Request, routine_id: str):
    store = request.app.state.store
    deleted = store.delete_routine(routine_id)
    if not deleted:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete routine '{routine_id}' (protected or not found).",
        )
    return {"status": "deleted", "id": routine_id}
```
`store.delete_routine(routine_id)` returns `False` when the routine does not exist. The endpoint raises `HTTP 400` with ambiguous `"protected or not found"` wording instead of returning `HTTP 404`.

### Beat 3: What Will Change
- In `src/web/routers/routines.py`, query `store.get_routine(routine_id)` prior to calling `store.delete_routine(routine_id)`.
- If `routine is None`, raise `HTTPException(status_code=404, detail=f"Routine '{routine_id}' not found.")`.
- If `store.delete_routine(routine_id)` returns `False`, raise `HTTPException(status_code=400, detail=f"Cannot delete routine '{routine_id}'.")`.
- Update tests in `tests/unit/web/test_routine_management_api.py` to assert HTTP 404 for non-existent routines.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `DELETE /api/routines/{non_existent_id}` returns HTTP 404 Not Found.
- [x] `DELETE /api/routines/{existing_routine_id}` successfully deletes routines with HTTP 200 OK.
- [x] Automated regression tests pass via `pytest tests/unit/web/test_routine_management_api.py`.
- [x] Zero lint errors via `ruff check src tests`.
- [x] All 7 preflight gates pass cleanly.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/card-371-routines-delete-404` branch cut from `qa` upon Jacob's `build` approval.
