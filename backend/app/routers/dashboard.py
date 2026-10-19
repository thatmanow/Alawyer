from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Consultation, Contract, KbDocument, User
from app.schemas import DashboardOut
from app.services.neo4j_service import neo4j_service
from app.services.ollama_client import ollama
from app.utils import now_cn

router = APIRouter(prefix="/api/dashboard", tags=["主页仪表盘"])


def _mysql_domain_stats(db: Session):
    rows = db.query(KbDocument.domain, func.count(KbDocument.id)).group_by(KbDocument.domain).all()
    return [{"name": r[0], "value": r[1]} for r in rows]


def _fallback_graph(db: Session):
    docs = db.query(KbDocument).all()
    nodes, links = [], []
    root = {"id": "root", "name": "alawyer 法律领域", "label": "Root", "size": 46}
    nodes.append(root)
    domains = {}
    for d in docs:
        did = f"doc-{d.id}"
        nodes.append({"id": did, "name": d.name, "label": "Document", "size": 26})
        links.append({"source": did, "target": f"dom-{d.domain}", "type": "BELONGS_TO"})
        for kw in (d.keywords or [])[:6]:
            kid = f"kw-{kw}"
            if kid not in [n["id"] for n in nodes]:
                nodes.append({"id": kid, "name": kw, "label": "Keyword", "size": 18})
            links.append({"source": did, "target": kid, "type": "MENTIONS"})
        if d.domain not in domains:
            domains[d.domain] = True
            nodes.append({"id": f"dom-{d.domain}", "name": d.domain, "label": "Domain", "size": 34})
            links.append({"source": f"dom-{d.domain}", "target": "root", "type": "PART_OF"})
    return {"nodes": nodes, "links": links}


@router.get("/summary", response_model=DashboardOut)
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today_start = now_cn().replace(hour=0, minute=0, second=0, microsecond=0)
    today_consultations = (
        db.query(Consultation).filter(Consultation.created_at >= today_start).count()
    )
    contract_reviewed = db.query(Contract).filter(Contract.status != "pending").count()
    kb_docs = db.query(KbDocument).count()
    total_users = db.query(User).count()
    online_users = db.query(User).filter(User.status == "online").count()

    domain_stats = (
        neo4j_service.domain_stats() if neo4j_service.available() else _mysql_domain_stats(db)
    )
    if not domain_stats:
        domain_stats = _mysql_domain_stats(db)

    graph = (
        neo4j_service.get_graph()
        if neo4j_service.available()
        else {"nodes": [], "links": []}
    )
    if not graph.get("nodes"):
        graph = _fallback_graph(db)

    trend = []
    for offset in range(6, -1, -1):
        day = today_start - timedelta(days=offset)
        day_end = day + timedelta(days=1)
        count = (
            db.query(Consultation)
            .filter(Consultation.created_at >= day, Consultation.created_at < day_end)
            .count()
        )
        trend.append({"date": day.strftime("%m-%d"), "value": count})

    services = {
        "mysql": True,
        "redis": None,
        "neo4j": neo4j_service.available(),
        "ollama": ollama.healthy(),
    }
    from app.services.redis_cache import cache_service

    services["redis"] = cache_service.available

    return DashboardOut(
        server_time=datetime.now(),
        today_consultations=today_consultations,
        contract_reviewed=contract_reviewed,
        kb_docs=kb_docs,
        total_users=total_users,
        online_users=online_users,
        domain_distribution=domain_stats,
        consultation_trend=trend,
        graph=graph,
        services=services,
    )