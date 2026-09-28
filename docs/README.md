# Walkthrough (docs/)

This directory holds the complete lab walkthrough and the code that builds it.

- `Smurf_Fraggle_Lab_Walkthrough.pdf` — the walkthrough. It explains the theory,
  the code, the environment, the setup, the attacks, the defenses, and the
  measured results. It covers every file in the repository.
- `generate_walkthrough.py` — the content of the walkthrough, as blocks.
- `wt_engine.py` — a small PDF rendering engine (built on `fpdf2`).

The prose follows **ASD-STE100 Simplified Technical English**: short sentences,
active voice, present tense, and one idea per sentence. Technical names keep
their exact spelling.

## Rebuild the PDF

Install the one dependency, then run the generator:

```bash
pip install fpdf2
cd docs
python3 generate_walkthrough.py     # writes Smurf_Fraggle_Lab_Walkthrough.pdf
```

The engine embeds the DejaVu fonts from `/usr/share/fonts/truetype/dejavu/`
(and Liberation for the italic face). Install those font packages if a font
path is missing.
