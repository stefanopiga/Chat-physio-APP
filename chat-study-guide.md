# Guida all'Uso della Chat per Studiare Fisioterapia

**Versione**: 1.0 (Story 7.1)  
**Target**: Studenti di Fisioterapia  
**Ultima Modifica**: 2025-10-22

---

## Introduzione

La chat FisioRAG è un tutor medico-accademico interattivo che ti aiuta a studiare fisioterapia.
Il sistema risponde **esclusivamente** basandosi sui materiali didattici caricati, garantendo risposte accurate e tracciabili.

---

## Come Fare Domande Efficaci

### ✅ Domande Mirate (Consigliato)

Le domande specifiche e circoscritte ottengono risposte più dettagliate e utili.

**Esempi:**
- "Cos'è la spondilolistesi e come si classifica?"
- "Quali sono i criteri diagnostici per stenosi spinale lombare?"
- "Qual è il meccanismo fisiopatologico della radicolopatia?"
- "Quali test clinici si usano per la valutazione del rachide lombare?"

**Perché funzionano:**
- Specificità permette al sistema di recuperare chunk rilevanti
- Tono clinico/tecnico migliora la ricerca semantica
- Domande chiuse facilitano risposte strutturate

---

### ❌ Domande da Evitare

**Troppo vaghe:**
- ❌ "Dimmi tutto sulla fisioterapia"
- ❌ "Come funziona il corpo umano?"
- ❌ "Cosa devo sapere per l'esame?"

**Fuori scope materiale:**
- ❌ "Come si cura il diabete?" (se materiale copre solo rachide)
- ❌ "Qual è il protocollo del Prof. X?" (se non presente in knowledge base)

**Consiglio:** Inizia con domande ampie solo per orientamento generale, poi approfondisci con follow-up specifici.

---

## Follow-up Progressivi (Story 7.1 Feature)

Dopo una risposta iniziale, puoi approfondire riferendoti alla conversazione precedente.

### Esempi di Follow-up

**Conversazione Esempio:**

1. **Tu**: "Cos'è la stenosi spinale lombare?"  
   **Tutor**: [Risposta strutturata con introduzione, concetti chiave, spiegazione, note cliniche]

2. **Tu**: "Approfondisci il punto 2"  
   **Tutor**: [Espansione del secondo concetto chiave citato nella risposta precedente]

3. **Tu**: "Fammi un esempio clinico"  
   **Tutor**: [Esempio pratico contestualizzato rispetto a quanto discusso]

4. **Tu**: "Come si collega alla radicolopatia?"  
   **Tutor**: [Correlazione tra stenosi e radicolopatia, usando cronologia conversazione]

### Frasi Follow-up Utili

- "Approfondisci il punto [numero]"
- "Puoi spiegarmi meglio [concetto]?"
- "Fammi un esempio clinico"
- "Quali sono le implicazioni pratiche?"
- "Come si differenzia da [condizione correlata]?"
- "Qual è la correlazione con quanto detto prima?"

---

## Struttura delle Risposte

Le risposte del tutor seguono una struttura pedagogica propedeutica (Story 7.1):

### 1. **Introduzione** (1-3 frasi)
Contestualizzazione dell'argomento richiesto.

### 2. **Concetti Chiave** (2-4 punti)
Identificazione esplicita dei concetti essenziali da comprendere.

### 3. **Spiegazione Dettagliata**
Sviluppo logico e progressivo:
- Definizioni precise con terminologia medica
- Meccanismi/processi fisiopatologici
- Correlazioni cliniche rilevanti

### 4. **Note Cliniche** (quando disponibile)
Applicazioni pratiche, implicazioni cliniche, esempi.

### 5. **Limitazioni del Materiale** (quando rilevante)
Indicazioni su cosa il materiale non copre e suggerimenti per approfondimenti.

### 6. **Citazioni**
Riferimenti ai documenti didattici utilizzati (es. "Come descritto nel documento 'Patologie Rachide Lombare'...").

---

## Gestione delle Limitazioni

### Cosa Fare Se...

**"Il materiale didattico disponibile non copre [aspetto X]"**

- ✅ Accetta che il sistema opera entro i limiti del materiale caricato
- ✅ Consulta materiali aggiuntivi o il docente per approfondire
- ✅ Prova a riformulare: magari l'info c'è ma espressa diversamente

**"Nessun contenuto rilevante trovato per la tua domanda"**

- ✅ Verifica spelling/terminologia (es. "spondilolistesi" vs "spondilolistesi")
- ✅ Prova sinonimi (es. "radicolopatia" vs "sindrome radicolare")
- ✅ Scomponi domanda complessa in sotto-domande più semplici

**Risposta incompleta o parziale**

- ✅ Usa follow-up: "Puoi approfondire [aspetto specifico]?"
- ✅ Chiedi esplicitamente: "Quali altri aspetti copre il materiale?"

---

## Best Practices

### 📝 Studio Sistematico

1. **Orientamento**: Inizia con domanda generale per avere panoramica
   - "Quali sono le principali patologie del rachide lombare?"
