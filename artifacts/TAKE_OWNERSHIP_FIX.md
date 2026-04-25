# Take Ownership Persistence - Investigation & Fix

## Problem Statement

The "Take Ownership" button on the Alerts page was not persisting the `investigating` status across polling cycles. When a user clicked the button:
1. ✅ The button immediately changed to "Already Investigating"
2. ✅ The status in the table row updated to "investigating"
3. ❌ **After 10 seconds** (when the polling cycle refreshed), the status reverted to "open"

## Root Cause Analysis

Through systematic investigation and browser automation testing, we discovered **two separate issues**:

### Issue #1: The "Disappearing Alert" Illusion

**Symptoms:** Alerts seemed to completely disappear or  change IDs after the polling cycle.

**Root Cause:** The alerts table is:
- **Sorted by Time Detected (oldest first)**  
- **Limited to 100 alerts maximum**

The backend continuously generates new alerts. When new alerts are added, the **oldest alerts at the top of the table age out** and are removed from the 100-alert window. This created the illusion that alert IDs were changing, when in reality the alert itself was being removed from the active set.

**Verification:**
```bash
# Backend returns stable IDs on consecutive requests
$ curl -s "http://localhost:8000/alerts?limit=5" | python3 -c "import json, sys; print([a['alert_id'] for a in json.load(sys.stdin)])"
['98876d68-f4fe-462e-a6de-0ba48d3c2ed9', 'b8b00279-9dd8-4f2e-8b6f-6bbd189ffe16', ...]

# Same IDs returned on second request
$ curl -s "http://localhost:8000/alerts?limit=5" | python3 -c "import json, sys; print([a['alert_id'] for a in json.load(sys.stdin)])"
['98876d68-f4fe-462e-a6de-0ba48d3c2ed9', 'b8b00279-9dd8-4f2e-8b6f-6bbd189ffe16', ...]
```

### Issue #2: Polling Overwrites Local Changes

**Symptoms:** Even for alerts that didn't age out, the `investigating` status reverted to `open` after polling.

**Root Cause:** The `loadAlerts()` function was replacing the entire alerts array with fresh backend data, which **overwrote any local optimistic updates**.

