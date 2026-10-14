from pathlib import Path
import sys

path = Path('backend/app/tools/sec_data_source.py')
if not path.is_file():
    sys.exit('Run this from the Agentic Finance Research repository root.')

text = path.read_text(encoding='utf-8')
old = '            fiscal_year = fact.get("fy")\n            fiscal_period = fact.get("fp")\n'
new = '            fiscal_period = fact.get("fp")\n'
if old not in text:
    if '            fiscal_year = fact.get("fy")\n' not in text:
        print('No unused fiscal_year assignment found; nothing changed.')
        raise SystemExit(0)
    text = text.replace('            fiscal_year = fact.get("fy")\n', '', 1)
else:
    text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
print('Removed the unused fiscal_year assignment from', path)
