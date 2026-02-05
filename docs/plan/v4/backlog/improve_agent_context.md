# Como popular o feature_id no AgentContext de forma elegante.

```python
        self.agent_context = AgentContext(
            owner_id=ctx_data.get("owner_id"),
            correlation_id=ctx_data.get("correlation_id"),
            feature=ctx_data.get("feature"),
            feature_id=ctx_data.get("feature_id"), # Obrigatorio para popular a tabela ai_result
            msg_id=ctx_data.get("msg_id"),
            user_input=user_input,
            user=ctx_data.get("user"),
            channel=ctx_data.get("channel"),
            memory=ctx_data.get("memory"),
            additional_context=ctx_data.get("context")
            or ctx_data.get("additional_context")
            or "",
        )
```
