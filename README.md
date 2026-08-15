# BackupTool

Ferramenta desktop para backup e restauração de perfis de usuário em estações de trabalho Windows e Linux, desenvolvida para suporte técnico em ambientes corporativos.

---

## Visão Geral

O BackupTool foi desenvolvido para uso por técnicos de TI no contexto de formatações de estações de trabalho. A ferramenta automatiza o processo de identificação, cópia e restauração de arquivos de perfis de usuário, eliminando etapas manuais e reduzindo o risco de perda de dados durante procedimentos de reinstalação do sistema operacional.

**Problema resolvido:** em ambientes corporativos com múltiplos usuários por máquina — muitas vezes ingressados em domínio Active Directory — o processo de backup pré-formatação é frequentemente manual, propenso a erros e sem rastreabilidade. O BackupTool padroniza esse processo, gera auditoria completa e viabiliza a restauração controlada posterior, inclusive para máquinas onde o perfil do usuário ainda não existe no Windows.

**Público-alvo:** técnicos de suporte de TI com privilégios administrativos em estações de trabalho Windows e Linux.

---

## Novidades na Versão Atual

- **Migração completa da interface para PySide6/Qt**: a antiga interface CustomTkinter foi substituída por um assistente (wizard) em `ui/`, com tema escuro próprio (`styles/dark_theme.py`) e ícones SVG
- **Backup multiusuário**: seleção de múltiplos perfis detectados na máquina (`core/profiles.py`) em uma única execução, com relatório consolidado por usuário
- **Restauração corporativa (multiusuário) com mapeamento de perfis**: a partir de um backup contendo vários usuários, cada um pode ser restaurado para um usuário de destino diferente (`auto_map_users`, mapeamento manual)
- **Suporte a domínio Active Directory na restauração**: quando o perfil de destino ainda não existe na máquina (ex.: reinstalação limpa ingressada no domínio), o BackupTool chama a API `CreateProfile` do Windows (`core/win_profile.py`) para registrar o perfil corretamente no `ProfileList` do registro antes de copiar os arquivos, evitando o problema clássico de perfis "soltos" fora do SID correto
- **Backup incremental**: disponível na página Backup (opção "Incremental"), compara contra o último backup no destino (detectado automaticamente via `find_latest_backup`, ou selecionado manualmente) e copia apenas arquivos novos/modificados
- **Compressão ZIP opcional**: seletor de nível de compressão (Nenhuma / Padrão / Máxima) na página Backup, aplicado ao final da cópia local
- **Envio remoto via SFTP**: configurável na página Destino (host, porta, usuário, senha ou chave privada, pasta remota, com botão de teste de conexão); quando habilitado, o resultado do backup (ZIP compactado ou a pasta inteira) é enviado automaticamente ao servidor remoto após a conclusão do backup local
- **Verificação de espaço em disco**: `core/destinations.py` valida espaço livre no destino antes da operação
- **Relatórios em HTML, além de JSON/CSV**: `core/report.py` gera relatório navegável em HTML para backups e restaurações
- **Suíte de testes com `pytest`**: `tests/` cobre backup, compressão e manifest
- **Correção de estabilidade**: nomes de pastas de backup agora incluem milissegundos e um sufixo de desempate, evitando colisão de nome ao rodar dois backups em sequência muito rápida (ex.: full seguido de incremental)
- **Correções de UI/polimento visual**: corrigido card de SFTP quebrado (faltava rolagem de página em `destination_page.py`/`backup_page.py`), estado vazio ausente na tabela de usuários, botões "Adicionar Usuário"/"Remover Selecionados" que eram apenas placeholders, cards de Resumo com espaço desproporcional, painel "Etapa X de 6" cortando texto, e substituição dos ícones nativos do SO (que destoavam do tema, parecendo emojis) por um conjunto SVG consistente

---

## Arquitetura da Solução

### Arquitetura identificada

