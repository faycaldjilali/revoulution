#

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil import parser
from typing import Optional, List, Dict, Any
import json

app = FastAPI(title="BOAMP Dashboard", version="1.0.0")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_PATH = "boamp.db"

def calculate_deadline_info(notice_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate deadline information for a notice."""
    today = date.today()
    seven_days_later = today + timedelta(days=7)
    
    # Initialize with defaults
    deadline_info = {
        'deadline_date': None,
        'deadline_field': None,
        'days_remaining': None,
        'is_urgent': False,
        'is_overdue': False,
        'deadline_text': "No deadline",
        'deadline_class': 'deadline-neutral'
    }
    
    # Check datelimitereponse first
    target_date = None
    date_field = None
    
    if notice_data.get('datelimitereponse'):
        try:
            if 'T' in str(notice_data['datelimitereponse']):
                target_date = parser.parse(str(notice_data['datelimitereponse'])).date()
            else:
                target_date = parser.parse(str(notice_data['datelimitereponse'])).date()
            date_field = 'datelimitereponse'
        except Exception as e:
            print(f"Error parsing datelimitereponse: {e}")
    
    # If no datelimitereponse, try datefindiffusion
    if not target_date and notice_data.get('datefindiffusion'):
        try:
            target_date = parser.parse(str(notice_data['datefindiffusion'])).date()
            date_field = 'datefindiffusion'
        except Exception as e:
            print(f"Error parsing datefindiffusion: {e}")
    
    if not target_date:
        return deadline_info
    
    # Calculate days remaining
    days_remaining = (target_date - today).days
    is_overdue = days_remaining < 0
    is_urgent = 0 <= days_remaining <= 7
    
    # Determine CSS class
    if is_overdue:
        deadline_class = 'deadline-overdue'
    elif is_urgent:
        deadline_class = 'deadline-urgent'
    elif days_remaining <= 30:
        deadline_class = 'deadline-warning'
    else:
        deadline_class = 'deadline-ok'
    
    # Create text description
    if days_remaining == 0:
        deadline_text = "Aujourd'hui"
    elif days_remaining > 0:
        if days_remaining > 30:
            months = days_remaining // 30
            remaining_days = days_remaining % 30
            if months > 0 and remaining_days > 0:
                deadline_text = f"{months}m {remaining_days}j"
            elif months > 0:
                deadline_text = f"{months} mois"
            else:
                deadline_text = f"{remaining_days}j"
        else:
            deadline_text = f"{days_remaining}j"
    else:
        days_overdue = abs(days_remaining)
        deadline_text = f"-{days_overdue}j"
    
    deadline_info.update({
        'deadline_date': target_date.strftime('%Y-%m-%d'),
        'deadline_field': date_field,
        'days_remaining': days_remaining,
        'is_urgent': is_urgent,
        'is_overdue': is_overdue,
        'deadline_text': deadline_text,
        'deadline_class': deadline_class
    })
    
    return deadline_info

def get_all_notices(filters: Optional[Dict] = None) -> List[Dict]:
    """Get all notices from database with optional filtering."""
    conn = sqlite3.connect(DB_PATH)
    
    # Base query
    query = """
    SELECT idweb, id, objet, nomacheteur, dateparution, 
           datelimitereponse, datefindiffusion, famille, 
           code_departement, type_procedure, nature,
           keywords_used, visite_obligatoire, dce_link, lot_numbers
    FROM boamp_notices
    WHERE 1=1
    """
    
    params = []
    
    # Apply filters
    if filters:
        if filters.get('keyword'):
            query += " AND (keywords_used LIKE ? OR objet LIKE ?)"
            keyword_term = f"%{filters['keyword']}%"
            params.extend([keyword_term, keyword_term])
        
        if filters.get('department'):
            query += " AND code_departement LIKE ?"
            params.append(f"%{filters['department']}%")
        
        if filters.get('nature'):
            query += " AND nature LIKE ?"
            params.append(f"%{filters['nature']}%")
        
        if filters.get('visite_obligatoire'):
            query += " AND visite_obligatoire = ?"
            params.append(filters['visite_obligatoire'])
        
        if filters.get('urgency') == 'urgent':
            query += " AND (datelimitereponse IS NOT NULL OR datefindiffusion IS NOT NULL)"
        elif filters.get('urgency') == 'overdue':
            # This filter will be applied in Python after calculation
            pass
    
    query += " ORDER BY dateparution DESC"
    
    # Execute query
    df = pd.read_sql_query(query, conn, params=params if params else None)
    conn.close()
    
    # Process each notice
    notices = []
    for _, row in df.iterrows():
        notice = row.to_dict()
        
        # Calculate deadline info
        deadline_info = calculate_deadline_info(notice)
        notice.update(deadline_info)
        
        # Format keywords
        if notice.get('keywords_used'):
            keywords = str(notice['keywords_used']).split(';')
            notice['keywords_list'] = [k.strip() for k in keywords if k.strip()]
        else:
            notice['keywords_list'] = []
        
        # Format lot numbers
        if notice.get('lot_numbers'):
            lots = str(notice['lot_numbers']).split(',')
            notice['lots_list'] = [lot.strip() for lot in lots if lot.strip()]
        else:
            notice['lots_list'] = []
        
        # Format department
        if notice.get('code_departement'):
            dept = str(notice['code_departement']).replace('["', '').replace('"]', '').replace('"', '')
            notice['departments_list'] = [d.strip() for d in dept.split(',') if d.strip()]
        else:
            notice['departments_list'] = []
        
        notices.append(notice)
    
    # Apply overdue filter if needed
    if filters and filters.get('urgency') == 'overdue':
        notices = [n for n in notices if n.get('is_overdue')]
    
    return notices

def get_notice_by_id(notice_id: str) -> Optional[Dict]:
    """Get a specific notice by ID."""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
    SELECT * 
    FROM boamp_notices 
    WHERE idweb = ? OR id = ?
    LIMIT 1
    """
    
    df = pd.read_sql_query(query, conn, params=[notice_id, notice_id])
    conn.close()
    
    if df.empty:
        return None
    
    notice = df.iloc[0].to_dict()
    
    # Calculate deadline info
    deadline_info = calculate_deadline_info(notice)
    notice.update(deadline_info)
    
    # Format complex fields
    if notice.get('keywords_used'):
        keywords = str(notice['keywords_used']).split(';')
        notice['keywords_list'] = [k.strip() for k in keywords if k.strip()]
    
    if notice.get('lot_numbers'):
        lots = str(notice['lot_numbers']).split(',')
        notice['lots_list'] = [lot.strip() for lot in lots if lot.strip()]
    
    # Parse JSON fields if they exist
    if notice.get('gestion') and isinstance(notice['gestion'], str):
        try:
            notice['gestion_parsed'] = json.loads(notice['gestion'])
        except:
            notice['gestion_parsed'] = None
    
    if notice.get('donnees') and isinstance(notice['donnees'], str):
        try:
            notice['donnees_parsed'] = json.loads(notice['donnees'])
        except:
            notice['donnees_parsed'] = None
    
    return notice

def get_dashboard_stats() -> Dict[str, Any]:
    """Get statistics for the dashboard."""
    notices = get_all_notices()
    
    total = len(notices)
    urgent = sum(1 for n in notices if n.get('is_urgent'))
    overdue = sum(1 for n in notices if n.get('is_overdue'))
    with_dce = sum(1 for n in notices if n.get('dce_link') and str(n['dce_link']).lower() != 'none')
    with_visite = sum(1 for n in notices if n.get('visite_obligatoire') and str(n['visite_obligatoire']).lower() == 'yes')
    
    # Get unique keywords
    all_keywords = []
    for n in notices:
        all_keywords.extend(n.get('keywords_list', []))
    unique_keywords = len(set(all_keywords))
    
    return {
        'total_notices': total,
        'urgent_deadlines': urgent,
        'overdue_deadlines': overdue,
        'with_dce_link': with_dce,
        'with_visite_obligatoire': with_visite,
        'unique_keywords': unique_keywords,
        'today': date.today().strftime('%d/%m/%Y')
    }

# API Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, 
                   keyword: Optional[str] = None,
                   department: Optional[str] = None,
                   nature: Optional[str] = None,
                   visite: Optional[str] = None,
                   urgency: Optional[str] = None):
    """Main dashboard page."""
    
    filters = {}
    if keyword:
        filters['keyword'] = keyword
    if department:
        filters['department'] = department
    if nature:
        filters['nature'] = nature
    if visite:
        filters['visite_obligatoire'] = visite
    if urgency:
        filters['urgency'] = urgency
    
    notices = get_all_notices(filters)
    stats = get_dashboard_stats()
    
    # Get unique values for filters
    conn = sqlite3.connect(DB_PATH)
    
    # Get unique departments
    dept_query = """
    SELECT DISTINCT code_departement 
    FROM boamp_notices 
    WHERE code_departement IS NOT NULL AND code_departement != 'None'
    """
    departments = pd.read_sql_query(dept_query, conn)['code_departement'].tolist()
    
    # Get unique natures
    nature_query = """
    SELECT DISTINCT nature 
    FROM boamp_notices 
    WHERE nature IS NOT NULL
    """
    natures = pd.read_sql_query(nature_query, conn)['nature'].tolist()
    
    conn.close()
    
    context = {
        "request": request,
        "notices": notices,
        "stats": stats,
        "filters": {
            "keyword": keyword,
            "department": department,
            "nature": nature,
            "visite": visite,
            "urgency": urgency
        },
        "departments": departments[:50],  # Limit to 50
        "natures": natures[:50]  # Limit to 50
    }
    
    return templates.TemplateResponse("index.html", context)

