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
## Run a lama server for Opencode
```
llama-server   -m ~/llamacpp/models/qwen2.5-14b-instruct-q8_0-00001-of-00004.gguf   --host 127.0.0.1   --port 11433   -c 50000   -ngl 99   --jinja
```

## Install goose
```
curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash
```
## Goose providers/models

```
goose configure
```

Select the correct providor or change it in the config file

## Opencode change models models
```
opencode
```

inside opencode

```
/models
```