Aplicação desktop monolítica com separação em camadas: interface gráfica em Qt/PySide6 (`main.py` + `ui/`), módulos de domínio (`core/`), configuração (`config/`) e estilos/recursos (`styles/`, `resources/`). Sem servidor, sem banco de dados; a única dependência de rede em tempo de execução é opcional (cliente SFTP, ainda não exposto na UI).

### Componentes principais

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| Entry point | `main.py` | Bootstrap do `QApplication`, fonte global, tema (`Fusion` + QSS escuro) e abertura da `MainWindow` |
| Janela principal | `ui/main_window.py` | Orquestra cabeçalho, stepper e páginas do wizard; não contém regra de negócio |
| Estado compartilhado | `ui/state.py` | `AppState` — dataclass única lida/escrita pelas páginas (origem, usuários, destino, scan, backup, restauração, sessão) |
| Workers assíncronos | `ui/workers.py` | `QThread`s que chamam as funções de `core/` (scan, backup, restore, restore corporativo) fora da thread da UI |
| Páginas do wizard | `ui/pages/*.py` | Usuários, Origem, Destino, Resumo, Backup, Restaurar, Logs, Configurações |
| Stepper | `ui/navigation.py` | Indicador de etapas com navegação livre para etapas já visitadas |
| Scanner | `core/scanner.py` | Varredura recursiva de diretórios com filtragem de exclusões |
| Engine de backup | `core/backup.py` | Cópia de arquivos com SHA-256, backup incremental, compressão opcional, backup multiusuário |
| Manifest | `core/manifest.py` | Serialização/desserialização do `manifest.json`, extração de usuários |
| Engine de restauração | `core/restore.py` | Restauração simples (por manifest único) e restauração corporativa multiusuário com mapeamento e suporte a domínio |
| Perfis de usuário | `core/profiles.py` | Detecção de perfis locais e cálculo do destino de restauração corporativa (`usuario` ou `usuario.DOMINIO`) |
| Perfil Windows/AD | `core/win_profile.py` | Resolução de SID (`LookupAccountNameW`) e criação de perfil via `CreateProfile` (`userenv.dll`) quando o perfil de destino ainda não existe |
| Detecção de destinos | `core/destinations.py` | Enumeração de drives externos, verificação de espaço livre, validação do destino |
| Compressão | `core/compression.py` | Compactação/descompactação ZIP do diretório de backup |
| Cliente SFTP | `core/sftp.py` | Upload/download via SFTP (`paramiko`), criação recursiva de diretórios remotos |
| Relatórios | `core/report.py` | Geração de relatórios de backup/restauração em JSON, CSV e HTML |
| Configuração padrão | `config/defaults.py` | Paths padrão por sistema operacional e listas de exclusão |
| Tema e ícones | `styles/dark_theme.py`, `styles/icons.py`, `styles/svg_icons.py` | QSS do tema escuro e sistema de ícones SVG |

### Fluxo geral de funcionamento

**Backup (único ou multiusuário):**

```
Técnico seleciona um ou mais perfis de usuário (página Usuários)
      ↓
Técnico revisa pastas de origem e exclusões (página Origem)
      ↓
Técnico seleciona destino (página Destino) — espaço livre é validado
      ↓
Sistema escaneia arquivos e exibe resumo por usuário (página Resumo)
      ↓
Técnico confirma e inicia o backup (página Backup)
      ↓
SHA-256 calculado por arquivo → cópia para Backup_YYYY-MM-DD_HHMMSS/files/
  (ou .../usuarios/<usuario>/ quando multiusuário)
      ↓
manifest.json gravado por usuário + relatórios JSON, CSV e HTML gerados em logs/
```

**Restauração simples (um manifest):**

```
Técnico seleciona pasta de backup (página Restaurar)
      ↓
manifest.json carregado e validado
      ↓
Técnico escolhe modo (tudo / seleção / destino alternativo) e política de conflito
      ↓
SHA-256 verificado por arquivo antes da cópia
      ↓
Arquivos restaurados + relatórios JSON e CSV gerados em logs/
```

