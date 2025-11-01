# Conversational Memory Patterns for RAG

**Document Type**: Technical Reference  
**Date**: 2025-10-22  
**Status**: Approved  
**Related**: Story 7.1 Task 4

---

## Problem Statement

**Current state**: Sistema RAG stateless — ogni query elaborata indipendentemente senza context conversazionale.

**Consequence**:
- ❌ Impossibili follow-up: "Approfondisci punto 2" → LLM non sa di cosa parliamo
- ❌ Studente deve riformulare contesto completo: "Nella spondilolistesi che abbiamo discusso prima..."
- ❌ Nessun vantaggio conversazionale vs ricerca statica documenti

**Solution**: Context window management per maintain

are memoria ultimi 2-3 turni conversazionali.

---

## Architecture

### Context Window Structure

```
┌─────────────────────────────────────────────────────┐
│ CONVERSATIONAL CONTEXT WINDOW                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Session ID: "abc-123"                              │
│  Max Turns: 3                                       │
│  Max Tokens: 2000                                   │
│                                                     │
│  Messages (chronological, last 6 messages):         │
│  ┌───────────────────────────────────────────────┐ │
│  │ [Turn 1]                                      │ │
│  │ USER: "Cos'è la spondilolistesi?"             │ │
│  │ ASSISTANT: "La spondilolistesi è..."          │ │
│  │ Chunks: [chunk-1, chunk-2, chunk-3]           │ │
│  │ Timestamp: 2025-10-22T10:30:00Z               │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │ [Turn 2]                                      │ │
│  │ USER: "Quali sono i gradi?"                   │ │
│  │ ASSISTANT: "Il grading di Meyerding..."       │ │
│  │ Chunks: [chunk-4, chunk-5]                    │ │
│  │ Timestamp: 2025-10-22T10:31:15Z               │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │ [Turn 3 - CURRENT]                            │ │
│  │ USER: "Approfondisci il punto 2"              │ │
│  │ ASSISTANT: [IN GENERATION]                    │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  Total Token Count: ~1800 / 2000                   │
└─────────────────────────────────────────────────────┘
```

---

## Implementation

### Data Models

```python
# apps/api/api/models/conversation.py

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime


class ConversationMessage(BaseModel):
    """Singolo messaggio nella conversation history."""
    
    role: Literal["user", "assistant"]
    content: str = Field(description="Testo messaggio")
    timestamp: datetime
    chunk_ids: Optional[List[str]] = Field(
        default=None,
        description="ID chunk usati per generare risposta (solo assistant messages)"
    )
    
    def to_compact_format(self, max_length: int = 150) -> str:
        """Formato compatto per inclusione in prompt (risparmio token)."""
        truncated = self.content[:max_length]
        if len(self.content) > max_length:
            truncated += "..."
        return truncated


class ChatContextWindow(BaseModel):
    """Context window per session conversazionale."""
    
    session_id: str
    messages: List[ConversationMessage] = Field(
        default_factory=list,
        max_items=6,  # 3 turni (user + assistant per turno)
        description="Cronologia messaggi recenti"
    )
    total_tokens: int = Field(
        default=0,
        description="Token count approssimativo (per budget management)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Conversation Manager Service

```python
# apps/api/api/services/conversation_service.py

import logging
from typing import List, Optional
from datetime import datetime

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logging.warning("tiktoken not available, using approximate token counting")

from ..models.conversation import ConversationMessage, ChatContextWindow
from ..stores import chat_messages_store

logger = logging.getLogger("api")


