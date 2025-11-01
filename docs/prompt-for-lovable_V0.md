# Generazione UI per l'applicazione FisioRAG

## 1. Obiettivo Generale

L'obiettivo è creare i componenti React per l'interfaccia di un assistente didattico chiamato FisioRAG. L'applicazione ha tre viste principali: una pagina di accesso per studenti, l'interfaccia di chat principale e un pannello di amministrazione per il professore. L'applicazione deve essere responsive, accessibile (WCAG AA), supportare temi light/dark e avere uno stile minimale e professionale.

## 2. Istruzioni Dettagliate, passo dopo passo

### Parte A: Pagina di Accesso Studente

1.  Crea un componente `StudentLoginPage.tsx`.
2.  Il componente deve essere centrato verticalmente e orizzontalmente nella pagina.
3.  Deve contenere un titolo `h1` con il testo "FisioRAG".
4.  Sotto il titolo, includi un paragrafo descrittivo: "Accedi all'assistente didattico inserendo il tuo codice".
5.  Includi un form con un singolo campo di input (`<Input />`) per il "Codice di Accesso" e un pulsante (`<Button />`) con il testo "Accedi".
6.  Il layout deve essere a colonna singola e rimanere tale su tutti i dispositivi.

### Parte B: Interfaccia Chat

1.  Crea un componente `ChatInterface.tsx`.
2.  Il layout deve occupare l'intera altezza e larghezza del viewport.
3.  La struttura deve essere divisa in due parti: un'area per la cronologia dei messaggi in alto e un'area fissa per l'input in basso.
4.  **Cronologia Messaggi**:
    *   Deve essere un'area scrollabile.
    *   I messaggi dell'utente devono essere allineati a destra.
    *   I messaggi del bot (risposte) devono essere allineati a sinistra.
    *   Ogni messaggio (sia utente che bot) deve essere contenuto in un componente `<Card />`.
    *   Le risposte del bot conterranno citazioni numerate (es. `[1]`, `[2]`). Queste citazioni devono essere rese come elementi `<button>` interattivi. Al click, devono attivare un `<Popover />` che mostra il testo della fonte.
    *   Sotto ogni risposta del bot, devono essere presenti due bottoni icona (pollice su/giù) per il feedback.
    *   Implementa un indicatore di "sta scrivendo" che appaia mentre si attende la risposta del bot.
5.  **Area Input**:
    *   Deve essere fissata in fondo alla pagina.
    *   Deve contenere un campo di input (`<Input />`) per scrivere la domanda e un pulsante di invio (`<Button />`).
    *   **Critico per mobile**: Questo layout deve adattarsi correttamente quando la tastiera a schermo è visibile, evitando che la tastiera copra l'input.

### Parte C: Pannello di Amministrazione

1.  Crea un componente `AdminDashboard.tsx`.
2.  **Layout**:
    *   **Desktop (>= md)**: Deve avere un layout a due colonne: una sidebar di navigazione a sinistra e un'area per il contenuto a destra.
    *   **Mobile (< md)**: La sidebar deve collassare e diventare accessibile tramite un bottone "hamburger".
3.  **Sidebar di Navigazione**: Deve contenere i link per "Gestione Codici" e "Sincronizzazione DB".
4.  **Vista Sincronizzazione**:
    *   Deve mostrare lo stato attuale (es. "Ultima sincronizzazione: ...").
    *   Deve avere un pulsante "Avvia Sincronizzazione".
    *   Quando la sincronizzazione è in corso, deve mostrare un'area di testo non modificabile che visualizza i log di avanzamento in tempo reale.

## 3. Esempi, Data Structures & Vincoli

*   **Tech Stack**: **React, TypeScript, Vite, Tailwind CSS**.
*   **Libreria Componenti**: **Shadcn/UI**. Utilizza esclusivamente i componenti di questa libreria (`Button`, `Input`, `Card`, `Popover`, `Alert`, `Table`, ecc.).
*   **Theming**: L'applicazione deve supportare sia un tema **light** che **dark**. Utilizza le variabili CSS semantiche fornite da Shadcn/UI per i colori (`background`, `foreground`, `primary`, `card`, ecc.) per garantire che il theming funzioni automaticamente. Non usare colori hard-coded.
*   **Font**: Utilizza un font stack di sistema sans-serif.
*   **Accessibilità**: Assicurati che tutti i form abbiano `<label>`, che tutti gli elementi interattivi siano accessibili da tastiera e che abbiano stati di focus visibili.
*   **API (per riferimento)**:
    *   Validazione codice studente: `POST /api/student/validate` -> `{ "token": "..." }`
    *   Query della chat: `POST /api/chat/query` -> `{ "response": "...", "sources": [...] }`
    *   Avvio Sincronizzazione: `POST /api/admin/sync` -> `{ "status": "started" }`
*   **Cosa NON Fare**: Non creare un design system custom. Non usare altre librerie di componenti. Non usare CSS vanilla o styled-components; usa esclusivamente le utility classes di Tailwind CSS.

### Clausola di Conformità Obbligatoria (Frontend)

Tutto il nuovo sviluppo frontend DEVE:

1. utilizzare Tailwind CSS per lo styling (solo classi utility),
2. utilizzare i componenti Shadcn/UI per elementi interattivi e contenitori,
3. rispettare il theming Light/Dark tramite variabili semantiche (nessun colore hard-coded),
4. evitare qualsiasi stile inline (`style={...}`) o CSS vanilla.

Qualsiasi contributo che non rispetti questa clausola non può essere accettato in revisione.

### Riferimenti di Setup

Per i passi di installazione e configurazione consulta: `docs/architecture/addendum-tailwind-shadcn-setup.md`.

## 4. Ambito di Lavoro Definito

*   **Crea i seguenti file**: `StudentLoginPage.tsx`, `ChatInterface.tsx`, `AdminDashboard.tsx`.
*   Puoi creare componenti più piccoli se necessario (es. `ChatMessage.tsx`), ma questi tre sono i componenti principali.
*   **Non modificare** file al di fuori di una cartella `components/` o `pages/`. Lo scopo è generare i componenti UI, non l'intera logica di routing o di state management dell'applicazione.
