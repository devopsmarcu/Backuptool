# BackupTool

Ferramenta desktop para backup e restauração de perfis de usuário em estações de trabalho Windows e Linux, desenvolvida para suporte técnico em ambientes corporativos com domínio Active Directory.

---

## Visão Geral

O BackupTool foi desenvolvido para uso por técnicos de TI no contexto de formatações de estações de trabalho. A ferramenta automatiza o processo de identificação, cópia e restauração de arquivos de perfis de usuário, eliminando etapas manuais e reduzindo o risco de perda de dados durante procedimentos de reinstalação do sistema operacional.

**Problema resolvido:** em ambientes corporativos com múltiplos usuários por máquina e perfis de domínio AD, o processo de backup pré-formatação é frequentemente manual, propenso a erros e sem rastreabilidade. O BackupTool padroniza esse processo, gera auditoria completa e viabiliza a restauração controlada posterior.

**Público-alvo:** técnicos de suporte de TI com privilégios administrativos em estações de trabalho Windows e Linux ingressadas em domínio Active Directory.

---

## Arquitetura da Solução

### Arquitetura identificada

Aplicação desktop monolítica com separação em camadas: interface gráfica (`main.py`), módulos de domínio (`core/`) e configuração (`config/`). Sem servidor, sem banco de dados, sem dependências de rede em tempo de execução.

### Componentes principais

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| Interface gráfica | `main.py` | Orquestração da UI, navegação entre abas, disparo de operações em threads |
| Scanner | `core/scanner.py` | Varredura recursiva de diretórios com filtragem de exclusões |
| Engine de backup | `core/backup.py` | Cópia de arquivos com cálculo de SHA-256 e geração de estrutura de backup |
| Manifest | `core/manifest.py` | Serialização/desserialização do `manifest.json`, extração de usuários |
| Engine de restauração | `core/restore.py` | Restauração por modo, verificação de integridade, tratamento de conflitos |
| Detecção de destinos | `core/destinations.py` | Enumeração de drives externos e validação do destino |
| Relatórios | `core/report.py` | Geração de relatórios de backup em JSON e CSV |
| Configuração padrão | `config/defaults.py` | Paths padrão por sistema operacional e listas de exclusão |

### Fluxo geral de funcionamento

**Backup:**

```
Técnico seleciona pastas (Aba 1)
      ↓
Técnico seleciona destino (Aba 2)
      ↓
Sistema escaneia arquivos e exibe resumo (Aba 3)
      ↓
Técnico confirma e inicia backup (Aba 4)
      ↓
SHA-256 calculado por arquivo → cópia para Backup_YYYY-MM-DD_HHMMSS/files/
      ↓
manifest.json gravado + relatórios JSON e CSV gerados em logs/
```

**Restauração:**

```
Técnico seleciona pasta de backup (Aba 5)
      ↓
manifest.json carregado e validado
      ↓
Técnico escolhe modo (tudo / seleção / destino alternativo) e política de conflito
      ↓
SHA-256 verificado por arquivo antes da cópia
      ↓
Arquivos restaurados + relatórios JSON e CSV gerados em logs/
```

### Camadas da aplicação

- **Apresentação:** `main.py` — CustomTkinter, execução de operações longas em `threading.Thread` daemon
- **Domínio:** `core/` — lógica de negócio isolada da UI, testável independentemente
- **Configuração:** `config/defaults.py` — paths e exclusões padrão derivados do sistema operacional em execução

### Integrações existentes

- **Windows API (ctypes):** enumeração de drives lógicos via `GetLogicalDrives` e `GetDriveTypeW`, leitura de rótulos via `GetVolumeInformationW`
- **Linux (subprocess/lsblk):** detecção de dispositivos montados em `/media` e `/mnt`
- Sem integrações com APIs externas, bancos de dados ou serviços de rede

---

## Tecnologias Utilizadas

