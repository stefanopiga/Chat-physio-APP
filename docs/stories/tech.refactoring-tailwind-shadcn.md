# Refactoring Tecnico: Adozione di Tailwind CSS e Shadcn/UI

**Status:** Done

## Scopo

Allineare il frontend ai requisiti architetturali prescritti dalla documentazione adottando esclusivamente **Tailwind CSS** e **Shadcn/UI**, rimuovendo gli stili inline e sostituendoli con classi utility e variabili di theming semantiche.

[Fonti: `docs/prompt-for-lovable_V0.md` Sez. 3 (L50–L55, L59); `docs/front-end-spec.md` Sez. 5, Sez. 7]

## Motivazione

Lo stack attuale usa stili CSS inline e valori hard-coded, in contrasto con i vincoli di progetto che richiedono Tailwind CSS e Shadcn/UI. Questo disallineamento impedisce l'implementazione di storie che dipendono da tali tecnologie.

## Acceptance Criteria

1. Installazione e configurazione di Tailwind CSS nel progetto web (`apps/web`).
2. Integrazione di Shadcn/UI nel progetto con configurazione base e temi Light/Dark.
3. Rimozione completa degli stili inline dai componenti esistenti in `apps/web/src/components` e `apps/web/src/pages`.
4. Sostituzione degli stili inline con classi utility Tailwind, senza colori hard-coded.
5. Adozione di variabili semantiche di theming (background, foreground, primary, card, ecc.) conformi alle linee guida.
6. Aggiornamento della documentazione `docs/prompt-for-lovable_V0.md` per ribadire la conformità obbligatoria a Tailwind + Shadcn/UI e il divieto di stili inline/CSS vanilla.
7. Verifica di accessibilità di base: focus visibile, navigazione da tastiera invariata dopo il refactoring.

## Note di Implementazione

- Ambito: solo frontend (`apps/web`). Nessuna modifica backend.
- Non introdurre librerie di componenti diverse da Shadcn/UI.
 - Riferimenti di setup: `docs/architecture/addendum-tailwind-shadcn-setup.md`.

## Dipendenze e Impatti

- Questa storia è un prerequisito bloccante per `docs/stories/3.5.in-app-user-guide.md`.

## Verifica

- Build e preview senza regressioni visive critiche.
- Controllo manuale che nessun componente mantenga `style={...}` inline.


