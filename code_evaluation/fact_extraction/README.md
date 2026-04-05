# PDF Converter Toolkit

This repository should contain only the code you maintain yourself for running PDF-to-text conversion workflows.

## Keep in the repository

- `convert.py`
- `convert1.py` if you still use it
- `converters/`
- `setup_docker_mirror.sh`
- small handwritten notes or tests that you actually maintain

## Do not upload

- `input_pdfs/`
- `pdf/`
- any `converted_*` directory
- `libs/science-parse-cli.jar`
- `__pycache__/`
- `v2/` if it is copied or derived from another project

## Suggested minimal public repo

If your goal is a clean GitHub repository, keep the project focused on the PDF conversion pipeline and remove any code that exists only to mirror another system.

## Basic usage

```bash
python convert.py -i input_pdfs -c science-parse
python convert.py -i input_pdfs -c grobid
python convert.py -i input_pdfs -c nougat-ocr
python convert.py -i input_pdfs -c llama-index
```
