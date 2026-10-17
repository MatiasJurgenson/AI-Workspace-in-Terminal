## This repo is made for easier testing of ollama/llama.cpp with Goose and OpenCode

# How to run models and agents

## Make the directories:

```
mkdir  -p ~/ollama/data 
mkdir  -p ~/llamacpp/models
```

## Download a guff file
```
curl --fail --location --output models/tinygemma3-Q8_0.gguf https://huggingface.co/ggml-org/tinygemma3-GGUF/resolve/main/tinygemma3-Q8_0.gguf
```

## Compose the models
```
podman-compose up --build --force-recreate --no-cache
```

## Install goose
```
curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash
```
## Goose providers


### Ollama
```
export GOOSE_PROVIDER=ollama
export OLLAMA_HOST=http://localhost:11434
```
### llama.cpp
```
export GOOSE_PROVIDER=openai
export OPENAI_HOST=http://localhost:11433
export OPENAI_BASE_PATH=v1/chat/completions
export OPENAI_API_KEY=not-needed
```

## install OpenCode
```
curl -fsSL https://opencode.ai/v2/install | bash
```
## Copy opencode.json to ~/.config/opencode/opencode.json