**Restauração corporativa (multiusuário, com ou sem domínio):**

```
Técnico seleciona a pasta de um backup multiusuário
      ↓
discover_corporate_restore_plans mapeia cada usuário de origem para um
usuário de destino (automático por nome local, ou manual)
      ↓
Para cada plano, se a máquina estiver no Windows:
   tenta CreateProfile(sid, username) via core/win_profile.py
      → perfil não existe:  cria e usa o novo ProfileImagePath
      → perfil já existe:   lê o path já registrado no ProfileList
      → sem privilégio admin ou outro erro: cai para destino heurístico
        (C:\Users\usuario ou C:\Users\usuario.DOMINIO) e registra warning
      ↓
Arquivos restaurados por usuário, com verificação SHA-256 e política de
conflito, reconstruindo o caminho relativo ao perfil original
      ↓
Relatório consolidado (JSON/CSV) por usuário gerado em logs/
```

### Camadas da aplicação

- **Apresentação:** `main.py` + `ui/` — PySide6/Qt, operações longas em `QThread` (`ui/workers.py`), comunicação com a UI via `Signal`/`Slot`
- **Domínio:** `core/` — lógica de negócio isolada da UI, testável independentemente (ver `tests/`)
- **Configuração:** `config/defaults.py` — paths e exclusões padrão derivados do sistema operacional em execução
- **Apresentação visual:** `styles/` — folha de estilo QSS e sistema de ícones SVG, sem lógica de negócio

### Integrações existentes

- **Windows API (ctypes):**
  - Enumeração de drives lógicos via `GetLogicalDrives`/`GetDriveTypeW`, rótulos via `GetVolumeInformationW` (`core/destinations.py`)
  - Resolução de SID via `LookupAccountNameW` e conversão via `ConvertSidToStringSidW` (`core/win_profile.py`)
  - Criação de perfil de usuário via `CreateProfile` (`userenv.dll`) — usada quando o técnico restaura um usuário cujo perfil local ainda não existe, cenário comum logo após o ingresso no domínio (`core/win_profile.py`)
  - Leitura do `ProfileImagePath` já registrado via `winreg` em `SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList` (`core/profiles.py`, `core/win_profile.py`)
- **Linux (subprocess/lsblk):** detecção de dispositivos montados em `/media` e `/mnt`
- **SFTP (paramiko):** cliente pronto em `core/sftp.py` para upload/download remoto; ainda não conectado a nenhuma página da UI
- Sem integrações com bancos de dados ou APIs externas de terceiros

---

## Tecnologias Utilizadas

| Tecnologia | Versão | Finalidade |
|---|---|---|
| Python | 3.11+ | Linguagem principal |
| PySide6 | >= 6.6 | Interface gráfica (Qt for Python) |
| paramiko | >= 3.0.0 | Cliente SFTP para destinos remotos |
| pytest | >= 7.0.0 | Framework de testes automatizados |
| PyInstaller | Não fixada | Empacotamento em executável portátil |
| hashlib | stdlib | Cálculo de SHA-256 |
| shutil | stdlib | Cópia de arquivos preservando metadados, verificação de espaço em disco |
| zipfile | stdlib | Compactação/descompactação do diretório de backup |
| pathlib / ntpath | stdlib | Manipulação de paths cross-platform (incluindo paths Windows processados em Linux) |
| json / csv | stdlib | Serialização de manifests e relatórios |
| dataclasses | stdlib | Estruturas de dados tipadas (`AppState`, `BackupResult`, `RestoreResult`, `CorporateRestorePlan`, etc.) |
| ctypes / winreg | stdlib | Interação com Windows API e registro (drives, SID, `CreateProfile`, `ProfileList`) |
| subprocess | stdlib | Execução de `lsblk` no Linux |

---

## Dependências

