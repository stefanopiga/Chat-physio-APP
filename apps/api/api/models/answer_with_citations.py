from pydantic import BaseModel, Field
from typing import List


class AnswerWithCitations(BaseModel):
    """Risposta LLM con citazioni dei chunk sorgente.

    Campi:
    - risposta: testo della risposta generata
    - citazioni: lista degli ID chunk usati come fonti
    """

    risposta: str = Field(description="La risposta alla domanda dell'utente.")
    citazioni: List[str] = Field(description="La lista degli ID dei chunk usati come fonte.")
