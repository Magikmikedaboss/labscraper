import json

# Load neural cells
try:
    with open('seeds/neural_cells.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print("Error: seeds/neural_cells.json not found. Run from repository root.")
    exit(1)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON in neural_cells.json: {e}")
    exit(1)

if 'neural_cells' not in data:
    print("Error: Expected 'neural_cells' key in JSON data.")
    exit(1)

print(f"Total neural cells: {len(data['neural_cells'])}")
print("\nFirst 10 neural cell terms:")
for i, cell in enumerate(data['neural_cells'][:10], 1):
    print(f"  {i}. {cell}")

print("\nSearching for key terms:")
key_terms = ['neuron', 'neurons', 'microglia', 'astrocyte', 'astrocytes']
neural_cells_lower = [cell.lower() for cell in data['neural_cells']]
for term in key_terms:
    if term.lower() in neural_cells_lower:
        print(f"  ✅ Found: {term}")
    else:
        print(f"  ❌ Missing: {term}")