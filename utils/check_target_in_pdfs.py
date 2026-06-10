import pdfplumber
from pathlib import Path
import re

def main():
    INPUT_DIR = Path("input_pdfs")
    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    targets_to_check = ['mtor', 'ampk', 'glp-1r', 'glp1r', 'akt', 'pi3k', 'mapk']
    
    print("=" * 60)
    print("CHECKING FOR TARGETS IN PDFs")
    print("=" * 60)
    
    target_found = {target: [] for target in targets_to_check}
    
    for pdf_path in pdfs:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    full_text += text.lower() + " "
                
                for target in targets_to_check:
                    if re.search(r'\b' + re.escape(target) + r'\b', full_text, re.IGNORECASE):
                        target_found[target].append(pdf_path.name)
                        
        except Exception as e:
            print(f"Error reading {pdf_path.name}: {e}")
    
    print("\nResults:")
    print("-" * 60)
    total_found = 0
    
    for target, pdfs_list in target_found.items():
        if pdfs_list:
            print(f"✓ {target.upper()}: Found in {len(pdfs_list)} PDF(s)")
            for pdf in pdfs_list:
                print(f"    - {pdf}")
            total_found += 1
        else:
            print(f"✗ {target.upper()}: Not found in any PDF")
    
    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    print(f"Targets found: {total_found}/{len(targets_to_check)}")
    
    if total_found == 0:
        print("\n❌ NO TARGETS IN THESE PDFs!")
        print("These PDFs are about peptide stability/degradation,")
        print("not about specific molecular targets like MTOR/AMPK.")
        print("\nThis is EXPECTED - the PDFs don't contain target data.")
    else:
        print(f"\n✓ {total_found} targets found in PDFs")
        print("If they're not in the database, they were filtered out")
        print("by the signal detection (no failure/decision/method phrases).")

if __name__ == "__main__":
    main()
