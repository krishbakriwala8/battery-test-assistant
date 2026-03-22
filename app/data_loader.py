import pandas as pd

def load_mpt(filepath):
    """
    Load a Bio-Logic .mpt file into a pandas DataFrame with standardized column names.
    Returns DataFrame with columns: timestamp, voltage, current, temperature.
    """
    # Find the line where column headers start (usually contains 'time/s')
    header_line = None
    with open(filepath, 'r', encoding='latin1') as f:
        for i, line in enumerate(f):
            if 'time/s' in line:
                header_line = i
                break
    if header_line is None:
        raise ValueError("Could not find column headers in .mpt file")

    # Read the file, skipping metadata lines up to the header line
    df = pd.read_csv(filepath, sep='\t', skiprows=header_line, encoding='latin1')

    # Standardize column names (adjust this mapping if your file uses different names)
    column_mapping = {
    'time/s': 'timestamp',
    'Ecell/V': 'voltage',
    'I/mA': 'current',
    'Temperature/ï¿½C': 'temperature'   # use exactly as printed
}

    # Rename only the columns that exist in the file
    for old, new in column_mapping.items():
        if old in df.columns:
            df.rename(columns={old: new}, inplace=True)

    # Check that we have all required columns
    required = ['timestamp', 'voltage', 'current', 'temperature']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns after mapping: {missing}")

    # Convert current from mA to A if values are large (typical for .mpt files)
    if df['current'].abs().max() > 10:  # if current is in mA
        df['current'] = df['current'] / 1000.0

    return df[required]