| Tecnologia | Versão | Finalidade |
|---|---|---|
| Python | 3.11+ | Linguagem principal |
| CustomTkinter | >= 5.2.0 | Interface gráfica moderna baseada em Tkinter |
| Tkinter | stdlib | Dialogs nativos (`filedialog`, `messagebox`) |
| PyInstaller | Não fixada | Empacotamento em executável portátil |
| hashlib | stdlib | Cálculo de SHA-256 e MD5 |
| shutil | stdlib | Cópia de arquivos preservando metadados |
| pathlib | stdlib | Manipulação de paths cross-platform |
| threading | stdlib | Execução não bloqueante de operações longas |
| json | stdlib | Serialização de manifests e relatórios |
| csv | stdlib | Exportação de relatórios tabulares |
| dataclasses | stdlib | Estruturas de dados tipadas |
| ctypes | stdlib | Interação com Windows API |
| subprocess | stdlib | Execução de `lsblk` no Linux |

---

## Dependências

| Dependência | Versão mínima | Finalidade |
|---|---|---|
| customtkinter | 5.2.0 | Widgets modernos para a interface gráfica |

Todas as demais dependências fazem parte da biblioteca padrão do Python (stdlib) e não requerem instalação adicional.

---

## Estrutura do Projeto

```
BackupTool/
├── main.py                  # Entry point e interface gráfica (5 abas)
├── build.py                 # Script de empacotamento via PyInstaller
├── requirements.txt         # Dependências Python
├── README.md
├── config/
│   ├── __init__.py
│   └── defaults.py          # Paths padrão e exclusões por SO
├── core/
│   ├── __init__.py
│   ├── scanner.py           # Varredura recursiva de arquivos
│   ├── backup.py            # Engine de cópia e geração de manifest
│   ├── manifest.py          # Estruturas ManifestEntry/Manifest, SHA-256, extração de usuários
│   ├── restore.py           # Engine de restauração e relatório de restore
│   ├── destinations.py      # Detecção de drives e validação de destino
│   └── report.py            # Geração de relatório de backup (JSON + CSV)
└── logs/                    # Gerado automaticamente; contém relatórios de operações
```

**Estrutura gerada em disco durante o backup:**

```
<destino>/
└── Backup_YYYY-MM-DD_HHMMSS/
    ├── manifest.json
    └── files/
        ├── <hash8>_<nome_original>.ext
        └── ...
```

---

## Requisitos

### Requisitos de sistema

| Item | Windows | Linux |
|---|---|---|
| Sistema operacional | Windows 10 ou superior | Ubuntu 20.04+ / Debian 11+ ou equivalente |
| Privilégios | Administrador local | root ou sudo |
| Python | 3.11 ou superior | 3.11 ou superior |
| Dependências de sistema | Nenhuma adicional | `lsblk` (util-linux, presente por padrão) |

### Requisitos para build do executável

- Python 3.11+
- pip
- Acesso à internet (para instalação de PyInstaller e customtkinter durante o build)

---

## Instalação

### Execução direta (desenvolvimento)

```bash
# Clonar ou copiar o repositório
cd BackupTool

# Instalar dependências
pip install -r requirements.txt

# Executar
python main.py
```

### Execução em ambiente virtual (recomendado)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

---

## Configuração

### Arquivo de configuração principal

**`config/defaults.py`**

Não utiliza arquivos externos de configuração (`.ini`, `.yaml`, `.env`). Os parâmetros são definidos diretamente no módulo e podem ser alterados antes do build.

#### Paths padrão por sistema operacional

