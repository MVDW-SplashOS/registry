import shutil
import os

source_dir = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "definitions")
)
destination_dir = "/etc/registry/definitions"

try:
    if os.path.exists(destination_dir):
        shutil.rmtree(destination_dir)

    shutil.copytree(source_dir, destination_dir)
    print(f"Successfully copied {source_dir} to {destination_dir}")
except Exception as e:
    print(f"Error copying definitions directory: {e}")
