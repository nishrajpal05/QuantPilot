import uuid
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/backtest", tags=["backtest"])

VALID_RESOLUTIONS = {"D", "1min", "2min", "3min", "5min", "10min", "15min", "30min", "60min"}


class BacktestRequest(BaseModel):
    symbol:          str
    exchange:        str   = "NSE"
    start_date:      str
    end_date:        str
    prompt:          str
    initial_capital: float = 100000.0
    resolution:      str   = "D"


class BacktestCreateResponse(BaseModel):
    backtest_id: str
    status:      str = "pending"


def run_backtest_task(
    backtest_id:     str,
    user_id:         str,
    symbol:          str,
    exchange:        str,
    start_date:      str,
    end_date:        str,
    prompt:          str,
    initial_capital: float,
    resolution:      str,
    db_url:          str,
):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, pool_pre_ping=True)
    Sess   = sessionmaker(bind=engine)
    db     = Sess()

    try:
        db.execute(
            text("UPDATE public.backtests SET status='running' WHERE id=:id"),
            {"id": backtest_id},
        )
        db.commit()

        from app.orchestrator import graph, AgentState

        initial_state: AgentState = {
            "user_id":         user_id,
            "backtest_id":     backtest_id,
            "symbol":          symbol,
            "exchange":        exchange,
            "start_date":      start_date,
            "end_date":        end_date,
            "prompt":          prompt,
            "initial_capital": initial_capital,
            "resolution":      resolution,
            "df":              None,
            "generated_code":  None,
            "backtest_result": None,
            "risk_result":     None,
            "compliance":      None,
            "audit_hash":      None,
            "error":           None,
            "current_step":    None,
        }

        final_state = graph.invoke(initial_state)

        if final_state.get("error"):
            raise RuntimeError(final_state["error"])

        risk = final_state.get("risk_result") or {}
        comp = final_state.get("compliance")  or {}

        results_dict = {
            "total_return_pct": risk.get("total_return_pct"),
            "cagr":             risk.get("cagr"),
            "sharpe_ratio":     risk.get("sharpe_ratio"),
            "max_drawdown_pct": risk.get("max_drawdown_pct"),
            "win_rate":         risk.get("win_rate"),
            "total_trades":     risk.get("total_trades"),
            "dsr_score":        risk.get("dsr_score"),
            "equity_curve":     risk.get("equity_curve", []),
            "trades":           risk.get("trades", []),
            "monte_carlo":      risk.get("monte_carlo"),
            "walk_forward":     risk.get("walk_forward"),
            "compliance":       comp,
            "generated_code":   final_state.get("generated_code"),
        }

        audit_hash = final_state.get("audit_hash", "")

        db.execute(
            text("""
                UPDATE public.backtests
                SET status='completed', results=:results,
                    audit_hash=:audit_hash, completed_at=NOW()
                WHERE id=:id
            """),
            {
                "id":         backtest_id,
                "results":    json.dumps(results_dict, default=str),
                "audit_hash": audit_hash,
            },
        )
        db.commit()
        _write_audit_log(db, backtest_id, "completed", {"audit_hash": audit_hash}, audit_hash)

    except Exception as e:
        db.execute(
            text("UPDATE public.backtests SET status='failed', error_message=:err, completed_at=NOW() WHERE id=:id"),
            {"id": backtest_id, "err": str(e)},
        )
        db.commit()
        _write_audit_log(db, backtest_id, "failed", {"error": str(e)}, "")
    finally:
        db.close()


def _write_audit_log(db, backtest_id: str, event: str, payload: dict, current_hash: str):
    try:
        prev = db.execute(
            text("SELECT hash FROM public.audit_log WHERE backtest_id=:bid ORDER BY id DESC LIMIT 1"),
            {"bid": backtest_id},
        ).fetchone()
        db.execute(
            text("INSERT INTO public.audit_log (backtest_id, event, payload, hash, prev_hash) VALUES (:bid, :event, :payload, :hash, :prev_hash)"),
            {
                "bid":       backtest_id,
                "event":     event,
                "payload":   json.dumps(payload, default=str),
                "hash":      current_hash,
                "prev_hash": prev[0] if prev else None,
            },
        )
        db.commit()
    except Exception:
        pass


