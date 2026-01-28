# Metrics and Monitoring

Sugestões rápidas de melhoria: 
Ver: adr_transcricao_assincrona_12.md

- Adicionar métricas de fila (latência, taxa de erro) e logs estruturados por correlação para rastrear o fluxo end-to-end.
- Definir thresholds operacionais para beam_size/compute_type por ambiente (dev/test/prod) em settings, com documentação no .env.example.