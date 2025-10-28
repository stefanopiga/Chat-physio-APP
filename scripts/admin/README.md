# Admin Scripts

Script per operazioni amministrative.

## generate_jwt.py

Genera token JWT per operazioni admin API.

**Uso**:
```bash
python generate_jwt.py --email admin@example.com --expires-days 7
```

**Variabili Richieste**:
- `SUPABASE_JWT_SECRET`

**Output**: JWT token + comandi export
