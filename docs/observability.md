# Observabilidade (OpenTelemetry, Prometheus, Grafana, Zipkin)

Este projeto utiliza **OpenTelemetry** para instrumentação, **Prometheus** para armazenamento de métricas, **Grafana** para visualização e **Zipkin** para rastreamento distribuído.

## Arquitetura

1.  **Aplicação (FastAPI/Worker/Scheduler)**: Instrumentada com OpenTelemetry SDK. Envia traços e métricas via OTLP (gRPC/HTTP) para o Collector.
2.  **OpenTelemetry Collector**: Recebe dados da aplicação, processa e:
    *   Exporta métricas para o Prometheus.
    *   Exporta traces para o Zipkin.
3.  **Prometheus**: Coleta métricas do Collector (scraping).
4.  **Zipkin**: Armazena e visualiza traces distribuídos.
5.  **Grafana**: Consulta o Prometheus e o Zipkin para exibir dashboards unificados.

## Como Executar

### 1. Iniciar a Stack de Observabilidade

Execute o comando abaixo para subir os containers do OTel Collector, Prometheus, Grafana e Zipkin:

```bash
make obs-up
```

Acesse:
- **Grafana**: http://localhost:3000 (Login: `admin` / Senha: `admin`)
- **Prometheus**: http://localhost:9090
- **Zipkin**: http://localhost:9411

### 2. Configurar Variáveis de Ambiente

Certifique-se de que seu `.env` contém as configurações de OTEL (veja `.env.example`):

```env
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=owner-api
OTEL_RESOURCE_ATTRIBUTES=service.name=owner-api,deployment.environment=development
```

> **Nota**: Se você estiver rodando a aplicação via Docker (não localmente), o endpoint deve ser `http://otel-collector:4317`.

### 3. Rodar a Aplicação

Inicie a aplicação normalmente. As métricas serão enviadas automaticamente.

```bash
make run
```

Gere tráfego na API (ex: acesse http://localhost:8000/docs ou faça requisições) para ver os dados aparecerem no Grafana.

## Dashboards

O Grafana já vem provisionado com um dashboard de **Golden Signals** (Latência, Tráfego, Erros, Saturação).

- **P99 Latency**: 99º percentil da latência das requisições.
- **P90 Latency**: 90º percentil.
- **Request Rate**: Total de requisições por segundo/minuto.
- **Error Rate**: Taxa de erros 5xx.

> **Atenção**: As métricas dependem da instrumentação do OpenTelemetry. Se os gráficos estiverem vazios, verifique se o nome da métrica no Prometheus corresponde às queries do Dashboard (ex: `http_server_duration_milliseconds_bucket`).

## Logs indesejáveis:
```
Transient error StatusCode.UNAVAILABLE ... exporting traces to localhost:4317
```
### Causa OpenTelemetry

Como Resolver:
Subir a Stack de Observabilidade (Recomendado)
```bash
make obs-up
```
Silenciar os Logs (Se não quiser rodar containers extras)
Se você não quer usar observabilidade agora e quer apenas limpar o terminal, você pode desativar a exportação de traces definindo a variável de ambiente OTEL_TRACES_EXPORTER como none .

No terminal onde você roda a aplicação:

```
export OTEL_TRACES_EXPORTER=none
make run
```
Ou ajustando seu .env :

```
OTEL_TRACES_EXPORTER=none
```

## Debug

Se as métricas não aparecerem:

1. Verifique os logs do Collector:
   ```bash
   docker logs owner-otel-collector
   ```
2. Verifique se a aplicação está conseguindo conectar no Collector (porta 4317).
3. Acesse o Prometheus e busque por métricas começando com `http_`.
