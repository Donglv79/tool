import pandas as pd
import json

xl = pd.ExcelFile('cong thuc mapping.xlsx')
data = ''
for sheet in xl.sheet_names:
    df = pd.read_excel(xl, sheet_name=sheet)
    data += f'# Sheet: {sheet}\n'
    data += df.to_markdown(index=False) + '\n\n'

with open('excel_content.md', 'w', encoding='utf-8') as f:
    f.write(data)
