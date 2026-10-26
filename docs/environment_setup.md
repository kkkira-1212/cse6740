# Environment Setup

**Python:** 3.11
**Environment Manager:** Conda (Miniforge)

## Setup

```bash
conda env create -f environment.yml
conda activate cse6740
```

## Update

```bash
conda env update -f environment.yml --prune
```

## Verify

```bash
python --version
python -m pip check
python -c "import torch, transformers, peft; print(torch.__version__, transformers.__version__, peft.__version__)"
```

On macOS, check GPU availability with `python -c "import torch; print(torch.backends.mps.is_available())"`.
If this is false, use CPU until MPS works in the terminal running the experiment.

## Dependency Management

- Add new dependencies to `environment.yml`.
- Keep dependencies compatible across macOS, Linux, and Windows.
- Document platform-specific GPU dependencies separately.
- Do not commit local environments, datasets, or model checkpoints.