**Windows** — derivados de `C:\Users\%USERNAME%\`:

```
Desktop, Documents, Downloads, Pictures, Videos, Music
```

**Linux** — derivados de `/home/$USER/`:

```
Desktop, Documentos, Documents, Downloads, Imagens, Pictures, Vídeos, Videos, Músicas, Music
```

Somente os diretórios que existem em disco são incluídos na lista inicial.

#### Exclusões padrão

**Diretórios excluídos:**

```
node_modules, .git, __pycache__, .cache, Temp, temp, tmp, .tmp,
AppData\Local\Temp, AppData\Local\Microsoft\Windows\INetCache,
AppData\Local\Google\Chrome\User Data\Default\Cache,
.local/share/Trash, .thumbnails, .mozilla/firefox,
dist, build, .next, venv, .venv, env
```

**Extensões excluídas:**

```
.tmp, .temp, .log, .bak, .DS_Store, Thumbs.db
```

### Parâmetros configuráveis em tempo de execução

Todos os parâmetros abaixo podem ser alterados diretamente pela interface antes de iniciar o backup:

- Lista de pastas incluídas no backup (adição e remoção individual)
- Lista de exclusões (editável como texto livre na Aba 1)

---

## Execução

```bash
python main.py
```

A interface abre na Aba 1 (Origem). A navegação entre abas pode ser feita pelos botões "Voltar" e "Próximo" no rodapé, ou clicando diretamente nas abas.

---

## Empacotamento

O script `build.py` automatiza a geração do executável portátil via PyInstaller.

```bash
python build.py
```

**Saída gerada:**

| Sistema operacional | Arquivo |
|---|---|
| Windows | `dist/BackupTool.exe` |
| Linux | `dist/BackupTool` |

**Flags utilizadas no PyInstaller:**

| Flag | Efeito |
|---|---|
| `--onefile` | Gera binário único sem diretório auxiliar |
| `--noconsole` | Suprime a janela de console (modo GUI) |
| `--add-data config:config` | Inclui o pacote `config/` no bundle |
| `--hidden-import=customtkinter` | Força inclusão do módulo não detectado automaticamente |
| `--hidden-import=PIL` | Força inclusão do Pillow (dependência interna do CustomTkinter) |
| `--icon=assets/icon.ico` | Aplica ícone personalizado (Windows, se o arquivo existir) |

O script instala automaticamente `requirements.txt` e `pyinstaller` antes de executar o build.

---

## Funcionalidades

### Varredura de arquivos

**Objetivo**

Percorrer recursivamente os diretórios selecionados, identificar todos os arquivos elegíveis e calcular métricas de tamanho antes do backup.

**Fluxo de Funcionamento**

1. Para cada caminho da lista de origens, executa `os.walk` recursivo
2. A cada diretório encontrado, filtra subdiretórios pela lista de exclusões (in-place, evitando descida desnecessária)
3. Para cada arquivo, verifica exclusão por nome de diretório pai e por extensão
4. Coleta `path`, `size`, `mtime` e `relative_path` via `os.stat`
5. Erros de permissão por arquivo são silenciados individualmente

**Regras de Negócio**

- Diretórios não existentes na lista de origens são silenciosamente ignorados
- A comparação de exclusões é case-insensitive para extensões
- A filtragem de diretórios é feita modificando `dirs[:]` in-place para evitar descida desnecessária
- O caminho relativo é calculado em relação ao diretório pai do path de origem, preservando a estrutura de pastas

**Limitações**

- Não segue symlinks
- Arquivos bloqueados pelo sistema operacional no momento do scan são ignorados sem notificação ao usuário

---

### Backup com geração de manifest

**Objetivo**

Copiar os arquivos varridos para um diretório de backup estruturado, calculando SHA-256 de cada arquivo e registrando os metadados em `manifest.json`.

**Fluxo de Funcionamento**

1. Cria subdiretório `Backup_YYYY-MM-DD_HHMMSS/` no destino selecionado
2. Cria subdiretório `files/` dentro do diretório de backup
3. Para cada arquivo da lista varrida:
   - Calcula SHA-256 antes da cópia
   - Gera nome seguro no formato `<hash8>_<nome_original>` (primeiros 8 caracteres do hash + nome original sanitizado)
   - Copia o arquivo para `files/` usando `shutil.copy2` (preserva metadados de data/hora)
   - Registra entrada no manifest com `source`, `backup`, `size`, `sha256` e `mtime`
4. Ao final, serializa o `manifest.json` na raiz do diretório de backup
5. Gera relatório em `logs/backup_YYYYMMDD_HHMMSS.json` e `.csv`

**Regras de Negócio**

- O SHA-256 é calculado antes da cópia; arquivos onde o hash não pode ser calculado (sem permissão, bloqueados) são registrados como erro e não copiados
- O nome do arquivo no backup é sempre único: o prefixo de hash previne colisões entre arquivos de mesmo nome em diretórios diferentes
- O manifest é gerado somente se ao menos um arquivo foi copiado com sucesso
- A estrutura de backup é criada atomicamente por execução (um novo diretório com timestamp por operação)

**Limitações**

- Não implementa deduplicação entre execuções distintas de backup
- O cálculo de SHA-256 por arquivo aumenta o tempo total de backup em relação a cópias simples
- O backup é sempre completo (não incremental)

---

### Restauração de backup

**Objetivo**

Recuperar arquivos de um backup existente para seus destinos, com verificação de integridade SHA-256 por arquivo e controle de conflitos.

**Fluxo de Funcionamento**

1. Técnico seleciona o diretório de backup (deve conter `manifest.json`)
2. O manifest é carregado e validado
3. Técnico seleciona o modo de restauração e a política de conflito
4. Para cada arquivo a restaurar:
   - Localiza o arquivo em `files/` usando o campo `backup` do manifest
   - Calcula SHA-256 do arquivo armazenado
   - Compara com o hash registrado no manifest; divergência cancela a restauração do arquivo e registra como corrompido
   - Resolve o caminho de destino conforme o modo selecionado
   - Aplica a política de conflito se o destino já existir
   - Copia usando `shutil.copy2`
5. Gera relatório em `logs/restore_YYYYMMDD_HHMMSS.json` e `.csv`

**Modos de restauração:**

| Modo | Comportamento |
|---|---|
| `all` | Restaura todos os arquivos para os caminhos originais registrados no manifest |
| `selection` | Restaura apenas os arquivos cujo `source` corresponde à lista informada |
| `alternate` | Restaura todos os arquivos para um diretório alternativo, preservando apenas o nome do arquivo (sem estrutura de subdiretórios) |

**Políticas de conflito:**

| Política | Comportamento |
|---|---|
| `overwrite` | Substitui o arquivo existente sem confirmação |
| `ask` | Exibe diálogo de confirmação para cada conflito; a thread de restauração aguarda a resposta via `threading.Event` |
| `ignore` | Mantém o arquivo existente; registra como ignorado |

**Regras de Negócio**

- A verificação de integridade SHA-256 é executada sobre o arquivo no backup (não sobre o destino)
- Arquivos corrompidos são registrados individualmente; a operação continua para os demais
- Arquivos ausentes no diretório `files/` (referenciados no manifest mas não encontrados em disco) são registrados como erro
- A criação de diretórios de destino é automática (`os.makedirs(..., exist_ok=True)`)

**Limitações**

- O modo `alternate` não preserva a estrutura de subdiretórios da origem; apenas o nome do arquivo é mantido
- Sem suporte a restauração diferencial (apenas o estado completo registrado no manifest)

---

### Detecção de dispositivos de destino

**Objetivo**

Enumerar automaticamente drives externos e de rede disponíveis para uso como destino de backup.

**Fluxo de Funcionamento**

**Windows:**
1. Obtém o bitmask de drives lógicos via `GetLogicalDrives`
2. Para cada letra com drive presente, chama `GetDriveTypeW`
3. Inclui drives removíveis (tipo 2), fixos (tipo 3) e de rede (tipo 4)
4. Obtém o rótulo via `GetVolumeInformationW`

**Linux:**
1. Executa `lsblk -o NAME,MOUNTPOINT,LABEL,TYPE --noheadings`
2. Filtra entradas com ponto de montagem em `/media` ou `/mnt`

**Regras de Negócio**

- O destino pode ser informado manualmente (campo de texto livre) além da seleção automática
- A validação do destino verifica existência, permissão de escrita e tenta criar o diretório se não existir

---

### Extração de usuários do manifest

**Objetivo**

Identificar os nomes de usuário presentes no manifest a partir dos caminhos dos arquivos, para uso na interface de mapeamento de perfis de domínio AD.

**Fluxo de Funcionamento**

1. Percorre todos os `source` paths do manifest
2. Para Windows: extrai `parts[2]` de paths com `parts[1] == "users"`
3. Para Linux: extrai `parts[2]` de paths com `parts[1] == "home"`
4. Filtra perfis de sistema: `default`, `public`, `all users`, `defaultuser0`, `default user`, `administrator`, `guest`
5. Retorna lista ordenada de nomes únicos

**Regras de Negócio**

- A comparação com perfis de sistema é case-insensitive
- O resultado é utilizado para geração automática do mapeamento de domínio AD (`usuario` → `usuario.SANTACASABA`)

---

### Geração de relatórios

**Objetivo**

Produzir registros auditáveis de cada operação de backup e restauração.

**Relatório de backup (`logs/backup_YYYYMMDD_HHMMSS.json` e `.csv`):**

Campos registrados:

```json
{
  "timestamp": "ISO 8601",
  "technician": "hostname da máquina do técnico",
  "machine": "hostname da máquina backupeada",
  "destination": "caminho do destino",
  "backup_dir": "caminho completo do diretório criado",
  "manifest": "caminho do manifest.json",
  "summary": {
    "total_files_scanned": 0,
    "files_copied": 0,
    "files_skipped": 0,
    "files_with_error": 0,
    "total_size": "legível",
    "total_size_bytes": 0
  },
  "errors": [],
  "files": []
}
```

**Relatório de restauração (`logs/restore_YYYYMMDD_HHMMSS.json` e `.csv`):**

Campos registrados:

```json
{
  "timestamp": "ISO 8601",
  "source_machine": "máquina de origem do backup",
  "backup_date": "data do backup original",
  "elapsed_seconds": 0.0,
  "summary": {
    "restored": 0,
    "skipped": 0,
    "overwritten": 0,
    "corrupted": 0,
    "errors": 0
  },
  "details": [
    {
      "status": "restored|skipped|overwritten|corrupted|error",
      "source": "caminho original",
      "dest": "caminho de destino",
      "reason": "descrição em caso de erro ou conflito"
    }
  ]
}
```

---

## Interface do Usuário

A interface é composta por um cabeçalho fixo, um rodapé de navegação e cinco abas de conteúdo.

### Cabeçalho

Exibe o título da aplicação e o hostname da máquina em execução.

### Rodapé

Botões "Voltar" e "Próximo" para navegação sequencial entre abas.

### Aba 1 — Origem

- Lista scrollável de pastas selecionadas para backup, com botão de remoção individual
- Botão para adicionar pasta via diálogo do sistema operacional
- Campo de texto editável com as exclusões ativas (uma por linha)

### Aba 2 — Destino

- Lista de dispositivos detectados automaticamente com botão "Usar" por item
- Botão para atualizar a lista de dispositivos
- Campo de texto livre para informar caminho manualmente (suporta caminhos UNC do Windows e caminhos Linux)
- Botão "Procurar" para seleção via diálogo

### Aba 3 — Resumo

- Área de texto somente leitura exibindo resultado do scan: total de arquivos, tamanho, pastas incluídas e primeiros 20 arquivos identificados
- Botão "Escanear agora" / "Escanear novamente"
- O scan é executado em thread separada; a UI exibe contagem em tempo real a cada 50 arquivos

### Aba 4 — Progresso (Backup)

- Label com o caminho do arquivo sendo copiado no momento
- Barra de progresso proporcional ao total de arquivos
- Contador `N / Total`
- Log em tempo real (área de texto somente leitura com rolagem automática)
- Botão "Iniciar backup" e botão "Parar" (habilitado durante a execução)
- Status final exibido após conclusão com contadores de copiados e erros

### Aba 5 — Restaurar

- Campo de seleção da pasta de backup com informações do manifest carregado (total de arquivos, tamanho, data, máquina de origem)
- Seleção de modo de restauração via radio buttons: "Restaurar tudo", "Restaurar seleção", "Restaurar para outro local"
- Seleção de política de conflito via radio buttons: "Sobrescrever", "Perguntar", "Ignorar"
- Campo de destino alternativo (visível somente no modo "Restaurar para outro local")
- Lista de checkboxes com pastas raiz do manifest (visível somente no modo "Restaurar seleção")
- Barra de progresso da restauração
- Log em tempo real
- Status final com contadores discriminados (restaurados, sobrescritos, ignorados, corrompidos, erros, tempo decorrido)

---

## Processamento Interno

### Threads

Todas as operações longas são executadas em `threading.Thread(daemon=True)` para evitar bloqueio da interface:

- Scan de arquivos
- Execução do backup
- Execução da restauração

A comunicação entre a thread de trabalho e a thread da UI é feita exclusivamente via `self.after(0, callback)`, padrão seguro para CustomTkinter/Tkinter.

O modo de conflito `ask` na restauração utiliza `threading.Event` para bloquear a thread de trabalho até que o usuário responda ao diálogo exibido na thread da UI.

### Cancelamento de operações

Um flag booleano (`_stop_flag` para backup, `_restore_stop` para restauração) é verificado no início de cada iteração do loop de arquivos. O cancelamento é cooperativo: o arquivo em processamento no momento do clique em "Parar" é concluído antes da interrupção.

### Cálculo de hash

- **SHA-256:** calculado por `hashlib.sha256` em blocos de 64 KB, utilizado para integridade no manifest e verificação pré-restauração
- **MD5:** função `calculate_hash` presente em `scanner.py` mas não utilizada no fluxo principal; disponível para uso futuro

### Manipulação de arquivos

- Cópias realizadas por `shutil.copy2`, que preserva metadados de data de modificação e acesso
- Diretórios de destino criados com `os.makedirs(..., exist_ok=True)`
- Erros de `PermissionError` e `OSError` são capturados individualmente por arquivo

---

## Segurança

### Controle de acesso

A ferramenta não implementa autenticação própria. O controle de acesso é delegado ao sistema operacional: a aplicação deve ser executada com privilégios administrativos para acessar perfis de outros usuários.

### Validações implementadas

- **Destino de backup:** verifica existência, permissão de escrita e tenta criar o diretório antes de iniciar o scan
- **Manifest na restauração:** verifica existência do arquivo `manifest.json` e valida a estrutura JSON antes de prosseguir
- **Integridade de arquivos:** SHA-256 calculado e comparado antes de cada restauração; arquivos com divergência são descartados individualmente
- **Paths de exclusão:** normalizados (barras invertidas/diretas) antes da comparação para evitar falsos negativos cross-platform

### Tratamento de exceções

- `PermissionError` e `OSError` capturados por arquivo em todas as operações de I/O
- `FileNotFoundError` capturado na leitura do manifest com mensagem de erro exibida na interface
- Exceções genéricas capturadas na leitura do manifest para evitar crash da aplicação

---

## Logs e Auditoria

### Localização

```
BackupTool/
└── logs/
    ├── backup_YYYYMMDD_HHMMSS.json
    ├── backup_YYYYMMDD_HHMMSS.csv
    ├── restore_YYYYMMDD_HHMMSS.json
    └── restore_YYYYMMDD_HHMMSS.csv