2. **Approfondimento**: Fai follow-up su singole condizioni
   - "Approfondisci la stenosi spinale"
3. **Dettagli**: Esplora aspetti specifici (diagnosi, trattamento, prognosi)
   - "Quali sono i criteri diagnostici?"
   - "Come si valuta clinicamente?"
4. **Integrazione**: Chiedi correlazioni tra argomenti
   - "Come si differenzia dalla spondilolistesi?"

### 🎯 Preparazione Esami

- **Ripasso concetti chiave**: Chiedi esplicitazione concetti per ogni argomento
- **Esempi clinici**: Richiedi sempre esempi pratici quando disponibili
- **Autovalutazione**: Poni domande chiuse per verificare comprensione
  - "Qual è la differenza tra stenosi centrale e foraminale?"

### 💡 Apprendimento Profondo

- Non limitarti a memorizzare risposte → chiedi "perché?" e "come?"
- Usa follow-up per esplorare meccanismi fisiopatologici
- Richiedi correlazioni cliniche per ancorare teoria a pratica

---

## Esempi di Conversazioni Efficaci

### Esempio 1: Studio Spondilolistesi

```
STUDENTE: Cos'è la spondilolistesi e come si classifica?

TUTOR: [Risposta strutturata]
- Introduzione: definizione scivolamento vertebrale
- Concetti chiave: 1) Meccanismo, 2) Classificazione Meyerding, 3) Gradi I-IV
- Spiegazione: dettagli classificazione, percentuali scivolamento
- Note cliniche: correlazione grado-sintomatologia

STUDENTE: Approfondisci il punto 2 sulla classificazione Meyerding

TUTOR: [Espansione Meyerding]
- Criteri radiografici specifici
- Metodo misurazione percentuale scivolamento
- Correlazione imaging-clinica

STUDENTE: Quali sono le indicazioni chirurgiche?

TUTOR: [Criteri chirurgici]
- Gradi III-IV con sintomi persistenti
- Fallimento trattamento conservativo
- Deficit neurologici progressivi
```

### Esempio 2: Comprensione Meccanismo

```
STUDENTE: Qual è il meccanismo della claudicatio neurogena nella stenosi?

TUTOR: [Spiegazione meccanismo]
- Restringimento canale → compressione vascolare
- Ridotta perfusione radici lombari sotto sforzo
- Sintomi posizionali (peggiora estensione, migliora flessione)

STUDENTE: Come si differenzia dalla claudicatio vascolare?

TUTOR: [Diagnosi differenziale]
- Claudicatio neurogena vs vascolare
- Criteri distintivi: posizione-dipendenza, polsi periferici, imaging

STUDENTE: Quali test clinici confermano la diagnosi?

TUTOR: [Test clinici]
- Walking test, flessione-sollievo test
- Correlazione con imaging (RMN gold standard)
```

---

## Tono e Stile del Tutor

Il tutor FisioRAG adotta il ruolo di **medico fisioterapista accademico**:

- **Autorevole ma disponibile**: Linguaggio clinico appropriato ma accessibile
- **Rigoroso scientificamente**: Terminologia medica precisa con spiegazioni
- **Orientato alla comprensione**: Obiettivo è apprendimento profondo, non solo trasmissione informazioni
- **Trasparente su limitazioni**: Indica chiaramente quando info non disponibile nel materiale

**Non aspettarti:**
- Tono colloquiale/informale
- Opinioni personali o speculazioni
- Conoscenze esterne ai materiali didattici

---

## FAQ

**Q: Posso fare domande in linguaggio colloquiale?**  
A: Sì, ma terminologia medica/clinica migliora accuracy ricerca semantica.

**Q: Quanti follow-up posso fare?**  
A: Il sistema mantiene ultimi 3 turni conversazionali (6 messaggi). Oltre, cronologia più vecchia viene compressa.

**Q: Cosa succede se il materiale non copre la mia domanda?**  
A: Il tutor indicherà esplicitamente le limitazioni e suggerirà di consultare risorse aggiuntive.

**Q: Le risposte sono sempre corrette?**  
A: Le risposte sono basate esclusivamente sul materiale didattico fornito. Accuracy dipende da qualità e completezza del materiale.

**Q: Posso usare la chat per prepararmi agli esami?**  
A: Sì, la chat è uno strumento di studio complementare. Integra con materiali ufficiali, lezioni, e confronto con docenti.

---

## Feedback e Miglioramento

Dopo ogni risposta puoi fornire feedback (👍/👎) per aiutarci a migliorare il sistema.

**Quando dare 👎:**
- Risposta non pertinente alla domanda
- Informazioni mancanti/incomplete (nonostante materiale disponibile)
- Tono/struttura non chiara

**Quando dare 👍:**
- Risposta completa e ben strutturata
- Follow-up contestualizzati correttamente
- Citazioni accurate e utili

---

## Supporto

Per domande sull'uso del sistema o segnalazione problemi:
- **Supporto tecnico**: [Contact Info TBD]
- **Feedback materiale didattico**: [Contact Info TBD]

---

**Buono Studio!** 📚