| Dependência | Versão mínima | Finalidade |
|---|---|---|
| PySide6 | 6.6 | Interface gráfica |
| paramiko | 3.0.0 | Cliente SFTP |
| pytest | 7.0.0 | Testes automatizados |

Todas as demais dependências fazem parte da biblioteca padrão do Python (stdlib) e não requerem instalação adicional.

---

## Estrutura do Projeto

```
BackupTool/
├── main.py                     # Entry point: bootstrap do QApplication e da MainWindow
├── build.py                    # Script de empacotamento via PyInstaller
├── requirements.txt            # Dependências Python
├── README.md
├── LICENSE                     # GNU GPL v3
├── config/
│   ├── __init__.py
│   └── defaults.py             # Paths padrão e exclusões por SO
├── core/
│   ├── __init__.py
│   ├── scanner.py              # Varredura recursiva de arquivos
│   ├── backup.py               # Engine de backup: cópia, SHA-256, incremental, compressão, multiusuário
│   ├── manifest.py             # Estruturas ManifestEntry/Manifest, SHA-256, extração de usuários
│   ├── restore.py              # Restauração simples e corporativa (multiusuário/domínio)
│   ├── profiles.py             # Detecção de perfis locais e destino de restauração corporativa
│   ├── win_profile.py          # SID lookup + CreateProfile (Windows/AD)
│   ├── destinations.py         # Detecção de drives, espaço em disco, validação de destino
│   ├── compression.py          # Compactação/descompactação ZIP
│   ├── sftp.py                 # Cliente SFTP (paramiko)
│   └── report.py               # Geração de relatórios (JSON, CSV, HTML)
├── ui/
│   ├── main_window.py          # Janela principal, stepper, orquestração das páginas
│   ├── state.py                # AppState — estado compartilhado entre páginas
│   ├── workers.py              # QThreads: Scan, Backup, Restore, CorporateRestore
│   ├── navigation.py           # Stepper horizontal de etapas
│   ├── toolbar.py              # Cabeçalho / seleção de seção (Wizard / Logs / Configurações)
│   ├── statusbar.py            # Barra de status inferior
│   ├── widgets.py              # Componentes reutilizáveis (Card, botões, etc.)
│   ├── os_utils.py             # Utilitários específicos de SO para a UI
│   ├── format_utils.py         # Formatação de tamanhos/datas para exibição
│   └── pages/
│       ├── users_page.py       # Seleção de perfis de usuário (múltipla)
│       ├── source_page.py      # Pastas de origem
│       ├── destination_page.py # Seleção de destino do backup
│       ├── summary_page.py     # Resumo pré-backup
│       ├── backup_page.py      # Execução e progresso do backup
│       ├── restore_page.py     # Restauração simples e corporativa
│       ├── logs_page.py        # Histórico de relatórios gerados
│       └── settings_page.py    # Exclusões, técnico responsável, domínio NetBIOS
├── styles/
│   ├── dark_theme.py           # Folha de estilo QSS
│   ├── icons.py                # Ícones nativos da aplicação (janela, etc.)
│   └── svg_icons.py            # Sistema de ícones SVG
├── resources/
│   ├── icons/
│   └── images/
├── tests/
│   ├── test_backup.py
│   ├── test_compression.py
│   └── test_manifest.py
└── logs/                       # Gerado automaticamente; contém relatórios de operações
```

**Estrutura gerada em disco durante o backup (single-user):**

```
<destino>/
└── Backup_YYYY-MM-DD_HHMMSS/
    ├── manifest.json
    └── files/
        ├── <hash8>_<nome_original>.ext
        └── ...
```

**Estrutura gerada em disco durante o backup multiusuário:**

```
<destino>/
└── Backup_YYYY-MM-DD_HHMMSS/
    └── usuarios/
        ├── <usuario1>/
        │   ├── manifest.json
        │   └── <hash8>_<nome_original>.ext ...
        └── <usuario2>/
            ├── manifest.json
            └── ...
```

---

