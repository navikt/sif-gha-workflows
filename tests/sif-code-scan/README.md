# sif-code-scan tester

## Kjør lokalt

Fra repo-roten:

```sh
python3 -m unittest discover -s tests/sif-code-scan -v
```

## Struktur

- `test_scan.py` — unittest-tester for `scan.py`
- `fixtures/` — ferdiglagde xlsx/docx-filer brukt av testene

## CI

Testene kjøres automatisk ved push/PR til `.github/actions/sif-code-scan/` via workflowen `test-sif-code-scan.yml`.