```

O diretório `logs/` é criado automaticamente na primeira operação e fica no mesmo diretório do executável.

### Eventos monitorados

| Evento | Arquivo |
|---|---|
| Arquivo copiado no backup | `backup_*.json` e `backup_*.csv` |
| Erro de cópia no backup | `backup_*.json` (campo `errors`) |
| Arquivo restaurado | `restore_*.json` e `restore_*.csv` |
| Arquivo ignorado por conflito | `restore_*.json` e `restore_*.csv` |
| Arquivo sobrescrito | `restore_*.json` e `restore_*.csv` |
| Arquivo corrompido (hash divergente) | `restore_*.json` e `restore_*.csv` |
| Arquivo ausente no backup | `restore_*.json` e `restore_*.csv` |

### Diagnóstico

Para identificar arquivos com falha, filtrar o campo `status` nos relatórios JSON:

```json
// Arquivos corrompidos na restauração
{ "status": "corrupted", "reason": "SHA256 divergente: esperado abc123... obtido def456..." }

// Arquivos com erro de permissão
{ "status": "error", "reason": "Sem permissão: [Errno 13] Permission denied: '...'" }
```

---

## Tratamento de Erros

| Situação | Tratamento |
|---|---|
| Arquivo sem permissão de leitura no scan | Silenciado; arquivo não incluído na lista |
| Arquivo sem permissão para cálculo de SHA-256 | Registrado como erro; arquivo não copiado |
| Erro de cópia (`PermissionError`, `OSError`) | Registrado no relatório; operação continua para os demais |
| `manifest.json` não encontrado | Mensagem de erro na interface; restauração bloqueada |
| `manifest.json` com JSON inválido | Exceção capturada; mensagem de erro na interface |
| Arquivo do backup ausente em disco | Registrado como erro no relatório de restauração |
| Hash divergente na restauração | Arquivo marcado como corrompido; não restaurado |
| Destino sem permissão de escrita | Validação pré-operação; mensagem de erro exibida |
| Usuário cancela operação | Flag cooperativo; arquivo em andamento é concluído |

---

## Desempenho e Limitações

### Requisitos mínimos

| Recurso | Mínimo recomendado |
|---|---|
| CPU | Qualquer dual-core |
| RAM | 256 MB disponíveis |
| Disco (executável) | Aproximadamente 30–60 MB (estimativa PyInstaller) |
| Python | 3.11+ (apenas para execução via fonte) |

### Limitações identificadas

- O backup é sempre completo, sem suporte a modo incremental ou diferencial
- O cálculo de SHA-256 durante o backup aumenta o tempo total proporcional ao volume de dados; para volumes acima de dezenas de gigabytes, o tempo pode ser significativo em hardware mais antigo
- O modo `alternate` na restauração não reconstrói a estrutura de subdiretórios
- A detecção de drives no Linux depende de `lsblk`; ambientes sem `util-linux` podem não detectar dispositivos automaticamente
- Não há controle de espaço em disco disponível no destino antes de iniciar o backup
- A interface gráfica não escala para resoluções abaixo de 860x620 pixels

### Boas práticas de utilização

- Executar sempre com privilégios de administrador para garantir acesso a todos os perfis
- Verificar espaço disponível no destino antes de iniciar o backup
- Em ambiente de domínio AD, realizar a restauração antes do primeiro login do usuário para evitar criação de perfil duplicado com sufixo de domínio
- Manter o diretório `logs/` para fins de auditoria após cada operação

---

## Testes

### Estratégia de testes identificada

Não há framework de testes automatizados (pytest, unittest) presente no repositório. Os testes identificados são scripts de validação ad hoc executados diretamente pelo interpretador Python.

### Testes ad hoc identificados

Os seguintes cenários foram validados diretamente via Python durante o desenvolvimento:

| Cenário | Resultado esperado |
|---|---|
| Cálculo de SHA-256 em arquivo real | Hash hexadecimal de 64 caracteres |
| Geração de nome seguro de backup | `<hash8>_<nome_sanitizado>.ext` |
| Round-trip de manifest (save/load) | Desserialização idêntica à serialização |
| Restauração para destino alternativo | `restored == 1`, `errors == 0` |
| Conflito com política `ignore` | `skipped == 1` |
| Detecção de arquivo corrompido | `corrupted == 1`, arquivo não restaurado |
| Geração de relatório JSON e CSV | Arquivos criados em `/tmp` |

### Como executar validações manuais

```bash
cd BackupTool

