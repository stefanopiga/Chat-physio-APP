

### Gruppo 1: Qualità e Stile della Risposta (Prompt Engineering)

Questi flag alterano la struttura e il tono del prompt inviato a OpenAI, influenzando direttamente lo stile della risposta.

-   `ENABLE_ACADEMIC_PROMPT=true`: Attiva un prompt che istruisce il modello a rispondere come un "medico fisioterapista esperto".
    -   **Come usarlo**: Lascialo a `true` per risposte formali, tecniche e accademiche. Impostalo a `false` per uno stile più generico e meno strutturato.
-   `ENABLE_ENHANCED_RESPONSE_MODEL=true`: Formatta la risposta in un modello strutturato (JSON) che include sezioni come "Sintesi", "Concetti Chiave", "Esempio Pratico".
    -   **Come usarlo**: Utile se l'output deve essere parsato da un'altra applicazione o se si desidera una risposta ben organizzata e prevedibile. Disattivalo (`false`) per una risposta in testo libero.

### Gruppo 2: Memoria Conversazionale

Questo gruppo controlla la capacità del sistema di ricordare i turni precedenti di una conversazione.

-   `ENABLE_CONVERSATIONAL_MEMORY=true`: Abilita la memoria. Se `false`, ogni domanda è trattata come indipendente.
    -   `CONVERSATION_MAX_TURNS=3`: Imposta quanti scambi (domanda+risposta) ricordare. Un valore di `3` significa che il sistema ricorderà le ultime 3 domande e le ultime 3 risposte.
        -   **Come usarlo**: Aumenta il valore (es. `5`) per conversazioni più lunghe e complesse, dove il contesto è cruciale. Diminuiscilo (es. `1`) per risparmiare token (costi) e ridurre il rischio che il modello si "confonda" con informazioni vecchie.
    -   `CONVERSATION_MAX_TOKENS=2000`: Limite massimo di token (circa parole/pezzi di parole) da usare per il contesto della conversazione.
        -   **Come usarlo**: Valori più alti permettono contesti più ricchi ma aumentano il costo e la latenza. Valori bassi sono più economici ma possono tagliare dettagli importanti.
    -   `CONVERSATION_MESSAGE_COMPACT_LENGTH=150`: I messaggi più vecchi (oltre `MAX_TURNS`) vengono riassunti e troncati a questa lunghezza in caratteri.
        -   **Come usarlo**: Aumenta questo valore se noti che i riassunti dei vecchi messaggi perdono informazioni vitali.

### Gruppo 3: Ottimizzazione del Recupero dei Documenti (Retrieval)

Questi flag e le relative configurazioni sono i più complessi e impattano direttamente sulla qualità e pertinenza dei documenti (i "chunk") estratti dalla base di conoscenza per costruire la risposta. Sono tecniche avanzate di RAG (Retrieval-Augmented Generation).

#### 1. Reranking di Precisione (Cross-Encoder)

-   `ENABLE_CROSS_ENCODER_RERANKING=true`: Dopo una prima ricerca veloce (semantica), un secondo modello più lento ma più accurato (il Cross-Encoder) riordina i risultati per mettere i più pertinenti in cima.
    -   `CROSS_ENCODER_MODEL_NAME`: Modello specifico da usare. Cambiare questo richiede conoscenza dei modelli disponibili su piattaforme come Hugging Face.
    -   `CROSS_ENCODER_OVER_RETRIEVE_FACTOR=3`: Per il reranking, il sistema recupera `N * fattore` documenti. Se vuoi 10 risultati finali, con fattore 3 ne recupera 30, li riordina e restituisce i migliori 10.
        -   **Come usarlo**: Aumenta a `4` o `5` per dare al reranker più candidati, potenzialmente migliorando la qualità a costo di maggiore latenza. Riduci a `2` per accelerare.
    -   `CROSS_ENCODER_THRESHOLD_POST_RERANK=0.6`: Punteggio minimo (da 0 a 1) che un documento deve avere dopo il reranking per essere considerato valido.
        -   **Come usarlo**: Aumenta (es. `0.8`) per risposte molto conservative basate solo su fonti estremamente pertinenti. Diminuisci (es. `0.3`) per includere più documenti, anche se meno attinenti, rischiando risposte più "creative" o imprecise.

#### 2. Numero di Risultati Dinamico

-   `ENABLE_DYNAMIC_MATCH_COUNT=true`: Invece di recuperare sempre lo stesso numero di documenti, il sistema analizza la domanda e decide quanti documenti recuperare.
    -   `DYNAMIC_MATCH_COUNT_MIN=5`: Numero minimo di documenti per domande semplici (es. "cos'è la fascite plantare?").
    -   `DYNAMIC_MATCH_COUNT_MAX=12`: Numero massimo per domande complesse (es. "confronta il trattamento per la fascite plantare con quello per la tendinite achillea in pazienti diabetici").
    -   `DYNAMIC_MATCH_COUNT_DEFAULT=8`: Numero di documenti per domande di media complessità.
        -   **Come usarlo**: Se ritieni che le risposte siano troppo superficiali, aumenta tutti e tre i valori (es. `MIN=8`, `DEFAULT=12`, `MAX=18`). Se sono troppo lente o confusionarie, diminuiscili.

#### 3. Diversificazione dei Risultati

-   `ENABLE_CHUNK_DIVERSIFICATION=true`: Limita il numero di chunk provenienti dallo stesso documento, per evitare risposte basate su una sola fonte e promuovere una visione più ampia.
    -   `DIVERSIFICATION_MAX_PER_DOCUMENT=2`: Non verranno mostrati più di 2 chunk dallo stesso documento sorgente.
        -   **Come usarlo**: Riduci a `1` per la massima diversità, utile per domande ampie. Aumenta a `3` o `4` se ti aspetti che la risposta si trovi in gran parte all'interno di un singolo, lungo documento.
    -   `DIVERSIFICATION_PRESERVE_TOP_N=3`: I primi 3 risultati della ricerca vengono sempre inclusi, ignorando la regola di diversificazione. Questo per non scartare risultati molto pertinenti.
        -   **Come usarlo**: Aumenta questo valore se noti che la diversificazione sta scartando documenti che ritieni fondamentali. Diminuiscilo per applicare la diversificazione in modo più aggressivo.

### Scenari di Esempio

-   **Scenario 1: Massima Precisione e Qualità (a costo di latenza)**
    -   Abilita tutti i flag di "Advanced Retrieval".
    -   `CROSS_ENCODER_OVER_RETRIEVE_FACTOR=4`
    -   `CROSS_ENCODER_THRESHOLD_POST_RERANK=0.7`
    -   Aumenta i valori di `DYNAMIC_MATCH_COUNT`.

-   **Scenario 2: Risposte Veloci e Concise**
    -   Disabilita `ENABLE_CROSS_ENCODER_RERANKING` (è il più costoso in termini di tempo).
    -   Disabilita `ENABLE_DYNAMIC_MATCH_COUNT` e imposta un numero fisso e basso di documenti da recuperare (questo va fatto nel codice, ma disabilitare il flag usa il default).
    -   Riduci `CONVERSATION_MAX_TURNS` e `CONVERSATION_MAX_TOKENS`.

-   **Scenario 3: Ampia Copertura e Diversità di Fonti**
    -   Abilita `ENABLE_CHUNK_DIVERSIFICATION`.
    -   `DIVERSIFICATION_MAX_PER_DOCUMENT=1`
    -   `DIVERSIFICATION_PRESERVE_TOP_N=1`
    -   Aumenta `DYNAMIC_MATCH_COUNT_MAX` per dare più materiale alla diversificazione.