## Requisitos

### Requisitos de sistema

| Item | Windows | Linux |
|---|---|---|
| Sistema operacional | Windows 10 ou superior | Ubuntu 20.04+ / Debian 11+ ou equivalente |
| Privilégios | Administrador local (obrigatório para `CreateProfile` em restaurações de domínio) | root ou sudo |
| Python | 3.11 ou superior | 3.11 ou superior |
| Dependências de sistema | Nenhuma adicional | `lsblk` (util-linux, presente por padrão) |

### Requisitos para build do executável

- Python 3.11+
- pip
- Acesso à internet (para instalação de PyInstaller, PySide6 e paramiko durante o build)

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

### Restauração com suporte a domínio (Windows + AD)

Para que a criação automática de perfil (`CreateProfile`) funcione durante a restauração corporativa:

1. Executar o BackupTool **como Administrador** na estação de destino
2. A estação de destino deve estar ingressada no mesmo domínio (ou domínio confiável) do usuário de origem, para que `LookupAccountNameW` resolva o SID
3. Na página **Configurações**, preencher o campo **Domínio (NetBIOS)** — deixar vazio para ambientes sem domínio (grupo de trabalho)
4. Se o perfil de destino não puder ser criado (sem privilégio, SID não resolvido, domínio inacessível), o BackupTool cai automaticamente para o destino heurístico (`C:\Users\usuario` ou `C:\Users\usuario.DOMINIO`) e registra um aviso no relatório da operação — a restauração não é interrompida

---

## Uso

A interface é organizada como um assistente (wizard) com seis etapas principais, mais duas seções acessíveis pelo cabeçalho:

| # | Etapa | Descrição |
|---|---|---|
| 1 | Usuários | Escolha de um ou mais perfis locais para backup |
| 2 | Origem | Revisão de pastas padrão, pastas extras e exclusões |
| 3 | Destino | Seleção de onde o backup será salvo (com checagem de espaço livre); configuração opcional de envio remoto via SFTP |
| 4 | Resumo | Conferência de usuários, arquivos, tamanho total e destino |
| 5 | Backup | Execução com progresso em tempo real (por usuário, se multiusuário); opções de tipo (completo/incremental) e compressão; status de envio SFTP quando habilitado |
| 6 | Restaurar | Validação de um backup e restauração — simples ou corporativa/multiusuário |
| — | Configurações | Exclusões aplicadas, técnico responsável, domínio NetBIOS |
| — | Logs | Histórico de relatórios de backup/restauração gerados |

O técnico pode voltar livremente para qualquer etapa já visitada clicando no stepper superior.

---

## Tratamento de Erros

| Cenário | Comportamento |
|---|---|
| Arquivo sem permissão de leitura no scan | Silenciado; arquivo não incluído na lista |
| Arquivo sem permissão para cálculo de SHA-256 | Registrado como erro; arquivo não copiado |
| Erro de cópia (`PermissionError`, `OSError`) | Registrado no relatório; operação continua para os demais |
| `manifest.json` não encontrado | Mensagem de erro na interface; restauração bloqueada |
| `manifest.json` com JSON inválido | Exceção capturada; mensagem de erro na interface |
| Arquivo do backup ausente em disco | Registrado como erro no relatório de restauração |
| Hash divergente na restauração | Arquivo marcado como corrompido; não restaurado |
| Destino sem permissão de escrita | Validação pré-operação; mensagem de erro exibida |
| `CreateProfile` retorna `E_ACCESSDENIED` | Perfil não criado; cai para destino heurístico com warning no relatório |
| `CreateProfile` retorna `ERROR_ALREADY_EXISTS` | Path já registrado é lido do `ProfileList`; restauração segue normalmente |
| SID não resolvido (usuário/domínio inexistente) | `ProfileError`; cai para destino heurístico com warning no relatório |
| Executando fora do Windows ou sem admin | Etapa de `CreateProfile` é pulada silenciosamente; destino heurístico é usado |
| Usuário cancela operação | Flag cooperativo; arquivo em andamento é concluído |

