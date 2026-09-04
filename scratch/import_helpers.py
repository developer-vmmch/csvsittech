def get_diagnosis_rows(file, filename):
    import csv
    import codecs
    import openpyxl
    
    column_mapping = {
        'code': 'icd_code',
        'title': 'diagnosis_name',
        'classkind': 'class_kind'
    }

    if filename.endswith('.csv'):
        file.seek(0)
        try:
            reader = csv.DictReader(codecs.iterdecode(file, 'utf-8-sig'))
            headers = [h.strip().lower() for h in reader.fieldnames if h]
        except UnicodeDecodeError:
            file.seek(0)
            reader = csv.DictReader(codecs.iterdecode(file, 'cp1252'))
            headers = [h.strip().lower() for h in reader.fieldnames if h]
            
        mapped_headers = [column_mapping.get(h, h) for h in headers]
        reader.fieldnames = mapped_headers
        for i, row in enumerate(reader):
            yield i + 2, row
    elif filename.endswith(('.xlsx', '.xls')):
        wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
        ws = wb.active
        headers = []
        mapped_headers = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                headers = [str(cell).strip().lower() if cell else "" for cell in row]
                mapped_headers = [column_mapping.get(h, h) for h in headers]
            else:
                row_data = {k: (v if v is not None else "") for k, v in zip(mapped_headers, row) if k}
                yield i + 1, row_data

