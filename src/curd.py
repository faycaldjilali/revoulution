from typing import Optional, Dict, List
import json
from src.db import read_sql
from src.service import calculate_deadline_info

def get_all_notices(filters: Optional[Dict] = None) -> List[Dict]:
    query = """
    SELECT idweb, id, objet, nomacheteur, dateparution,
           datelimitereponse, datefindiffusion, famille,
           code_departement, type_procedure, nature,
           keywords_used, visite_obligatoire, dce_link, lot_numbers
    FROM boamp_notices
    WHERE 1=1
    """
    params = []

    if filters:
        if filters.get("keyword"):
            query += " AND (objet LIKE ? OR keywords_used LIKE ?)"
            k = f"%{filters['keyword']}%"
            params.extend([k, k])

        if filters.get("department"):
            query += " AND code_departement LIKE ?"
            params.append(f"%{filters['department']}%")

    query += " ORDER BY dateparution DESC"

    df = read_sql(query, params if params else None)

    notices = []
    for _, row in df.iterrows():
        n = row.to_dict()
        n.update(calculate_deadline_info(n))

        n["keywords_list"] = str(n.get("keywords_used", "")).split(";")
        n["lots_list"] = str(n.get("lot_numbers", "")).split(",")

        notices.append(n)

    if filters and filters.get("urgency") == "overdue":
        notices = [n for n in notices if n["is_overdue"]]

    return notices


def get_notice_by_id(notice_id: str):
    df = read_sql(
        "SELECT * FROM boamp_notices WHERE idweb=? OR id=? LIMIT 1",
        [notice_id, notice_id]
    )

    if df.empty:
        return None

    notice = df.iloc[0].to_dict()
    notice.update(calculate_deadline_info(notice))

    for field in ["gestion", "donnees"]:
        if notice.get(field):
            try:
                notice[f"{field}_parsed"] = json.loads(notice[field])
            except Exception:
                notice[f"{field}_parsed"] = None

    return notice
