"""Translatable error payloads for HTTPException details.

Em vez de retornar `HTTPException(detail="texto em português")`, retornamos
`HTTPException(detail={"code": "invoice_paid", ...kwargs})`. O frontend
mapeia o código pra mensagem localizada (ex: `useUiT('error.invoice_paid')`).

Códigos seguem `dominio_subdominio` em snake_case, lowercase, ASCII.
Campos extras (ids, datas) viajam no mesmo objeto e podem ser interpolados
na mensagem traduzida.

Exemplo:
    raise HTTPException(status_code=409, detail=err("invoice_paid",
                                                    invoice_id=inv.id))
"""
from __future__ import annotations

from typing import Any


def err(code: str, **kwargs: Any) -> dict[str, Any]:
    """Constrói payload de erro com código traduzível + dados auxiliares.

    `code` deve casar com chave `error.<code>` no dicionário de tradução
    do frontend. Campos extras (ids, datas) viajam no mesmo objeto.
    """
    return {"code": code, **kwargs}
