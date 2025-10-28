
### 1. Gestione Errori di `langchain_openai.OpenAIEmbeddings`

* **Variabili d'Ambiente Richieste:**
    * `OPENAI_API_KEY` - automaticamente inferita se non fornita come parametro
    * `OPENAI_ORG_ID` (opzionale) - per specificare l'organizzazione
    * `OPENAI_API_VERSION` (opzionale) - per specificare la versione API

* **Eccezione per Autenticazione Fallita:**
    * `openai.AuthenticationError` - sollevata quando la chiave API è invalida, scaduta o revocata (status code 401)
    * `openai.APIConnectionError` - sollevata quando il server non è raggiungibile
    * `openai.APIStatusError` - classe base per errori con status code 4xx/5xx

* **Pattern di Gestione Errore (Codice):**
    ```python
    import openai
    from langchain_openai import OpenAIEmbeddings
    
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
        vectors = embeddings.embed_documents(["test text"])
    except openai.AuthenticationError as e:
        # Chiave API mancante, invalida o revocata
        logger.error(f"Autenticazione OpenAI fallita: {e}")
        raise
    except openai.APIConnectionError as e:
        # Server non raggiungibile
        logger.error(f"Connessione OpenAI fallita: {e.__cause__}")
        raise
    except openai.RateLimitError as e:
        # Rate limit (429)
        logger.warning(f"Rate limit OpenAI raggiunto: {e}")
        raise
    except openai.APIStatusError as e:
        # Altri errori API
        logger.error(f"Errore API OpenAI {e.status_code}: {e.response}")
        raise
    ```

* **Fonte Ufficiale:**
    * https://github.com/openai/openai-python
    * https://api.python.langchain.com/en/latest/embeddings/langchain_openai.embeddings.base.OpenAIEmbeddings.html

---

### 2. Gestione Errori di `langchain_community.vectorstores.SupabaseVectorStore`

* **Eccezioni Comuni del Metodo `add_texts`:**
    * `Exception("Error inserting: No rows added")` - sollevata quando `client.from_(table_name).upsert(chunk).execute()` restituisce `result.data` vuoto
    * `ValueError` - per validazione parametri (es. numero metadati/ID non corrispondente al numero di testi)
    * Eccezioni del client Supabase non catturate - per problemi di connessione, autenticazione, permessi, schema

* **Valori di Ritorno (Successo/Fallimento):**
    * **Successo:** Restituisce `List[str]` contenente gli ID dei documenti inseriti
    * **Fallimento:** Solleva `Exception` se `len(result.data) == 0` dopo l'operazione di upsert
    * **Importante:** Il metodo esegue upsert in chunk (default 500 documenti). Se un chunk fallisce, l'eccezione viene sollevata immediatamente

* **Pattern di Gestione Errore (Codice):**
    ```python
    from langchain_community.vectorstores import SupabaseVectorStore
    from supabase.client import Client
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        ids = vector_store.add_texts(
            texts=chunks,
            metadatas=metadatas,
            ids=chunk_ids
        )
        
        if not ids or len(ids) == 0:
            logger.error("add_texts ha restituito lista vuota - nessun chunk inserito")
            raise ValueError("Nessun chunk inserito nel vector store")
            
        logger.info(f"Inseriti {len(ids)} chunks con successo")
        
    except Exception as e:
        if "Error inserting: No rows added" in str(e):
            logger.error(f"Fallimento inserimento Supabase: {e}")
            # Verificare connessione, permessi, schema tabella
        else:
            logger.error(f"Errore durante add_texts: {type(e).__name__}: {e}")
        raise
    ```

* **Fonte Ufficiale:**
    * https://python.langchain.com/api_reference/community/vectorstores/langchain_community.vectorstores.supabase.SupabaseVectorStore.html
    * https://api.python.langchain.com/en/latest/_modules/langchain_community/vectorstores/supabase.html (codice sorgente)
    * https://supabase.com/docs/guides/ai/langchain