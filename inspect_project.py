import os

# Files we want to read content from
ALLOWED_EXTENSIONS = {'.py', '.html', '.css', '.js', '.json', '.txt'}

# Folders we want to completely ignore
IGNORE_FOLDERS = {
    'venv', 'env', '.git', '__pycache__', '.idea', '.vscode',
    'node_modules', 'dist', 'build', 'migrations'
}

# Files we want to ignore (like secrets)
IGNORE_FILES = {
    '.env', '.DS_Store', 'inspect_project.py', 'package-lock.json',
    'poetry.lock', 'yarn.lock'
}


def print_directory_tree(startpath):
    output = []
    output.append(f"PROJECT ROOT: {os.path.abspath(startpath)}\n")
    output.append("=" * 50 + "\n")

    for root, dirs, files in os.walk(startpath):
        # Modify dirs in-place to skip ignored folders
        dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]

        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        output.append(f"{indent}{os.path.basename(root)}/")

        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if f not in IGNORE_FILES:
                output.append(f"{subindent}{f}")

    output.append("\n" + "=" * 50 + "\n")
    return "\n".join(output)


def read_file_contents(startpath):
    output = []
    output.append("FILE CONTENTS:\n")

    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]

        for f in files:
            if f in IGNORE_FILES:
                continue

            ext = os.path.splitext(f)[1]
            if ext in ALLOWED_EXTENSIONS:
                filepath = os.path.join(root, f)
                relpath = os.path.relpath(filepath, startpath)

                output.append(f"\n--- FILE: {relpath} ---")
                try:
                    with open(filepath, 'r', encoding='utf-8') as file_obj:
                        content = file_obj.read()
                        output.append(content)
                except Exception as e:
                    output.append(f"[Error reading file: {e}]")
                output.append("\n" + "-" * 30)

    return "\n".join(output)


if __name__ == "__main__":
    current_dir = os.getcwd()

    print(f"Scanning directory: {current_dir}...")

    tree = print_directory_tree(current_dir)
    contents = read_file_contents(current_dir)

    full_report = tree + "\n" + contents

    output_filename = "project_context.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(full_report)

    print(f"✅ Done! Summary saved to '{output_filename}'")
    print("👉 Please open 'project_context.txt', copy everything, and paste it into the chat.")