---

## Desempenho e Limitações

### Requisitos mínimos

| Recurso | Mínimo recomendado |
|---|---|
| CPU | Qualquer dual-core |
| RAM | 256 MB disponíveis |
| Disco (executável) | Estimativa maior que a versão CustomTkinter devido ao PySide6/Qt (dezenas de MB a mais) |
| Python | 3.11+ (apenas para execução via fonte) |

### Limitações identificadas

- **`build.py` ainda referencia a stack antiga** (`--hidden-import=customtkinter`) e não foi atualizado para PySide6, e não define `--icon` para o executável Windows (o ícone em `resources/icons/icon.ico` só é aplicado em tempo de execução via `QIcon`, não no `.exe` empacotado)
- O modo `alternate` na restauração simples não reconstrói a estrutura de subdiretórios
- A detecção de drives no Linux depende de `lsblk`; ambientes sem `util-linux` podem não detectar dispositivos automaticamente
- `CreateProfile`/resolução de SID dependem de a estação estar corretamente ingressada no domínio e de o controlador de domínio estar acessível; em cenários offline, a restauração cai para o destino heurístico
- O cliente SFTP (`core/sftp.py`) usa `RejectPolicy` para host keys desconhecidas: se o host de destino não estiver em um arquivo `known_hosts` já confiável na máquina, a conexão falha por segurança. Isso é intencional (evita MITM), mas gera uma mensagem genérica de falha na UI — vale revisar caso o técnico relate "não foi possível conectar" mesmo com credenciais corretas
- O envio via SFTP é sequencial, arquivo por arquivo, sem paralelismo; backups muito grandes podem demorar para transferir

### Boas práticas de utilização

- Executar sempre como Administrador/root para garantir acesso a todos os perfis e, no Windows, permitir a criação de perfil via `CreateProfile`
- Verificar espaço disponível no destino antes de iniciar o backup (a interface já sinaliza isso na etapa Destino)
- Preencher o domínio NetBIOS em Configurações sempre que a máquina de destino estiver ingressada em AD
- Manter o diretório `logs/` para fins de auditoria após cada operação

---

## Testes

### Estratégia de testes identificada

Suíte automatizada com `pytest` em `tests/`, cobrindo os módulos `core/backup.py`, `core/compression.py` e `core/manifest.py`.

### Como executar

```bash
cd BackupTool
pip install -r requirements.txt
pytest
```

### Cobertura atual e lacunas conhecidas

| Módulo | Coberto por teste automatizado? |
|---|---|
| `core/backup.py` | Sim (`tests/test_backup.py`) |
| `core/compression.py` | Sim (`tests/test_compression.py`) |
| `core/manifest.py` | Sim (`tests/test_manifest.py`) |
| `core/restore.py` (restauração simples e corporativa) | Não |
| `core/win_profile.py` (`CreateProfile`, resolução de SID) | Não — depende de Windows/AD real; recomenda-se mock de `ctypes.WinDLL`/`ctypes.windll.userenv` |
| `core/profiles.py`, `core/destinations.py`, `core/sftp.py`, `core/scanner.py` | Não |
| `ui/` (páginas, workers) | Não |

### Cenários validados manualmente

| Cenário | Resultado esperado |
|---|---|
| Cálculo de SHA-256 em arquivo real | Hash hexadecimal de 64 caracteres |
| Geração de nome seguro de backup | `<hash8>_<nome_sanitizado>.ext` |
| Round-trip de manifest (save/load) | Desserialização idêntica à serialização |
| Restauração para destino alternativo | `restored == 1`, `errors == 0` |
| Conflito com política `ignore` | `skipped == 1` |
| Detecção de arquivo corrompido | `corrupted == 1`, arquivo não restaurado |
| Geração de relatório JSON, CSV e HTML | Arquivos criados com sucesso |
| Restauração corporativa sem domínio (grupo de trabalho) | Destino heurístico `C:\Users\usuario`, sem chamada a `CreateProfile` |
| Restauração corporativa com domínio, perfil inexistente | `CreateProfile` cria o perfil; destino passa a ser o `ProfileImagePath` retornado |
| Restauração corporativa com domínio, perfil já existente | `ERROR_ALREADY_EXISTS`; path lido do `ProfileList` |
| Restauração corporativa sem privilégio de Administrador | `ProfileError`; fallback heurístico com warning no relatório |