class ConversationManager:
    """
    Gestisce memoria conversazionale per RAG context-aware.
    
    Features:
    - Mantiene ultimi 3 turni (6 messaggi)
    - Token counting per evitare overflow
    - Truncation automatica se eccede budget
    - Formatting per prompt injection
    """
    
    MAX_TURNS = 3  # Turni conversazionali (user + assistant = 1 turno)
    MAX_MESSAGES = MAX_TURNS * 2  # 6 messaggi totali
    MAX_CONTEXT_TOKENS = 2000  # Budget token per history
    COMPACT_MESSAGE_LENGTH = 150  # Lunghezza max per messaggio in prompt
    
    def __init__(self):
        """Initialize conversation manager con token encoder."""
        if TIKTOKEN_AVAILABLE:
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        else:
            self.tokenizer = None
    
    def get_context_window(self, session_id: str) -> ChatContextWindow:
        """
        Recupera context window per session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ChatContextWindow con messaggi recenti e token count
        """
        # Recupera messaggi da store
        messages_data = chat_messages_store.get(session_id, [])
        
        if not messages_data:
            logger.debug({
                "event": "conversation_no_history",
                "session_id": session_id
            })
            return ChatContextWindow(session_id=session_id, messages=[])
        
        # Converti a ConversationMessage objects
        messages = []
        for msg_data in messages_data:
            try:
                msg = ConversationMessage(
                    role=msg_data.get('role'),
                    content=msg_data.get('content', ''),
                    timestamp=msg_data.get('timestamp', datetime.utcnow().isoformat()),
                    chunk_ids=msg_data.get('chunk_ids')
                )
                messages.append(msg)
            except Exception as e:
                logger.warning({
                    "event": "conversation_message_parse_error",
                    "error": str(e),
                    "session_id": session_id
                })
                continue
        
        # Mantieni solo ultimi N messaggi (sliding window)
        recent_messages = messages[-self.MAX_MESSAGES:]
        
        # Calcola token totali
        total_tokens = self._count_tokens(recent_messages)
        
        # Truncate se eccede budget
        if total_tokens > self.MAX_CONTEXT_TOKENS:
            logger.info({
                "event": "conversation_truncating",
                "session_id": session_id,
                "before_tokens": total_tokens,
                "before_messages": len(recent_messages)
            })
            recent_messages = self._truncate_to_budget(recent_messages)
            total_tokens = self._count_tokens(recent_messages)
        
        logger.debug({
            "event": "conversation_context_loaded",
            "session_id": session_id,
            "messages_count": len(recent_messages),
            "total_tokens": total_tokens
        })
        
        return ChatContextWindow(
            session_id=session_id,
            messages=recent_messages,
            total_tokens=total_tokens,
            updated_at=datetime.utcnow()
        )
    
    def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        chunk_ids: Optional[List[str]] = None
    ) -> None:
        """
        Aggiunge turno conversazionale completo (user + assistant).
        
        Args:
            session_id: Session identifier
            user_message: Messaggio utente
            assistant_message: Risposta assistant
            chunk_ids: ID chunk usati per generare risposta
        """
        if session_id not in chat_messages_store:
            chat_messages_store[session_id] = []
        
        now = datetime.utcnow().isoformat()
        
        # Aggiungi entrambi messaggi del turno
        chat_messages_store[session_id].extend([
            {
                "role": "user",
                "content": user_message,
                "timestamp": now,
                "chunk_ids": None
            },
            {
                "role": "assistant",
                "content": assistant_message,
                "timestamp": now,
                "chunk_ids": chunk_ids or []
            }
        ])
        
        logger.debug({
            "event": "conversation_turn_added",
            "session_id": session_id,
            "total_messages": len(chat_messages_store[session_id])
        })
    
    def format_for_prompt(
        self,
        context_window: ChatContextWindow,
        include_chunk_refs: bool = False
    ) -> str:
        """
        Formatta history per inclusione nel prompt LLM.
        
        Args:
            context_window: Context window da formattare
            include_chunk_refs: Includi riferimenti chunk_ids (verbose)
            
        Returns:
            Stringa formattata per prompt injection
        """
        if not context_window.messages:
            return "Nessuna conversazione precedente."
        
        formatted_lines = []
        
        for msg in context_window.messages:
            role_label = "STUDENTE" if msg.role == "user" else "TUTOR"
            
            # Usa versione compatta per risparmiare token
            content = msg.to_compact_format(self.COMPACT_MESSAGE_LENGTH)
            
            line = f"{role_label}: {content}"
            
            # Opzionale: includi chunk references per debug
            if include_chunk_refs and msg.chunk_ids:
                chunk_refs = ", ".join(msg.chunk_ids[:3])  # Max 3 ID
                line += f" [fonti: {chunk_refs}]"
            
            formatted_lines.append(line)
        
        header = f"=== CRONOLOGIA CONVERSAZIONE (ultimi {len(context_window.messages)//2} turni) ==="
        footer = "=== FINE CRONOLOGIA ==="
        
        return f"{header}\n" + "\n".join(formatted_lines) + f"\n{footer}"
    
    def clear_session(self, session_id: str) -> None:
        """Elimina cronologia sessione (es. su richiesta utente)."""
        if session_id in chat_messages_store:
            del chat_messages_store[session_id]
            logger.info({
                "event": "conversation_cleared",
                "session_id": session_id
            })
    
    # === Private Methods ===
    
    def _count_tokens(self, messages: List[ConversationMessage]) -> int:
        """Conta token totali nei messaggi."""
        if self.tokenizer:
            total = 0
            for msg in messages:
                total += len(self.tokenizer.encode(msg.content))
            return total
        else:
            # Approssimazione: 1 token ~= 4 caratteri inglese, ~3 caratteri italiano
            total_chars = sum(len(msg.content) for msg in messages)
            return total_chars // 3
    
    def _truncate_to_budget(
        self,
        messages: List[ConversationMessage]
    ) -> List[ConversationMessage]:
        """
        Rimuove messaggi più vecchi finché sotto token budget.
        
        Garantisce rimozione turni completi (user + assistant insieme).
        """
        while messages and self._count_tokens(messages) > self.MAX_CONTEXT_TOKENS:
            # Rimuovi 2 messaggi alla volta (1 turno completo)
            if len(messages) >= 2:
                messages = messages[2:]
            else:
                messages = messages[1:]  # Edge case: rimane 1 solo
        
        return messages


