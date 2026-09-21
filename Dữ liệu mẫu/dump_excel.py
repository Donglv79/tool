import pandas as pd
import json

df = pd.read_excel('c:/Users/NapoleDong/Documents/Vinuni/Thực tập/tool/Dữ liệu mẫu/cong thuc mapping.xlsx')
# drop NaNs and convert to dict
data = df.fillna("").to_dict(orient="records")
with open('c:/Users/NapoleDong/Documents/Vinuni/Thực tập/tool/Dữ liệu mẫu/mapping_rules.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
