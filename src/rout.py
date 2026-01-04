from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
from src.curd import get_all_notices, get_notice_by_id
from .config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    keyword: Optional[str] = None,
    department: Optional[str] = None,
    urgency: Optional[str] = None,
):
    filters = {
        "keyword": keyword,
        "department": department,
        "urgency": urgency,
    }

    notices = get_all_notices(filters)

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "notices": notices}
    )


@router.get("/notice/{notice_id}", response_class=HTMLResponse)
async def notice_detail(request: Request, notice_id: str):
    notice = get_notice_by_id(notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")

    return templates.TemplateResponse(
        "notice.html",
        {"request": request, "notice": notice}
    )


@router.get("/api/notices", response_class=JSONResponse)
async def api_notices():
    return {"notices": get_all_notices()}
