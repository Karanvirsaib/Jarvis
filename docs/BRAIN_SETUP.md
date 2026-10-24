# Jarvis model routing

Jarvis's text brain uses OpenRouter's free-model router (`openrouter/free`) first. If that request fails, the adapter tries the configured local Ollama model (`qwen3.5:4b`). OpenRouter may choose a different free model from request to request; this is convenient for experimentation, but can make behavior less consistent. The route and free model availability are controlled by OpenRouter.

## OpenRouter

1. Create an API key in your OpenRouter account dashboard.
2. Copy `.env.example` to `.env` in the Jarvis root and replace the placeholder with the key. `.env` is ignored by Git. Do not put the key in YAML, source code, logs, or chat.
3. The configured route is `openrouter/free`, which uses free variants only. Do not change it to `openrouter/auto` or a paid model if you want to avoid model charges.
4. OpenRouter's current free plan is limited to 50 requests per day and 20 per minute. Autonomous tasks may use multiple requests per task. Check current limits before relying on it.
5. Requests go through OpenRouter to the selected inference provider. Avoid sending personal reference documents, Honcho contents, credentials, or private email through this route unless you have reviewed the providers' data terms and chosen to do so.

## Local fallback

Ollama is installed, but before downloading a model set **Ollama → Settings → Model location** to `D:\Jarvis\data\models`. The current server log still reports Ollama's default model folder under the Windows user profile even though the `OLLAMA_MODELS` user variable is set, so verify the app setting before downloading. This keeps the model files on D:.

Then download the configured fallback model:

```powershell
ollama pull qwen3.5:4b
```

Ollama must be running locally at `http://localhost:11434`. Change the URLs/model in `config/models.yaml` only if using a different local endpoint or model. Jarvis falls back to Ollama when the OpenRouter key is missing or a request fails.

## Current scope

The current Python executive adapter sends text chat requests and returns text. It does not yet implement tool/function calling, autonomous multi-step execution, or the Hermes Agent harness. Those require separate work; model routing alone does not grant Jarvis actions or capabilities.
