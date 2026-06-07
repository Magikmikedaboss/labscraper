import json
import sys

def main() -> int:
    try:
        with open("seeds/neural_cells.json", "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        print("Error: seeds/neural_cells.json not found. Run from repository root.")
        return 1
    except json.JSONDecodeError as error:
        print(f"Error: Invalid JSON in neural_cells.json: {error}")
        return 1

    if "neural_cells" not in data:
        print("Error: Expected 'neural_cells' key in JSON data.")
        return 1

    print(f"Total neural cells: {len(data['neural_cells'])}")
    print("\nFirst 10 neural cell terms:")
    for index, cell in enumerate(data["neural_cells"][:10], 1):
        print(f"  {index}. {cell}")

    print("\nSearching for key terms:")
    key_terms = ["neuron", "neurons", "microglia", "astrocyte", "astrocytes"]
    neural_cells_lower = [cell.lower() for cell in data["neural_cells"]]
    for term in key_terms:
        if term.lower() in neural_cells_lower:
            print(f"  ✅ Found: {term}")
        else:
            print(f"  ❌ Missing: {term}")

    return 0


if __name__ == "__main__":
    sys.exit(main())