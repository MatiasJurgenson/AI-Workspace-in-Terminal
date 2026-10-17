FROM ghcr.io/ggml-org/llama.cpp:full-rocm

ENV MODEL=tinygemma3-Q8_0.gguf
ENV NGL=99

CMD ["--run", "-m", "/models/tinygemma3-Q8_0.gguf", "-ngl", "99", "--color"]