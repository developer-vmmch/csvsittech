from datetime import datetime, timedelta, time

def get_laboratory_day(current_time, day_start_time, day_end_time):
    # Lab day is 04:00 AM to 03:59 AM next day
    # Returns (start_dt, end_dt)
    start_dt = datetime.combine(current_time.date(), day_start_time)
    if current_time.time() < day_start_time:
        start_dt -= timedelta(days=1)
    
    end_dt = datetime.combine(start_dt.date(), day_end_time)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
        
    return start_dt, end_dt

def get_expected_entries(current_time, lab_start, lab_end, trigger_time, rush_time, max_entries, rush_pct):
    trigger_dt = datetime.combine(lab_start.date(), trigger_time)
    if trigger_dt < lab_start:
        trigger_dt += timedelta(days=1)
        
    rush_dt = datetime.combine(lab_start.date(), rush_time)
    if rush_dt < trigger_dt:
        rush_dt += timedelta(days=1)
        
    if current_time <= trigger_dt:
        return 0
        
    rush_target = round(max_entries * (rush_pct / 100.0))
    rem_target = max_entries - rush_target
    
    if current_time <= rush_dt:
        # We are in rush period
        total_rush_mins = (rush_dt - trigger_dt).total_seconds() / 60.0
        elapsed_mins = (current_time - trigger_dt).total_seconds() / 60.0
        return int((elapsed_mins / total_rush_mins) * rush_target)
    else:
        # We are in remaining period
        if current_time >= lab_end:
            return max_entries
            
        total_rem_mins = (lab_end - rush_dt).total_seconds() / 60.0
        elapsed_mins = (current_time - rush_dt).total_seconds() / 60.0
        return rush_target + int((elapsed_mins / total_rem_mins) * rem_target)

# Test cases
cur = datetime.strptime("2026-08-28 10:30:00", "%Y-%m-%d %H:%M:%S")
s, e = get_laboratory_day(cur, time(4, 0), time(3, 59))
expected = get_expected_entries(cur, s, e, time(10, 0), time(14, 0), 125, 75)
print("Expected at 10:30 AM:", expected)