# Singleton instance
_conversation_manager: Optional[ConversationManager] = None

def get_conversation_manager() -> ConversationManager:
    """Factory function per dependency injection."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
```

---

## Integration with RAG Endpoint

### Updated Prompt Template

```python
# apps/api/api/routers/chat.py

from ..services.conversation_service import get_conversation_manager

ACADEMIC_MEDICAL_PROMPT_WITH_MEMORY = """
Sei un medico fisioterapista con esperienza accademica e clinica.
Supporti studenti fornendo risposte chiare, strutturate e propedeutiche.

{conversation_history}

MATERIALE DIDATTICO DISPONIBILE:
{context}

ISTRUZIONI:
- Se la domanda corrente si riferisce alla conversazione precedente (es. "approfondisci", "come prima", "il punto 2"), usa la cronologia per contestualizzare
- Mantieni coerenza con risposte precedenti
- Se necessario, fai riferimento esplicito a concetti già discussi
- Rispondi SOLO basandoti su materiale didattico + cronologia conversazione
- Cita sempre le fonti con ID chunk

DOMANDA CORRENTE:
{question}
"""

@router.post("/sessions/{sessionId}/messages")
def create_chat_message(...):
    # ... existing code ...
    
    # NUOVO: Recupera conversation context
    conv_manager = get_conversation_manager()
    context_window = conv_manager.get_context_window(sessionId)
    conversation_history = conv_manager.format_for_prompt(context_window)
    
    # Update prompt con history
    prompt = ChatPromptTemplate.from_messages([
        ("system", ACADEMIC_MEDICAL_PROMPT_WITH_MEMORY),
        ("user", "{question}")
    ]).partial(
        conversation_history=conversation_history,
        context=context,  # Chunk retrieved
        format_instructions=format_instructions
    )
    
    # Generate response
    result = chain.invoke({"question": user_message})
    
    # NUOVO: Salva turno conversazionale
    conv_manager.add_turn(
        session_id=sessionId,
        user_message=user_message,
        assistant_message=result.risposta,
        chunk_ids=result.citazioni
    )
    
    # ... rest of endpoint ...
```

---

## Token Budget Management

### Context Window Budget Allocation

**gpt-5-nano limit**: 4096 token input max

```
┌─────────────────────────────────────────────┐
│ TOKEN BUDGET BREAKDOWN                      │
├─────────────────────────────────────────────┤
│                                             │
│  System Prompt:              ~800 tokens   │
│  Conversation History:      ~1500 tokens   │
│  Retrieved Chunks (6 chunk): ~1500 tokens  │
│  User Question:              ~200 tokens   │
│  Format Instructions:        ~100 tokens   │
│  ──────────────────────────────────────    │
│  TOTAL:                     ~4100 tokens   │
│                                             │
│  ⚠️ OVERFLOW RISK se conversation history   │
│     non troncata aggressivamente           │
└─────────────────────────────────────────────┘
```

**Mitigation strategies**:

1. **Aggressive truncation**: max 150 char per message in history
2. **Reduced chunk count**: 6 chunk invece 8 quando history presente
3. **Compact prompt format**: rimuovere verbosità non essenziale

---

## Use Cases

### Use Case 1: Follow-up Disambiguazione

```
USER: "Cos'è la spondilolistesi?"
AI: [Risposta completa con 4 concetti chiave]

USER: "Quali sono i gradi?"
      ↓
      Context window: "Nella conversazione precedente ho spiegato spondilolistesi"
      ↓
AI: "Nell'ambito della spondilolistesi di cui abbiamo parlato, il grading di 
     Meyerding classifica lo scivolamento in 4 gradi..."
```

**Without memory**: AI non capirebbe che "gradi" si riferisce a spondilolistesi → risposta generica o "non trovato".

### Use Case 2: Approfondimenti Progressivi

```
USER: "Parliamo di lombalgia meccanica"
AI: [Risposta con 3 punti chiave: 1) Definizione 2) Cause 3) Diagnosi]

USER: "Approfondisci il punto 2"
      ↓
      Context window: "Precedentemente ho elencato 3 punti su lombalgia meccanica"
      ↓
AI: "Riguardo alle cause della lombalgia meccanica (punto 2 della risposta precedente), 
     possiamo distinguere..."
```

### Use Case 3: Correzioni e Chiarimenti

```
USER: "Hai detto che la stenosi è sempre sintomatica?"
      ↓
      Context window: Recupera risposta precedente su stenosi
      ↓
AI: "Correggo quanto affermato prima: la stenosi spinale lombare può essere 
     asintomatica in fase iniziale. Nei gradi lievi (Schizas A-B)..."
```

---

## Best Practices

### 1. Clear Session on Explicit Request

```python
# Endpoint per reset conversazione
@router.delete("/sessions/{sessionId}/history")
def clear_conversation_history(sessionId: str):
    """Studente può resettare conversazione per nuovo argomento."""
    conv_manager = get_conversation_manager()
    conv_manager.clear_session(sessionId)
    return {"message": "Cronologia conversazione eliminata"}
```

### 2. History Visualization (Frontend)

```typescript
// Frontend: visualizza cronologia per studente
<ConversationHistory sessionId={sessionId}>
  {messages.map(msg => (
    <Message role={msg.role} content={msg.content} timestamp={msg.timestamp} />
  ))}
</ConversationHistory>
```

### 3. Graceful Degradation

```python
# Se token counting fallisce, continua senza memory
try:
    context_window = conv_manager.get_context_window(sessionId)
    history = conv_manager.format_for_prompt(context_window)
except Exception as e:
    logger.warning({"event": "conversation_memory_fallback", "error": str(e)})
    history = "Nessuna cronologia disponibile."
```

### 4. Conversation Decay

```python
# Opzionale: elimina sessioni vecchie (>24h inattive)
SESSION_TTL_HOURS = 24

def cleanup_old_sessions():
    """Background job per cleanup sessioni inattive."""
    now = datetime.utcnow()
    for session_id, messages in list(chat_messages_store.items()):
        if not messages:
            continue
        last_msg_ts = messages[-1].get('timestamp')
        if (now - last_msg_ts).total_seconds() > SESSION_TTL_HOURS * 3600:
            del chat_messages_store[session_id]
```

---

## Testing

```python
# tests/services/test_conversation_service.py

def test_context_window_sliding():
    """Verify sliding window mantiene solo ultimi N messaggi."""
    manager = ConversationManager()
    session_id = "test-session"
    
    # Aggiungi 5 turni (10 messaggi)
    for i in range(5):
        manager.add_turn(session_id, f"User msg {i}", f"AI response {i}")
    
    # Retrieve context (max 3 turni = 6 messaggi)
    context = manager.get_context_window(session_id)
    
    assert len(context.messages) == 6
    # Verify primi 2 turni eliminati, ultimi 3 mantenuti
    assert context.messages[0].content == "User msg 2"


def test_token_budget_truncation():
    """Verify truncation quando eccede token budget."""
    manager = ConversationManager()
    session_id = "test-session"
    
    # Aggiungi messaggi molto lunghi
    long_msg = "Lorem ipsum " * 500  # ~3000 caratteri = ~1000 token
    for i in range(4):
        manager.add_turn(session_id, long_msg, long_msg)
    
    context = manager.get_context_window(session_id)
    
    # Verify token count sotto budget
    assert context.total_tokens <= manager.MAX_CONTEXT_TOKENS


def test_format_for_prompt():
    """Verify formatting output corretto per prompt injection."""
    manager = ConversationManager()
    session_id = "test-session"
    
    manager.add_turn(session_id, "Domanda 1", "Risposta 1", ["chunk-1"])
    context = manager.get_context_window(session_id)
    formatted = manager.format_for_prompt(context)
    
    assert "STUDENTE: Domanda 1" in formatted
    assert "TUTOR: Risposta 1" in formatted
    assert "=== CRONOLOGIA" in formatted
```

---

## Dependencies

```toml
# pyproject.toml
[tool.poetry.dependencies]
tiktoken = "^0.5.1"  # Token counting per GPT models
```

---

## References

- LangChain ConversationBufferMemory: https://python.langchain.com/docs/modules/memory/types/buffer
- OpenAI Token Counting: https://github.com/openai/tiktoken
- Anthropic Claude Memory: https://docs.anthropic.com/claude/docs/long-context-window-tips