# Validação de imports e lógica core
python -c "
from core.manifest import make_manifest, save_manifest, load_manifest, sha256_file, _safe_backup_name, ManifestEntry
from core.restore import run_restore, generate_restore_report
from core.backup import run_backup
print('Imports OK')
"
```

---

## Manutenção

### Atualização de dependências

```bash
pip install --upgrade customtkinter
pip freeze > requirements.txt
```

### Adição de novos paths padrão

Editar `config/defaults.py`, nas listas `candidates` de cada sistema operacional. Os paths são incluídos automaticamente apenas se existirem em disco.

### Adição de novas exclusões padrão

Editar `DEFAULT_EXCLUSIONS` ou `DEFAULT_EXCLUDED_EXTENSIONS` em `config/defaults.py`.

### Adição de novo modo de restauração

1. Implementar a lógica de resolução de destino em `core/restore.py`, função `_resolve_dest`
2. Adicionar o novo valor ao parâmetro `mode` de `run_restore`
3. Adicionar o radio button correspondente em `_build_tab_restaurar` em `main.py`
4. Tratar o novo modo em `_start_restore` em `main.py`

### Regeneração do executável

```bash
python build.py
```

O executável deve ser regenerado após qualquer alteração no código-fonte ou nas dependências.

---

## Roadmap

Com base na arquitetura atual, as seguintes evoluções são plausíveis sem necessidade de reescrita estrutural:

| Prioridade | Melhoria |
|---|---|
| Alta | Mapeamento automático de usuários de domínio AD (`usuario` → `usuario.SANTACASABA`) na tela de restauração |
| Alta | Verificação de espaço disponível no destino antes de iniciar o backup |
| Alta | Suporte a backup incremental utilizando o manifest como referência de estado anterior |
| Média | Seleção de múltiplos perfis de usuário na tela de origem (suporte a máquinas compartilhadas) |
| Média | Exportação do relatório diretamente para o destino do backup junto com o manifest |
| Média | Suporte a destino via SSH/SFTP (substituindo dependência de mount do sistema operacional) |
| Baixa | Adição de ícone e metadados de versão no executável Windows |
| Baixa | Framework de testes automatizados (pytest) cobrindo os módulos `core/` |
| Baixa | Modo de linha de comando (CLI) sem dependência de interface gráfica, para uso em scripts de automação |
| Baixa | Histórico de backups: exibição de execuções anteriores na aba de restauração |

---

## Contribuição

### Configuração do ambiente de desenvolvimento

```bash
git clone <repositorio>
cd BackupTool
python -m venv .venv
source .venv/bin/activate  # Linux
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Convenções de código

