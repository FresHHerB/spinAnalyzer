# Sistema de Upload e Processamento Automático

## Visão Geral

O SpinAnalyzer agora suporta upload de arquivos com processamento ETL automático. Os usuários podem arrastar arquivos de hand history diretamente na interface e o sistema processará automaticamente.

## Formatos Suportados

### 1. PokerStars (.txt)
- Arquivos de texto com hand histories
- Formato padrão: `PokerStars Hand #...`
- Exemplo: `handHistory-147171.txt`

### 2. iPoker (.xml)
- Arquivos XML com sessões completas
- Contém múltiplos `<game>` elements
- Exemplo: `8384804669.xml`

## Arquitetura do Sistema

```
User Upload (Frontend)
    ↓
FastAPI Endpoint (/upload/file)
    ↓
Background Task (Async Processing)
    ↓
Unified Parser
    ├── Detecta formato automaticamente
    ├── Parse XML (iPoker) ou TXT (PokerStars)
    └── Converte para PHH format
    ↓
Build FAISS Indices
    ├── Vetoriza decision points
    └── Cria índices por villain
    ↓
Ready for Search!
```

## API Endpoints

### 1. Upload de Arquivo Único
```http
POST /upload/file
Content-Type: multipart/form-data

Parameters:
- file: arquivo .txt ou .xml
- heads_up_only: boolean (padrão: true)

Response:
{
  "job_id": "uuid-here",
  "filename": "handHistory.txt",
  "status": "queued",
  "message": "Arquivo recebido e enfileirado para processamento"
}
```

### 2. Upload de Múltiplos Arquivos
```http
POST /upload/files
Content-Type: multipart/form-data

Parameters:
- files: lista de arquivos
- heads_up_only: boolean

Response:
{
  "total_files": 3,
  "jobs": [
    { "job_id": "...", "filename": "...", "status": "queued" },
    ...
  ]
}
```

### 3. Consultar Status do Job
```http
GET /upload/status/{job_id}

Response:
{
  "job_id": "uuid",
  "filename": "handHistory.txt",
  "status": "processing",  // queued | processing | completed | failed
  "stage": "parsing",      // parsing | building_indices | done
  "created_at": "2025-01-15T10:00:00",
  "parser_stats": {
    "total_hands": 150,
    "hu_hands": 98,
    "converted": 98,
    "errors": 0
  }
}
```

### 4. Listar Todos os Jobs
```http
GET /upload/jobs?status=completed&limit=50

Response:
{
  "total": 10,
  "jobs": [...]
}
```

### 5. Deletar Job
```http
DELETE /upload/job/{job_id}

Response:
{
  "message": "Job removido com sucesso"
}
```

### 6. Reconstruir Índices Manualmente
```http
POST /upload/rebuild-indices

Response:
{
  "job_id": "uuid",
  "message": "Reconstrução de índices iniciada"
}
```

## Componente Frontend

### FileUpload.tsx

O componente React fornece:

**Recursos:**
- ✅ Drag and drop de múltiplos arquivos
- ✅ Preview dos arquivos selecionados
- ✅ Validação de formato (.txt, .xml)
- ✅ Upload paralelo de múltiplos arquivos
- ✅ Polling automático de status
- ✅ Exibição de progresso em tempo real
- ✅ Estatísticas de processamento
- ✅ Indicadores visuais de status

**Estados do Job:**
- `queued` - Na fila para processamento
- `processing` - Sendo processado
- `completed` - Concluído com sucesso
- `failed` - Falhou com erro

**Stages do Processing:**
- `parsing` - Parsing do arquivo
- `building_indices` - Construindo índices FAISS
- `done` - Finalizado

## Fluxo de Processamento

### 1. Upload
```typescript
// Frontend envia arquivo
const formData = new FormData();
formData.append('file', file);

const response = await axios.post(
  `${API_URL}/upload/file?heads_up_only=true`,
  formData
);

const { job_id } = response.data;
```

### 2. Background Processing
```python
# Backend processa em background
def process_uploaded_file(job_id, file_path, filters):
    # 1. Parse arquivo
    parser = UnifiedParser(output_dir=PHH_OUTPUT_DIR)
    phh_files = parser.parse_file(file_path, filters)

    # 2. Build índices
    builder = IndexBuilder(phh_dir=PHH_OUTPUT_DIR, indices_dir=INDICES_DIR)
    stats = builder.build_all_indices()

    # 3. Atualiza status
    processing_jobs[job_id]["status"] = "completed"
```