---

## Manutenção

### Atualização de dependências

```bash
pip install --upgrade PySide6 paramiko pytest
pip freeze > requirements.txt
```

### Adição de novos paths padrão

Editar `config/defaults.py`, nas listas `candidates` de cada sistema operacional. Os paths são incluídos automaticamente apenas se existirem em disco.

### Adição de novas exclusões padrão

Editar `DEFAULT_EXCLUSIONS` ou `DEFAULT_EXCLUDED_EXTENSIONS` em `config/defaults.py`.

### Adição de novo modo de restauração

1. Implementar a lógica de resolução de destino em `core/restore.py` (`_resolve_dest` para restauração simples, ou `_profile_relative_path`/`CorporateRestorePlan` para corporativa)
2. Expor o novo modo/parâmetro no worker correspondente em `ui/workers.py`
3. Adicionar o controle correspondente em `ui/pages/restore_page.py`

### Exposição na UI (concluída)

Backup incremental, compressão ZIP e envio via SFTP já estão disponíveis na interface:

- Backup incremental e nível de compressão: página **Backup**, card "Opções de Backup"
- Envio via SFTP: página **Destino**, card "Envio remoto via SFTP (opcional)"

Os parâmetros escolhidos ficam em `ui/state.py` (`AppState.backup_type`, `previous_backup_dir`, `compression_level`, `sftp_*`) e são repassados por `ui/workers.py` (`BackupWorker`, `SftpTestWorker`, `SftpUploadWorker`) para `core/backup.py` e `core/sftp.py`.

### Correção do `build.py` para PySide6 (pendente)

Substituir `--hidden-import=customtkinter` pelos hidden imports relevantes do PySide6 (tipicamente não são necessários manualmente, mas pode ser preciso `--add-data` para `resources/` e `styles/`) e validar o build em uma máquina limpa antes de distribuir.

### Regeneração do executável

```bash
python build.py
```

O executável deve ser regenerado após qualquer alteração no código-fonte ou nas dependências. **Atenção:** ver limitação acima sobre `build.py` desatualizado.

---

## Roadmap

| Prioridade | Melhoria |
|---|---|
| Alta | Atualizar `build.py` para gerar o executável corretamente com PySide6 |
| Alta | Testes automatizados para `core/restore.py` (simples e corporativa), `core/win_profile.py` e `core/sftp.py` (com mocks de `ctypes`/`paramiko`) |
| Média | Exportação do relatório HTML já gerado para o destino do backup, junto com o manifest |
| Média | Verificação prévia de conectividade com o domínio antes de tentar `CreateProfile`, com aviso antecipado na UI |
| Média | Mensagem de erro mais específica na UI quando a falha de SFTP for por host key desconhecida (hoje cai na mensagem genérica de falha de conexão) |
| Baixa | Adição de ícone e metadados de versão no executável Windows |
| Baixa | Histórico de backups: exibição de execuções anteriores na página Restaurar a partir de `list_backups` |
| Baixa | Reconstrução de subdiretórios no modo `alternate` da restauração simples |
| Baixa | Progresso em bytes (não apenas por arquivo) durante o upload SFTP |

---

## Contribuição

### Configuração do ambiente de desenvolvimento

```bash
git clone https://github.com/seu-usuario/BackupTool.git
cd BackupTool
python -m venv .venv
source .venv/bin/activate  # Linux
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
pytest  # roda a suíte antes de começar a alterar
```

