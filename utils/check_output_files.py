import datetime
import sys
from pathlib import Path

def main() -> int:
    output_dir = Path("output")

    if not output_dir.exists() or not output_dir.is_dir():
        print(f"Output directory '{output_dir}' does not exist or is not a directory.")
        print("Please run the scraper first to generate output files.")
        return 1

    files = []

    for file_path in output_dir.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append(
                {
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.datetime.fromtimestamp(stat.st_mtime),
                }
            )

    files.sort(key=lambda item: item["modified"], reverse=True)

    print("\n" + "=" * 80)
    print("OUTPUT FOLDER FILES (sorted by most recent)")
    print("=" * 80)

    for file_info in files:
        size_kb = file_info["size"] / 1024
        print(
            f"{file_info['name']:50s} {file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')} {size_kb:>10.1f} KB"
        )

    print("\n" + "=" * 80)
    print(f"Total files: {len(files)}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
