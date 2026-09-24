with open('dashboard/index.html', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'currentDataset' in line:
            print(f"{i+1}: {line.strip()}")