### Convenções de código

- Python 3.11+ com type hints em todas as funções públicas
- Módulos de domínio em `core/` não devem importar de `ui/` nem de `main.py`
- `ui/` não deve conter lógica de negócio; apenas orquestração e apresentação
- Operações de I/O longas devem ser executadas em `QThread` (ver `ui/workers.py`), nunca bloqueando a thread principal
- Comunicação thread → UI exclusivamente via `Signal`/`Slot` do Qt
- Erros de arquivo devem ser capturados individualmente sem interromper o loop de processamento
- Chamadas a Windows API via `ctypes` devem checar `SYSTEM != "Windows"` antes de executar e tratar falhas com exceções de domínio (`ProfileError`), nunca deixando `ctypes` propagar erro cru para a UI

### Checklist para novos módulos em `core/`

- [ ] Módulo independente de PySide6/Qt
- [ ] Exceções de I/O tratadas por arquivo
- [ ] Funções públicas com type hints
- [ ] Docstring descrevendo o propósito do módulo
- [ ] Teste em `tests/` cobrindo o caminho feliz e ao menos um caso de erro

---

## Versionamento

Recomenda-se adotar o padrão **Semantic Versioning (SemVer)** conforme `MAJOR.MINOR.PATCH`:

| Incremento | Quando aplicar |
|---|---|
| `MAJOR` | Quebra de compatibilidade no formato do `manifest.json` ou mudança estrutural na interface |
| `MINOR` | Adição de novo modo de restauração, novo destino suportado ou nova funcionalidade retrocompatível |
| `PATCH` | Correção de bugs, ajuste de exclusões padrão, atualização de dependências |

Versão atual: `2.0.0` (migração da interface para PySide6 e adição de restauração corporativa multiusuário com suporte a domínio — mudanças estruturais em relação à `1.1.0`)

---

## Licença

GNU General Public License v3.0 — ver [`LICENSE`](./LICENSE).

---

## Autor

Desenvolvido para uso em ambientes corporativos. O projeto é distribuído sob a licença GNU GPL v3.0.

---

## Histórico de Versões

| Versão | Data | Alterações |
|---|---|---|
| 2.0.0 | 2026-08 | Migração completa da UI para PySide6; backup e restauração multiusuário; restauração corporativa com mapeamento de perfis e suporte a domínio via `CreateProfile`; verificação de espaço em disco; motores de backup incremental, compressão ZIP e SFTP adicionados a `core/` (ainda não expostos na UI); suíte de testes com `pytest` |
| 1.1.0 | 2026-07 | Interface responsiva completa, DPI awareness moderna, sistema de fontes dinâmicas, layout ultrawide, 6 abas organizadas (CustomTkinter) |
| 1.0.0 | 2026-06 | Versão inicial: backup com manifest, restauração com verificação SHA-256, interface com 5 abas, empacotamento via PyInstaller |

---

## Observações Técnicas

- O campo `technician` nos relatórios de backup é populado por padrão com o hostname da máquina onde a ferramenta é executada (`socket.gethostname()`), mas agora é editável na página Configurações
- A verificação de integridade SHA-256 na restauração é executada sobre o arquivo armazenado no backup, não sobre o arquivo de origem original
- O formato de nome dos arquivos no backup (`<hash8>_<nome>`) usa apenas os primeiros 8 caracteres do SHA-256 como prefixo; colisões de prefixo são teoricamente possíveis, embora extremamente improváveis em volumes típicos
- `core/restore.py` processa paths de origem Windows (`ntpath`) mesmo quando executado em Linux, para permitir inspecionar/restaurar backups feitos em máquinas Windows a partir de uma estação Linux
- A criação de perfil via `CreateProfile` exige privilégio de Administrador local; sem ele, `core/win_profile.py` levanta `ProfileError` antes mesmo de tentar a chamada à API, e a restauração corporativa cai para o destino heurístico sem travar a operação
