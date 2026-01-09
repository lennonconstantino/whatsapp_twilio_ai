### Como Utilizar
O script foi projetado para ser flexível e pode ser executado de duas formas, dependendo da sua infraestrutura:

1. Modo Daemon (Recomendado para Docker/Systemd) :
   Roda continuamente em loop, verificando a cada 60 segundos (padrão).
   
   ```
   python3 src/workers/background_tasks.py
   # Ou com intervalo personalizado (segundos)
   python3 src/workers/background_tasks.py 300
   ```
2. Modo Cron/Scheduler (Recomendado para AWS Lambda/Cronjob) :
   Roda uma única vez e encerra. Ideal para agendadores externos.
   
   ```
   python3 src/workers/background_tasks.py --once
   ```
### Validação
Executei um teste com a flag --once e o sistema processou corretamente:

- Identificou e expirou 1 conversa antiga que estava pendente no banco.
- Logou as operações com sucesso.
Isso remove a responsabilidade de manutenção de estado do Webhook, garantindo respostas rápidas para o Twilio e evitando timeouts na API.