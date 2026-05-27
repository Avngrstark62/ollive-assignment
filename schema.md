llm_inference_logs (final minimal set)

  • id — unique log id
  • request_started_at — inference start time
  • request_completed_at — inference end time
  • provider — openai, anthropic, etc.
  • model — model name used
  • latency_ms — total latency in ms (can be derived from start/end, but useful to store)
  • status — success / error
  • input_tokens — prompt/input tokens
  • output_tokens — completion/output tokens
  • total_tokens — total tokens
  • input_preview — normalized/truncated preview of model input prompt
  • output_preview — normalized/truncated preview of model output text
  • conversation_id — conversation grouping
  • error_type — normalized error category (nullable)
  • metadata — JSON for provider-specific extras (nullable)