- Python 3.11+ com type hints em todas as funções públicas
- Módulos de domínio em `core/` não devem importar de `main.py`
- `main.py` não deve conter lógica de domínio; apenas orquestração da UI
- Operações de I/O longas devem ser executadas em `threading.Thread(daemon=True)`
- Comunicação thread → UI exclusivamente via `self.after(0, callback)`
- Erros de arquivo devem ser capturados individualmente sem interromper o loop de processamento

### Checklist para novos módulos em `core/`

- [ ] Módulo independente de CustomTkinter e Tkinter
- [ ] Exceções de I/O tratadas por arquivo
- [ ] Funções públicas com type hints
- [ ] Docstring descrevendo o propósito do módulo

---

## Versionamento

Recomenda-se adotar o padrão **Semantic Versioning (SemVer)** conforme `MAJOR.MINOR.PATCH`:

| Incremento | Quando aplicar |
|---|---|
| `MAJOR` | Quebra de compatibilidade no formato do `manifest.json` ou mudança estrutural na interface |
| `MINOR` | Adição de novo modo de restauração, novo destino suportado ou nova funcionalidade retrocompatível |
| `PATCH` | Correção de bugs, ajuste de exclusões padrão, atualização de dependências |

Versão inicial sugerida: `1.0.0`

---