@router.post("", response_model=BacktestCreateResponse, status_code=202)
def create_backtest(
    body:             BacktestRequest,
    background_tasks: BackgroundTasks,
    db:               Session = Depends(get_db),
    current_user:     dict    = Depends(get_current_user),
):
    try:
        start = date.fromisoformat(body.start_date)
        end   = date.fromisoformat(body.end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Dates must be YYYY-MM-DD")
    if start >= end:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt cannot be empty")
    if body.resolution not in VALID_RESOLUTIONS:
        raise HTTPException(status_code=400, detail=f"resolution must be one of {VALID_RESOLUTIONS}")

    backtest_id = str(uuid.uuid4())
    user_id     = current_user["sub"]

    db.execute(
        text("""
            INSERT INTO public.backtests
                (id, user_id, symbol, exchange, start_date, end_date, initial_capital, status)
            VALUES (:id, :user_id, :symbol, :exchange, :start_date, :end_date, :capital, 'pending')
        """),
        {
            "id":         backtest_id,
            "user_id":    user_id,
            "symbol":     body.symbol.upper().strip(),
            "exchange":   body.exchange.upper(),
            "start_date": body.start_date,
            "end_date":   body.end_date,
            "capital":    body.initial_capital,
        },
    )
    db.commit()

    _write_audit_log(db, backtest_id, "created", {
        "symbol": body.symbol, "start": body.start_date,
        "end": body.end_date, "resolution": body.resolution,
        "prompt": body.prompt[:200],
    }, "")

    background_tasks.add_task(
        run_backtest_task,
        backtest_id=backtest_id,
        user_id=user_id,
        symbol=body.symbol.upper().strip(),
        exchange=body.exchange.upper(),
        start_date=body.start_date,
        end_date=body.end_date,
        prompt=body.prompt,
        initial_capital=body.initial_capital,
        resolution=body.resolution,
        db_url=settings.database_url,
    )

    return BacktestCreateResponse(backtest_id=backtest_id)


@router.get("/list")
def list_backtests(
    limit:        int  = 20,
    offset:       int  = 0,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user),
):
    rows = db.execute(
        text("""
            SELECT id, symbol, exchange, start_date, end_date,
                   status, audit_hash, created_at, completed_at,
                   results->>'total_return_pct' AS total_return_pct,
                   results->>'sharpe_ratio'     AS sharpe_ratio,
                   results->>'dsr_score'        AS dsr_score
            FROM public.backtests
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"uid": current_user["sub"], "limit": limit, "offset": offset},
    ).fetchall()

    return [
        {
            "id":               str(r.id),
            "symbol":           r.symbol,
            "exchange":         r.exchange,
            "start_date":       str(r.start_date),
            "end_date":         str(r.end_date),
            "status":           r.status,
            "audit_hash":       r.audit_hash,
            "created_at":       str(r.created_at),
            "completed_at":     str(r.completed_at) if r.completed_at else None,
            "total_return_pct": r.total_return_pct,
            "sharpe_ratio":     r.sharpe_ratio,
            "dsr_score":        r.dsr_score,
        }
        for r in rows
    ]


@router.get("/{backtest_id}/audit")
def get_audit_trail(
    backtest_id:  str,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user),
):
    owner = db.execute(
        text("SELECT user_id FROM public.backtests WHERE id=:id"),
        {"id": backtest_id},
    ).fetchone()
    if not owner or str(owner.user_id) != current_user["sub"]:
        raise HTTPException(status_code=404, detail="Backtest not found")

    logs = db.execute(
        text("SELECT event, payload, hash, prev_hash, created_at FROM public.audit_log WHERE backtest_id=:bid ORDER BY id ASC"),
        {"bid": backtest_id},
    ).fetchall()

    return [{"event": r.event, "payload": r.payload, "hash": r.hash, "prev_hash": r.prev_hash, "created_at": str(r.created_at)} for r in logs]


@router.get("/{backtest_id}")
def get_backtest(
    backtest_id:  str,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user),
):
    row = db.execute(
        text("""
            SELECT id, user_id, symbol, exchange, start_date, end_date,
                   initial_capital, status, error_message, results,
                   audit_hash, created_at, completed_at
            FROM public.backtests
            WHERE id=:id AND user_id=:uid
        """),
        {"id": backtest_id, "uid": current_user["sub"]},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Backtest not found")

    response = {
        "id":              str(row.id),
        "symbol":          row.symbol,
        "exchange":        row.exchange,
        "start_date":      str(row.start_date),
        "end_date":        str(row.end_date),
        "initial_capital": float(row.initial_capital),
        "status":          row.status,
        "error_message":   row.error_message,
        "audit_hash":      row.audit_hash,
        "created_at":      str(row.created_at),
        "completed_at":    str(row.completed_at) if row.completed_at else None,
    }

    if row.results:
        results = row.results if isinstance(row.results, dict) else json.loads(row.results)
        response.update(results)

    return response
