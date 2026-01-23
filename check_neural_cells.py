import json

# Load neural cells
with open('seeds/neural_cells.json', 'r') as f:
    data = json.load(f)

print(f"Total neural cells: {len(data['neural_cells'])}")
print("\nFirst 10 neural cell terms:")
for i, cell in enumerate(data['neural_cells'][:10], 1):
    print(f"  {i}. {cell}")

print("\nSearching for key terms:")
key_terms = ['neuron', 'neurons', 'microglia', 'astrocyte', 'astrocytes']
for term in key_terms:
    if term in data['neural_cells']:
        print(f"  ✅ Found: {term}")
    else:
        print(f"  ❌ Missing: {term}")
