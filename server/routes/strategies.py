from fastapi import APIRouter, HTTPException, Query
from typing import List
from server.schemas import StrategyCreate, StrategyUpdate, StrategyOut
from strategies.engine import (
    load_strategy, list_strategies, create_strategy,
    update_strategy, delete_strategy, validate_strategy
)
from strategies.indicators import list_indicators
from strategies.templates import list_templates

router = APIRouter(prefix="/strategies", tags=["strategies"])

@router.get("/templates")
def get_strategy_templates():
    """Return all pre-built strategy templates for the Template Gallery."""
    return list_templates()

@router.get("/", response_model=List[StrategyOut])
def get_all_strategies():
    try:
        strats = list_strategies()
        detailed_strats = []
        for s in strats:
            name = s[1]
            full_strat = load_strategy(name)
            if full_strat:
                detailed_strats.append(
                    StrategyOut(
                        id=full_strat["id"],
                        name=full_strat["name"],
                        description=full_strat["description"],
                        columns=full_strat["columns"],
                        signal_rule=full_strat["signal_rule"],
                        created_at=full_strat["created_at"]
                    )
                )
        return detailed_strats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{name}", response_model=StrategyOut)
def get_strategy_detail(name: str):
    strat = load_strategy(name)
    if strat is None:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found.")
    return StrategyOut(
        id=strat["id"],
        name=strat["name"],
        description=strat["description"],
        columns=strat["columns"],
        signal_rule=strat["signal_rule"],
        created_at=strat["created_at"]
    )

@router.post("/", response_model=StrategyOut)
def create_new_strategy(req: StrategyCreate):
    validation = validate_strategy(req.columns, req.signal_rule)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=f"Strategy validation failed: {validation['error']}")
    
    try:
        strat_id = create_strategy(
            name=req.name,
            description=req.description,
            columns=req.columns,
            signal_rule=req.signal_rule
        )
        created = load_strategy(req.name)
        return StrategyOut(
            id=created["id"],
            name=created["name"],
            description=created["description"],
            columns=created["columns"],
            signal_rule=created["signal_rule"],
            created_at=created["created_at"]
        )
    except Exception as e:
        error_msg = str(e)
        if "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise HTTPException(status_code=400, detail=f"Strategy '{req.name}' already exists.")
        raise HTTPException(status_code=500, detail=error_msg)

@router.put("/{name}")
def update_existing_strategy(name: str, req: StrategyUpdate):
    existing = load_strategy(name)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found.")
    
    new_cols = req.columns if req.columns is not None else existing["columns"]
    new_signal = req.signal_rule if req.signal_rule is not None else existing["signal_rule"]
    
    validation = validate_strategy(new_cols, new_signal)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=f"Strategy validation failed: {validation['error']}")
        
    try:
        updated = update_strategy(
            name=name,
            description=req.description,
            columns=req.columns,
            signal_rule=req.signal_rule
        )
        if not updated:
            raise HTTPException(status_code=400, detail="No updates were applied.")
        return {"success": True, "message": f"Strategy '{name}' updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{name}")
def delete_existing_strategy(name: str, force: bool = Query(False)):
    result = delete_strategy(name, force=force)
    if result["deleted"]:
        return {
            "success": True,
            "message": f"Strategy '{name}' deleted.",
            "deleted_runs": result.get("deleted_runs", 0)
        }
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@router.get("/meta/indicators")
def get_indicators_list():
    return list_indicators()
