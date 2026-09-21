import json

data = json.load(open('mapping_update.json', encoding='utf-8'))
ai_fields = []
for item in data:
    have_ai = str(item.get('Have AI', '')).strip()
    if have_ai:
        ai_fields.append(f"- {item.get('OUTPUT FIELD')}: {have_ai}")

with open('ai_fields.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(ai_fields))