The sequence was:
1. User clicks "Take Ownership" → status updated to `'investigating'` in local state
2. 10 seconds later → `loadAlerts()` fetches fresh data from backend
3. Backend returns `status: 'open'` (because backend doesn't persist status yet)
4. Frontend `transformBackendAlert()` hardcodes `status: 'open'`  
5. `setAlerts(data)` **replaces** the entire array, **losing** the local modification

## Solution: `localModifications` State

We implemented a **merge strategy** to combine backend data with local modifications:

### Implementation

1. **Track Local Changes:**
```typescript
const [localModifications, setLocalModifications] = useState<Record<string, Partial<Alert>>>({});
```

2. **Store Modifications on "Take Ownership":**
```typescript
const handleTakeOwnership = async () => {
    if (!selectedAlert) return;

    // Track this modification locally
    setLocalModifications(prev => ({
        ...prev,
        [selectedAlert.id]: { status: 'investigating' as const }
    }));

    // Update local state immediately (optimistic UI)
    const updatedAlerts = alerts.map(a =>
        a.id === selectedAlert.id ? { ...a, status: 'investigating' as const } : a
    );
    setAlerts(updatedAlerts);

    // TODO: Send update to backend API
    // await updateAlertStatus(selectedAlert.id, 'investigating');
};
```

3. **Merge Backend Data with Local Modifications:**
```typescript
const loadAlerts = useCallback(async () => {
    setRefreshing(true);
    try {
        const data = await fetchAlerts({ limit: 100 });
        
        // Merge backend data with local modifications
        const mergedAlerts = data.map(alert => {
            const localMod = localModifications[alert.id];
            return localMod ? { ...alert, ...localMod } : alert;
        });
        
        setAlerts(mergedAlerts);
        setError(null);
    } catch (err) {
        console.error('Failed to load alerts:', err);
        setError('Failed to load alerts from backend');
    } finally {
        setLoading(false);
        setRefreshing(false);
    }
}, [localModifications]);
```

4. **Update `useEffect` Dependencies:**
```typescript
useEffect(() => {
    loadAlerts();

    // Auto-refresh every 10 seconds
    const interval = setInterval(loadAlerts, 10000);
    return () => clearInterval(interval);
}, [loadAlerts]);  // Added loadAlerts as dependency
```

## Test Results

**Test Procedure:**
1. Selected alert #50 (middle of list to avoid age-out)
2. Alert ID: `e5bf2c11-51c5-4b00-9535-d6576d57e168`
3. Clicked "Take Ownership" → status changed to `investigating`
4. Waited **45+ seconds** (crossing multiple 10-second polling cycles)

**Result: ✅ SUCCESS**
- Status **remained `investigating`** throughout the test
- Button remained in "Already Investigating" state
- Local modifications successfully persisted across all polling cycles

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│ User clicks "Take Ownership"                                │
│ ├─ setLocalModifications({ [alert.id]: { status: 'investigating' } })
│ └─ setAlerts(updated array) ← Optimistic UI update         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 10 seconds pass...                                          │
│ Backend polling cycle triggers                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ loadAlerts() executes                                       │
│ ├─ Fetches fresh data from backend (all status: 'open')    │
│ ├─ Merges with localModifications                          │
│ │  └─ If alert.id matches a key in localModifications:     │
│ │      { ...backendAlert, ...localMod }                   │
│ │      → { ...alert, status: 'investigating' }             │
│ └─ setAlerts(merged array) ← Backend data + local mods     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Result: Status remains 'investigating' in UI! ✅            │
└─────────────────────────────────────────────────────────────┘
```

## Next Steps

### Backend Implementation (TODO)
1. Add a `status` field to the Alert model in the backend
2. Create a `PATCH /alerts/{alert_id}` endpoint to update alert status
3. Implement status persistence in storage layer
4. Update frontend to call the API and remove from `localModifications` on success:

```typescript
const handleTakeOwnership = async () => {
    // ... existing code ...

    try {
        await updateAlertStatus(selectedAlert.id, 'investigating');
        
        // On success, remove from localModifications (backend now has it)
        setLocalModifications(prev => {
            const { [selectedAlert.id]: _, ...rest } = prev;
            return rest;
        });
    } catch (error) {
        console.error('Failed to update status:', error);
        // Keep in localModifications so it persists locally
    }
};
```

## Files Modified

- `client/src/pages/Alerts.tsx`:
  - Added `localModifications` state (line 16)
  - Updated `handleTakeOwnership` to track modifications (lines 59-66)
  - Wrapped `loadAlerts` in `useCallback` with `localModifications` dependency (line 81)
  - Added merge logic in `loadAlerts` (lines 86-89)
  - Added `useCallback` to React imports (line 1)
  - Updated `useEffect` dependency array (line 135)

## Testing Recommendations

1. **Happy Path:** Click "Take Ownership" on a mid-list alert, wait 30+ seconds, confirm status persists
2. **Filter Test:** After taking ownership, use Status filter to show only "investigating" alerts
3. **Reopen Test:** Close detail panel, reopen the same alert, confirm button shows "Already Investigating"  
4. **Age-Out Test:** Take ownership of top alert, watch it age out naturally (expected: disappears from list)
5. **Backend Integration:** Once backend API is implemented, verify local modifications are cleared after API success

## Conclusion

The `localModifications` strategy successfully decouples local UI state from backend polling cycles. The fix allows users to interact with alerts fluidly without waiting for backend synchronization, while still maintaining data consistency when the backend catches up.

**Status:** ✅ **FIXED** (pending backend API implementation for full persistence)
