from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv(override=True)

sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

# Check chunks
r = sb.table('document_chunks').select('id', count='exact').limit(1).execute()
print(f'Total chunks: {r.count}')

# Check documents
r2 = sb.table('documents').select('id, file_name', count='exact').execute()
print(f'Total documents: {r2.count}')

if r2.data:
    print('\nDocuments:')
    for d in r2.data[:5]:
        print(f"  - {d['file_name']}")

