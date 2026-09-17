import json
import argparse
import sys
from mapper import map_patient_data

def main():
    parser = argparse.ArgumentParser(description="Map patient data to schema")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")
    
    args = parser.parse_args()

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

    print("Mapping data...")
    output_data = map_patient_data(input_data)

    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"Mapping successful! Output saved to {args.output}")
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