@app.get("/notice/{notice_id}", response_class=HTMLResponse)
async def notice_detail(request: Request, notice_id: str):
    """Notice detail page."""
    notice = get_notice_by_id(notice_id)
    
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    
    context = {
        "request": request,
        "notice": notice
    }
    
    return templates.TemplateResponse("notice.html", context)

@app.get("/api/notices", response_class=JSONResponse)
async def api_notices(keyword: Optional[str] = None, 
                     department: Optional[str] = None,
                     urgency: Optional[str] = None):
    """API endpoint to get notices in JSON format."""
    filters = {}
    if keyword:
        filters['keyword'] = keyword
    if department:
        filters['department'] = department
    if urgency:
        filters['urgency'] = urgency
    
    notices = get_all_notices(filters)
    
    # Simplify for API response
    simplified_notices = []
    for n in notices:
        simplified = {
            'idweb': n.get('idweb'),
            'objet': n.get('objet'),
            'nomacheteur': n.get('nomacheteur'),
            'dateparution': n.get('dateparution'),
            'deadline_date': n.get('deadline_date'),
            'deadline_text': n.get('deadline_text'),
            'deadline_class': n.get('deadline_class'),
            'keywords': n.get('keywords_list', []),
            'lots': n.get('lots_list', []),
            'visite_obligatoire': n.get('visite_obligatoire'),
            'dce_link': n.get('dce_link'),
            'is_urgent': n.get('is_urgent'),
            'is_overdue': n.get('is_overdue')
        }
        simplified_notices.append(simplified)
    
    return {"notices": simplified_notices}

@app.get("/api/stats", response_class=JSONResponse)
async def api_stats():
    """API endpoint to get dashboard statistics."""
    stats = get_dashboard_stats()
    return stats

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