### 3. Polling de Status
```typescript
// Frontend faz polling a cada 5 segundos
const poll = setInterval(async () => {
  const response = await axios.get(`/upload/status/${jobId}`);
  const job = response.data;

  if (job.status === 'completed' || job.status === 'failed') {
    clearInterval(poll);
  }
}, 5000);
```

## Parsers

### UnifiedParser

Detecta formato automaticamente:

```python
from src.parsers.unified_parser import UnifiedParser

parser = UnifiedParser(output_dir=Path("dataset/phh_hands"))

# Auto-detecta e processa
phh_files = parser.parse_file(
    file_path=Path("handHistory.txt"),
    filters={"heads_up_only": True}
)

# Estatísticas
print(parser.stats)
# {
#   'total_files': 1,
#   'total_hands': 150,
#   'hu_hands': 98,
#   'converted': 98,
#   'errors': 0
# }
```

### Formatos Específicos

**iPoker XML:**
- Parser: `_parse_xml_ipoker()`
- Extrai: players, actions, cards, pots
- Converte para PHH format

**PokerStars TXT:**
- Parser: `_parse_txt_pokerstars()`
- Detecta: `PokerStars Hand #...`
- Separa mãos individuais
- Filtra heads-up se solicitado

## Diretórios

```
project/
├── uploads/
│   ├── temp/           # Arquivos temporários durante upload
│   └── processed/      # Arquivos processados
├── dataset/
│   └── phh_hands/      # PHH files convertidos
└── indices/            # FAISS indices
    ├── villain1.index
    ├── villain1_ids.npy
    ├── villain2.index
    └── ...
```

## Configuração Frontend

### Adicionar ao App.tsx

```typescript
import FileUpload from './components/FileUpload';

function App() {
  return (
    <div>
      <FileUpload />
      {/* outros componentes */}
    </div>
  );
}
```

### Variáveis de Ambiente

```env
VITE_API_URL=http://localhost:8000
```

## Uso Prático

### Exemplo 1: Upload via Interface

1. Abra a aplicação frontend
2. Arraste arquivos .txt ou .xml para a área de upload
3. (Opcional) Desmarque "apenas heads-up" para processar todas as mãos
4. Clique em "Enviar"
5. Acompanhe o progresso em tempo real

### Exemplo 2: Upload via API

```bash
# Upload de arquivo
curl -X POST "http://localhost:8000/upload/file?heads_up_only=true" \
  -F "file=@handHistory.txt"

# Resposta
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "handHistory.txt",
  "status": "queued"
}

# Consultar status
curl "http://localhost:8000/upload/status/550e8400-e29b-41d4-a716-446655440000"
```

## Performance

### Métricas Típicas

- **Upload**: ~1-5 MB/s (depende da conexão)
- **Parsing**: ~100-500 mãos/segundo
- **Index Building**: ~1000-5000 vectors/segundo
- **Total**: ~30 segundos para 1000 mãos

### Otimizações

1. **Upload Paralelo**: Múltiplos arquivos em paralelo
2. **Background Processing**: Não bloqueia a UI
3. **Streaming**: Processa enquanto faz upload
4. **Incremental Indexing**: Apenas novos decision points

## Limitações Atuais

1. **Memória**: Jobs em memória (não persistente)
   - Solução futura: Redis ou database

2. **Concorrência**: Processamento sequencial
   - Solução futura: Celery ou task queue

3. **Validação**: Validação básica de formato
   - Solução futura: Validação mais robusta

4. **Rollback**: Sem rollback em caso de erro
   - Solução futura: Transações e cleanup

## Próximos Passos

- [ ] Persistir jobs em database
- [ ] Adicionar queue system (Celery/RQ)
- [ ] Implementar rollback automático
- [ ] Adicionar validação avançada
- [ ] Suportar mais formatos (GGPoker, etc)
- [ ] Compressão de uploads
- [ ] Resumable uploads para arquivos grandes
- [ ] Notificações via websocket

## Troubleshooting

### Arquivo não é processado

1. Verifique o formato (.txt ou .xml)
2. Confira logs do backend
3. Veja status do job: `GET /upload/status/{job_id}`

### Erro ao construir índices

1. Verifique espaço em disco
2. Confirme que dataset/phh_hands existe
3. Tente rebuild manual: `POST /upload/rebuild-indices`

### Frontend não mostra progresso

1. Verifique CORS no backend
2. Confirme VITE_API_URL está correto
3. Veja console do navegador para erros

## Suporte

Para issues ou dúvidas:
- GitHub: [issues](https://github.com/FresHHerB/spinAnalyzer/issues)
- Documentação: `DEPLOYMENT.md`