## Licença

Licença não identificada.

---

## Autor

Não identificado no código-fonte.

---

## Histórico de Versões

| Versão | Data | Alterações |
|---|---|---|
| 1.0.0 | 2026-06 | Versão inicial: backup com manifest, restauração com verificação SHA-256, interface com 5 abas, empacotamento via PyInstaller |

---

## Observações Técnicas

- O campo `technician` nos relatórios de backup é populado com o hostname da máquina onde a ferramenta é executada (`socket.gethostname()`), não com o nome do técnico
- A função `calculate_hash` em `core/scanner.py` utiliza MD5 e está presente no módulo mas não é chamada no fluxo principal; o hash efetivo utilizado é SHA-256 via `core/manifest.py`
- O módulo `core/destinations.py` importa `shutil` implicitamente dentro da função `detect_external_drives` (Windows) sem declaração no topo do arquivo; isso não causa erro em Linux mas pode gerar `NameError` em Windows se `shutil` não estiver no escopo no momento da chamada
- O modo de restauração `domain` está definido na assinatura de `run_restore` com suporte ao parâmetro `user_mapping`, mas a lógica de reescrita de path e a entrada correspondente na interface gráfica ainda não estão implementadas na versão atual
- A verificação de integridade SHA-256 na restauração é executada sobre o arquivo armazenado no backup, não sobre o arquivo de origem original; portanto, detecta corrupção ocorrida após o backup mas não valida a integridade do arquivo original no momento em que foi backupeado
- O formato de nome dos arquivos no backup (`<hash8>_<nome>`) usa apenas os primeiros 8 caracteres do SHA-256 como prefixo; colisões de prefixo são teoricamente possíveis, embora extremamente improváveis em volumes típicos de suporte



 
