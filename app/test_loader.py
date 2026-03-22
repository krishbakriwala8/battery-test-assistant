from data_loader import load_mpt

# Replace 'your_file.mpt' with the actual name of your downloaded file
filename = '../data/sample_logs/SINTEF__NaCR32140-MP10-04__2025-08-25__CCCV_0p02C_25degC__BioLogic__Outlier_Bug.mpt'   

try:
    df = load_mpt(filename)
    print(" Data loaded successfully!")
    print("\nFirst 5 rows:")
    print(df.head())
    print("\nColumn names:")
    print(df.columns.tolist())
    print("\nData types:")
    print(df.dtypes)
except Exception as e:
    print("❌ Error loading data:")
    print(e)