# Backuptool 🔄

Uma ferramenta profissional e robusta para automatizar backups de arquivos e diretórios em ambientes Python.

## 📋 Descrição

**Backuptool** é uma solução desenvolvida em Python para gerenciar, automatizar e garantir a segurança de seus dados através de backups confiáveis. Ideal para profissionais de DevOps, administradores de sistemas e desenvolvedores que precisam proteger dados críticos.

## ✨ Funcionalidades

- ✅ Backup automatizado de arquivos e diretórios
- ✅ Suporte a múltiplos formatos de armazenamento
- ✅ Agendamento de backups periódicos
- ✅ Compressão de dados para economia de espaço
- ✅ Logs detalhados de operações
- ✅ Recuperação segura de arquivos
- ✅ Verificação de integridade de dados

## 🛠️ Requisitos

- Python 3.7+
- pip (gerenciador de pacotes Python)
- Espaço em disco suficiente para armazenar backups

## 📦 Instalação

### Via Git
```bash
git clone https://github.com/devopsmarcu/Backuptool.git
cd Backuptool
pip install -r requirements.txt
```

### Via pip (quando publicado)
```bash
pip install backuptool
```

## 🚀 Uso Rápido

### Exemplo Básico
```python
from backuptool import Backup

# Criar instância de backup
backup = Backup(source='./dados', destination='./backups')

# Executar backup
backup.run()
```

### Agendamento
```python
from backuptool import ScheduledBackup
from datetime import time

# Agendar backup diário às 2 da manhã
scheduled = ScheduledBackup(
    source='./dados',
    destination='./backups',
    time=time(2, 0)
)

scheduled.start()
```

### Compressão
```python
backup = Backup(
    source='./dados',
    destination='./backups',
    compress=True,
    compression_level=9
)

backup.run()
```

## 📚 Documentação

Para documentação completa, consulte a [Wiki](https://github.com/devopsmarcu/Backuptool/wiki) do projeto.

### Exemplos Avançados
- [Configuração com arquivo YAML](./docs/yaml-config.md)
- [Integração com Cron Jobs](./docs/cron-integration.md)
- [Backup na Nuvem](./docs/cloud-backup.md)
- [Recuperação de Dados](./docs/restore.md)

## 🔐 Segurança

- Suporte a criptografia de backups
- Validação de integridade com checksum
- Logging de todas as operações
- Permissões de arquivo preservadas

**Importante:** Mantenha seus backups em local seguro e faça backup também do local de armazenamento!

## 🐛 Resolução de Problemas

### Backup não inicia
```bash
# Verificar permissões
chmod +x backuptool.py

# Verificar dependências
pip install -r requirements.txt
```

### Espaço em disco insuficiente
- Aumente o espaço disponível
- Configure compressão para reduzir tamanho
- Implemente rotação de backups antigos

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Faça um Fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Diretrizes
- Siga o PEP 8 para estilo de código
- Adicione testes para novas funcionalidades
- Atualize a documentação conforme necessário

## 📝 Licença

Este projeto está licenciado sob a **GNU General Public License v3.0** - veja o arquivo [LICENSE](./LICENSE) para detalhes.

## 👨‍💻 Autor

**devopsmarcu** - [GitHub Profile](https://github.com/devopsmarcu)

## 💬 Suporte

Encontrou um problema? Abra uma [Issue](https://github.com/devopsmarcu/Backuptool/issues) no GitHub!

## 🗺️ Roadmap

- [ ] Interface web
- [ ] Suporte a backup incremental
- [ ] Integração com principais provedores de nuvem
- [ ] Dashboard de monitoramento
- [ ] API REST
- [ ] Suporte a replicação em tempo real

## ⭐ Se você achou útil, deixe uma star!

---

**Última atualização:** Julho 2026
