from datetime import date, timedelta
from dateutil import parser
from typing import Dict, Any

def calculate_deadline_info(notice: Dict[str, Any]) -> Dict[str, Any]:
    today = date.today()

    deadline_info = {
        "deadline_date": None,
        "deadline_field": None,
        "days_remaining": None,
        "is_urgent": False,
        "is_overdue": False,
        "deadline_text": "No deadline",
        "deadline_class": "deadline-neutral",
    }

    target_date = None
    field = None

    for f in ["datelimitereponse", "datefindiffusion"]:
        if notice.get(f):
            try:
                target_date = parser.parse(str(notice[f])).date()
                field = f
                break
            except Exception:
                pass

    if not target_date:
        return deadline_info

    days = (target_date - today).days

    deadline_info.update({
        "deadline_date": target_date.strftime("%Y-%m-%d"),
        "deadline_field": field,
        "days_remaining": days,
        "is_urgent": 0 <= days <= 7,
        "is_overdue": days < 0,
        "deadline_text": f"{days}j" if days >= 0 else f"-{abs(days)}j",
        "deadline_class": (
            "deadline-overdue" if days < 0 else
            "deadline-urgent" if days <= 7 else
            "deadline-warning" if days <= 30 else
            "deadline-ok"
        )
    })

    return deadline_info
