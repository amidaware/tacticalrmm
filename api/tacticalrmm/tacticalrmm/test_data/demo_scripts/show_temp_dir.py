import os

temp_dir = "C:\\Windows\\Temp"
files = []
total = 0

with os.scandir(temp_dir) as it:
    for f in it:
        file = {}
        if not f.name.startswith(".") and f.is_file():

            total += 1
            stats = f.stat()

            file["name"] = f.name
            file["size"] = stats.st_size
            file["mtime"] = stats.st_mtime

            files.append(file)

    print(f"Total files: {total}\n")

    for file in files:
        print(file)
